"""
Settings Handler
User preference configuration: notifications, timezone, defaults
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
)

from database import get_db
from services.user_service import get_or_create_user

logger = logging.getLogger(__name__)

# Conversation states
SETTINGS_MENU = 0

# Priority options
PRIORITY_OPTIONS = {
    "low": "🟢 Thấp",
    "normal": "🟡 Bình thường",
    "high": "🟠 Cao",
    "urgent": "🔴 Khẩn cấp",
}

# Timezone options (Vietnam-centric)
TIMEZONE_OPTIONS = [
    ("Asia/Ho_Chi_Minh", "🇻🇳 Việt Nam (GMT+7)"),
    ("Asia/Bangkok", "🇹🇭 Thái Lan (GMT+7)"),
    ("Asia/Singapore", "🇸🇬 Singapore (GMT+8)"),
    ("Asia/Tokyo", "🇯🇵 Nhật Bản (GMT+9)"),
    ("UTC", "🌍 UTC (GMT+0)"),
]


def settings_menu_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create settings menu keyboard."""
    # Get current values from user record
    reminder_enabled = user_data.get("notify_reminder", True)
    weekly_report = user_data.get("notify_weekly_report", True)
    monthly_report = user_data.get("notify_monthly_report", True)
    timezone = user_data.get("timezone", "Asia/Ho_Chi_Minh")

    # Status icons
    reminder_icon = "✅" if reminder_enabled else "❌"
    weekly_icon = "✅" if weekly_report else "❌"
    monthly_icon = "✅" if monthly_report else "❌"

    # Find timezone display name
    tz_display = timezone
    for tz_code, tz_name in TIMEZONE_OPTIONS:
        if tz_code == timezone:
            tz_display = tz_name.split(" ")[0]  # Just the flag
            break

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"⏰ Nhắc việc: {reminder_icon}",
                callback_data="settings:toggle:notify_reminder"
            ),
        ],
        [
            InlineKeyboardButton(
                f"📊 Báo cáo tuần: {weekly_icon}",
                callback_data="settings:toggle:notify_weekly_report"
            ),
        ],
        [
            InlineKeyboardButton(
                f"📈 Báo cáo tháng: {monthly_icon}",
                callback_data="settings:toggle:notify_monthly_report"
            ),
        ],
        [
            InlineKeyboardButton(
                f"🌏 Múi giờ: {tz_display}",
                callback_data="settings:edit:timezone"
            ),
        ],
        [
            InlineKeyboardButton("❌ Đóng", callback_data="settings:close"),
        ],
    ])


def timezone_keyboard() -> InlineKeyboardMarkup:
    """Create timezone selection keyboard."""
    buttons = []
    for tz_code, tz_name in TIMEZONE_OPTIONS:
        buttons.append([
            InlineKeyboardButton(tz_name, callback_data=f"settings:set:timezone:{tz_code}")
        ])
    buttons.append([
        InlineKeyboardButton("« Quay lại", callback_data="settings:back")
    ])
    return InlineKeyboardMarkup(buttons)


async def get_user_data(db, telegram_id: int) -> dict:
    """Get user data from database."""
    result = await db.fetch_one(
        """SELECT notify_reminder, notify_weekly_report, notify_monthly_report, timezone
           FROM users WHERE telegram_id = $1""",
        telegram_id
    )
    if result:
        return dict(result)
    return {}


async def update_user_setting(db, telegram_id: int, column: str, value) -> None:
    """Update a single user setting in database."""
    # Use parameterized query - column name is from our code, not user input
    await db.execute(
        f"UPDATE users SET {column} = $1 WHERE telegram_id = $2",
        value, telegram_id
    )


