"""
Start Handler
Handles /start, /help, /thongtin, /menu commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import get_db
from services import get_or_create_user, get_user_tasks
from utils import MSG_START, MSG_START_GROUP, MSG_HELP, MSG_HELP_GROUP, MSG_INFO, ERR_DATABASE

logger = logging.getLogger(__name__)


def main_menu_keyboard(is_group: bool = False) -> InlineKeyboardMarkup:
    """Create main menu keyboard with feature buttons."""
    buttons = [
        [InlineKeyboardButton("➕ Tạo việc mới", callback_data="menu:taoviec")],
    ]

    # Only show "Giao việc" in group chats
    if is_group:
        buttons.append([InlineKeyboardButton("👥 Giao việc", callback_data="menu:giaoviec")])

    buttons.extend([
        [InlineKeyboardButton("📋 Xem việc của tôi", callback_data="menu:xemviec")],
        [InlineKeyboardButton("🔄 Việc lặp lại", callback_data="menu:vieclaplai")],
        [InlineKeyboardButton("🗑️ Xóa việc", callback_data="menu:xoaviec")],
        [InlineKeyboardButton("📊 Thống kê", callback_data="menu:thongke")],
        [InlineKeyboardButton("📤 Xuất báo cáo", callback_data="menu:export")],
        [InlineKeyboardButton("📅 Google Calendar", callback_data="menu:lichgoogle")],
        [InlineKeyboardButton("⚙️ Cài đặt", callback_data="menu:caidat")],
        [InlineKeyboardButton("❓ Hướng dẫn", callback_data="menu:help")],
    ])

    return InlineKeyboardMarkup(buttons)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.
    Register user and show welcome message.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        # Register/update user
        db_user = await get_or_create_user(db, user)

        # Use different message for private chat vs group
        chat = update.effective_chat
        is_private = chat.type == "private"
        msg = MSG_START if is_private else MSG_START_GROUP

        # Send welcome message
        await update.message.reply_text(
            msg.format(name=db_user.get("display_name", user.first_name))
        )

        logger.info(f"User {user.id} started bot")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command.
    Show detailed help message (different for private vs group).
    """
    chat = update.effective_chat
    is_private = chat.type == "private"
    msg = MSG_HELP if is_private else MSG_HELP_GROUP
    await update.message.reply_text(msg)


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongtin command.
    Show user account information and statistics.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Get task counts
        all_tasks = await get_user_tasks(db, user_id, include_completed=True)
        in_progress = [t for t in all_tasks if t.get("status") == "in_progress"]
        completed = [t for t in all_tasks if t.get("status") == "completed"]

        # Count overdue (deadline passed, not completed)
        from datetime import datetime
        import pytz
        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        now = datetime.now(tz)

        overdue = []
        for t in all_tasks:
            if t.get("status") != "completed" and t.get("deadline"):
                deadline = t["deadline"]
                if deadline.tzinfo is None:
                    deadline = tz.localize(deadline)
                if deadline < now:
                    overdue.append(t)

        await update.message.reply_text(
            MSG_INFO.format(
                name=db_user.get("display_name", "N/A"),
                username=db_user.get("username") or "Không có",
                telegram_id=user.id,
                total_tasks=len(all_tasks),
                in_progress=len(in_progress),
                completed=len(completed),
                overdue=len(overdue),
                timezone=db_user.get("timezone", "Asia/Ho_Chi_Minh"),
            )
        )

    except Exception as e:
        logger.error(f"Error in info_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /menu command.
    Show interactive menu with feature buttons.
    """
    user = update.effective_user
    if not user:
        return

    chat = update.effective_chat
    is_group = chat.type in ("group", "supergroup")

    await update.message.reply_text(
        "📱 <b>MENU CHÍNH</b>\n\n"
        "Chọn chức năng bạn muốn sử dụng:",
        reply_markup=main_menu_keyboard(is_group=is_group),
        parse_mode="HTML",
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle menu button callbacks."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":")[1] if ":" in query.data else ""

    if action == "taoviec":
        # Trigger task wizard
        await query.message.reply_text(
            "📝 <b>TẠO VIỆC MỚI</b>\n\n"
            "Nhập nội dung việc cần làm:\n"
            "Ví dụ: <code>Họp đội 14h30</code>\n\n"
            "Hoặc dùng lệnh: /taoviec [nội dung]",
            parse_mode="HTML",
        )

    elif action == "xemviec":
        # Show task category menu
        from utils import task_category_keyboard
        await query.message.reply_text(
            "📋 <b>XEM VIỆC</b>\n\n"
            "Chọn loại việc muốn xem:",
            reply_markup=task_category_keyboard(),
            parse_mode="HTML",
        )

    elif action == "vieclaplai":
        await query.message.reply_text(
            "🔄 <b>VIỆC LẶP LẠI</b>\n\n"
            "• /vieclaplai - Tạo việc lặp lại mới\n"
            "• /danhsachvieclaplai - Xem danh sách việc lặp\n\n"
            "Ví dụ:\n"
            "<code>/vieclaplai Họp đội hàng tuần thứ 2 9h</code>",
            parse_mode="HTML",
        )

    elif action == "xoaviec":
        # Show delete menu
        from handlers.task_delete import delete_menu_keyboard
        await query.message.reply_text(
            "🗑️ <b>XÓA VIỆC</b>\n\n"
            "Chọn loại việc muốn xóa:",
            reply_markup=delete_menu_keyboard(),
            parse_mode="HTML",
        )

    elif action == "thongke":
        await query.message.reply_text(
            "📊 <b>THỐNG KÊ</b>\n\n"
            "• /thongke - Thống kê tổng hợp\n"
            "• /thongketuan - Thống kê tuần này\n"
            "• /thongkethang - Thống kê tháng này\n"
            "• /viectrehan - Xem việc trễ hạn",
            parse_mode="HTML",
        )

    elif action == "export":
        await query.message.reply_text(
            "📤 <b>XUẤT BÁO CÁO</b>\n\n"
            "Dùng lệnh /export để xuất báo cáo.\n\n"
            "Định dạng hỗ trợ: CSV, Excel, PDF",
            parse_mode="HTML",
        )

    elif action == "giaoviec":
        await query.message.reply_text(
            "👥 <b>GIAO VIỆC</b>\n\n"
            "Dùng lệnh /giaoviec để giao việc cho thành viên trong nhóm.\n\n"
            "Cách dùng:\n"
            "<code>/giaoviec @username Nội dung việc</code>\n\n"
            "Ví dụ:\n"
            "<code>/giaoviec @nam Hoàn thành báo cáo 17h</code>",
            parse_mode="HTML",
        )

    elif action == "lichgoogle":
        await query.message.reply_text(
            "📅 <b>GOOGLE CALENDAR</b>\n\n"
            "Dùng lệnh /lichgoogle để kết nối và cài đặt Google Calendar.\n\n"
            "<b>🔗 Kết nối:</b> Đăng nhập Google để đồng bộ lịch\n"
            "<b>⚙️ Chế độ đồng bộ:</b> Tự động hoặc thủ công\n"
            "<b>📤 Đồng bộ ngay:</b> Đồng bộ tất cả việc vào lịch",
            parse_mode="HTML",
        )

    elif action == "caidat":
        await query.message.reply_text(
            "⚙️ <b>CÀI ĐẶT</b>\n\n"
            "Dùng lệnh /caidat để mở menu cài đặt cá nhân.\n\n"
            "<b>🔔 Thông báo:</b> Giao việc mới, trạng thái việc, nhắc việc, báo cáo\n"
            "<b>🌏 Múi giờ:</b> Chọn múi giờ hiển thị",
            parse_mode="HTML",
        )

    elif action == "help":
        chat = update.effective_chat
        is_private = chat.type == "private"
        msg = MSG_HELP if is_private else MSG_HELP_GROUP
        await query.message.reply_text(msg)

    elif action == "back":
        chat = update.effective_chat
        is_group = chat.type in ("group", "supergroup")
        await query.edit_message_text(
            "📱 <b>MENU CHÍNH</b>\n\n"
            "Chọn chức năng bạn muốn sử dụng:",
            reply_markup=main_menu_keyboard(is_group=is_group),
            parse_mode="HTML",
        )


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("thongtin", info_command),
        CommandHandler("menu", menu_command),
        CallbackQueryHandler(menu_callback, pattern=r"^menu:"),
    ]
