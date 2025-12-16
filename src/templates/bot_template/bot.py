#!/usr/bin/env python3
"""
TeleTask Bot - Entry Point
Vietnamese Task Management Telegram Bot

Usage:
    python bot.py

Environment Variables:
    BOT_TOKEN: Telegram bot token from @BotFather
    DATABASE_URL: PostgreSQL connection string
    See .env.example for full configuration
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        *(
            [logging.FileHandler(LOG_FILE)]
            if LOG_FILE
            else []
        ),
    ],
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Post-initialization hook to set bot commands."""
    commands = [
        ("start", "Bắt đầu sử dụng bot"),
        ("help", "Xem hướng dẫn sử dụng"),
        ("taoviec", "Tạo việc cá nhân mới"),
        ("giaoviec", "Giao việc cho người khác"),
        ("vieccanhan", "Xem danh sách việc cá nhân"),
        ("viecdagiao", "Xem việc bạn đã giao"),
        ("xemviec", "Xem chi tiết việc"),
        ("xong", "Đánh dấu việc hoàn thành"),
        ("tiendo", "Cập nhật tiến độ việc"),
        ("xoa", "Xóa việc"),
        ("timviec", "Tìm kiếm việc"),
        ("nhacviec", "Đặt nhắc việc tự động"),
        ("vieclaplai", "Tạo việc lặp lại tự động"),
        ("danhsachvieclaplai", "Xem danh sách việc lặp lại"),
        ("thongke", "Xem thống kê tổng hợp"),
        ("thongketuan", "Xem thống kê tuần này"),
        ("thongkethang", "Xem thống kê tháng này"),
        ("viectrehan", "Xem việc trễ hạn"),
        ("export", "Xuất báo cáo thống kê"),
        ("thongtin", "Xem thông tin tài khoản"),
        ("lichnhatky", "Kết nối Google Calendar"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered")


async def main() -> None:
    """Main entry point for the bot."""
    logger.info("=" * 60)
    logger.info("TeleTask Bot Starting...")
    logger.info("=" * 60)

    # Validate required environment variables
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is required")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable is required")
        sys.exit(1)

    logger.info(f"Bot Name: {os.getenv('BOT_NAME', 'TeleTask')}")
    logger.info(f"Timezone: {os.getenv('TZ', 'UTC')}")
    logger.info(f"Log Level: {LOG_LEVEL}")

    # Initialize database connection
    from database.connection import init_database, close_database
    logger.info("Connecting to database...")
    await init_database(database_url)
    logger.info("Database connected")

    # Build application
    application = (
        Application.builder()
        .token(bot_token)
        .post_init(post_init)
        .build()
    )

    # Register handlers
    from handlers import register_handlers
    register_handlers(application)
    application.add_error_handler(error_handler)
    logger.info("Handlers registered")

    # Initialize reminder scheduler
    from database import get_db
    from scheduler import init_scheduler, reminder_scheduler, init_report_scheduler
    db = get_db()
    init_scheduler(application.bot, db)
    logger.info("Reminder scheduler started")

    # Initialize report scheduler (uses same APScheduler instance)
    init_report_scheduler(reminder_scheduler.scheduler, application.bot, db)
    logger.info("Report scheduler started")

    # Initialize monitoring (optional - only if admin IDs configured)
    health_server = None
    alert_service = None
    resource_monitor = None
    start_time = datetime.now()

    admin_ids_str = os.getenv('ADMIN_IDS', '')
    admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip().isdigit()]

    if admin_ids:
        try:
            from monitoring import HealthCheckServer, AlertService, ResourceMonitor

            # Initialize alert service
            alert_service = AlertService(application.bot, admin_ids)

            # Start health check server
            health_port = int(os.getenv('HEALTH_PORT', 8080))
            health_server = HealthCheckServer(application, db, port=health_port)
            await health_server.start()

            # Start resource monitor
            resource_monitor = ResourceMonitor(db, alert_service, start_time)
            await resource_monitor.start()

            # Store alert service in bot_data for error handler
            application.bot_data['alert_service'] = alert_service

            # Send startup alert
            await alert_service.alert_bot_start()

            logger.info(f"Monitoring started (health port: {health_port}, admins: {len(admin_ids)})")
        except ImportError as e:
            logger.warning(f"Monitoring not available: {e}")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
    else:
        logger.info("Monitoring disabled (no ADMIN_IDS configured)")

    # Start OAuth callback server (for Google Calendar)
    oauth_runner = None
    if os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true":
        try:
            from services.oauth_callback import start_oauth_server
            oauth_runner = await start_oauth_server()
        except Exception as e:
            logger.warning(f"OAuth callback server not started: {e}")

    logger.info("Bot initialization complete")
    logger.info("Starting polling...")

    try:
        # Start polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

        logger.info("Bot is running. Press Ctrl+C to stop.")

        # Keep running until interrupted
        stop_event = asyncio.Event()
        await stop_event.wait()

    except asyncio.CancelledError:
        logger.info("Bot stopping...")
    finally:
        # Cleanup
        logger.info("Shutting down...")

        # Stop monitoring
        if resource_monitor:
            await resource_monitor.stop()
        if health_server:
            await health_server.stop()

        # Stop OAuth server
        if oauth_runner:
            from services.oauth_callback import stop_oauth_server
            await stop_oauth_server(oauth_runner)

        from scheduler import stop_scheduler
        stop_scheduler()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await close_database()
        logger.info("Cleanup complete")


async def error_handler(update, context):
    """Global error handler with monitoring integration."""
    error = context.error
    logger.error(f"Error handling update: {error}", exc_info=error)

    # Record error metric
    try:
        from monitoring.metrics import record_error
        record_error(type(error).__name__)
    except ImportError:
        pass

    # Send alert to admins
    alert_service = context.application.bot_data.get('alert_service')
    if alert_service:
        try:
            await alert_service.alert_bot_crash(error)
        except Exception as e:
            logger.warning(f"Failed to send error alert: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)
