"""
Task Delete Handler
Commands for deleting tasks with undo support
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    soft_delete_task,
    restore_task,
    get_tasks_created_by_user,
    get_tasks_assigned_to_others,
    bulk_delete_tasks,
)
from utils import (
    MSG_TASK_DELETED,
    MSG_TASK_RESTORED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_DATABASE,
    undo_keyboard,
    confirm_keyboard,
    bulk_delete_confirm_keyboard,
    format_datetime,
    format_status,
)

logger = logging.getLogger(__name__)


async def xoa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xoa or /xoaviec [task_id] command.
    Delete task with confirmation and 10-second undo.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc.\n\nVí dụ: /xoa P-0001"
        )
        return

    task_id = context.args[0].upper()

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task = await get_task_by_public_id(db, task_id)

        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Only creator can delete
        if task["creator_id"] != db_user["id"]:
            await update.message.reply_text(ERR_NO_PERMISSION)
            return

        # Show task details for review before deletion
        status = format_status(task["status"])
        deadline_str = format_datetime(task.get("deadline"), relative=True) if task.get("deadline") else "Không có"
        assignee_name = task.get("assignee_name", "Chưa giao")

        await update.message.reply_text(
            f"⚠️ XÁC NHẬN XÓA VIỆC?\n\n"
            f"📋 *{task_id}*: {task['content']}\n"
            f"📊 Trạng thái: {status}\n"
            f"👤 Người nhận: {assignee_name}\n"
            f"📅 Deadline: {deadline_str}\n\n"
            f"Bấm *Xác nhận* để xóa hoặc *Hủy* để giữ lại.",
            reply_markup=confirm_keyboard("delete", task_id),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Error in xoa_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def process_delete(
    db,
    task_id: str,
    user_id: int,
    bot,
) -> tuple:
    """
    Process task deletion.
    Returns (success, undo_id or error_message).
    """
    task = await get_task_by_public_id(db, task_id)

    if not task:
        return False, ERR_TASK_NOT_FOUND.format(task_id=task_id)

    # Soft delete
    undo = await soft_delete_task(db, task["id"], user_id)

    if not undo:
        return False, "Lỗi khi xóa việc."

    # Notify assignee if different from creator
    if task["assignee_id"] != task["creator_id"]:
        try:
            assignee = await db.fetch_one(
                "SELECT telegram_id FROM users WHERE id = $1",
                task["assignee_id"]
            )
            if assignee:
                await bot.send_message(
                    chat_id=assignee["telegram_id"],
                    text=f"Việc {task_id} đã bị xóa bởi người tạo.\n\n"
                         f"Nội dung: {task['content'][:50]}...",
                )
        except Exception as e:
            logger.warning(f"Could not notify assignee: {e}")

    return True, undo["id"]


async def process_restore(db, undo_id: int) -> tuple:
    """
    Process task restoration.
    Returns (success, task or error_message).
    """
    task = await restore_task(db, undo_id)

    if not task:
        return False, "Không thể hoàn tác. Đã hết thời gian (10 giây)."

    return True, task


# =============================================================================
# Bulk Delete Commands
# =============================================================================

async def xoahet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xoahet command - Delete all tasks created by user.
    Shows confirmation before deletion.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Get all tasks created by user (including assigned to self)
        tasks = await get_tasks_created_by_user(db, db_user["id"], include_assigned_to_others=True)

        if not tasks:
            await update.message.reply_text("Bạn không có việc nào để xóa.")
            return

        # Store task IDs in context for callback
        task_ids = [t["id"] for t in tasks]
        context.user_data["bulk_delete_ids"] = task_ids
        context.user_data["bulk_delete_type"] = "all"

        # Build task list preview
        preview_lines = []
        for t in tasks[:5]:  # Show max 5 tasks
            content_short = t["content"][:30] + "..." if len(t["content"]) > 30 else t["content"]
            preview_lines.append(f"• {t['public_id']}: {content_short}")

        if len(tasks) > 5:
            preview_lines.append(f"... và {len(tasks) - 5} việc khác")

        preview = "\n".join(preview_lines)

        await update.message.reply_text(
            f"⚠️ XÁC NHẬN XÓA TẤT CẢ VIỆC?\n\n"
            f"Bạn có *{len(tasks)}* việc sẽ bị xóa:\n\n"
            f"{preview}\n\n"
            f"⚠️ *Lưu ý:* Hành động này không thể hoàn tác!",
            reply_markup=bulk_delete_confirm_keyboard("all", len(tasks)),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Error in xoahet_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def xoaviecdagiao_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xoaviecdagiao command - Delete tasks assigned to others.
    Only deletes tasks where creator != assignee.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Get tasks assigned to others (creator != assignee)
        tasks = await get_tasks_assigned_to_others(db, db_user["id"])

        if not tasks:
            await update.message.reply_text("Bạn không có việc đã giao cho người khác.")
            return

        # Store task IDs in context for callback
        task_ids = [t["id"] for t in tasks]
        context.user_data["bulk_delete_ids"] = task_ids
        context.user_data["bulk_delete_type"] = "assigned"

        # Build task list preview
        preview_lines = []
        for t in tasks[:5]:  # Show max 5 tasks
            content_short = t["content"][:25] + "..." if len(t["content"]) > 25 else t["content"]
            assignee = t.get("assignee_name", "?")
            preview_lines.append(f"• {t['public_id']}: {content_short} → {assignee}")

        if len(tasks) > 5:
            preview_lines.append(f"... và {len(tasks) - 5} việc khác")

        preview = "\n".join(preview_lines)

        await update.message.reply_text(
            f"⚠️ XÁC NHẬN XÓA VIỆC ĐÃ GIAO?\n\n"
            f"Bạn có *{len(tasks)}* việc đã giao:\n\n"
            f"{preview}\n\n"
            f"⚠️ *Lưu ý:* Hành động này không thể hoàn tác!",
            reply_markup=bulk_delete_confirm_keyboard("assigned", len(tasks)),
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Error in xoaviecdagiao_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def process_bulk_delete(
    db,
    user_id: int,
    task_ids: list,
    bot,
) -> int:
    """
    Process bulk deletion.
    Returns count of deleted tasks.
    """
    count = await bulk_delete_tasks(db, task_ids, user_id)
    return count


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler(["xoa", "xoaviec"], xoa_command),
        CommandHandler("xoahet", xoahet_command),
        CommandHandler("xoaviecdagiao", xoaviecdagiao_command),
    ]
