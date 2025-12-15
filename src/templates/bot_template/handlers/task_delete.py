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
)
from utils import (
    MSG_TASK_DELETED,
    MSG_TASK_RESTORED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_DATABASE,
    undo_keyboard,
    confirm_keyboard,
)

logger = logging.getLogger(__name__)


async def xoa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xoa [task_id] command.
    Delete task with confirmation and 30-second undo.
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

        # Show confirmation
        content = task["content"]
        if len(content) > 50:
            content = content[:47] + "..."

        await update.message.reply_text(
            f"Xác nhận xóa việc?\n\n"
            f"{task_id}: {content}",
            reply_markup=confirm_keyboard("delete", task_id),
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
        return False, "Không thể hoàn tác. Đã hết thời gian (30 giây)."

    return True, task


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("xoa", xoa_command),
    ]
