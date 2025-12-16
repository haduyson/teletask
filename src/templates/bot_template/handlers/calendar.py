"""
Google Calendar Handler
Commands for calendar connection and sync
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import get_db
from services import get_or_create_user
from services.calendar_service import (
    is_calendar_enabled,
    get_oauth_url,
    is_user_connected,
    disconnect_calendar,
    get_user_token_data,
    create_calendar_event,
    get_user_reminder_source,
)

logger = logging.getLogger(__name__)


async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /lichgoogle - Show calendar connection status and options.
    """
    user = update.effective_user

    if not is_calendar_enabled():
        await update.message.reply_text(
            "⚠️ Tính năng Google Calendar chưa được kích hoạt.\n\n"
            "Liên hệ admin để cấu hình."
        )
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        connected = await is_user_connected(db, db_user["id"])

        if connected:
            # User is connected
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Đồng bộ tất cả việc", callback_data="cal_sync_all")],
                [InlineKeyboardButton("❌ Ngắt kết nối", callback_data="cal_disconnect")],
            ])

            await update.message.reply_text(
                "📅 GOOGLE CALENDAR\n\n"
                "✅ Đã kết nối Google Calendar!\n\n"
                "Các việc mới sẽ tự động được thêm vào lịch của bạn.\n\n"
                "Tùy chọn:",
                reply_markup=keyboard,
            )
        else:
            # User not connected
            auth_url = get_oauth_url(user.id)

            if auth_url:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Kết nối Google Calendar", url=auth_url)],
                ])

                await update.message.reply_text(
                    "📅 GOOGLE CALENDAR\n\n"
                    "Kết nối Google Calendar để tự động đồng bộ các việc.\n\n"
                    "Bấm nút bên dưới để đăng nhập Google:",
                    reply_markup=keyboard,
                )
            else:
                await update.message.reply_text(
                    "⚠️ Không thể tạo liên kết kết nối.\n"
                    "Vui lòng liên hệ admin."
                )

    except Exception as e:
        logger.error(f"Error in calendar_command: {e}")
        await update.message.reply_text("Lỗi hệ thống. Vui lòng thử lại.")


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle calendar-related callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        if data == "cal_disconnect":
            # Disconnect calendar
            await disconnect_calendar(db, db_user["id"])

            await query.edit_message_text(
                "✅ Đã ngắt kết nối Google Calendar.\n\n"
                "Sử dụng /lichgoogle để kết nối lại."
            )

        elif data == "cal_sync_all":
            # Sync all tasks to calendar
            await query.edit_message_text(
                "🔄 Đang đồng bộ các việc vào Google Calendar...\n\n"
                "Vui lòng đợi..."
            )

            synced = await sync_all_tasks_to_calendar(db, db_user)

            await query.edit_message_text(
                f"✅ Đã đồng bộ {synced} việc vào Google Calendar!\n\n"
                f"Sử dụng /lichgoogle để xem tùy chọn."
            )

    except Exception as e:
        logger.error(f"Error in calendar_callback: {e}")
        await query.edit_message_text("Lỗi hệ thống. Vui lòng thử lại.")


async def sync_all_tasks_to_calendar(db, db_user: dict) -> int:
    """
    Sync all pending tasks with deadline to calendar.

    Args:
        db: Database connection
        db_user: Database user dict

    Returns:
        Number of tasks synced
    """
    try:
        token_data = await get_user_token_data(db, db_user["id"])
        if not token_data:
            return 0

        # Get tasks with deadline that don't have calendar event
        tasks = await db.fetch_all(
            """
            SELECT id, public_id, content, description, deadline, priority
            FROM tasks
            WHERE assignee_id = $1
            AND deadline IS NOT NULL
            AND status != 'completed'
            AND is_deleted = false
            AND google_event_id IS NULL
            ORDER BY deadline ASC
            LIMIT 50
            """,
            db_user["id"]
        )

        synced = 0
        reminder_source = await get_user_reminder_source(db, db_user["id"])
        for task in tasks:
            event_id = await create_calendar_event(
                token_data,
                task["public_id"],
                task["content"],
                task["deadline"],
                task.get("description", ""),
                task.get("priority", "normal"),
                reminder_source,
            )

            if event_id:
                # Save event ID to task
                await db.execute(
                    "UPDATE tasks SET google_event_id = $2 WHERE id = $1",
                    task["id"], event_id
                )
                synced += 1

        logger.info(f"Synced {synced} tasks to calendar for user {db_user['id']}")
        return synced

    except Exception as e:
        logger.error(f"Error syncing tasks to calendar: {e}")
        return 0


async def sync_task_to_calendar(db, task: dict, user_id: int) -> Optional[str]:
    """
    Sync a single task to user's calendar.

    Args:
        db: Database connection
        task: Task dict
        user_id: Database user ID

    Returns:
        Event ID or None
    """
    if not is_calendar_enabled():
        return None

    if not task.get("deadline"):
        return None

    try:
        token_data = await get_user_token_data(db, user_id)
        if not token_data:
            return None

        reminder_source = await get_user_reminder_source(db, user_id)
        event_id = await create_calendar_event(
            token_data,
            task["public_id"],
            task["content"],
            task["deadline"],
            task.get("description", ""),
            task.get("priority", "normal"),
            reminder_source,
        )

        if event_id:
            await db.execute(
                "UPDATE tasks SET google_event_id = $2 WHERE id = $1",
                task["id"], event_id
            )

        return event_id

    except Exception as e:
        logger.error(f"Error syncing task to calendar: {e}")
        return None


def get_handlers() -> list:
    """Return calendar handlers."""
    return [
        CommandHandler("lichgoogle", calendar_command),
        CallbackQueryHandler(calendar_callback, pattern="^cal_"),
    ]
