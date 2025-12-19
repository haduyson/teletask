"""
Reminder Handler
Commands for managing task reminders
"""

import logging
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import pytz

from database import get_db
from services import get_or_create_user, get_task_by_public_id, parse_vietnamese_time
from services.reminder_service import create_reminder, get_task_reminders, snooze_reminder
from utils import ERR_TASK_NOT_FOUND, ERR_NO_PERMISSION, ERR_DATABASE

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


async def nhacviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /nhacviec [task_id] [time] command.
    Set custom reminder for a task.

    Examples:
        /nhacviec P-0001 14h30
        /nhacviec P-0001 ngay mai 9h
        /nhacviec P-0001 2 tieng truoc deadline
    """
    user = update.effective_user
    if not user:
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Cú pháp: /nhacviec [mã việc] [thời gian]\n\n"
            "Ví dụ:\n"
            "  /nhacviec P-0001 14h30\n"
            "  /nhacviec P-0001 ngày mai 9h\n"
            "  /nhacviec P-0001 2 tiếng trước deadline"
        )
        return

    task_id = context.args[0].upper()
    time_text = " ".join(context.args[1:])

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Get task
        task = await get_task_by_public_id(db, task_id)

        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Check permission (assignee or creator)
        if task["assignee_id"] != db_user["id"] and task["creator_id"] != db_user["id"]:
            await update.message.reply_text(ERR_NO_PERMISSION)
            return

        # Parse time
        remind_at = None

        # Check if relative to deadline
        if "truoc deadline" in time_text.lower() and task.get("deadline"):
            remind_at = parse_relative_to_deadline(task["deadline"], time_text)
        else:
            # Parse absolute time
            remind_at, _ = parse_vietnamese_time(time_text)

        if not remind_at:
            await update.message.reply_text(
                "Không hiểu thời gian. Vui lòng thử lại.\n\n"
                "Ví dụ: 14h30, ngày mai 9h, 2 tiếng trước deadline"
            )
            return

        now = datetime.now(TZ)
        if remind_at.tzinfo is None:
            remind_at = TZ.localize(remind_at)

        if remind_at <= now:
            await update.message.reply_text("Thời gian nhắc phải trong tương lai.")
            return

        # Create reminder
        reminder = await create_reminder(
            db, task["id"], db_user["id"], remind_at,
            "custom", time_text[:50]
        )

        if not reminder:
            await update.message.reply_text("Không thể tạo nhắc việc. Có thể đã tồn tại.")
            return

        # Schedule with APScheduler if available
        try:
            from scheduler.reminder_scheduler import reminder_scheduler
            if reminder_scheduler.scheduler:
                reminder_scheduler.add_custom_reminder(task["id"], db_user["id"], remind_at)
        except Exception as e:
            logger.warning(f"Could not schedule custom reminder: {e}")

        await update.message.reply_text(
            f"Đã đặt nhắc việc!\n\n"
            f"{task_id}: {task['content'][:50]}...\n"
            f"Sẽ nhắc lúc: {remind_at.strftime('%H:%M %d/%m/%Y')}"
        )

    except Exception as e:
        logger.error(f"Error in nhacviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def xemnhac_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xemnhac [task_id] command.
    View reminders for a task.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Cú pháp: /xemnhac [mã việc]\n\n"
            "Ví dụ: /xemnhac P-0001"
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

        # Get reminders
        reminders = await get_task_reminders(db, task["id"], pending_only=True)

        if not reminders:
            await update.message.reply_text(f"Không có nhắc việc nào cho {task_id}.")
            return

        lines = [f"Nhắc việc cho {task_id}:\n"]
        for r in reminders:
            remind_at = r["remind_at"]
            if remind_at.tzinfo is None:
                remind_at = TZ.localize(remind_at)
            lines.append(f"  - {remind_at.strftime('%H:%M %d/%m')} ({r['reminder_type']})")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        logger.error(f"Error in xemnhac_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def parse_relative_to_deadline(deadline: datetime, text: str) -> datetime:
    """
    Parse time relative to deadline.

    Examples:
        "2 tieng truoc deadline" -> deadline - 2 hours
        "30 phut truoc deadline" -> deadline - 30 minutes
    """
    if deadline.tzinfo is None:
        deadline = TZ.localize(deadline)

    text = text.lower()

    # Match pattern: number + unit + truoc
    match = re.search(r"(\d+)\s*(tieng|gio|phut|ngay)\s*truoc", text)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit in ("tieng", "gio"):
        return deadline - timedelta(hours=amount)
    elif unit == "phut":
        return deadline - timedelta(minutes=amount)
    elif unit == "ngay":
        return deadline - timedelta(days=amount)

    return None


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("nhacviec", nhacviec_command),
        CommandHandler("xemnhac", xemnhac_command),
    ]
