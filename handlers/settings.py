"""
Settings Handler
User preference configuration: notifications, timezone, reminder settings
Organized with submenus for better UX
"""

import warnings
warnings.filterwarnings("ignore", message=".*per_message.*", category=UserWarning)

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
from utils.db_utils import validate_user_setting_column, InvalidColumnError

logger = logging.getLogger(__name__)

# Conversation states
SETTINGS_MENU = 0

# Timezone options (Vietnam-centric)
TIMEZONE_OPTIONS = [
    ("Asia/Ho_Chi_Minh", "🇻🇳 Việt Nam (GMT+7)"),
    ("Asia/Bangkok", "🇹🇭 Thái Lan (GMT+7)"),
    ("Asia/Singapore", "🇸🇬 Singapore (GMT+8)"),
    ("Asia/Tokyo", "🇯🇵 Nhật Bản (GMT+9)"),
    ("UTC", "🌍 UTC (GMT+0)"),
]

# Reminder time options
REMINDER_OPTIONS = [
    ("remind_24h", "24h trước"),
    ("remind_1h", "1h trước"),
    ("remind_30m", "30 phút trước"),
    ("remind_5m", "5 phút trước"),
    ("remind_overdue", "Quá hạn"),
]

# Reminder source options
REMINDER_SOURCE_OPTIONS = [
    ("telegram", "✈️ Telegram"),
    ("google_calendar", "📅 Google Calendar"),
    ("both", "✈️ + 📅 Cả hai"),
]


def on_off_button(label: str, is_on: bool, callback: str) -> InlineKeyboardButton:
    """Create a button with clear ON/OFF status."""
    status = "🟢" if is_on else "🔴"
    return InlineKeyboardButton(f"{status} {label}", callback_data=callback)


def get_tz_display(timezone: str) -> str:
    """Get timezone display name."""
    for tz_code, tz_name in TIMEZONE_OPTIONS:
        if tz_code == timezone:
            return tz_name
    return timezone


def get_source_display(source: str) -> str:
    """Get reminder source display name."""
    for src_code, src_label in REMINDER_SOURCE_OPTIONS:
        if src_code == source:
            return src_label
    return "✈️ + 📅 Cả hai"


# ============================================
# MAIN MENU - 2 categories (notifications, timezone)
# ============================================

def main_menu_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create main settings menu with 2 categories."""
    timezone = user_data.get("timezone", "Asia/Ho_Chi_Minh")
    tz_short = "GMT+7" if "Ho_Chi_Minh" in timezone or "Bangkok" in timezone else timezone[:10]

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Thông báo »", callback_data="settings:notifications")],
        [InlineKeyboardButton(f"🌏 Múi giờ: {tz_short}", callback_data="settings:edit:timezone")],
        [InlineKeyboardButton("❌ Đóng", callback_data="settings:close")],
    ])


# ============================================
# NOTIFICATIONS SUBMENU
# ============================================

def notifications_menu_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create notifications submenu."""
    notify_task_assigned = user_data.get("notify_task_assigned", True)
    notify_task_status = user_data.get("notify_task_status", True)
    weekly_report = user_data.get("notify_weekly_report", True)
    monthly_report = user_data.get("notify_monthly_report", True)

    return InlineKeyboardMarkup([
        [on_off_button("Giao việc mới", notify_task_assigned, "settings:toggle:notify_task_assigned")],
        [on_off_button("Trạng thái việc", notify_task_status, "settings:toggle:notify_task_status")],
        [InlineKeyboardButton("⏰ Nhắc việc »", callback_data="settings:reminders")],
        [on_off_button("Báo cáo tuần", weekly_report, "settings:toggle:notify_weekly_report")],
        [on_off_button("Báo cáo tháng", monthly_report, "settings:toggle:notify_monthly_report")],
        [InlineKeyboardButton("« Quay lại", callback_data="settings:back")],
    ])


# ============================================
# REMINDER SETTINGS SUBMENU
# ============================================

