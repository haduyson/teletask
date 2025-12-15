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
        ("thongtin", "Xem thông tin tài khoản"),
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
        from scheduler import stop_scheduler
        stop_scheduler()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await close_database()
        logger.info("Cleanup complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)
