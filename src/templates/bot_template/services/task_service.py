"""
Task Service
CRUD operations for tasks
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pytz

from database.connection import Database

logger = logging.getLogger(__name__)

# Timezone
TZ = pytz.timezone("Asia/Ho_Chi_Minh")


async def generate_task_id(db: Database, prefix: str = "P") -> str:
    """
    Generate unique task ID.

    Args:
        db: Database connection
        prefix: Task ID prefix - T (regular), G (group parent), P (group child)

    Returns:
        Task ID like T-0001, G-0001, or P-0001
    """
    # Get and increment counter
    result = await db.fetch_one(
        """
        UPDATE bot_config
        SET value = (CAST(value AS INTEGER) + 1)::TEXT, updated_at = NOW()
        WHERE key = 'task_id_counter'
        RETURNING value
        """
    )

    counter = int(result["value"]) if result else 1

    # Format: P0001-P9999 (4 digits), P10000+ (grows automatically, unlimited)
    return f"{prefix}{counter:04d}"


async def create_task(
    db: Database,
    content: str,
    creator_id: int,
    assignee_id: int,
    deadline: Optional[datetime] = None,
    priority: str = "normal",
    is_personal: bool = True,
    group_id: Optional[int] = None,
    description: str = None,
    group_task_id: str = None,
) -> Dict[str, Any]:
    """
    Create a new task.

    Args:
        db: Database connection
        content: Task content
        creator_id: Creator user ID
        assignee_id: Assignee user ID
        deadline: Task deadline
        priority: Task priority (low/normal/high/urgent)
        is_personal: True for personal task
        group_id: Group ID (for group tasks)
        description: Optional description
        group_task_id: Parent group task ID (for multi-assignee)

    Returns:
        Created task record
    """
    # Generate unique public ID
    # P-xxx for all individual tasks, G-xxx for group parent tasks
    public_id = await generate_task_id(db, prefix="P")

    task = await db.fetch_one(
        """
        INSERT INTO tasks (
            public_id, content, description, creator_id, assignee_id,
            deadline, priority, is_personal, group_id, group_task_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
        """,
        public_id,
        content,
        description,
        creator_id,
        assignee_id,
        deadline,
        priority,
        is_personal,
        group_id,
        group_task_id,
    )

    # Log history
    await add_task_history(
        db,
        task["id"],
        creator_id,
        action="created",
        note=f"Task created: {content[:50]}"
    )

    # Create default reminders if deadline exists
    if deadline:
        await create_default_reminders(db, task["id"], assignee_id, deadline)

    # Auto-sync to Google Calendar if enabled
    if deadline:
        try:
            from services.calendar_service import (
                is_calendar_enabled,
                get_user_token_data,
                create_calendar_event,
            )
            if is_calendar_enabled():
                token_data = await get_user_token_data(db, assignee_id)
                if token_data:
                    event_id = await create_calendar_event(
                        token_data,
                        public_id,
                        content,
                        deadline,
                        description or "",
                        priority,
                    )
                    if event_id:
                        await db.execute(
                            "UPDATE tasks SET google_event_id = $2 WHERE id = $1",
                            task["id"], event_id
                        )
                        logger.info(f"Task {public_id} synced to calendar: {event_id}")
        except Exception as e:
            logger.warning(f"Calendar sync failed for task {public_id}: {e}")

    logger.info(f"Created task {public_id}: {content[:30]}...")
    return dict(task)


async def get_task_by_public_id(db: Database, public_id: str) -> Optional[Dict[str, Any]]:
    """
    Get task by public ID (P-xxxx or G-xxxx).

    Args:
        db: Database connection
        public_id: Task public ID

    Returns:
        Task record or None
    """
    task = await db.fetch_one(
        """
        SELECT t.*, u.display_name as assignee_name, c.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        LEFT JOIN users c ON t.creator_id = c.id
        WHERE t.public_id = $1 AND t.is_deleted = false
        """,
        public_id.upper()
    )
    return dict(task) if task else None


async def get_task_by_id(db: Database, task_id: int) -> Optional[Dict[str, Any]]:
    """Get task by internal ID."""
    task = await db.fetch_one(
        """
        SELECT t.*, u.display_name as assignee_name, c.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        LEFT JOIN users c ON t.creator_id = c.id
        WHERE t.id = $1 AND t.is_deleted = false
        """,
        task_id
    )
    return dict(task) if task else None


async def get_user_tasks(
    db: Database,
    user_id: int,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get tasks assigned to user.

    Args:
        db: Database connection
        user_id: Assignee user ID
        status: Filter by status
        limit: Max results
        offset: Skip results
        include_completed: Include completed tasks

    Returns:
        List of task records
    """
    conditions = ["t.assignee_id = $1", "t.is_deleted = false"]
    params = [user_id]

    if status:
        conditions.append(f"t.status = ${len(params) + 1}")
        params.append(status)
    elif not include_completed:
        conditions.append("t.status != 'completed'")

    query = f"""
        SELECT t.*, u.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.creator_id = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY
            CASE t.priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
            END,
            t.deadline ASC NULLS LAST,
            t.created_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
    """

    tasks = await db.fetch_all(query, *params, limit, offset)
    return [dict(t) for t in tasks]


async def get_user_created_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get tasks created by user (assigned to others)."""
    tasks = await db.fetch_all(
        """
        SELECT t.*, u.display_name as assignee_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE t.creator_id = $1
        AND t.assignee_id != $1
        AND t.is_deleted = false
        ORDER BY t.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, limit, offset
    )
    return [dict(t) for t in tasks]