def reminders_menu_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create reminder settings submenu."""
    reminder_source = user_data.get("reminder_source", "both")
    source_display = get_source_display(reminder_source)

    buttons = [
        [InlineKeyboardButton(f"🔔 Nguồn: {source_display}", callback_data="settings:edit:reminder_source")],
    ]

    for column, label in REMINDER_OPTIONS:
        is_on = user_data.get(column, True)
        buttons.append([on_off_button(label, is_on, f"settings:toggle:{column}")])

    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="settings:notifications")])

    return InlineKeyboardMarkup(buttons)


def reminder_source_keyboard(current: str) -> InlineKeyboardMarkup:
    """Create reminder source selection keyboard."""
    buttons = []
    for source_code, source_label in REMINDER_SOURCE_OPTIONS:
        prefix = "✅ " if source_code == current else ""
        buttons.append([
            InlineKeyboardButton(
                f"{prefix}{source_label}",
                callback_data=f"settings:set:reminder_source:{source_code}"
            )
        ])
    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="settings:reminders")])
    return InlineKeyboardMarkup(buttons)


# ============================================
# TIMEZONE SELECTION
# ============================================

def timezone_keyboard() -> InlineKeyboardMarkup:
    """Create timezone selection keyboard."""
    buttons = []
    for tz_code, tz_name in TIMEZONE_OPTIONS:
        buttons.append([
            InlineKeyboardButton(tz_name, callback_data=f"settings:set:timezone:{tz_code}")
        ])
    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="settings:back")])
    return InlineKeyboardMarkup(buttons)


# ============================================
# DATABASE HELPERS
# ============================================

async def get_user_data(db, telegram_id: int) -> dict:
    """Get user data from database."""
    result = await db.fetch_one(
        """SELECT id, notify_reminder, notify_weekly_report, notify_monthly_report, timezone,
                  remind_24h, remind_1h, remind_30m, remind_5m, remind_overdue,
                  reminder_source, notify_task_assigned, notify_task_status
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


# ============================================
# COMMAND HANDLERS
# ============================================

