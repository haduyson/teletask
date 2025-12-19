"""
Statistics Service
Calculate and store user statistics
"""

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

import pytz

from utils.db_utils import get_report_column, InvalidColumnError

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


async def calculate_user_stats(
    db,
    user_id: int,
    period_type: str,
    period_start: date,
    period_end: date,
    group_id: Optional[int] = None,
) -> Dict[str, int]:
    """Calculate stats for user in period."""

    base_query = """
        SELECT
            COUNT(*) FILTER (WHERE creator_id = $1) as assigned_total,
            COUNT(*) FILTER (WHERE creator_id = $1 AND status = 'completed') as assigned_completed,
            COUNT(*) FILTER (WHERE creator_id = $1 AND status != 'completed' AND deadline < CURRENT_TIMESTAMP) as assigned_overdue,

            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id != $1) as received_total,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id != $1 AND status = 'completed') as received_completed,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id != $1 AND status != 'completed' AND deadline < CURRENT_TIMESTAMP) as received_overdue,

            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id = $1 AND is_personal = true) as personal_total,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id = $1 AND is_personal = true AND status = 'completed') as personal_completed
        FROM tasks
        WHERE is_deleted = false
          AND created_at >= $2
          AND created_at < $3
    """

    if group_id:
        base_query += " AND group_id = $4"
        row = await db.fetch_one(base_query, user_id, period_start, period_end, group_id)
    else:
        row = await db.fetch_one(base_query, user_id, period_start, period_end)

    if row:
        return {
            "assigned_total": row["assigned_total"] or 0,
            "assigned_completed": row["assigned_completed"] or 0,
            "assigned_overdue": row["assigned_overdue"] or 0,
            "received_total": row["received_total"] or 0,
            "received_completed": row["received_completed"] or 0,
            "received_overdue": row["received_overdue"] or 0,
            "personal_total": row["personal_total"] or 0,
            "personal_completed": row["personal_completed"] or 0,
        }
    return {}


async def calculate_all_time_stats(db, user_id: int) -> Dict[str, int]:
    """Calculate all-time stats for user."""
    row = await db.fetch_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE creator_id = $1) as total_assigned,
            COUNT(*) FILTER (WHERE creator_id = $1 AND status = 'completed') as assigned_done,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id != $1) as total_received,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND creator_id != $1 AND status = 'completed') as received_done,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND is_personal = true) as total_personal,
            COUNT(*) FILTER (WHERE assignee_id = $1 AND is_personal = true AND status = 'completed') as personal_done
        FROM tasks
        WHERE is_deleted = false AND (creator_id = $1 OR assignee_id = $1)
        """,
        user_id,
    )

    if row:
        return {
            "total_assigned": row["total_assigned"] or 0,
            "assigned_done": row["assigned_done"] or 0,
            "total_received": row["total_received"] or 0,
            "received_done": row["received_done"] or 0,
            "total_personal": row["total_personal"] or 0,
            "personal_done": row["personal_done"] or 0,
        }
    return {}


async def store_user_stats(
    db,
    user_id: int,
    group_id: Optional[int],
    period_type: str,
    stats: Dict[str, int],
    period_start: date,
    period_end: date,
) -> None:
    """Store calculated stats."""
    await db.execute(
        """
        INSERT INTO user_statistics (
            user_id, group_id, period_type, period_start, period_end,
            tasks_assigned_total, tasks_assigned_completed, tasks_assigned_overdue,
            tasks_received_total, tasks_received_completed, tasks_received_overdue,
            tasks_personal_total, tasks_personal_completed
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (user_id, COALESCE(group_id, 0), period_type, period_start)
        DO UPDATE SET
            tasks_assigned_total = $6,
            tasks_assigned_completed = $7,
            tasks_assigned_overdue = $8,
            tasks_received_total = $9,
            tasks_received_completed = $10,
            tasks_received_overdue = $11,
            tasks_personal_total = $12,
            tasks_personal_completed = $13,
            updated_at = CURRENT_TIMESTAMP
        """,
        user_id,
        group_id,
        period_type,
        period_start,
        period_end,
        stats.get("assigned_total", 0),
        stats.get("assigned_completed", 0),
        stats.get("assigned_overdue", 0),
        stats.get("received_total", 0),
        stats.get("received_completed", 0),
        stats.get("received_overdue", 0),
        stats.get("personal_total", 0),
        stats.get("personal_completed", 0),
    )


def get_week_range() -> tuple:
    """Get current week's start/end (Mon-Sun)."""
    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=7)
    return start, end


def get_previous_week_range() -> tuple:
    """Get previous week's start/end."""
    today = datetime.now(TZ).date()
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=7)
    return start, end


