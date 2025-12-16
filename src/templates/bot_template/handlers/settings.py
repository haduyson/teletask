"""
Settings Handler
User preference configuration: notifications, timezone, reminder settings
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
    ("remind_24h", "24 giờ trước"),
    ("remind_1h", "1 giờ trước"),
    ("remind_30m", "30 phút trước"),
    ("remind_5m", "5 phút trước"),
    ("remind_overdue", "Khi quá hạn"),
]

# Reminder source options (✈️ Telegram icon, 📅 Google Calendar icon)
REMINDER_SOURCE_OPTIONS = [
    ("telegram", "✈️ Telegram", "Bot nhắc qua Telegram"),
    ("google_calendar", "📅 Google Calendar", "Google Calendar tự nhắc"),
    ("both", "✈️ Telegram + 📅 Google", "Telegram và Google Calendar"),
]

# Calendar sync interval options
SYNC_INTERVAL_OPTIONS = [
    ("24h", "🔄 Mỗi 24 giờ"),
    ("12h", "🔄 Mỗi 12 giờ"),
    ("weekly", "🔄 Mỗi tuần"),
    ("manual", "👆 Thủ công"),
]


def on_off_button(label: str, is_on: bool, callback: str) -> InlineKeyboardButton:
    """Create a button with clear ON/OFF status."""
    status = "🟢 BẬT" if is_on else "🔴 TẮT"
    return InlineKeyboardButton(f"{label}: {status}", callback_data=callback)


def settings_menu_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create main settings menu keyboard."""
    # Get current values
    weekly_report = user_data.get("notify_weekly_report", True)
    monthly_report = user_data.get("notify_monthly_report", True)
    timezone = user_data.get("timezone", "Asia/Ho_Chi_Minh")
    reminder_source = user_data.get("reminder_source", "both")

    # Find timezone display name
    tz_display = timezone
    for tz_code, tz_name in TIMEZONE_OPTIONS:
        if tz_code == timezone:
            tz_display = tz_name
            break

    # Find reminder source display name
    source_display = "✈️ Telegram + 📅 Google"
    for src_code, src_label, _desc in REMINDER_SOURCE_OPTIONS:
        if src_code == reminder_source:
            source_display = src_label
            break

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏰ Cài đặt nhắc việc »", callback_data="settings:reminders")],
        [InlineKeyboardButton(f"🔔 {source_display}", callback_data="settings:edit:reminder_source")],
        [InlineKeyboardButton("📅 Cài đặt đồng bộ Google Calendar »", callback_data="settings:gcal")],
        [on_off_button("📊 Báo cáo tuần", weekly_report, "settings:toggle:notify_weekly_report")],
        [on_off_button("📈 Báo cáo tháng", monthly_report, "settings:toggle:notify_monthly_report")],
        [InlineKeyboardButton(f"🌏 Múi giờ: {tz_display}", callback_data="settings:edit:timezone")],
        [InlineKeyboardButton("❌ Đóng", callback_data="settings:close")],
    ])