async def caidat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /caidat command - show settings menu."""
    user = update.effective_user
    db = get_db()

    await get_or_create_user(db, user)
    user_data = await get_user_data(db, user.id)

    message = (
        "⚙️ <b>CÀI ĐẶT</b>\n\n"
        "Chọn mục cần thiết lập:"
    )

    await update.message.reply_text(
        message,
        reply_markup=main_menu_keyboard(user_data),
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

    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    # ---- CLOSE ----
    if action == "close":
        await query.edit_message_text("✅ Đã lưu cài đặt.")
        return ConversationHandler.END

    # ---- BACK TO MAIN ----
    if action == "back":
        user_data = await get_user_data(db, user.id)
        await query.edit_message_text(
            "⚙️ <b>CÀI ĐẶT</b>\n\nChọn mục cần thiết lập:",
            reply_markup=main_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    # ---- NOTIFICATIONS SUBMENU ----
    if action == "notifications":
        user_data = await get_user_data(db, user.id)
        await query.edit_message_text(
            "🔔 <b>THÔNG BÁO</b>\n\n"
            "Cài đặt các loại thông báo:\n\n"
            "<i>🟢 Bật | 🔴 Tắt</i>",
            reply_markup=notifications_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    # ---- REMINDERS SUBMENU ----
    if action == "reminders":
        user_data = await get_user_data(db, user.id)
        await query.edit_message_text(
            "⏰ <b>NHẮC VIỆC</b>\n\n"
            "Cài đặt nguồn và thời điểm nhắc:\n\n"
            "<i>🟢 Bật | 🔴 Tắt</i>",
            reply_markup=reminders_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    # ---- TOGGLE SETTINGS ----
    if action == "toggle":
        column = parts[2] if len(parts) > 2 else ""

        valid_columns = [
            "notify_reminder", "notify_weekly_report", "notify_monthly_report",
            "remind_24h", "remind_1h", "remind_30m", "remind_5m", "remind_overdue",
            "notify_task_assigned", "notify_task_status"
        ]
        if column not in valid_columns:
            return SETTINGS_MENU

        user_data = await get_user_data(db, user.id)
        current = user_data.get(column, True)
        new_value = not current

        await update_user_setting(db, user.id, column, new_value)
        user_data[column] = new_value

        status = "🟢 BẬT" if new_value else "🔴 TẮT"
        setting_names = {
            "notify_reminder": "Nhắc việc",
            "notify_weekly_report": "Báo cáo tuần",
            "notify_monthly_report": "Báo cáo tháng",
            "remind_24h": "Nhắc 24h",
            "remind_1h": "Nhắc 1h",
            "remind_30m": "Nhắc 30p",
            "remind_5m": "Nhắc 5p",
            "remind_overdue": "Nhắc quá hạn",
            "notify_task_assigned": "Giao việc mới",
            "notify_task_status": "Trạng thái việc",
        }
        setting_name = setting_names.get(column, column)
        await query.answer(f"{setting_name}: {status}")

        # Determine which menu to return to
        if column.startswith("remind_"):
            # Reminder submenu
            await query.edit_message_text(
                "⏰ <b>NHẮC VIỆC</b>\n\n"
                "Cài đặt nguồn và thời điểm nhắc:\n\n"
                "<i>🟢 Bật | 🔴 Tắt</i>",
                reply_markup=reminders_menu_keyboard(user_data),
                parse_mode="HTML"
            )
        else:
            # Notifications submenu
            await query.edit_message_text(
                "🔔 <b>THÔNG BÁO</b>\n\n"
                "Cài đặt các loại thông báo:\n\n"
                "<i>🟢 Bật | 🔴 Tắt</i>",
                reply_markup=notifications_menu_keyboard(user_data),
                parse_mode="HTML"
            )

        return SETTINGS_MENU

    # ---- EDIT SELECTIONS ----
    if action == "edit":
        edit_type = parts[2] if len(parts) > 2 else ""

        if edit_type == "timezone":
            await query.edit_message_text(
                "🌏 <b>MÚI GIỜ</b>\n\n"
                "Chọn múi giờ của bạn:",
                reply_markup=timezone_keyboard(),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        if edit_type == "reminder_source":
            user_data = await get_user_data(db, user.id)
            current_source = user_data.get("reminder_source", "both")
            await query.edit_message_text(
                "🔔 <b>NGUỒN NHẮC VIỆC</b>\n\n"
                "Chọn nơi nhận nhắc nhở:",
                reply_markup=reminder_source_keyboard(current_source),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        return SETTINGS_MENU

    # ---- SET VALUES ----
    if action == "set":
        set_type = parts[2] if len(parts) > 2 else ""
        value = parts[3] if len(parts) > 3 else ""

        if set_type == "timezone" and value:
            valid_timezones = [tz[0] for tz in TIMEZONE_OPTIONS]
            if value not in valid_timezones:
                return SETTINGS_MENU

            await update_user_setting(db, user.id, "timezone", value)
            tz_display = get_tz_display(value)
            await query.answer(f"✅ {tz_display}")

            # Return to main menu
            user_data = await get_user_data(db, user.id)
            await query.edit_message_text(
                "⚙️ <b>CÀI ĐẶT</b>\n\nChọn mục cần thiết lập:",
                reply_markup=main_menu_keyboard(user_data),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        if set_type == "reminder_source" and value:
            valid_sources = [src[0] for src in REMINDER_SOURCE_OPTIONS]
            if value not in valid_sources:
                return SETTINGS_MENU

            await update_user_setting(db, user.id, "reminder_source", value)
            source_display = get_source_display(value)
            await query.answer(f"✅ {source_display}")

            # Return to reminders menu
            user_data = await get_user_data(db, user.id)
            await query.edit_message_text(
                "⏰ <b>NHẮC VIỆC</b>\n\n"
                "Cài đặt nguồn và thời điểm nhắc:\n\n"
                "<i>🟢 Bật | 🔴 Tắt</i>",
                reply_markup=reminders_menu_keyboard(user_data),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        return SETTINGS_MENU

    return SETTINGS_MENU


async def settings_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel settings conversation."""
    await update.message.reply_text("✅ Đã lưu cài đặt.")
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
        per_message=False,
    )

    return [conv_handler]
