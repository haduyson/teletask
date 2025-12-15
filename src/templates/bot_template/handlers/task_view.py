"""
Task View Handler
Commands for viewing and searching tasks
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    get_user_tasks,
    get_group_tasks,
    get_tasks_with_deadline,
)
from utils import (
    ERR_TASK_NOT_FOUND,
    ERR_GROUP_ONLY,
    ERR_DATABASE,
    format_task_detail,
    format_task_list,
    task_detail_keyboard,
    task_list_with_pagination,
)

logger = logging.getLogger(__name__)


async def xemviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xemviec or /vic [task_id] command.
    View task detail by ID or list all tasks.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Check if task ID provided
        if context.args:
            task_id = context.args[0].upper()
            task = await get_task_by_public_id(db, task_id)

            if not task:
                await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
                return

            # Check permission (assignee or creator)
            can_edit = task["creator_id"] == db_user["id"]
            can_complete = task["assignee_id"] == db_user["id"]

            msg = format_task_detail(task)
            keyboard = task_detail_keyboard(
                task_id,
                can_edit=can_edit,
                can_complete=can_complete and task["status"] != "completed",
            )

            await update.message.reply_text(msg, reply_markup=keyboard)
        else:
            # List all user tasks
            tasks = await get_user_tasks(db, db_user["id"], limit=10)

            if not tasks:
                await update.message.reply_text(
                    "Bạn chưa có việc nào.\n\nTạo việc mới: /taoviec [nội dung]"
                )
                return

            total = len(tasks)
            total_pages = (total + 9) // 10

            msg = format_task_list(
                tasks=tasks,
                title="DANH SÁCH VIỆC CỦA BẠN",
                page=1,
                total=total,
            )

            await update.message.reply_text(
                msg,
                reply_markup=task_list_with_pagination(tasks, 1, total_pages, "all"),
            )

    except Exception as e:
        logger.error(f"Error in xemviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def viecnhom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /viecnhom command.
    View all tasks in current group.
    """
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    # Check if in group
    if chat.type == "private":
        await update.message.reply_text(ERR_GROUP_ONLY)
        return

    try:
        db = get_db()

        # Get group
        group = await db.fetch_one(
            "SELECT id FROM groups WHERE telegram_id = $1",
            chat.id
        )

        if not group:
            await update.message.reply_text("Nhóm chưa có việc nào.")
            return

        tasks = await get_group_tasks(db, group["id"], limit=20)

        if not tasks:
            await update.message.reply_text(
                f"Nhóm {chat.title} chưa có việc nào.\n\nGiao việc: /giaoviec @username [nội dung]"
            )
            return

        total = len(tasks)
        total_pages = (total + 9) // 10

        msg = format_task_list(
            tasks=tasks,
            title=f"VIỆC TRONG NHÓM {chat.title}",
            page=1,
            total=total,
        )

        await update.message.reply_text(
            msg,
            reply_markup=task_list_with_pagination(tasks, 1, total_pages, "group"),
        )

    except Exception as e:
        logger.error(f"Error in viecnhom_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def timviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /timviec [keyword] command.
    Search tasks by keyword.
    """
    user = update.effective_user
    if not user:
        return

    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text("Nhập từ khoá: /timviec [từ khoá]")
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Search in user's tasks
        tasks = await db.fetch_all(
            """
            SELECT t.*, u.display_name as assignee_name, c.display_name as creator_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            LEFT JOIN users c ON t.creator_id = c.id
            WHERE (t.assignee_id = $1 OR t.creator_id = $1)
            AND t.is_deleted = false
            AND (
                LOWER(t.content) LIKE LOWER($2)
                OR LOWER(t.description) LIKE LOWER($2)
                OR t.public_id ILIKE $2
            )
            ORDER BY t.created_at DESC
            LIMIT 20
            """,
            db_user["id"],
            f"%{query}%",
        )

        if not tasks:
            await update.message.reply_text(f"Không tìm thấy việc với từ khoá: {query}")
            return

        tasks = [dict(t) for t in tasks]
        msg = format_task_list(
            tasks=tasks,
            title=f"KẾT QUẢ TÌM KIẾM: {query}",
            page=1,
            total=len(tasks),
        )

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in timviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def deadline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /deadline [hours] command.
    Show tasks with deadline within specified hours.
    """
    user = update.effective_user
    if not user:
        return

    # Parse hours (default 24)
    hours = 24
    if context.args:
        try:
            arg = context.args[0].lower().replace("h", "")
            hours = int(arg)
        except ValueError:
            pass

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        tasks = await get_tasks_with_deadline(db, hours, db_user["id"])

        if not tasks:
            await update.message.reply_text(f"Không có việc nào trong {hours} giờ tới.")
            return

        msg = format_task_list(
            tasks=tasks,
            title=f"VIỆC TRONG {hours} GIỜ TỚI",
            page=1,
            total=len(tasks),
        )

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in deadline_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler(["xemviec", "vic"], xemviec_command),
        CommandHandler(["viecnhom", "viecduan"], viecnhom_command),
        CommandHandler("timviec", timviec_command),
        CommandHandler("deadline", deadline_command),
    ]
