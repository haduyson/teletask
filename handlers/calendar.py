"""
Google Calendar Handler
Commands for calendar connection, sync, and settings
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import get_db
from services import get_or_create_user
from utils.db_utils import validate_user_setting_column, InvalidColumnError
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

# Sync mode options
SYNC_OPTIONS = [
    ("auto", "🔄 Tự động khi có thay đổi"),
    ("manual", "👆 Thủ công (bấm đồng bộ)"),
]


def get_sync_display(sync_mode: str) -> str:
    """Get sync mode display name."""
    for code, label in SYNC_OPTIONS:
        if code == sync_mode:
            return label
    return "🔄 Tự động"


async def get_user_calendar_data(db, telegram_id: int) -> dict:
    """Get user calendar settings from database."""
    result = await db.fetch_one(
        """SELECT id, calendar_sync_interval
           FROM users WHERE telegram_id = $1""",
        telegram_id
    )
    if result:
        return dict(result)
    return {}


async def update_user_setting(db, telegram_id: int, column: str, value) -> None:
    """Update a single user setting in database with column validation."""
    try:
        validated_column = validate_user_setting_column(column)
    except InvalidColumnError:
        logger.warning(f"Attempted invalid column update: {column}")
        return

    await db.execute(
        f"UPDATE users SET {validated_column} = $1 WHERE telegram_id = $2",
        value, telegram_id
    )


def calendar_connected_keyboard(sync_mode: str) -> InlineKeyboardMarkup:
    """Create keyboard for connected calendar."""
    sync_display = get_sync_display(sync_mode)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⚙️ Chế độ: {sync_display}", callback_data="cal_edit_sync")],
        [InlineKeyboardButton("📤 Đồng bộ ngay", callback_data="cal_sync_all")],
        [InlineKeyboardButton("❌ Ngắt kết nối", callback_data="cal_disconnect")],
    ])


def sync_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    """Create sync mode selection keyboard."""
    buttons = []
    for code, label in SYNC_OPTIONS:
        prefix = "✅ " if code == current else ""
        buttons.append([
            InlineKeyboardButton(
                f"{prefix}{label}",
                callback_data=f"cal_set_sync:{code}"
            )
        ])
    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="cal_back")])
    return InlineKeyboardMarkup(buttons)


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
            # User is connected - show settings
            user_data = await get_user_calendar_data(db, user.id)
            sync_mode = user_data.get("calendar_sync_interval", "auto")

            await update.message.reply_text(
                "📅 <b>GOOGLE CALENDAR</b>\n\n"
                "✅ Đã kết nối Google Calendar!\n\n"
                "Các việc mới sẽ tự động được thêm vào lịch của bạn.",
                reply_markup=calendar_connected_keyboard(sync_mode),
                parse_mode="HTML",
            )
        else:
            # User not connected
            auth_url = get_oauth_url(user.id)

            if auth_url:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Kết nối Google Calendar", url=auth_url)],
                ])

                await update.message.reply_text(
                    "📅 <b>GOOGLE CALENDAR</b>\n\n"
                    "Kết nối Google Calendar để tự động đồng bộ các việc.\n\n"
                    "Bấm nút bên dưới để đăng nhập Google:",
                    reply_markup=keyboard,
                    parse_mode="HTML",
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

        # ---- DISCONNECT ----
        if data == "cal_disconnect":
            await disconnect_calendar(db, db_user["id"])

            await query.edit_message_text(
                "✅ Đã ngắt kết nối Google Calendar.\n\n"
                "Sử dụng /lichgoogle để kết nối lại."
            )

        # ---- SYNC ALL ----
        elif data == "cal_sync_all":
            await query.edit_message_text(
                "🔄 Đang đồng bộ các việc vào Google Calendar...\n\n"
                "Vui lòng đợi..."
            )

            synced = await sync_all_tasks_to_calendar(db, db_user)

            user_data = await get_user_calendar_data(db, user.id)
            sync_mode = user_data.get("calendar_sync_interval", "auto")

            await query.edit_message_text(
                f"📅 <b>GOOGLE CALENDAR</b>\n\n"
                f"✅ Đã đồng bộ {synced} việc vào lịch!",
                reply_markup=calendar_connected_keyboard(sync_mode),
                parse_mode="HTML",
            )

        # ---- EDIT SYNC MODE ----
        elif data == "cal_edit_sync":
            user_data = await get_user_calendar_data(db, user.id)
            current_mode = user_data.get("calendar_sync_interval", "auto")

            await query.edit_message_text(
                "⚙️ <b>CHẾ ĐỘ ĐỒNG BỘ</b>\n\n"
                "Chọn cách đồng bộ với Google Calendar:",
                reply_markup=sync_mode_keyboard(current_mode),
                parse_mode="HTML",
            )

        # ---- SET SYNC MODE ----
        elif data.startswith("cal_set_sync:"):
            value = data.split(":")[1]
            valid_modes = [m[0] for m in SYNC_OPTIONS]
            if value not in valid_modes:
                return

            await update_user_setting(db, user.id, "calendar_sync_interval", value)
            mode_display = get_sync_display(value)
            await query.answer(f"✅ {mode_display}")

            # Return to main calendar menu
            await query.edit_message_text(
                "📅 <b>GOOGLE CALENDAR</b>\n\n"
                "✅ Đã kết nối Google Calendar!\n\n"
                "Các việc mới sẽ tự động được thêm vào lịch của bạn.",
                reply_markup=calendar_connected_keyboard(value),
                parse_mode="HTML",
            )

        # ---- BACK TO MAIN ----
        elif data == "cal_back":
            user_data = await get_user_calendar_data(db, user.id)
            sync_mode = user_data.get("calendar_sync_interval", "auto")

            await query.edit_message_text(
                "📅 <b>GOOGLE CALENDAR</b>\n\n"
                "✅ Đã kết nối Google Calendar!\n\n"
                "Các việc mới sẽ tự động được thêm vào lịch của bạn.",
                reply_markup=calendar_connected_keyboard(sync_mode),
                parse_mode="HTML",
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