def get_month_range() -> tuple:
    """Get current month's start/end."""
    today = datetime.now(TZ).date()
    start = today.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month


def get_previous_month_range() -> tuple:
    """Get previous month's start/end."""
    today = datetime.now(TZ).date()
    end = today.replace(day=1)
    if end.month == 1:
        start = end.replace(year=end.year - 1, month=12)
    else:
        start = end.replace(month=end.month - 1)
    return start, end


async def get_group_rankings(
    db, group_id: int, period_type: str, period_start: date
) -> List[Dict[str, Any]]:
    """Get user rankings in group."""
    rows = await db.fetch_all(
        """
        SELECT us.*, u.display_name, u.username,
               CASE
                   WHEN us.tasks_received_total > 0
                   THEN (us.tasks_received_completed::float / us.tasks_received_total * 100)
                   ELSE 0
               END as completion_rate
        FROM user_statistics us
        JOIN users u ON us.user_id = u.id
        WHERE us.group_id = $1
          AND us.period_type = $2
          AND us.period_start = $3
        ORDER BY completion_rate DESC NULLS LAST
        """,
        group_id,
        period_type,
        period_start,
    )
    return [dict(r) for r in rows]


async def get_active_users_for_report(db, report_type: str = "weekly") -> List[Dict]:
    """Get users who have report notification enabled."""
    try:
        column = get_report_column(report_type)
    except InvalidColumnError:
        logger.warning(f"Invalid report type: {report_type}")
        return []

    # Use validated column - safe from SQL injection
    rows = await db.fetch_all(
        f"""
        SELECT id, telegram_id, display_name, username
        FROM users
        WHERE is_active = true AND {column} = true
        """
    )
    return [dict(r) for r in rows]


async def get_user_groups(db, user_id: int) -> List[Dict]:
    """Get groups user belongs to."""
    rows = await db.fetch_all(
        """
        SELECT g.id, g.title
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = $1 AND g.is_active = true
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def get_overdue_tasks(
    db,
    user_id: int,
    period: str = "all",
) -> List[Dict[str, Any]]:
    """
    Get overdue tasks for user.

    Args:
        db: Database connection
        user_id: User ID
        period: Filter period - 'day' (today), 'week', 'month', 'all'

    Returns:
        List of overdue task records
    """
    now = datetime.now(TZ)

    # Build date filter based on period
    if period == "day":
        # Today only
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_filter = "AND deadline >= $3"
    elif period == "week":
        # This week (Mon-Sun)
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        period_start = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=TZ)
        period_filter = "AND deadline >= $3"
    elif period == "month":
        # This month
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_filter = "AND deadline >= $3"
    else:
        # All overdue
        period_start = None
        period_filter = ""

    base_query = f"""
        SELECT t.*, u.display_name as creator_name,
               g.title as group_name
        FROM tasks t
        LEFT JOIN users u ON t.creator_id = u.id
        LEFT JOIN groups g ON t.group_id = g.id
        WHERE (t.assignee_id = $1 OR t.creator_id = $1)
          AND t.is_deleted = false
          AND t.status != 'completed'
          AND t.deadline IS NOT NULL
          AND t.deadline < $2
          {period_filter}
        ORDER BY t.deadline ASC
    """

    if period_start:
        rows = await db.fetch_all(base_query, user_id, now, period_start)
    else:
        rows = await db.fetch_all(base_query.replace("$3", ""), user_id, now)

    return [dict(r) for r in rows]


async def get_overdue_stats(
    db,
    user_id: int,
) -> Dict[str, int]:
    """
    Get overdue task counts by period.

    Args:
        db: Database connection
        user_id: User ID

    Returns:
        Dict with overdue counts: today, this_week, this_month, total
    """
    now = datetime.now(TZ)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = datetime.combine(
        now.date() - timedelta(days=now.date().weekday()),
        datetime.min.time()
    ).replace(tzinfo=TZ)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    row = await db.fetch_one(
        """
        SELECT
            COUNT(*) FILTER (WHERE deadline >= $3) as today,
            COUNT(*) FILTER (WHERE deadline >= $4) as this_week,
            COUNT(*) FILTER (WHERE deadline >= $5) as this_month,
            COUNT(*) as total
        FROM tasks
        WHERE (assignee_id = $1 OR creator_id = $1)
          AND is_deleted = false
          AND status != 'completed'
          AND deadline IS NOT NULL
          AND deadline < $2
        """,
        user_id, now, today_start, week_start, month_start,
    )

    if row:
        return {
            "today": row["today"] or 0,
            "this_week": row["this_week"] or 0,
            "this_month": row["this_month"] or 0,
            "total": row["total"] or 0,
        }
    return {"today": 0, "this_week": 0, "this_month": 0, "total": 0}
