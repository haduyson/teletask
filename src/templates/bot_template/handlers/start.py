"""
Start Handler
Handles /start, /help, /thongtin commands
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import get_or_create_user, get_user_tasks
from utils import MSG_START, MSG_START_GROUP, MSG_HELP, MSG_HELP_GROUP, MSG_INFO, ERR_DATABASE

logger = logging.getLogger(__name__)


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


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("thongtin", info_command),
    ]