async def get_user_received_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
    """Get tasks assigned TO the user BY others (not self-created)."""
    status_filter = "" if include_completed else "AND t.status != 'completed'"
    tasks = await db.fetch_all(
        f"""
        SELECT t.*, c.display_name as creator_name
        FROM tasks t
        LEFT JOIN users c ON t.creator_id = c.id
        WHERE t.assignee_id = $1
        AND t.creator_id != $1
        AND t.is_deleted = false
        {status_filter}
        ORDER BY
            CASE t.priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
            END,
            t.deadline ASC NULLS LAST,
            t.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, limit, offset
    )
    return [dict(t) for t in tasks]


async def get_user_personal_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
    """Get personal tasks (created by user for themselves)."""
    status_filter = "" if include_completed else "AND t.status != 'completed'"
    tasks = await db.fetch_all(
        f"""
        SELECT t.*, u.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.creator_id = u.id
        WHERE t.creator_id = $1
        AND t.assignee_id = $1
        AND t.is_deleted = false
        {status_filter}
        ORDER BY
            CASE t.priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
            END,
            t.deadline ASC NULLS LAST,
            t.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, limit, offset
    )
    return [dict(t) for t in tasks]


async def get_all_user_related_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
    """Get ALL tasks related to user (created, received, or assigned)."""
    status_filter = "" if include_completed else "AND t.status != 'completed'"
    tasks = await db.fetch_all(
        f"""
        SELECT t.*,
            u.display_name as assignee_name,
            c.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        LEFT JOIN users c ON t.creator_id = c.id
        WHERE (t.assignee_id = $1 OR t.creator_id = $1)
        AND t.is_deleted = false
        {status_filter}
        ORDER BY
            CASE t.priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
            END,
            t.deadline ASC NULLS LAST,
            t.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id, limit, offset
    )
    return [dict(t) for t in tasks]


async def get_group_tasks(
    db: Database,
    group_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get all tasks in a group."""
    tasks = await db.fetch_all(
        """
        SELECT t.*,
            u.display_name as assignee_name,
            c.display_name as creator_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        LEFT JOIN users c ON t.creator_id = c.id
        WHERE t.group_id = $1 AND t.is_deleted = false
        ORDER BY t.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        group_id, limit, offset
    )
    return [dict(t) for t in tasks]


async def update_task_status(
    db: Database,
    task_id: int,
    status: str,
    user_id: int,
    progress: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update task status.

    Args:
        db: Database connection
        task_id: Task ID
        status: New status
        user_id: User making the change
        progress: Optional progress percentage

    Returns:
        Updated task record
    """
    # Get current task
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    old_status = current["status"]

    # Set completed_at if completing
    completed_at = None
    if status == "completed":
        completed_at = datetime.now()
        progress = 100

    task = await db.fetch_one(
        """
        UPDATE tasks SET
            status = $2,
            progress = COALESCE($3, progress),
            completed_at = $4,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        task_id, status, progress, completed_at
    )

    # Log history
    await add_task_history(
        db, task_id, user_id,
        action="status_changed",
        field_name="status",
        old_value=old_status,
        new_value=status
    )

    # Update Google Calendar event if completed
    if status == "completed" and current.get("google_event_id"):
        try:
            from services.calendar_service import (
                is_calendar_enabled,
                get_user_token_data,
                update_calendar_event,
            )
            if is_calendar_enabled():
                token_data = await get_user_token_data(db, current.get("assignee_id"))
                if token_data and current.get("deadline"):
                    await update_calendar_event(
                        token_data, current["google_event_id"],
                        current["public_id"], current["content"],
                        current["deadline"], current.get("description", ""),
                        current.get("priority", "normal"), "completed",
                    )
        except Exception as e:
            logger.warning(f"Calendar update failed for task {task_id}: {e}")

    return dict(task) if task else None


async def update_task_progress(
    db: Database,
    task_id: int,
    progress: int,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Update task progress percentage."""
    # Validate progress
    progress = max(0, min(100, progress))

    # Get current
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    # Auto-update status based on progress
    status = current["status"]
    if progress == 100 and status != "completed":
        status = "completed"
    elif progress > 0 and status == "pending":
        status = "in_progress"

    return await update_task_status(db, task_id, status, user_id, progress)


async def update_task_content(
    db: Database,
    task_id: int,
    content: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Update task content."""
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    old_content = current["content"]

    task = await db.fetch_one(
        """
        UPDATE tasks SET
            content = $2,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        task_id, content
    )

    await add_task_history(
        db, task_id, user_id,
        action="content_changed",
        field_name="content",
        old_value=old_content[:100] if old_content else None,
        new_value=content[:100]
    )

    return dict(task) if task else None


async def update_task_deadline(
    db: Database,
    task_id: int,
    deadline: Optional[datetime],
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Update task deadline."""
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    old_deadline = current.get("deadline")

    task = await db.fetch_one(
        """
        UPDATE tasks SET
            deadline = $2,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        task_id, deadline
    )

    await add_task_history(
        db, task_id, user_id,
        action="deadline_changed",
        field_name="deadline",
        old_value=str(old_deadline) if old_deadline else None,
        new_value=str(deadline) if deadline else None
    )

    # Sync to Google Calendar
    if deadline and task:
        try:
            from services.calendar_service import (
                is_calendar_enabled,
                get_user_token_data,
                create_calendar_event,
                update_calendar_event,
            )
            if is_calendar_enabled():
                assignee_id = current.get("assignee_id")
                token_data = await get_user_token_data(db, assignee_id)
                if token_data:
                    event_id = current.get("google_event_id")
                    if event_id:
                        # Update existing event
                        await update_calendar_event(
                            token_data, event_id,
                            current["public_id"], current["content"],
                            deadline, current.get("description", ""),
                            current.get("priority", "normal"),
                            current.get("status", "pending"),
                        )
                    else:
                        # Create new event
                        new_event_id = await create_calendar_event(
                            token_data,
                            current["public_id"], current["content"],
                            deadline, current.get("description", ""),
                            current.get("priority", "normal"),
                        )
                        if new_event_id:
                            await db.execute(
                                "UPDATE tasks SET google_event_id = $2 WHERE id = $1",
                                task_id, new_event_id
                            )
        except Exception as e:
            logger.warning(f"Calendar sync failed for task {task_id}: {e}")

    return dict(task) if task else None


async def update_task_priority(
    db: Database,
    task_id: int,
    priority: str,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Update task priority."""
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    old_priority = current.get("priority", "normal")

    task = await db.fetch_one(
        """
        UPDATE tasks SET
            priority = $2,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        task_id, priority
    )

    await add_task_history(
        db, task_id, user_id,
        action="priority_changed",
        field_name="priority",
        old_value=old_priority,
        new_value=priority
    )

    return dict(task) if task else None


async def update_task_assignee(
    db: Database,
    task_id: int,
    new_assignee_id: int,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Update task assignee."""
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    old_assignee_id = current.get("assignee_id")

    # Get old assignee name
    old_assignee = await db.fetch_one(
        "SELECT display_name FROM users WHERE id = $1",
        old_assignee_id
    )
    old_name = old_assignee["display_name"] if old_assignee else str(old_assignee_id)

    # Get new assignee name
    new_assignee = await db.fetch_one(
        "SELECT display_name FROM users WHERE id = $1",
        new_assignee_id
    )
    new_name = new_assignee["display_name"] if new_assignee else str(new_assignee_id)

    task = await db.fetch_one(
        """
        UPDATE tasks SET
            assignee_id = $2,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        task_id, new_assignee_id
    )

    await add_task_history(
        db, task_id, user_id,
        action="assignee_changed",
        field_name="assignee_id",
        old_value=old_name,
        new_value=new_name
    )

    return dict(task) if task else None


async def soft_delete_task(
    db: Database,
    task_id: int,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Soft delete task with 30-second undo window.

    Args:
        db: Database connection
        task_id: Task ID
        user_id: User deleting the task

    Returns:
        Undo record for restoring
    """
    task = await get_task_by_id(db, task_id)
    if not task:
        return None

    # Store in undo buffer
    expires_at = datetime.now() + timedelta(seconds=30)
    undo = await db.fetch_one(
        """
        INSERT INTO deleted_tasks_undo (task_id, task_data, deleted_by, expires_at)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        task_id,
        json.dumps(task, default=str),
        user_id,
        expires_at
    )

    # Mark task as deleted
    await db.execute(
        """
        UPDATE tasks SET
            is_deleted = true,
            deleted_at = NOW(),
            deleted_by = $2,
            updated_at = NOW()
        WHERE id = $1
        """,
        task_id, user_id
    )

    # Log history
    await add_task_history(
        db, task_id, user_id,
        action="deleted",
        note="Task deleted (30s undo available)"
    )

    return dict(undo) if undo else None


async def restore_task(db: Database, undo_id: int) -> Optional[Dict[str, Any]]:
    """
    Restore deleted task from undo buffer.

    Args:
        db: Database connection
        undo_id: Undo record ID

    Returns:
        Restored task record
    """
    # Get undo record
    undo = await db.fetch_one(
        """
        SELECT * FROM deleted_tasks_undo
        WHERE id = $1 AND is_restored = false AND expires_at > NOW()
        """,
        undo_id
    )

    if not undo:
        return None

    task_id = undo["task_id"]

    # Restore task
    await db.execute(
        """
        UPDATE tasks SET
            is_deleted = false,
            deleted_at = NULL,
            deleted_by = NULL,
            updated_at = NOW()
        WHERE id = $1
        """,
        task_id
    )

    # Mark undo as used
    await db.execute(
        "UPDATE deleted_tasks_undo SET is_restored = true WHERE id = $1",
        undo_id
    )

    # Log history
    await add_task_history(
        db, task_id, undo["deleted_by"],
        action="restored",
        note="Task restored from undo"
    )

    return await get_task_by_id(db, task_id)


async def get_tasks_created_by_user(
    db: Database,
    user_id: int,
    include_assigned_to_others: bool = True,
) -> List[Dict[str, Any]]:
    """
    Get all non-deleted tasks created by user.

    Args:
        db: Database connection
        user_id: Creator user ID
        include_assigned_to_others: Include tasks assigned to others

    Returns:
        List of tasks
    """
    if include_assigned_to_others:
        query = """
            SELECT t.*, u.display_name as assignee_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            WHERE t.creator_id = $1 AND t.is_deleted = false
            ORDER BY t.created_at DESC
        """
    else:
        # Only tasks assigned to self
        query = """
            SELECT t.*, u.display_name as assignee_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            WHERE t.creator_id = $1 AND t.assignee_id = $1 AND t.is_deleted = false
            ORDER BY t.created_at DESC
        """

    tasks = await db.fetch_all(query, user_id)
    return [dict(t) for t in tasks]


async def get_tasks_assigned_to_others(
    db: Database,
    creator_id: int,
) -> List[Dict[str, Any]]:
    """
    Get tasks created by user but assigned to others (not self).

    Args:
        db: Database connection
        creator_id: Creator user ID

    Returns:
        List of tasks assigned to others
    """
    tasks = await db.fetch_all(
        """
        SELECT t.*, u.display_name as assignee_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE t.creator_id = $1
          AND t.assignee_id != $1
          AND t.is_deleted = false
          AND t.parent_task_id IS NULL
        ORDER BY t.created_at DESC
        """,
        creator_id
    )
    return [dict(t) for t in tasks]


async def bulk_delete_tasks(
    db: Database,
    task_ids: List[int],
    user_id: int,
) -> int:
    """
    Bulk delete multiple tasks (no undo).

    Args:
        db: Database connection
        task_ids: List of task IDs to delete
        user_id: User performing deletion

    Returns:
        Number of tasks deleted
    """
    if not task_ids:
        return 0

    # Mark tasks as deleted
    result = await db.execute(
        """
        UPDATE tasks SET
            is_deleted = true,
            deleted_at = NOW(),
            deleted_by = $2,
            updated_at = NOW()
        WHERE id = ANY($1) AND is_deleted = false
        """,
        task_ids, user_id
    )

    # Also delete child tasks (for group tasks)
    await db.execute(
        """
        UPDATE tasks SET
            is_deleted = true,
            deleted_at = NOW(),
            deleted_by = $2,
            updated_at = NOW()
        WHERE parent_task_id = ANY($1) AND is_deleted = false
        """,
        task_ids, user_id
    )

    return len(task_ids)


async def add_task_history(
    db: Database,
    task_id: int,
    user_id: int,
    action: str,
    field_name: str = None,
    old_value: str = None,
    new_value: str = None,
    note: str = None,
) -> None:
    """Add entry to task history."""
    await db.execute(
        """
        INSERT INTO task_history (task_id, user_id, action, field_name, old_value, new_value, note)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        task_id, user_id, action, field_name, old_value, new_value, note
    )


async def create_default_reminders(
    db: Database,
    task_id: int,
    user_id: int,
    deadline: datetime,
) -> None:
    """Create default reminders for a task."""
    # Reminder 24h before
    remind_24h = deadline - timedelta(hours=24)
    if remind_24h > datetime.now(TZ):
        await db.execute(
            """
            INSERT INTO reminders (task_id, user_id, remind_at, reminder_type, reminder_offset)
            VALUES ($1, $2, $3, 'before_deadline', '24h')
            """,
            task_id, user_id, remind_24h
        )

    # Reminder 1h before
    remind_1h = deadline - timedelta(hours=1)
    if remind_1h > datetime.now(TZ):
        await db.execute(
            """
            INSERT INTO reminders (task_id, user_id, remind_at, reminder_type, reminder_offset)
            VALUES ($1, $2, $3, 'before_deadline', '1h')
            """,
            task_id, user_id, remind_1h
        )


async def get_tasks_with_deadline(
    db: Database,
    hours: int = 24,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get tasks with deadline within specified hours."""
    deadline_cutoff = datetime.now(TZ) + timedelta(hours=hours)

    conditions = [
        "is_deleted = false",
        "status != 'completed'",
        "deadline IS NOT NULL",
        "deadline <= $1"
    ]
    params = [deadline_cutoff]

    if user_id:
        conditions.append(f"assignee_id = ${len(params) + 1}")
        params.append(user_id)

    query = f"""
        SELECT t.*, u.display_name as assignee_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY t.deadline ASC
    """

    tasks = await db.fetch_all(query, *params)
    return [dict(t) for t in tasks]


# ============================================
# GROUP TASK FUNCTIONS (G-ID / P-ID System)
# ============================================

async def create_group_task(
    db: Database,
    content: str,
    creator_id: int,
    assignees: List[Dict[str, Any]],
    deadline: Optional[datetime] = None,
    priority: str = "normal",
    group_id: Optional[int] = None,
    description: str = None,
) -> tuple:
    """
    Create group task with individual assignments.

    Args:
        db: Database connection
        content: Task content
        creator_id: Creator user ID
        assignees: List of assignee user dicts
        deadline: Task deadline
        priority: Task priority
        group_id: Telegram group ID
        description: Optional description

    Returns:
        Tuple of (parent_task, list of (child_task, assignee))
    """
    # Generate G-ID for parent
    group_task_id = await generate_task_id(db, prefix="G")

    # Create parent task (container)
    parent = await db.fetch_one(
        """
        INSERT INTO tasks (
            public_id, content, description, creator_id,
            deadline, priority, is_personal, group_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, false, $7)
        RETURNING *
        """,
        group_task_id,
        content,
        description,
        creator_id,
        deadline,
        priority,
        group_id,
    )

    # Log history for parent
    await add_task_history(
        db, parent["id"], creator_id,
        action="created",
        note=f"Group task created with {len(assignees)} assignees"
    )

    # Create individual P-IDs for each assignee
    individual_tasks = []
    parent_id = parent["id"]  # Integer ID for FK

    for assignee in assignees:
        personal_id = await generate_task_id(db, prefix="P")

        task = await db.fetch_one(
            """
            INSERT INTO tasks (
                public_id, group_task_id, parent_task_id, content, description,
                creator_id, assignee_id, deadline, priority,
                is_personal, group_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, false, $10)
            RETURNING *
            """,
            personal_id,
            group_task_id,
            parent_id,
            content,
            description,
            creator_id,
            assignee["id"],
            deadline,
            priority,
            group_id,
        )

        # Log history
        await add_task_history(
            db, task["id"], creator_id,
            action="created",
            note=f"Individual task for {assignee.get('display_name', 'user')}"
        )

        # Create reminders
        if deadline:
            await create_default_reminders(db, task["id"], assignee["id"], deadline)

        individual_tasks.append((dict(task), assignee))

    logger.info(f"Created group task {group_task_id} with {len(assignees)} P-IDs")
    return dict(parent), individual_tasks


async def get_group_task_progress(
    db: Database,
    group_task_id: str,
) -> Dict[str, Any]:
    """
    Get aggregated progress for group task.

    Args:
        db: Database connection
        group_task_id: Parent G-ID

    Returns:
        Dict with total, completed, progress, members, is_complete
    """
    result = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COALESCE(AVG(progress), 0) as avg_progress
        FROM tasks
        WHERE group_task_id = $1 AND is_deleted = false
        """,
        group_task_id,
    )

    # Get individual member status
    members = await db.fetch_all(
        """
        SELECT t.public_id, t.status, t.progress, t.completed_at,
               u.display_name as assignee_name, u.telegram_id
        FROM tasks t
        JOIN users u ON t.assignee_id = u.id
        WHERE t.group_task_id = $1 AND t.is_deleted = false
        ORDER BY t.created_at
        """,
        group_task_id,
    )

    total = result["total"] or 0
    completed = result["completed"] or 0

    return {
        "total": total,
        "completed": completed,
        "progress": int(result["avg_progress"] or 0),
        "members": [dict(m) for m in members],
        "is_complete": total > 0 and completed == total,
    }


async def get_child_tasks(
    db: Database,
    group_task_id: str,
) -> List[Dict[str, Any]]:
    """
    Get all child P-ID tasks under a G-ID.

    Args:
        db: Database connection
        group_task_id: Parent G-ID

    Returns:
        List of child task records
    """
    tasks = await db.fetch_all(
        """
        SELECT t.*, u.display_name as assignee_name, u.username as assignee_username, u.telegram_id
        FROM tasks t
        JOIN users u ON t.assignee_id = u.id
        WHERE t.group_task_id = $1 AND t.is_deleted = false
        ORDER BY t.created_at
        """,
        group_task_id,
    )
    return [dict(t) for t in tasks]


async def check_and_complete_group_task(
    db: Database,
    task_id: int,
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Check if group task should be completed after individual update.

    Args:
        db: Database connection
        task_id: Individual task ID
        user_id: User making the update

    Returns:
        Group task if completed, None otherwise
    """
    # Get task with group_task_id
    task = await db.fetch_one(
        "SELECT group_task_id FROM tasks WHERE id = $1",
        task_id
    )

    if not task or not task["group_task_id"]:
        return None

    group_task_id = task["group_task_id"]

    # Get group progress
    progress = await get_group_task_progress(db, group_task_id)

    if progress["is_complete"]:
        # Mark parent as complete
        parent = await db.fetch_one(
            """
            UPDATE tasks SET
                status = 'completed',
                progress = 100,
                completed_at = NOW(),
                updated_at = NOW()
            WHERE public_id = $1
            RETURNING *
            """,
            group_task_id,
        )

        await add_task_history(
            db, parent["id"], user_id,
            action="status_changed",
            field_name="status",
            old_value="in_progress",
            new_value="completed",
            note="All members completed"
        )

        logger.info(f"Group task {group_task_id} completed (all members done)")
        return dict(parent)

    # Update parent progress
    await db.execute(
        """
        UPDATE tasks SET
            progress = $2,
            status = CASE WHEN $2 > 0 THEN 'in_progress' ELSE status END,
            updated_at = NOW()
        WHERE public_id = $1
        """,
        group_task_id,
        progress["progress"],
    )

    return None


async def is_group_task(db: Database, public_id: str) -> bool:
    """Check if task is a group task (G-ID or GXXXX)."""
    upper_id = public_id.upper()
    # Check G- prefix or G followed by digits (G0041, G-0041, etc.)
    if upper_id.startswith("G-"):
        return True
    if upper_id.startswith("G") and len(upper_id) > 1 and upper_id[1:].lstrip("0").isdigit():
        return True
    return False


async def convert_individual_to_group(
    db: Database,
    task_id: int,
    assignees: List[Dict[str, Any]],
    modifier_id: int,
) -> tuple:
    """
    Convert individual task to group task with multiple assignees.

    Args:
        db: Database connection
        task_id: Task ID (integer)
        assignees: List of assignee user dicts (must have 2+ assignees)
        modifier_id: User making the change

    Returns:
        Tuple of (group_task, list of child_tasks)
    """
    # Get original task
    task = await db.fetch_one("SELECT * FROM tasks WHERE id = $1", task_id)
    if not task:
        return None, []

    # Generate G-ID for new parent
    group_task_id = await generate_task_id(db, prefix="G")

    # Create parent task
    parent = await db.fetch_one(
        """
        INSERT INTO tasks (
            public_id, content, description, creator_id,
            deadline, priority, is_personal, group_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, false, $7)
        RETURNING *
        """,
        group_task_id,
        task["content"],
        task.get("description"),
        task["creator_id"],
        task.get("deadline"),
        task.get("priority", "normal"),
        task.get("group_id"),
    )

    parent_id = parent["id"]

    # Create P-IDs for each assignee
    child_tasks = []
    for assignee in assignees:
        personal_id = await generate_task_id(db, prefix="P")
        child = await db.fetch_one(
            """
            INSERT INTO tasks (
                public_id, group_task_id, parent_task_id, content, description,
                creator_id, assignee_id, deadline, priority,
                is_personal, group_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, false, $10)
            RETURNING *
            """,
            personal_id,
            group_task_id,
            parent_id,
            task["content"],
            task.get("description"),
            task["creator_id"],
            assignee["id"],
            task.get("deadline"),
            task.get("priority", "normal"),
            task.get("group_id"),
        )
        child_tasks.append((dict(child), assignee))

        # Create reminders
        if task.get("deadline"):
            await create_default_reminders(db, child["id"], assignee["id"], task["deadline"])

    # Soft delete original task
    await db.execute(
        """
        UPDATE tasks SET
            is_deleted = true,
            deleted_at = NOW(),
            deleted_by = $2
        WHERE id = $1
        """,
        task_id, modifier_id
    )

    # Log history
    await add_task_history(
        db, parent_id, modifier_id,
        action="converted",
        note=f"Converted from {task['public_id']} to group task with {len(assignees)} assignees"
    )

    logger.info(f"Converted task {task['public_id']} to group task {group_task_id}")
    return dict(parent), child_tasks


async def update_group_assignees(
    db: Database,
    group_task_id: str,
    assignees: List[Dict[str, Any]],
    modifier_id: int,
) -> List[tuple]:
    """
    Update assignees for a group task (add/remove P-IDs).

    Args:
        db: Database connection
        group_task_id: G-ID of parent task
        assignees: New list of assignee user dicts
        modifier_id: User making the change

    Returns:
        List of (child_task, assignee) tuples
    """
    # Get parent task
    parent = await get_task_by_public_id(db, group_task_id)
    if not parent:
        return []

    # Get current child tasks
    current_children = await get_child_tasks(db, group_task_id)
    current_assignee_ids = {c["assignee_id"] for c in current_children}
    new_assignee_ids = {a["id"] for a in assignees}

    # Find assignees to add and remove
    to_remove = current_assignee_ids - new_assignee_ids
    to_add = [a for a in assignees if a["id"] not in current_assignee_ids]

    # Soft delete removed assignees' tasks
    for child in current_children:
        if child["assignee_id"] in to_remove:
            await db.execute(
                """
                UPDATE tasks SET
                    is_deleted = true,
                    deleted_at = NOW(),
                    deleted_by = $2
                WHERE id = $1
                """,
                child["id"], modifier_id
            )

    # Add new P-IDs
    new_children = []
    for assignee in to_add:
        personal_id = await generate_task_id(db, prefix="P")
        child = await db.fetch_one(
            """
            INSERT INTO tasks (
                public_id, group_task_id, parent_task_id, content, description,
                creator_id, assignee_id, deadline, priority,
                is_personal, group_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, false, $10)
            RETURNING *
            """,
            personal_id,
            group_task_id,
            parent["id"],
            parent["content"],
            parent.get("description"),
            parent["creator_id"],
            assignee["id"],
            parent.get("deadline"),
            parent.get("priority", "normal"),
            parent.get("group_id"),
        )
        new_children.append((dict(child), assignee))

        if parent.get("deadline"):
            await create_default_reminders(db, child["id"], assignee["id"], parent["deadline"])

    # Log history
    await add_task_history(
        db, parent["id"], modifier_id,
        action="updated_assignees",
        note=f"Added {len(to_add)}, removed {len(to_remove)} assignees"
    )

    logger.info(f"Updated group {group_task_id}: +{len(to_add)}, -{len(to_remove)}")
    return new_children
