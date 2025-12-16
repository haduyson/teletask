"""
Export Handler
Step-by-step export wizard for statistical reports
"""

import os
import logging
from datetime import datetime, timedelta

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import get_db
from services import get_or_create_user, create_export_report, REPORT_TTL_HOURS
from utils import ERR_DATABASE

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# Conversation states
PERIOD, TASK_FILTER, FILE_FORMAT, CONFIRM = range(200, 204)

# Period options
PERIOD_OPTIONS = {
    "last7": "7 ngày qua",
    "last30": "30 ngày qua",
    "this_week": "Tuần này",
    "last_week": "Tuần trước",
    "this_month": "Tháng này",
    "last_month": "Tháng trước",
    "all": "Tất cả",
}

# Task filter options
FILTER_OPTIONS = {
    "all": "Tất cả việc",
    "created": "Việc đã tạo",
    "assigned": "Việc đã giao",
    "received": "Việc được giao",
}

# File format options
FORMAT_OPTIONS = {
    "csv": "CSV (đơn giản)",
    "xlsx": "Excel (có biểu đồ)",
    "pdf": "PDF (báo cáo đẹp)",
}


def get_export_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Get export wizard data from user_data."""
    if "export" not in context.user_data:
        context.user_data["export"] = {}
    return context.user_data["export"]


def clear_export_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear export wizard data."""
    if "export" in context.user_data:
        del context.user_data["export"]


def period_keyboard() -> InlineKeyboardMarkup:
    """Create period selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 7 ngày qua", callback_data="export_period:last7"),
            InlineKeyboardButton("📅 30 ngày qua", callback_data="export_period:last30"),
        ],
        [
            InlineKeyboardButton("📆 Tuần này", callback_data="export_period:this_week"),
            InlineKeyboardButton("📆 Tuần trước", callback_data="export_period:last_week"),
        ],
        [
            InlineKeyboardButton("📊 Tháng này", callback_data="export_period:this_month"),
            InlineKeyboardButton("📊 Tháng trước", callback_data="export_period:last_month"),
        ],
        [
            InlineKeyboardButton("📋 Tất cả thời gian", callback_data="export_period:all"),
        ],
        [
            InlineKeyboardButton("❌ Hủy", callback_data="export_cancel"),
        ],
    ])


def filter_keyboard() -> InlineKeyboardMarkup:
    """Create task filter selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Tất cả việc", callback_data="export_filter:all"),
        ],
        [
            InlineKeyboardButton("✏️ Việc đã tạo", callback_data="export_filter:created"),
            InlineKeyboardButton("👤 Việc đã giao", callback_data="export_filter:assigned"),
        ],
        [
            InlineKeyboardButton("📬 Việc được giao", callback_data="export_filter:received"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="export_back:period"),
            InlineKeyboardButton("❌ Hủy", callback_data="export_cancel"),
        ],
    ])


def format_keyboard() -> InlineKeyboardMarkup:
    """Create file format selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 CSV", callback_data="export_format:csv"),
        ],
        [
            InlineKeyboardButton("📊 Excel (biểu đồ)", callback_data="export_format:xlsx"),
        ],
        [
            InlineKeyboardButton("📑 PDF (báo cáo)", callback_data="export_format:pdf"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="export_back:filter"),
            InlineKeyboardButton("❌ Hủy", callback_data="export_cancel"),
        ],
    ])


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tạo báo cáo", callback_data="export_confirm:create"),
            InlineKeyboardButton("❌ Hủy bỏ", callback_data="export_confirm:cancel"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="export_back:format"),
        ],
    ])


def format_summary(data: dict) -> str:
    """Format export settings summary."""
    period = PERIOD_OPTIONS.get(data.get("period", ""), "?")
    task_filter = FILTER_OPTIONS.get(data.get("filter", ""), "?")
    file_format = FORMAT_OPTIONS.get(data.get("format", ""), "?")

    return f"""📊 XUẤT BÁO CÁO THỐNG KÊ

Khoảng thời gian: {period}
Loại việc: {task_filter}
Định dạng: {file_format}

Xác nhận tạo báo cáo?

⏱ Báo cáo sẽ hết hạn sau {REPORT_TTL_HOURS} giờ."""


# =============================================================================
# Entry Point
# =============================================================================


async def export_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start export wizard."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    clear_export_data(context)

    await update.message.reply_text(
        "📊 XUẤT BÁO CÁO THỐNG KÊ\n\n"
        "Bước 1/4: Chọn khoảng thời gian\n\n"
        "Chọn khoảng thời gian cho báo cáo:",
        reply_markup=period_keyboard(),
    )

    return PERIOD


# =============================================================================
# Step 1: Period Selection
# =============================================================================


async def period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle period selection."""
    query = update.callback_query
    await query.answer()

    data = get_export_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action not in PERIOD_OPTIONS:
        return PERIOD

    data["period"] = action

    await query.edit_message_text(
        f"Khoảng thời gian: {PERIOD_OPTIONS[action]}\n\n"
        "Bước 2/4: Chọn loại việc\n\n"
        "Chọn loại việc cần xuất:",
        reply_markup=filter_keyboard(),
    )

    return TASK_FILTER


