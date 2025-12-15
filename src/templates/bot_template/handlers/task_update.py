"""
Task Update Handler
Commands for updating task status and progress
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    update_task_status,
    update_task_progress,
)
from utils import (
    MSG_TASK_COMPLETED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_ALREADY_COMPLETED,
    ERR_DATABASE,
    format_datetime,
    progress_keyboard,
)

logger = logging.getLogger(__name__)


async def xong_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xong [task_id] or /hoanthanh [task_id] command.
    Mark task as completed.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc.\n\nVí dụ: /xong P-0001"
        )
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Support multiple task IDs: /xong P-0001, P-0002
        task_ids = [t.strip().upper() for t in " ".join(context.args).split(",")]
        results = []

        for task_id in task_ids:
            task = await get_task_by_public_id(db, task_id)

            if not task:
                results.append(f"{task_id}: Không tồn tại")
                continue

            # Check permission (assignee or creator can mark complete)
            if task["assignee_id"] != db_user["id"] and task["creator_id"] != db_user["id"]:
                results.append(f"{task_id}: Không có quyền")
                continue

            if task["status"] == "completed":
                results.append(f"{task_id}: Đã hoàn thành rồi")
                continue

            # Update status
            updated = await update_task_status(
                db, task["id"], "completed", db_user["id"]
            )

            results.append(f"{task_id}: Hoàn thành!")

            # Notify creator if different from person completing
            if task["creator_id"] != db_user["id"]:
                try:
                    creator = await db.fetch_one(
                        "SELECT telegram_id FROM users WHERE id = $1",
                        task["creator_id"]
                    )
                    if creator:
                        await context.bot.send_message(
                            chat_id=creator["telegram_id"],
                            text=f"Việc {task_id} đã được hoàn thành!\n\n"
                                 f"Nội dung: {task['content']}\n"
                                 f"Người thực hiện: {db_user.get('display_name', 'N/A')}",
                        )
                except Exception as e:
                    logger.warning(f"Could not notify creator: {e}")

        # Response
        if len(task_ids) == 1 and results[0].endswith("Hoàn thành!"):
            await update.message.reply_text(
                MSG_TASK_COMPLETED.format(
                    task_id=task_ids[0],
                    content=task["content"],
                    completed_at=format_datetime(updated.get("completed_at")),
                )
            )
        else:
            await update.message.reply_text("\n".join(results))

    except Exception as e:
        logger.error(f"Error in xong_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def danglam_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /danglam [task_id] command.
    Mark task as in progress.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc.\n\nVí dụ: /danglam P-0001"
        )
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task_ids = [t.strip().upper() for t in " ".join(context.args).split(",")]
        updated_count = 0

        for task_id in task_ids:
            task = await get_task_by_public_id(db, task_id)

            if not task:
                continue

            # Only assignee can update status
            if task["assignee_id"] != db_user["id"]:
                continue

            await update_task_status(db, task["id"], "in_progress", db_user["id"])
            updated_count += 1

        if updated_count > 0:
            await update.message.reply_text(
                f"Đã cập nhật {updated_count} việc sang 'Đang làm'"
            )
        else:
            await update.message.reply_text("Không cập nhật được việc nào.")

    except Exception as e:
        logger.error(f"Error in danglam_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def tiendo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tiendo [task_id] [%] command.
    Update task progress percentage.
    """
    user = update.effective_user
    if not user:
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Cú pháp: /tiendo [mã việc] [%]\n\n"
            "Ví dụ:\n"
            "  /tiendo P-0001 50\n"
            "  /tiendo P-0001 75%"
        )
        return

    task_id = context.args[0].upper()

    # Parse progress if provided
    progress = None
    if len(context.args) >= 2:
        try:
            progress = int(context.args[1].replace("%", ""))
            progress = max(0, min(100, progress))
        except ValueError:
            await update.message.reply_text("Phần trăm phải là số (0-100)")
            return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task = await get_task_by_public_id(db, task_id)

        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Only assignee can update progress
        if task["assignee_id"] != db_user["id"]:
            await update.message.reply_text(ERR_NO_PERMISSION)
            return

        if progress is not None:
            # Update progress
            updated = await update_task_progress(
                db, task["id"], progress, db_user["id"]
            )

            # Format response with progress bar
            bar = progress_bar(progress)
            status_text = "Hoàn thành!" if progress == 100 else "Đang làm"

            await update.message.reply_text(
                f"Cập nhật tiến độ {task_id}!\n\n"
                f"{bar} {progress}%\n"
                f"Trạng thái: {status_text}"
            )
        else:
            # Show progress selection keyboard
            current = task.get("progress", 0)
            await update.message.reply_text(
                f"Chọn tiến độ mới cho {task_id}:\n\n"
                f"Hiện tại: {progress_bar(current)} {current}%",
                reply_markup=progress_keyboard(task_id),
            )

    except Exception as e:
        logger.error(f"Error in tiendo_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def progress_bar(percent: int, width: int = 10) -> str:
    """Generate visual progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler(["xong", "hoanthanh", "done"], xong_command),
        CommandHandler("danglam", danglam_command),
        CommandHandler("tiendo", tiendo_command),
    ]