async def caidat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /caidat command - show settings menu."""
    user = update.effective_user
    db = get_db()

    # Ensure user exists
    await get_or_create_user(db, user)

    # Get current settings
    user_data = await get_user_data(db, user.id)

    message = (
        "⚙️ <b>Cài đặt</b>\n\n"
        "Tùy chỉnh các thiết lập của bạn:\n\n"
        "• <b>Nhắc việc</b>: Nhận nhắc nhở trước deadline\n"
        "• <b>Báo cáo tuần</b>: Nhận báo cáo tổng kết tuần\n"
        "• <b>Báo cáo tháng</b>: Nhận báo cáo tổng kết tháng\n"
        "• <b>Múi giờ</b>: Thời gian hiển thị deadline"
    )

    await update.message.reply_text(
        message,
        reply_markup=settings_menu_keyboard(user_data),
        parse_mode="HTML"
    )

    return SETTINGS_MENU


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle settings callback buttons."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db = get_db()
    data = query.data

    # Parse callback data
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "close":
        await query.edit_message_text("Đã đóng cài đặt.")
        return ConversationHandler.END

    if action == "back":
        # Return to main settings menu
        user_data = await get_user_data(db, user.id)
        message = (
            "⚙️ <b>Cài đặt</b>\n\n"
            "Tùy chỉnh các thiết lập của bạn:"
        )
        await query.edit_message_text(
            message,
            reply_markup=settings_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    if action == "toggle":
        column = parts[2] if len(parts) > 2 else ""

        # Validate column name (whitelist)
        valid_columns = ["notify_reminder", "notify_weekly_report", "notify_monthly_report"]
        if column not in valid_columns:
            return SETTINGS_MENU

        # Get current value and toggle
        user_data = await get_user_data(db, user.id)
        current = user_data.get(column, True)
        new_value = not current

        await update_user_setting(db, user.id, column, new_value)

        # Update user_data for display
        user_data[column] = new_value

        status = "bật" if new_value else "tắt"
        setting_name = {
            "notify_reminder": "Nhắc việc",
            "notify_weekly_report": "Báo cáo tuần",
            "notify_monthly_report": "Báo cáo tháng",
        }.get(column, column)

        await query.answer(f"Đã {status} {setting_name}")

        # Refresh menu
        message = (
            "⚙️ <b>Cài đặt</b>\n\n"
            "Tùy chỉnh các thiết lập của bạn:"
        )
        await query.edit_message_text(
            message,
            reply_markup=settings_menu_keyboard(user_data),
            parse_mode="HTML"
        )

        return SETTINGS_MENU

    if action == "edit":
        edit_type = parts[2] if len(parts) > 2 else ""

        if edit_type == "timezone":
            await query.edit_message_text(
                "🌏 <b>Chọn múi giờ</b>\n\n"
                "Múi giờ ảnh hưởng đến thời gian hiển thị deadline và nhắc nhở.",
                reply_markup=timezone_keyboard(),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        return SETTINGS_MENU

    if action == "set":
        set_type = parts[2] if len(parts) > 2 else ""
        value = parts[3] if len(parts) > 3 else ""

        if set_type == "timezone" and value:
            # Validate timezone
            valid_timezones = [tz[0] for tz in TIMEZONE_OPTIONS]
            if value not in valid_timezones:
                return SETTINGS_MENU

            await update_user_setting(db, user.id, "timezone", value)

            # Find display name
            tz_display = value
            for tz_code, tz_name in TIMEZONE_OPTIONS:
                if tz_code == value:
                    tz_display = tz_name
                    break

            await query.answer(f"Đã đặt múi giờ: {tz_display}")

        # Return to main menu
        user_data = await get_user_data(db, user.id)
        message = (
            "⚙️ <b>Cài đặt</b>\n\n"
            "Tùy chỉnh các thiết lập của bạn:"
        )
        await query.edit_message_text(
            message,
            reply_markup=settings_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    return SETTINGS_MENU


async def settings_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel settings conversation."""
    await update.message.reply_text("Đã đóng cài đặt.")
    return ConversationHandler.END


def get_handlers():
    """Get settings handlers."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("caidat", caidat_command)],
        states={
            SETTINGS_MENU: [
                CallbackQueryHandler(settings_callback, pattern=r"^settings:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", settings_cancel),
            CommandHandler("huy", settings_cancel),
        ],
        name="settings_conversation",
        persistent=False,
    )

    return [conv_handler]