def reminders_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create reminder settings keyboard with ON/OFF for each time."""
    buttons = []

    for column, label in REMINDER_OPTIONS:
        is_on = user_data.get(column, True)
        buttons.append([on_off_button(f"⏰ {label}", is_on, f"settings:toggle:{column}")])

    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="settings:back")])

    return InlineKeyboardMarkup(buttons)


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


def reminder_source_keyboard(current: str) -> InlineKeyboardMarkup:
    """Create reminder source selection keyboard."""
    buttons = []
    for source_code, source_label, _desc in REMINDER_SOURCE_OPTIONS:
        # Add checkmark to current selection
        prefix = "✅ " if source_code == current else ""
        buttons.append([
            InlineKeyboardButton(
                f"{prefix}{source_label}",
                callback_data=f"settings:set:reminder_source:{source_code}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("« Quay lại", callback_data="settings:back")
    ])
    return InlineKeyboardMarkup(buttons)


def gcal_settings_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """Create Google Calendar settings keyboard."""
    sync_interval = user_data.get("calendar_sync_interval", "manual")

    # Find current sync interval display
    interval_display = "👆 Thủ công"
    for interval_code, interval_label in SYNC_INTERVAL_OPTIONS:
        if interval_code == sync_interval:
            interval_display = interval_label
            break

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏱️ Chọn thời gian: {interval_display}", callback_data="settings:edit:sync_interval")],
        [InlineKeyboardButton("🔄 Đồng bộ ngay", callback_data="settings:action:sync_now")],
        [InlineKeyboardButton("« Quay lại", callback_data="settings:back")],
    ])


def sync_interval_keyboard(current: str) -> InlineKeyboardMarkup:
    """Create sync interval selection keyboard."""
    buttons = []
    for interval_code, interval_label in SYNC_INTERVAL_OPTIONS:
        prefix = "✅ " if interval_code == current else ""
        buttons.append([
            InlineKeyboardButton(
                f"{prefix}{interval_label}",
                callback_data=f"settings:set:sync_interval:{interval_code}"
            )
        ])
    buttons.append([
        InlineKeyboardButton("« Quay lại", callback_data="settings:gcal")
    ])
    return InlineKeyboardMarkup(buttons)


async def get_user_data(db, telegram_id: int) -> dict:
    """Get user data from database."""
    result = await db.fetch_one(
        """SELECT id, notify_reminder, notify_weekly_report, notify_monthly_report, timezone,
                  remind_24h, remind_1h, remind_30m, remind_5m, remind_overdue,
                  reminder_source, calendar_sync_interval
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
        "⚙️ <b>CÀI ĐẶT</b>\n\n"
        "Tùy chỉnh các thiết lập của bạn:\n\n"
        "• <b>Nhắc việc</b>: Chọn thời điểm nhận nhắc nhở\n"
        "• <b>Báo cáo</b>: Bật/tắt báo cáo tự động\n"
        "• <b>Múi giờ</b>: Thời gian hiển thị deadline\n\n"
        "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
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
            "⚙️ <b>CÀI ĐẶT</b>\n\n"
            "Tùy chỉnh các thiết lập của bạn:\n\n"
            "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
        )
        await query.edit_message_text(
            message,
            reply_markup=settings_menu_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    if action == "reminders":
        # Show reminder settings submenu
        user_data = await get_user_data(db, user.id)
        message = (
            "⏰ <b>CÀI ĐẶT NHẮC VIỆC</b>\n\n"
            "Chọn thời điểm nhận nhắc nhở trước deadline:\n\n"
            "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
        )
        await query.edit_message_text(
            message,
            reply_markup=reminders_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    if action == "gcal":
        # Show Google Calendar settings submenu
        user_data = await get_user_data(db, user.id)
        message = (
            "📅 <b>CÀI ĐẶT ĐỒNG BỘ GOOGLE CALENDAR</b>\n\n"
            "Quản lý đồng bộ với Google Calendar:\n\n"
            "• <b>Chọn thời gian</b>: Chọn thời gian tự động đồng bộ\n"
            "• <b>Đồng bộ ngay</b>: Thực hiện đồng bộ thủ công"
        )
        await query.edit_message_text(
            message,
            reply_markup=gcal_settings_keyboard(user_data),
            parse_mode="HTML"
        )
        return SETTINGS_MENU

    if action == "action":
        action_type = parts[2] if len(parts) > 2 else ""

        if action_type == "sync_now":
            # Trigger manual sync
            user_data = await get_user_data(db, user.id)
            user_db_id = user_data.get("id")

            if user_db_id:
                try:
                    from handlers.calendar import sync_all_tasks_to_calendar
                    synced = await sync_all_tasks_to_calendar(db, user_data)
                    await query.answer(f"✅ Đã đồng bộ {synced} việc!", show_alert=True)
                except Exception as e:
                    logger.error(f"Manual sync failed: {e}")
                    await query.answer("❌ Đồng bộ thất bại. Kiểm tra kết nối Google Calendar.", show_alert=True)
            else:
                await query.answer("❌ Không tìm thấy thông tin người dùng.", show_alert=True)

            # Return to gcal menu
            message = (
                "📅 <b>CÀI ĐẶT GOOGLE CALENDAR</b>\n\n"
                "Quản lý đồng bộ với Google Calendar:"
            )
            await query.edit_message_text(
                message,
                reply_markup=gcal_settings_keyboard(user_data),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        return SETTINGS_MENU

    if action == "toggle":
        column = parts[2] if len(parts) > 2 else ""

        # Validate column name (whitelist)
        valid_columns = [
            "notify_reminder", "notify_weekly_report", "notify_monthly_report",
            "remind_24h", "remind_1h", "remind_30m", "remind_5m", "remind_overdue"
        ]
        if column not in valid_columns:
            return SETTINGS_MENU

        # Get current value and toggle
        user_data = await get_user_data(db, user.id)
        current = user_data.get(column, True)
        new_value = not current

        await update_user_setting(db, user.id, column, new_value)

        # Update user_data for display
        user_data[column] = new_value

        status = "🟢 BẬT" if new_value else "🔴 TẮT"
        setting_names = {
            "notify_reminder": "Nhắc việc",
            "notify_weekly_report": "Báo cáo tuần",
            "notify_monthly_report": "Báo cáo tháng",
            "remind_24h": "Nhắc 24 giờ trước",
            "remind_1h": "Nhắc 1 giờ trước",
            "remind_30m": "Nhắc 30 phút trước",
            "remind_5m": "Nhắc 5 phút trước",
            "remind_overdue": "Nhắc khi quá hạn",
        }
        setting_name = setting_names.get(column, column)

        await query.answer(f"{setting_name}: {status}")

        # Determine which menu to show
        if column.startswith("remind_"):
            # Reminder submenu
            message = (
                "⏰ <b>CÀI ĐẶT NHẮC VIỆC</b>\n\n"
                "Chọn thời điểm nhận nhắc nhở trước deadline:\n\n"
                "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
            )
            await query.edit_message_text(
                message,
                reply_markup=reminders_keyboard(user_data),
                parse_mode="HTML"
            )
        else:
            # Main menu
            message = (
                "⚙️ <b>CÀI ĐẶT</b>\n\n"
                "Tùy chỉnh các thiết lập của bạn:\n\n"
                "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
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
                "🌏 <b>CHỌN MÚI GIỜ</b>\n\n"
                "Múi giờ ảnh hưởng đến thời gian hiển thị deadline và nhắc nhở.",
                reply_markup=timezone_keyboard(),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        if edit_type == "reminder_source":
            user_data = await get_user_data(db, user.id)
            current_source = user_data.get("reminder_source", "both")
            await query.edit_message_text(
                "🔔 <b>NGUỒN NHẮC VIỆC</b>\n\n"
                "Chọn nơi bạn muốn nhận nhắc nhở:\n\n"
                "• <b>✈️ Telegram</b>: Bot gửi tin nhắn nhắc nhở\n"
                "• <b>📅 Google Calendar</b>: Lịch Google tự nhắc\n"
                "• <b>Cả hai</b>: Nhận từ cả Telegram và Google\n\n"
                "<i>Chọn một tùy chọn bên dưới:</i>",
                reply_markup=reminder_source_keyboard(current_source),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        if edit_type == "sync_interval":
            user_data = await get_user_data(db, user.id)
            current_interval = user_data.get("calendar_sync_interval", "manual")
            await query.edit_message_text(
                "⏱️ <b>TẦN SUẤT ĐỒNG BỘ</b>\n\n"
                "Chọn thời gian tự động đồng bộ với Google Calendar:\n\n"
                "• <b>Mỗi 24 giờ</b>: Đồng bộ mỗi ngày\n"
                "• <b>Mỗi 12 giờ</b>: Đồng bộ 2 lần/ngày\n"
                "• <b>Mỗi tuần</b>: Đồng bộ mỗi tuần\n"
                "• <b>Thủ công</b>: Chỉ đồng bộ khi bạn bấm",
                reply_markup=sync_interval_keyboard(current_interval),
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

        if set_type == "reminder_source" and value:
            # Validate reminder source
            valid_sources = [src[0] for src in REMINDER_SOURCE_OPTIONS]
            if value not in valid_sources:
                return SETTINGS_MENU

            await update_user_setting(db, user.id, "reminder_source", value)

            # Find display name
            source_display = value
            for src_code, src_label, _desc in REMINDER_SOURCE_OPTIONS:
                if src_code == value:
                    source_display = src_label
                    break

            await query.answer(f"Đã đặt nguồn nhắc: {source_display}")

        if set_type == "sync_interval" and value:
            # Validate sync interval
            valid_intervals = [interval[0] for interval in SYNC_INTERVAL_OPTIONS]
            if value not in valid_intervals:
                return SETTINGS_MENU

            await update_user_setting(db, user.id, "calendar_sync_interval", value)

            # Find display name
            interval_display = value
            for interval_code, interval_label in SYNC_INTERVAL_OPTIONS:
                if interval_code == value:
                    interval_display = interval_label
                    break

            await query.answer(f"Đã đặt: {interval_display}")

            # Return to gcal menu
            user_data = await get_user_data(db, user.id)
            message = (
                "📅 <b>CÀI ĐẶT GOOGLE CALENDAR</b>\n\n"
                "Quản lý đồng bộ với Google Calendar:"
            )
            await query.edit_message_text(
                message,
                reply_markup=gcal_settings_keyboard(user_data),
                parse_mode="HTML"
            )
            return SETTINGS_MENU

        # Return to main menu
        user_data = await get_user_data(db, user.id)
        message = (
            "⚙️ <b>CÀI ĐẶT</b>\n\n"
            "Tùy chỉnh các thiết lập của bạn:\n\n"
            "<i>Bấm nút để bật/tắt (🟢 BẬT / 🔴 TẮT)</i>"
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
        per_message=False,
    )

    return [conv_handler]