# =============================================================================
# Step 2: Task Filter Selection
# =============================================================================


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle task filter selection."""
    query = update.callback_query
    await query.answer()

    data = get_export_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action not in FILTER_OPTIONS:
        return TASK_FILTER

    data["filter"] = action

    await query.edit_message_text(
        f"Loại việc: {FILTER_OPTIONS[action]}\n\n"
        "Bước 3/4: Chọn định dạng file\n\n"
        "📄 CSV - Đơn giản, mở được trong Excel\n"
        "📊 Excel - Có biểu đồ và màu sắc\n"
        "📑 PDF - Báo cáo đẹp, dễ chia sẻ",
        reply_markup=format_keyboard(),
    )

    return FILE_FORMAT


# =============================================================================
# Step 3: File Format Selection
# =============================================================================


async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle file format selection."""
    query = update.callback_query
    await query.answer()

    data = get_export_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action not in FORMAT_OPTIONS:
        return FILE_FORMAT

    data["format"] = action

    summary = format_summary(data)
    await query.edit_message_text(
        f"Bước 4/4: Xác nhận\n\n{summary}",
        reply_markup=confirm_keyboard(),
    )

    return CONFIRM


# =============================================================================
# Step 4: Confirm and Generate
# =============================================================================


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation and generate report."""
    query = update.callback_query
    await query.answer()

    data = get_export_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action == "cancel":
        clear_export_data(context)
        await query.edit_message_text("Đã hủy xuất báo cáo.")
        return ConversationHandler.END

    if action == "create":
        await query.edit_message_text("⏳ Đang tạo báo cáo, vui lòng chờ...")

        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            # Create the report
            result = await create_export_report(
                db=db,
                user_id=db_user["id"],
                user_name=db_user.get("display_name") or user.full_name,
                report_type=data.get("period", "all"),
                file_format=data.get("format", "csv"),
                task_filter=data.get("filter", "all"),
            )

            # Get report URL from environment
            base_url = os.getenv("EXPORT_BASE_URL", "http://localhost:8080")
            report_url = f"{base_url}/report/{result['report_id']}"

            # Format file size
            file_size = result.get("file_size", 0)
            if file_size > 1024 * 1024:
                size_str = f"{file_size / 1024 / 1024:.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} bytes"

            # Format expiry time
            expires_at = result.get("expires_at")
            if expires_at:
                expiry_str = expires_at.strftime("%H:%M %d/%m/%Y")
            else:
                expiry_str = "72 giờ"

            format_name = FORMAT_OPTIONS.get(data.get("format", "csv"), "File")

            message = f"""✅ BÁO CÁO ĐÃ TẠO THÀNH CÔNG!

📊 Định dạng: {format_name}
📦 Kích thước: {size_str}

🔗 Link tải về:
{report_url}

🔐 Mật khẩu: `{result['password']}`

⏱ Hết hạn: {expiry_str}

💡 Mở link trên trình duyệt, nhập mật khẩu để tải file."""

            await query.edit_message_text(message, parse_mode="Markdown")

            logger.info(f"Export: User {user.id} created report {result['report_id']}")

        except Exception as e:
            logger.error(f"Error creating export report: {e}")
            await query.edit_message_text(f"❌ Lỗi tạo báo cáo: {str(e)}")

        clear_export_data(context)
        return ConversationHandler.END

    return CONFIRM


# =============================================================================
# Back Handler
# =============================================================================


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back button."""
    query = update.callback_query
    await query.answer()

    target = query.data.split(":")[1] if ":" in query.data else ""
    data = get_export_data(context)

    if target == "period":
        await query.edit_message_text(
            "📊 XUẤT BÁO CÁO THỐNG KÊ\n\n"
            "Bước 1/4: Chọn khoảng thời gian\n\n"
            "Chọn khoảng thời gian cho báo cáo:",
            reply_markup=period_keyboard(),
        )
        return PERIOD

    elif target == "filter":
        period = PERIOD_OPTIONS.get(data.get("period", ""), "?")
        await query.edit_message_text(
            f"Khoảng thời gian: {period}\n\n"
            "Bước 2/4: Chọn loại việc\n\n"
            "Chọn loại việc cần xuất:",
            reply_markup=filter_keyboard(),
        )
        return TASK_FILTER

    elif target == "format":
        task_filter = FILTER_OPTIONS.get(data.get("filter", ""), "?")
        await query.edit_message_text(
            f"Loại việc: {task_filter}\n\n"
            "Bước 3/4: Chọn định dạng file\n\n"
            "📄 CSV - Đơn giản, mở được trong Excel\n"
            "📊 Excel - Có biểu đồ và màu sắc\n"
            "📑 PDF - Báo cáo đẹp, dễ chia sẻ",
            reply_markup=format_keyboard(),
        )
        return FILE_FORMAT

    return PERIOD


# =============================================================================
# Cancel Handler
# =============================================================================


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button."""
    query = update.callback_query
    await query.answer()

    clear_export_data(context)
    await query.edit_message_text("Đã hủy xuất báo cáo.")
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /huy command."""
    clear_export_data(context)
    await update.message.reply_text("Đã hủy xuất báo cáo.")
    return ConversationHandler.END


# =============================================================================
# Handler Registration
# =============================================================================


def get_export_conversation_handler() -> ConversationHandler:
    """Get the export wizard ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("export", export_start),
            CommandHandler("xuatbaocao", export_start),
        ],
        states={
            PERIOD: [
                CallbackQueryHandler(period_callback, pattern=r"^export_period:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^export_cancel$"),
            ],
            TASK_FILTER: [
                CallbackQueryHandler(filter_callback, pattern=r"^export_filter:"),
                CallbackQueryHandler(back_callback, pattern=r"^export_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^export_cancel$"),
            ],
            FILE_FORMAT: [
                CallbackQueryHandler(format_callback, pattern=r"^export_format:"),
                CallbackQueryHandler(back_callback, pattern=r"^export_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^export_cancel$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_callback, pattern=r"^export_confirm:"),
                CallbackQueryHandler(back_callback, pattern=r"^export_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^export_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("huy", cancel_command),
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_callback, pattern=r"^export_cancel$"),
        ],
        per_user=True,
        per_chat=True,
    )


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        get_export_conversation_handler(),
    ]
