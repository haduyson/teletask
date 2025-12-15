"""
Notification Service
Send reminder and status notifications to users
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import pytz

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


async def send_reminder_notification(bot: Bot, reminder: Dict[str, Any]) -> None:
    """
    Send a reminder notification to user.

    Args:
        bot: Telegram bot instance
        reminder: Reminder data with task and user info
    """
    now = datetime.now(TZ)
    deadline = reminder["deadline"]

    if deadline.tzinfo is None:
        deadline = TZ.localize(deadline)

    # Format message based on type
    if reminder["reminder_type"] == "after_deadline":
        overdue = now - deadline
        text = format_overdue_message(reminder, overdue)
    else:
        time_left = deadline - now
        text = format_upcoming_message(reminder, time_left)

    # Action buttons
    task_id = reminder["public_id"]
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Xong", callback_data=f"task_complete:{task_id}"),
            InlineKeyboardButton("📊 Tiến độ", callback_data=f"task_progress:{task_id}"),
        ],
        [
            InlineKeyboardButton("⏰ Nhắc sau 30p", callback_data=f"snooze:{reminder['id']}:30"),
        ],
    ])

    await bot.send_message(
        chat_id=reminder["telegram_id"],
        text=text,
        reply_markup=keyboard,
    )


async def send_reminder_by_task(
    bot: Bot,
    db,
    task_id: int,
    user_id: int,
) -> None:
    """
    Send reminder for a specific task to a user.

    Args:
        bot: Telegram bot instance
        db: Database connection
        task_id: Task internal ID
        user_id: User internal ID
    """
    # Get task and user info
    task = await db.fetch_one(
        """
        SELECT t.*, u.telegram_id, u.display_name
        FROM tasks t
        JOIN users u ON u.id = $2
        WHERE t.id = $1 AND t.is_deleted = false
        """,
        task_id, user_id
    )

    if not task or task["status"] == "completed":
        return

    task = dict(task)
    now = datetime.now(TZ)
    deadline = task.get("deadline")

    if deadline:
        if deadline.tzinfo is None:
            deadline = TZ.localize(deadline)

        if now > deadline:
            text = format_overdue_message(task, now - deadline)
        else:
            text = format_upcoming_message(task, deadline - now)
    else:
        text = format_simple_reminder(task)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Xong", callback_data=f"task_complete:{task['public_id']}"),
            InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{task['public_id']}"),
        ],
    ])

    await bot.send_message(
        chat_id=task["telegram_id"],
        text=text,
        reply_markup=keyboard,
    )


def format_upcoming_message(data: Dict[str, Any], time_left: timedelta) -> str:
    """Format reminder message for upcoming deadline."""
    hours = time_left.total_seconds() / 3600

    if hours <= 0.5:
        prefix = "🚨 KHẨN CẤP - Còn 30 phút!"
    elif hours <= 1:
        prefix = "🚨 KHẨN CẤP - Còn 1 giờ!"
    elif hours <= 3:
        prefix = "⚠️ SẮP ĐẾN HẠN - Còn vài giờ"
    elif hours <= 24:
        prefix = "🔔 NHẮC VIỆC - Còn 1 ngày"
    else:
        prefix = "🔔 NHẮC VIỆC"

    content = data.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    deadline = data.get("deadline")
    deadline_str = deadline.strftime("%H:%M %d/%m") if deadline else "N/A"

    return f"""{prefix}

{data.get('public_id', '')}: {content}

Ưu tiên: {format_priority(data.get('priority', 'normal'))}
Tiến độ: {format_progress_bar(data.get('progress', 0))}
Deadline: {deadline_str}
Còn lại: {format_time_delta(time_left)}"""


def format_overdue_message(data: Dict[str, Any], overdue: timedelta) -> str:
    """Format reminder message for overdue task."""
    hours = overdue.total_seconds() / 3600

    if hours >= 168:  # 1 week
        prefix = "🚨 TRỄ RẤT NGHIÊM TRỌNG!"
    elif hours >= 24:
        prefix = "🚨 TRỄ NGHIÊM TRỌNG!"
    else:
        prefix = "🚨 VIỆC ĐÃ TRỄ HẠN!"

    content = data.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    deadline = data.get("deadline")
    deadline_str = deadline.strftime("%H:%M %d/%m") if deadline else "N/A"

    return f"""{prefix}

{data.get('public_id', '')}: {content}

Ưu tiên: {format_priority(data.get('priority', 'normal'))}
Tiến độ: {format_progress_bar(data.get('progress', 0))}
Deadline: {deadline_str}
Đã trễ: {format_time_delta(overdue)}

Vui lòng hoàn thành sớm nhất!"""


def format_simple_reminder(data: Dict[str, Any]) -> str:
    """Format simple reminder without deadline."""
    content = data.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    return f"""🔔 NHẮC VIỆC

{data.get('public_id', '')}: {content}

Ưu tiên: {format_priority(data.get('priority', 'normal'))}
Tiến độ: {format_progress_bar(data.get('progress', 0))}"""


def format_time_delta(td: timedelta) -> str:
    """Format timedelta as readable Vietnamese."""
    total_seconds = int(abs(td.total_seconds()))

    if total_seconds < 60:
        return f"{total_seconds} giây"

    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} phút"

    hours = minutes // 60
    remaining_mins = minutes % 60
    if hours < 24:
        if remaining_mins > 0:
            return f"{hours} giờ {remaining_mins} phút"
        return f"{hours} giờ"

    days = hours // 24
    remaining_hours = hours % 24
    if remaining_hours > 0:
        return f"{days} ngày {remaining_hours} giờ"
    return f"{days} ngày"


def format_priority(priority: str) -> str:
    """Format priority label."""
    return {
        "urgent": "🔴 Khẩn cấp",
        "high": "🟠 Cao",
        "normal": "🟡 Bình thường",
        "low": "🟢 Thấp",
    }.get(priority, "🟡 Bình thường")


def format_progress_bar(percent: int, width: int = 10) -> str:
    """Format progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {percent}%"
