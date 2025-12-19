"""
Recurring Task Handler
Handles commands for recurring/scheduled task templates
"""

import logging
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
from services import (
    get_or_create_user,
    create_recurring_template,
    get_recurring_template,
    get_user_recurring_templates,
    toggle_recurring_template,
    delete_recurring_template,
    parse_recurrence_pattern,
    format_recurrence_description,
)
from utils import (
    ERR_DATABASE,
    ERR_NOT_FOUND,
    ERR_NO_CONTENT,
    validate_task_content,
    format_datetime,
    format_priority,
)

logger = logging.getLogger(__name__)

# Conversation states
CONTENT, RECURRENCE, CONFIRM = range(3)


async def vieclaplai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /vieclaplai command.
    Start conversation to create recurring task template.

    Format: /vieclaplai [nội dung] [lịch lặp]
    Examples:
        /vieclaplai Họp đội hàng tuần thứ 2 9h
        /vieclaplai Báo cáo tháng hàng tháng ngày 1
        /vieclaplai Kiểm tra email hàng ngày 8h
    """
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    text = " ".join(context.args) if context.args else ""

    if not text:
        # Start conversation flow
        await update.message.reply_text(
            "📅 *TẠO VIỆC LẶP LẠI*\n\n"
            "Nhập nội dung việc và lịch lặp lại:\n\n"
            "Ví dụ:\n"
            "• `Họp đội hàng tuần thứ 2 9h`\n"
            "• `Báo cáo hàng tháng ngày 1 10h`\n"
            "• `Kiểm tra email hàng ngày 8h`\n\n"
            "Hoặc nhập `/huy` để hủy.",
            parse_mode="Markdown",
        )
        return CONTENT

    # Direct creation with arguments
    return await process_recurring_creation(update, context, text)


async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive task content and recurrence pattern."""
    text = update.message.text.strip()

    if text.lower() == "/huy":
        await update.message.reply_text("Đã hủy tạo việc lặp lại.")
        return ConversationHandler.END

    return await process_recurring_creation(update, context, text)


