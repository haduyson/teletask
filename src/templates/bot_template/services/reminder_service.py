"""
Reminder Service
CRUD operations for task reminders
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

from database.connection import Database

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# Default reminder offsets before deadline
BEFORE_DEADLINE = [
    ("24h", timedelta(hours=24)),
    ("1h", timedelta(hours=1)),
]

# Default reminder offsets after deadline (for overdue tasks)
AFTER_DEADLINE = [
    ("1h", timedelta(hours=1)),
    ("1d", timedelta(days=1)),
]


async def create_default_reminders(
    db: Database,
    task_id: int,
    user_id: int,
    deadline: datetime,
) -> None:
    """
    Create default reminders for a task.

    Args:
        db: Database connection
        task_id: Task internal ID
        user_id: User to remind
        deadline: Task deadline
    """
    now = datetime.now(TZ)

    # Make deadline timezone-aware if needed
    if deadline.tzinfo is None:
        deadline = TZ.localize(deadline)

    # Before deadline reminders
    for offset_name, offset in BEFORE_DEADLINE:
        remind_at = deadline - offset
        if remind_at > now:
            await create_reminder(
                db, task_id, user_id, remind_at,
                "before_deadline", offset_name
            )

    # After deadline reminders (for escalation)
    for offset_name, offset in AFTER_DEADLINE:
        remind_at = deadline + offset
        await create_reminder(
            db, task_id, user_id, remind_at,
            "after_deadline", offset_name
        )

    logger.info(f"Created default reminders for task {task_id}")


async def create_reminder(
    db: Database,
    task_id: int,
    user_id: int,
    remind_at: datetime,
    reminder_type: str,
    reminder_offset: str,
) -> Optional[Dict[str, Any]]:
    """
    Create a single reminder.

    Args:
        db: Database connection
        task_id: Task internal ID
        user_id: User to remind
        remind_at: When to send reminder
        reminder_type: Type (before_deadline, after_deadline, custom)
        reminder_offset: Offset label (24h, 1h, etc.)

    Returns:
        Created reminder or None if duplicate
    """
    try:
        reminder = await db.fetch_one(
            """
            INSERT INTO reminders (task_id, user_id, remind_at, reminder_type, reminder_offset)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT DO NOTHING
            RETURNING *
            """,
            task_id, user_id, remind_at, reminder_type, reminder_offset
        )
        return dict(reminder) if reminder else None
    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        return None


async def get_pending_reminders(db: Database) -> List[Dict[str, Any]]:
    """
    Get all reminders due now.

    Args:
        db: Database connection

    Returns:
        List of pending reminders with task and user info
    """
    reminders = await db.fetch_all(
        """
        SELECT r.*,
               t.content, t.public_id, t.status, t.priority, t.progress, t.deadline,
               u.telegram_id, u.display_name
        FROM reminders r
        JOIN tasks t ON r.task_id = t.id
        JOIN users u ON r.user_id = u.id
        WHERE r.is_sent = false
          AND r.remind_at <= CURRENT_TIMESTAMP
          AND t.is_deleted = false
          AND t.status != 'completed'
        ORDER BY r.remind_at
        LIMIT 50
        """
    )
    return [dict(r) for r in reminders]


async def mark_reminder_sent(
    db: Database,
    reminder_id: int,
    error: Optional[str] = None,
) -> None:
    """
    Mark a reminder as sent.

    Args:
        db: Database connection
        reminder_id: Reminder ID
        error: Error message if failed
    """
    await db.execute(
        """
        UPDATE reminders
        SET is_sent = true, sent_at = CURRENT_TIMESTAMP, error_message = $2
        WHERE id = $1
        """,
        reminder_id, error
    )


async def delete_task_reminders(db: Database, task_id: int) -> int:
    """
    Delete all unsent reminders for a task.
    Called when task is completed or deleted.

    Args:
        db: Database connection
        task_id: Task internal ID

    Returns:
        Number of reminders deleted
    """
    result = await db.execute(
        """
        DELETE FROM reminders
        WHERE task_id = $1 AND is_sent = false
        """,
        task_id
    )
    return int(result.split()[-1]) if result else 0


async def get_task_reminders(
    db: Database,
    task_id: int,
    pending_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Get all reminders for a task.

    Args:
        db: Database connection
        task_id: Task internal ID
        pending_only: Only return unsent reminders

    Returns:
        List of reminders
    """
    conditions = ["task_id = $1"]
    if pending_only:
        conditions.append("is_sent = false")

    query = f"""
        SELECT * FROM reminders
        WHERE {' AND '.join(conditions)}
        ORDER BY remind_at
    """

    reminders = await db.fetch_all(query, task_id)
    return [dict(r) for r in reminders]


async def snooze_reminder(
    db: Database,
    reminder_id: int,
    snooze_minutes: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Snooze a reminder by delaying it.

    Args:
        db: Database connection
        reminder_id: Reminder ID
        snooze_minutes: Minutes to delay

    Returns:
        Updated reminder
    """
    new_time = datetime.now(TZ) + timedelta(minutes=snooze_minutes)

    reminder = await db.fetch_one(
        """
        UPDATE reminders
        SET remind_at = $2, is_sent = false, sent_at = NULL
        WHERE id = $1
        RETURNING *
        """,
        reminder_id, new_time
    )
    return dict(reminder) if reminder else None
