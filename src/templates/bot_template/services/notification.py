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
    task_id = reminder["public_id"]
    reminder_type = reminder.get("reminder_type", "")

    if reminder_type == "creator_overdue":
        # Special message for task creators when assigned task is overdue
        overdue = now - deadline
        text = format_creator_overdue_message(reminder, overdue)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{task_id}"),
            ],
        ])
    elif reminder_type == "after_deadline":
        overdue = now - deadline
        text = format_overdue_message(reminder, overdue)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Tiến độ", callback_data=f"task_progress:{task_id}"),
                InlineKeyboardButton("⏰ Nhắc sau 30p", callback_data=f"snooze:{reminder['id']}:30"),
            ],
            [
                InlineKeyboardButton("✅ HOÀN THÀNH", callback_data=f"task_complete:{task_id}"),
            ],
        ])
    else:
        time_left = deadline - now
        text = format_upcoming_message(reminder, time_left)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Tiến độ", callback_data=f"task_progress:{task_id}"),
                InlineKeyboardButton("⏰ Nhắc sau 30p", callback_data=f"snooze:{reminder['id']}:30"),
            ],
            [
                InlineKeyboardButton("✅ HOÀN THÀNH", callback_data=f"task_complete:{task_id}"),
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
            InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{task['public_id']}"),
        ],
        [
            InlineKeyboardButton("✅ HOÀN THÀNH", callback_data=f"task_complete:{task['public_id']}"),
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


def format_creator_overdue_message(data: Dict[str, Any], overdue: timedelta) -> str:
    """Format reminder message for task creators when assigned task is overdue."""
    content = data.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    deadline = data.get("deadline")
    deadline_str = deadline.strftime("%H:%M %d/%m") if deadline else "N/A"

    return f"""⚠️ VIỆC GIAO ĐÃ TRỄ HẠN!

{data.get('public_id', '')}: {content}

Deadline: {deadline_str}
Đã trễ: {format_time_delta(overdue)}
Tiến độ: {format_progress_bar(data.get('progress', 0))}

Công việc bạn giao chưa được hoàn thành đúng hạn.
Hãy liên hệ người nhận việc để cập nhật."""


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


# ============================================
# GROUP TASK NOTIFICATIONS
# ============================================

async def send_group_task_created_notification(
    bot: Bot,
    group_task: Dict[str, Any],
    child_tasks: list,
    assignees: list,
    creator: Dict[str, Any],
) -> None:
    """
    Send notification to all assignees when group task is created.

    Args:
        bot: Telegram bot instance
        group_task: Parent G-ID task data
        child_tasks: List of P-ID child tasks
        assignees: List of assignee user data
        creator: Creator user data
    """
    content = group_task.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    deadline = group_task.get("deadline")
    deadline_str = deadline.strftime("%H:%M %d/%m") if deadline else "Không có"

    for i, assignee in enumerate(assignees):
        if assignee.get("telegram_id") == creator.get("telegram_id"):
            continue  # Skip notifying creator

        # Check user notification preferences
        if not assignee.get("notify_all", True):
            continue  # User disabled all notifications
        if not assignee.get("notify_task_assigned", True):
            continue  # User disabled task assignment notifications

        child_task = child_tasks[i] if i < len(child_tasks) else None
        if not child_task:
            continue

        text = f"""👥 VIỆC NHÓM MỚI!

{group_task['public_id']}: {content}

Từ: {creator.get('display_name', 'N/A')}
Deadline: {deadline_str}
Thành viên: {len(assignees)} người

📋 Việc của bạn: {child_task['public_id']}

Trả lời /xong {child_task['public_id']} khi hoàn thành."""

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Tiến độ", callback_data=f"task_progress:{child_task['public_id']}"),
                InlineKeyboardButton("👥 Xem nhóm", callback_data=f"task_detail:{group_task['public_id']}"),
            ],
            [
                InlineKeyboardButton("✅ HOÀN THÀNH", callback_data=f"task_complete:{child_task['public_id']}"),
            ],
        ])

        try:
            await bot.send_message(
                chat_id=assignee["telegram_id"],
                text=text,
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.warning(f"Could not notify assignee {assignee.get('telegram_id')}: {e}")


async def send_member_completed_notification(
    bot: Bot,
    db,
    completed_task: Dict[str, Any],
    completer: Dict[str, Any],
) -> None:
    """
    Notify other group members when someone completes their task.

    Args:
        bot: Telegram bot instance
        db: Database connection
        completed_task: The P-ID task that was completed
        completer: User who completed the task
    """
    # Get parent task
    parent_id = completed_task.get("parent_task_id")
    if not parent_id:
        return

    parent = await db.fetch_one(
        "SELECT * FROM tasks WHERE id = $1 AND is_deleted = false",
        parent_id
    )
    if not parent:
        return

    parent = dict(parent)

    # Get all child tasks with assignee info and notification preferences
    siblings = await db.fetch_all(
        """
        SELECT t.*, u.telegram_id, u.display_name, u.notify_all, u.notify_task_status
        FROM tasks t
        JOIN users u ON t.assignee_id = u.id
        WHERE t.parent_task_id = $1 AND t.is_deleted = false
        """,
        parent_id
    )

    # Calculate progress
    total = len(siblings)
    completed = sum(1 for s in siblings if s["status"] == "completed")
    progress = int((completed / total) * 100) if total > 0 else 0

    content = parent.get("content", "")
    if len(content) > 50:
        content = content[:47] + "..."

    # Notify each sibling (except completer)
    for sibling in siblings:
        if sibling["telegram_id"] == completer.get("telegram_id"):
            continue
        if sibling["status"] == "completed":
            continue  # Don't notify already completed members

        # Check user notification preferences
        if not sibling.get("notify_all", True):
            continue  # User disabled all notifications
        if not sibling.get("notify_task_status", True):
            continue  # User disabled task status notifications

        text = f"""📊 CẬP NHẬT VIỆC NHÓM

{parent['public_id']}: {content}

✅ {completer.get('display_name', 'Ai đó')} đã hoàn thành!

Tiến độ nhóm: {format_progress_bar(progress)}
Hoàn thành: {completed}/{total}

Việc của bạn: {sibling['public_id']}"""

        try:
            await bot.send_message(
                chat_id=sibling["telegram_id"],
                text=text,
            )
        except Exception as e:
            logger.warning(f"Could not notify sibling {sibling.get('telegram_id')}: {e}")


async def send_group_completed_notification(
    bot: Bot,
    db,
    group_task: Dict[str, Any],
) -> None:
    """
    Notify creator when all group members have completed.

    Args:
        bot: Telegram bot instance
        db: Database connection
        group_task: The G-ID parent task that is now complete
    """
    # Get creator with notification preferences
    creator = await db.fetch_one(
        "SELECT telegram_id, display_name, notify_all, notify_task_status FROM users WHERE id = $1",
        group_task["creator_id"]
    )

    if not creator:
        return

    # Check user notification preferences
    if not creator.get("notify_all", True):
        return  # User disabled all notifications
    if not creator.get("notify_task_status", True):
        return  # User disabled task status notifications

    # Get child task count
    children = await db.fetch_all(
        """
        SELECT t.public_id, u.display_name
        FROM tasks t
        JOIN users u ON t.assignee_id = u.id
        WHERE t.parent_task_id = $1 AND t.is_deleted = false
        ORDER BY t.completed_at DESC
        """,
        group_task["id"]
    )

    member_list = "\n".join(f"  ✅ {c['display_name']}" for c in children)

    content = group_task.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    text = f"""🎉 VIỆC NHÓM ĐÃ HOÀN THÀNH!

{group_task['public_id']}: {content}

👥 TẤT CẢ {len(children)} THÀNH VIÊN ĐÃ HOÀN THÀNH:
{member_list}

Xem chi tiết: /xemviec {group_task['public_id']}"""

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{group_task['public_id']}"),
        ],
    ])

    try:
        await bot.send_message(
            chat_id=creator["telegram_id"],
            text=text,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning(f"Could not notify creator {creator.get('telegram_id')}: {e}")


async def send_task_completed_to_assigner(
    bot: Bot,
    db,
    task: Dict[str, Any],
    completer: Dict[str, Any],
) -> None:
    """
    Notify the task assigner/creator when assigned task is completed.

    Args:
        bot: Telegram bot instance
        db: Database connection
        task: The completed task data
        completer: User who completed the task
    """
    # Skip if this is a group task child (handled separately)
    if task.get("parent_task_id"):
        return

    # Get creator info
    creator_id = task.get("creator_id")
    assignee_id = task.get("assignee_id")

    # Skip if creator completed their own task
    if not creator_id or not assignee_id or creator_id == assignee_id:
        return

    creator = await db.fetch_one(
        "SELECT telegram_id, display_name, notify_all, notify_task_status FROM users WHERE id = $1",
        creator_id
    )

    if not creator:
        return

    # Check user notification preferences
    if not creator.get("notify_all", True):
        return  # User disabled all notifications
    if not creator.get("notify_task_status", True):
        return  # User disabled task status notifications

    content = task.get("content", "")
    if len(content) > 100:
        content = content[:97] + "..."

    completed_at = task.get("completed_at")
    if completed_at:
        completed_str = completed_at.strftime("%H:%M %d/%m")
    else:
        completed_str = datetime.now(TZ).strftime("%H:%M %d/%m")

    text = f"""✅ VIỆC ĐÃ HOÀN THÀNH!

{task['public_id']}: {content}

👤 Người thực hiện: {completer.get('display_name', 'N/A')}
⏰ Hoàn thành lúc: {completed_str}

Xem chi tiết: /xemviec {task['public_id']}"""

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{task['public_id']}"),
        ],
    ])

    try:
        await bot.send_message(
            chat_id=creator["telegram_id"],
            text=text,
            reply_markup=keyboard,
        )
        logger.info(f"Notified creator {creator_id} about task {task['public_id']} completion")
    except Exception as e:
        logger.warning(f"Could not notify creator {creator.get('telegram_id')}: {e}")