async def process_recurring_creation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> int:
    """Process recurring task creation from text."""
    user = update.effective_user

    try:
        db = get_db()

        # Get/create user
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Parse recurrence pattern
        recurrence, remaining = parse_recurrence_pattern(text)

        if not recurrence:
            await update.message.reply_text(
                "⚠️ Không nhận dạng được lịch lặp lại.\n\n"
                "Vui lòng thêm một trong các mẫu:\n"
                "• `hàng ngày` / `mỗi ngày`\n"
                "• `hàng tuần` / `mỗi tuần`\n"
                "• `hàng tháng` / `mỗi tháng`\n"
                "• `mỗi 2 ngày` / `mỗi 3 tuần`\n\n"
                "Ví dụ: `Họp đội hàng tuần thứ 2 9h`",
                parse_mode="Markdown",
            )
            return CONTENT if context.args is None else ConversationHandler.END

        # Validate content
        content = remaining.strip() if remaining else text
        is_valid, result = validate_task_content(content)

        if not is_valid:
            await update.message.reply_text(result)
            return CONTENT if context.args is None else ConversationHandler.END

        content = result

        # Create recurring template
        template = await create_recurring_template(
            db=db,
            content=content,
            creator_id=user_id,
            recurrence_type=recurrence["recurrence_type"],
            recurrence_interval=recurrence.get("recurrence_interval", 1),
            recurrence_days=recurrence.get("recurrence_days"),
            recurrence_time=recurrence.get("recurrence_time"),
        )

        # Format response
        recurrence_str = format_recurrence_description(template)
        next_due_str = format_datetime(template["next_due"], relative=True) if template["next_due"] else "N/A"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Tạm dừng", callback_data=f"recurring_pause:{template['public_id']}"),
                InlineKeyboardButton("🗑 Xóa", callback_data=f"recurring_delete:{template['public_id']}"),
            ],
            [
                InlineKeyboardButton("📋 Danh sách việc lặp", callback_data="recurring_list"),
            ],
        ])

        await update.message.reply_text(
            f"✅ *ĐÃ TẠO VIỆC LẶP LẠI*\n\n"
            f"🆔 `{template['public_id']}`\n"
            f"📝 {content}\n\n"
            f"🔄 Lịch: {recurrence_str}\n"
            f"⏰ Việc tiếp theo: {next_due_str}\n\n"
            f"_Hệ thống sẽ tự động tạo việc theo lịch._",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        logger.info(f"User {user.id} created recurring template {template['public_id']}")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in recurring creation: {e}")
        await update.message.reply_text(ERR_DATABASE)
        return ConversationHandler.END


async def cancel_recurring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel recurring task creation."""
    await update.message.reply_text("Đã hủy tạo việc lặp lại.")
    return ConversationHandler.END


async def danhsachvieclaplai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /danhsachvieclaplai command.
    List user's recurring task templates.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        templates = await get_user_recurring_templates(db, user_id, active_only=False)

        if not templates:
            await update.message.reply_text(
                "Bạn chưa có việc lặp lại nào.\n\n"
                "Tạo mới: /vieclaplai [nội dung] [lịch lặp]"
            )
            return

        # Format list
        lines = ["📅 *DANH SÁCH VIỆC LẶP LẠI*\n"]

        for t in templates:
            status = "✅" if t["is_active"] else "⏸"
            recurrence_str = format_recurrence_description(t)
            next_str = format_datetime(t["next_due"], relative=True) if t["next_due"] else "N/A"

            lines.append(
                f"{status} `{t['public_id']}`: {t['content'][:40]}\n"
                f"   🔄 {recurrence_str}\n"
                f"   ⏰ Tiếp theo: {next_str}\n"
            )

        lines.append(f"\n_Tổng: {len(templates)} mẫu_")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tạo mới", callback_data="recurring_new")],
        ])

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.error(f"Error in danhsachvieclaplai: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def recurring_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle recurring task callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        if data == "recurring_list":
            # Redirect to list command
            templates = await get_user_recurring_templates(db, db_user["id"], active_only=False)

            if not templates:
                await query.edit_message_text(
                    "Bạn chưa có việc lặp lại nào.\n\n"
                    "Tạo mới: /vieclaplai [nội dung] [lịch lặp]"
                )
                return

            lines = ["📅 *DANH SÁCH VIỆC LẶP LẠI*\n"]
            for t in templates:
                status = "✅" if t["is_active"] else "⏸"
                recurrence_str = format_recurrence_description(t)
                lines.append(f"{status} `{t['public_id']}`: {t['content'][:40]}\n   🔄 {recurrence_str}\n")

            await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
            return

        elif data == "recurring_new":
            await query.edit_message_text(
                "Tạo việc lặp lại mới: /vieclaplai [nội dung] [lịch lặp]\n\n"
                "Ví dụ: `/vieclaplai Họp đội hàng tuần thứ 2 9h`",
                parse_mode="Markdown",
            )
            return

        # Parse action:public_id
        parts = data.split(":")
        if len(parts) != 2:
            return

        action, public_id = parts

        template = await get_recurring_template(db, public_id)
        if not template:
            await query.edit_message_text(ERR_NOT_FOUND)
            return

        # Check ownership
        if template["creator_id"] != db_user["id"]:
            await query.edit_message_text("Bạn không có quyền thao tác với mẫu này.")
            return

        if action == "recurring_pause":
            # Toggle active state
            new_state = not template["is_active"]
            await toggle_recurring_template(db, template["id"], new_state)

            status_text = "đã kích hoạt" if new_state else "đã tạm dừng"
            status_emoji = "✅" if new_state else "⏸"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "▶️ Kích hoạt" if not new_state else "⏸ Tạm dừng",
                        callback_data=f"recurring_pause:{public_id}"
                    ),
                    InlineKeyboardButton("🗑 Xóa", callback_data=f"recurring_delete:{public_id}"),
                ],
            ])

            await query.edit_message_text(
                f"{status_emoji} Việc lặp lại `{public_id}` {status_text}.\n\n"
                f"📝 {template['content']}",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

        elif action == "recurring_delete":
            # Confirm deletion
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Xác nhận xóa", callback_data=f"recurring_confirm_delete:{public_id}"),
                    InlineKeyboardButton("❌ Hủy", callback_data=f"recurring_cancel_delete:{public_id}"),
                ],
            ])

            await query.edit_message_text(
                f"⚠️ Xác nhận xóa việc lặp lại?\n\n"
                f"🆔 `{public_id}`\n"
                f"📝 {template['content']}\n\n"
                f"_Thao tác này không thể hoàn tác._",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

        elif action == "recurring_confirm_delete":
            await delete_recurring_template(db, template["id"])
            await query.edit_message_text(
                f"✅ Đã xóa việc lặp lại `{public_id}`.",
                parse_mode="Markdown",
            )
            logger.info(f"User {user.id} deleted recurring template {public_id}")

        elif action == "recurring_cancel_delete":
            recurrence_str = format_recurrence_description(template)

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⏸ Tạm dừng" if template["is_active"] else "▶️ Kích hoạt",
                        callback_data=f"recurring_pause:{public_id}"
                    ),
                    InlineKeyboardButton("🗑 Xóa", callback_data=f"recurring_delete:{public_id}"),
                ],
            ])

            await query.edit_message_text(
                f"📅 *VIỆC LẶP LẠI*\n\n"
                f"🆔 `{public_id}`\n"
                f"📝 {template['content']}\n"
                f"🔄 {recurrence_str}\n"
                f"📊 Đã tạo: {template['instances_created']} việc",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

    except Exception as e:
        logger.error(f"Error in recurring callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    # Conversation handler for /vieclaplai
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("vieclaplai", vieclaplai_command)],
        states={
            CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content),
                CommandHandler("huy", cancel_recurring),
            ],
        },
        fallbacks=[CommandHandler("huy", cancel_recurring)],
    )

    return [
        conv_handler,
        CommandHandler("danhsachvieclaplai", danhsachvieclaplai_command),
        CallbackQueryHandler(recurring_callback, pattern=r"^recurring_"),
    ]
