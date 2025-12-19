"""
Task Create Handler
Handles /taoviec command for personal task creation
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    create_task,
    parse_vietnamese_time,
)
from utils import (
    MSG_TASK_CREATED,
    ERR_NO_CONTENT,
    ERR_INVALID_TIME,
    ERR_DATABASE,
    validate_task_content,
    parse_task_command,
    format_datetime,
    format_priority,
    task_actions_keyboard,
)

logger = logging.getLogger(__name__)


async def taoviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /taoviec command.
    Create personal task for the user.

    Format: /taoviec [content] [time]
    Examples:
        /taoviec Hop doi 14h30
        /taoviec Nop bao cao ngay mai 10h
        /taoviec Mua qua sinh nhat 15/12
    """
    user = update.effective_user
    if not user:
        return

    # Get text after command
    text = " ".join(context.args) if context.args else ""

    if not text:
        await update.message.reply_text(
            ERR_NO_CONTENT + "\n\nVí dụ: /taoviec Họp đội 14h30"
        )
        return

    try:
        db = get_db()

        # Register/get user
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Parse command
        parsed = parse_task_command(text)

        # Extract time from content
        deadline, remaining = parse_vietnamese_time(parsed["content"])

        # Validate content
        content = remaining.strip() if remaining else parsed["content"]
        is_valid, result = validate_task_content(content)

        if not is_valid:
            await update.message.reply_text(result)
            return

        content = result

        # Create task
        task = await create_task(
            db=db,
            content=content,
            creator_id=user_id,
            assignee_id=user_id,  # Personal task: assign to self
            deadline=deadline,
            priority=parsed["priority"],
            is_personal=True,
        )

        # Format response
        deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
        priority_str = format_priority(parsed["priority"])

        await update.message.reply_text(
            MSG_TASK_CREATED.format(
                task_id=task["public_id"],
                content=content,
                deadline=deadline_str,
                priority=priority_str,
            ),
            reply_markup=task_actions_keyboard(task["public_id"]),
        )

        logger.info(f"User {user.id} created task {task['public_id']}: {content[:30]}")

    except Exception as e:
        logger.error(f"Error in taoviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def vieccanhan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /vieccanhan command.
    List personal tasks for the user.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Get user's tasks
        from services import get_user_tasks
        tasks = await get_user_tasks(db, user_id, limit=10)

        if not tasks:
            await update.message.reply_text(
                "Bạn chưa có việc nào.\n\nTạo việc mới: /taoviec [nội dung]"
            )
            return

        # Format task list
        from utils import format_task_list, task_list_with_pagination

        total = len(tasks)
        total_pages = (total + 9) // 10

        msg = format_task_list(
            tasks=tasks,
            title="VIỆC CÁ NHÂN CỦA BẠN",
            page=1,
            total=total,
        )

        await update.message.reply_text(
            msg,
            reply_markup=task_list_with_pagination(tasks, 1, total_pages, "personal"),
        )

    except Exception as e:
        logger.error(f"Error in vieccanhan_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    # Note: /taoviec is now handled by task_wizard.py
    return [
        CommandHandler("vieccanhan", vieccanhan_command),
    ]
