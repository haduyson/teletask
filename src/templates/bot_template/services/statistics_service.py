"""
Statistics Service
Calculate and store user statistics
"""

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

import pytz

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
        row = await db.fetchrow(base_query, user_id, period_start, period_end, group_id)
    else:
        row = await db.fetchrow(base_query, user_id, period_start, period_end)

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
    row = await db.fetchrow(
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
    rows = await db.fetch(
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
    column = "notify_weekly_report" if report_type == "weekly" else "notify_monthly_report"

    rows = await db.fetch(
        f"""
        SELECT id, telegram_id, display_name, username
        FROM users
        WHERE is_active = true AND {column} = true
        """
    )
    return [dict(r) for r in rows]


async def get_user_groups(db, user_id: int) -> List[Dict]:
    """Get groups user belongs to."""
    rows = await db.fetch(
        """
        SELECT g.id, g.title
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = $1 AND g.is_active = true
        """,
        user_id,
    )
    return [dict(r) for r in rows]
