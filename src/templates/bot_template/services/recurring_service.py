"""
Recurring Task Service
CRUD operations for recurring task templates
"""

import re
import logging
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple
from dateutil.relativedelta import relativedelta
import pytz

from database.connection import Database

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


async def generate_recurring_id(db: Database) -> str:
    """
    Generate unique recurring template ID.

    Args:
        db: Database connection

    Returns:
        Recurring ID like R-0001
    """
    result = await db.fetch_one(
        """
        UPDATE bot_config
        SET value = (CAST(value AS INTEGER) + 1)::TEXT, updated_at = NOW()
        WHERE key = 'recurring_id_counter'
        RETURNING value
        """
    )

    counter = int(result["value"]) if result else 1
    return f"R-{counter:04d}"


async def create_recurring_template(
    db: Database,
    content: str,
    creator_id: int,
    recurrence_type: str,
    recurrence_interval: int = 1,
    recurrence_days: List[int] = None,
    recurrence_time: time = None,
    recurrence_end_date: datetime = None,
    recurrence_count: int = None,
    assignee_id: int = None,
    group_id: int = None,
    priority: str = "normal",
    description: str = None,
    is_personal: bool = True,
) -> Dict[str, Any]:
    """
    Create a new recurring task template.

    Args:
        db: Database connection
        content: Task content template
        creator_id: Creator user ID
        recurrence_type: daily, weekly, or monthly
        recurrence_interval: Every N periods (default 1)
        recurrence_days: Days of week (0-6) or month (1-31)
        recurrence_time: Time of day for deadline
        recurrence_end_date: When to stop generating
        recurrence_count: Max instances to generate
        assignee_id: Default assignee
        group_id: Group ID for group tasks
        priority: Task priority
        description: Optional description
        is_personal: Personal or group template

    Returns:
        Created recurring template record
    """
    public_id = await generate_recurring_id(db)

    # Calculate first next_due
    next_due = calculate_next_due(
        recurrence_type=recurrence_type,
        recurrence_interval=recurrence_interval,
        recurrence_days=recurrence_days,
        recurrence_time=recurrence_time,
        from_date=datetime.now(TZ),
    )

    template = await db.fetch_one(
        """
        INSERT INTO recurring_templates (
            public_id, content, description, priority,
            creator_id, assignee_id, group_id, is_personal,
            recurrence_type, recurrence_interval, recurrence_days,
            recurrence_time, recurrence_end_date, recurrence_count,
            next_due
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING *
        """,
        public_id,
        content,
        description,
        priority,
        creator_id,
        assignee_id or creator_id,
        group_id,
        is_personal,
        recurrence_type,
        recurrence_interval,
        recurrence_days,
        recurrence_time,
        recurrence_end_date,
        recurrence_count,
        next_due,
    )

    logger.info(f"Created recurring template {public_id}: {content[:30]}...")
    return dict(template)


def calculate_next_due(
    recurrence_type: str,
    recurrence_interval: int = 1,
    recurrence_days: List[int] = None,
    recurrence_time: time = None,
    from_date: datetime = None,
    last_generated: datetime = None,
) -> Optional[datetime]:
    """
    Calculate next due date for recurring template.

    Args:
        recurrence_type: daily, weekly, monthly
        recurrence_interval: Every N periods
        recurrence_days: Days of week/month
        recurrence_time: Time of day
        from_date: Start calculating from this date
        last_generated: Last time task was generated

    Returns:
        Next due datetime
    """
    now = datetime.now(TZ)
    base = last_generated or from_date or now

    if base.tzinfo is None:
        base = TZ.localize(base)

    # Default time is 9:00 AM
    target_time = recurrence_time or time(9, 0)

    if recurrence_type == "daily":
        # Every N days
        next_date = base + timedelta(days=recurrence_interval)
        next_date = next_date.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0,
        )
        # Ensure it's in the future
        while next_date <= now:
            next_date += timedelta(days=recurrence_interval)
        return next_date

    elif recurrence_type == "weekly":
        # Days of week (0=Monday, 6=Sunday)
        if not recurrence_days:
            recurrence_days = [base.weekday()]  # Same day as created

        # Find next matching day
        next_date = base + timedelta(days=1)
        while True:
            if next_date.weekday() in recurrence_days:
                candidate = next_date.replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0,
                )
                if candidate > now:
                    return candidate
            next_date += timedelta(days=1)
            # Safety limit: don't loop forever
            if (next_date - base).days > 365:
                break

    elif recurrence_type == "monthly":
        # Days of month (1-31)
        if not recurrence_days:
            recurrence_days = [base.day]  # Same day as created

        # Start from next month if interval > 1
        next_month = base + relativedelta(months=recurrence_interval)

        for day in sorted(recurrence_days):
            try:
                candidate = next_month.replace(
                    day=day,
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0,
                )
                if candidate > now:
                    return candidate
            except ValueError:
                # Day doesn't exist in this month (e.g., Feb 30)
                continue

        # Try next month
        next_month += relativedelta(months=1)
        for day in sorted(recurrence_days):
            try:
                return next_month.replace(
                    day=day,
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0,
                )
            except ValueError:
                continue

    return None


def parse_recurrence_pattern(text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Parse Vietnamese recurrence pattern from text.

    Supported patterns:
    - "hàng ngày" / "mỗi ngày" -> daily
    - "hàng tuần" / "mỗi tuần" -> weekly
    - "hàng tháng" / "mỗi tháng" -> monthly
    - "thứ 2, thứ 4" -> weekly on Mon, Wed
    - "ngày 1, ngày 15" -> monthly on 1st, 15th
    - "mỗi 2 ngày" -> every 2 days
    - "mỗi 2 tuần" -> every 2 weeks

    Args:
        text: Input text

    Returns:
        Tuple of (recurrence config dict, remaining text)
    """
    text_lower = text.lower()
    result = None
    matched_parts = []

    # Daily patterns
    daily_patterns = [
        (r"hàng\s*ngày", 1),
        (r"mỗi\s*ngày", 1),
        (r"mỗi\s*(\d+)\s*ngày", None),  # "mỗi 2 ngày"
    ]

    for pattern, interval in daily_patterns:
        match = re.search(pattern, text_lower)
        if match:
            actual_interval = interval
            if interval is None and match.lastindex >= 1:
                actual_interval = int(match.group(1))
            result = {
                "recurrence_type": "daily",
                "recurrence_interval": actual_interval or 1,
                "recurrence_days": None,
            }
            matched_parts.append(match.group(0))
            text_lower = text_lower.replace(match.group(0), " ")
            break

    # Weekly patterns
    if not result:
        weekly_patterns = [
            (r"hàng\s*tuần", 1),
            (r"mỗi\s*tuần", 1),
            (r"mỗi\s*(\d+)\s*tuần", None),
        ]

        for pattern, interval in weekly_patterns:
            match = re.search(pattern, text_lower)
            if match:
                actual_interval = interval
                if interval is None and match.lastindex >= 1:
                    actual_interval = int(match.group(1))
                result = {
                    "recurrence_type": "weekly",
                    "recurrence_interval": actual_interval or 1,
                    "recurrence_days": None,
                }
                matched_parts.append(match.group(0))
                text_lower = text_lower.replace(match.group(0), " ")
                break

    # Monthly patterns
    if not result:
        monthly_patterns = [
            (r"hàng\s*tháng", 1),
            (r"mỗi\s*tháng", 1),
            (r"mỗi\s*(\d+)\s*tháng", None),
        ]

        for pattern, interval in monthly_patterns:
            match = re.search(pattern, text_lower)
            if match:
                actual_interval = interval
                if interval is None and match.lastindex >= 1:
                    actual_interval = int(match.group(1))
                result = {
                    "recurrence_type": "monthly",
                    "recurrence_interval": actual_interval or 1,
                    "recurrence_days": None,
                }
                matched_parts.append(match.group(0))
                text_lower = text_lower.replace(match.group(0), " ")
                break

    # Extract specific days of week
    if result and result["recurrence_type"] == "weekly":
        weekday_map = {
            "thứ 2": 0, "thứ hai": 0, "t2": 0,
            "thứ 3": 1, "thứ ba": 1, "t3": 1,
            "thứ 4": 2, "thứ tư": 2, "t4": 2,
            "thứ 5": 3, "thứ năm": 3, "t5": 3,
            "thứ 6": 4, "thứ sáu": 4, "t6": 4,
            "thứ 7": 5, "thứ bảy": 5, "t7": 5,
            "chủ nhật": 6, "cn": 6,
        }

        days = []
        for keyword, day_num in weekday_map.items():
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                days.append(day_num)
                text_lower = re.sub(rf"\b{re.escape(keyword)}\b", " ", text_lower)

        if days:
            result["recurrence_days"] = sorted(set(days))

    # Extract specific days of month
    if result and result["recurrence_type"] == "monthly":
        # Pattern: "ngày 1, ngày 15" or "1, 15"
        day_matches = re.findall(r"ngày\s*(\d{1,2})|(?:^|,)\s*(\d{1,2})(?:,|$)", text_lower)
        days = []
        for m in day_matches:
            day = int(m[0] or m[1])
            if 1 <= day <= 31:
                days.append(day)
        if days:
            result["recurrence_days"] = sorted(set(days))
            text_lower = re.sub(r"ngày\s*\d{1,2}[,\s]*", " ", text_lower)

    # Extract time
    time_match = re.search(r"(\d{1,2})h(\d{2})?|(\d{1,2}):(\d{2})", text_lower)
    if time_match and result:
        hour = int(time_match.group(1) or time_match.group(3))
        minute = int(time_match.group(2) or time_match.group(4) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            result["recurrence_time"] = time(hour, minute)
            text_lower = text_lower.replace(time_match.group(0), " ")

    # Clean remaining text
    remaining = re.sub(r"\s+", " ", text_lower).strip()

    return result, remaining


async def get_recurring_template(
    db: Database,
    public_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get recurring template by public ID.

    Args:
        db: Database connection
        public_id: Template public ID (R-xxxx)

    Returns:
        Template record or None
    """
    template = await db.fetch_one(
        """
        SELECT r.*, u.display_name as creator_name, a.display_name as assignee_name
        FROM recurring_templates r
        LEFT JOIN users u ON r.creator_id = u.id
        LEFT JOIN users a ON r.assignee_id = a.id
        WHERE r.public_id = $1
        """,
        public_id.upper(),
    )
    return dict(template) if template else None


async def get_user_recurring_templates(
    db: Database,
    user_id: int,
    active_only: bool = True,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Get recurring templates created by user.

    Args:
        db: Database connection
        user_id: User ID
        active_only: Only return active templates
        limit: Max results

    Returns:
        List of template records
    """
    conditions = ["creator_id = $1"]
    params = [user_id]

    if active_only:
        conditions.append("is_active = true")

    query = f"""
        SELECT r.*, u.display_name as assignee_name
        FROM recurring_templates r
        LEFT JOIN users u ON r.assignee_id = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT ${len(params) + 1}
    """

    templates = await db.fetch_all(query, *params, limit)
    return [dict(t) for t in templates]


async def get_due_templates(db: Database) -> List[Dict[str, Any]]:
    """
    Get templates due for task generation.

    Returns templates where:
    - is_active = true
    - next_due <= now
    - recurrence_end_date is null or > now
    - instances_created < recurrence_count (if set)

    Returns:
        List of due template records
    """
    now = datetime.now(TZ)

    templates = await db.fetch_all(
        """
        SELECT r.*, u.telegram_id as creator_telegram_id
        FROM recurring_templates r
        JOIN users u ON r.creator_id = u.id
        WHERE r.is_active = true
        AND r.next_due <= $1
        AND (r.recurrence_end_date IS NULL OR r.recurrence_end_date > $1)
        AND (r.recurrence_count IS NULL OR r.instances_created < r.recurrence_count)
        ORDER BY r.next_due ASC
        """,
        now,
    )
    return [dict(t) for t in templates]


async def generate_task_from_template(
    db: Database,
    template: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Generate a task instance from recurring template.

    Args:
        db: Database connection
        template: Recurring template record

    Returns:
        Created task record
    """
    from .task_service import create_task

    # Calculate deadline from next_due
    deadline = template["next_due"]

    # Create task
    task = await create_task(
        db=db,
        content=template["content"],
        creator_id=template["creator_id"],
        assignee_id=template["assignee_id"],
        deadline=deadline,
        priority=template["priority"],
        is_personal=template["is_personal"],
        group_id=template["group_id"],
        description=template["description"],
    )

    # Link task to template
    await db.execute(
        "UPDATE tasks SET recurring_template_id = $1 WHERE id = $2",
        template["id"],
        task["id"],
    )

    # Update template: last_generated, instances_created, next_due
    next_due = calculate_next_due(
        recurrence_type=template["recurrence_type"],
        recurrence_interval=template["recurrence_interval"],
        recurrence_days=template["recurrence_days"],
        recurrence_time=template["recurrence_time"],
        last_generated=deadline,
    )

    await db.execute(
        """
        UPDATE recurring_templates SET
            last_generated = $2,
            instances_created = instances_created + 1,
            next_due = $3,
            updated_at = NOW()
        WHERE id = $1
        """,
        template["id"],
        datetime.now(TZ),
        next_due,
    )

    logger.info(f"Generated task {task['public_id']} from template {template['public_id']}")
    return task


async def toggle_recurring_template(
    db: Database,
    template_id: int,
    is_active: bool,
) -> Optional[Dict[str, Any]]:
    """
    Activate or deactivate a recurring template.

    Args:
        db: Database connection
        template_id: Template ID
        is_active: New active state

    Returns:
        Updated template record
    """
    template = await db.fetch_one(
        """
        UPDATE recurring_templates SET
            is_active = $2,
            updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        template_id,
        is_active,
    )
    return dict(template) if template else None


async def delete_recurring_template(
    db: Database,
    template_id: int,
) -> bool:
    """
    Delete a recurring template.

    Args:
        db: Database connection
        template_id: Template ID

    Returns:
        True if deleted
    """
    result = await db.execute(
        "DELETE FROM recurring_templates WHERE id = $1",
        template_id,
    )
    return result > 0


def format_recurrence_description(template: Dict[str, Any]) -> str:
    """
    Format recurrence pattern as Vietnamese description.

    Args:
        template: Template record

    Returns:
        Vietnamese description like "Hàng ngày lúc 9:00"
    """
    rec_type = template["recurrence_type"]
    interval = template["recurrence_interval"] or 1
    days = template["recurrence_days"]
    rec_time = template["recurrence_time"]

    time_str = rec_time.strftime("%H:%M") if rec_time else "9:00"

    if rec_type == "daily":
        if interval == 1:
            return f"Hàng ngày lúc {time_str}"
        return f"Mỗi {interval} ngày lúc {time_str}"

    elif rec_type == "weekly":
        weekday_names = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        if days:
            day_str = ", ".join(weekday_names[d] for d in days)
        else:
            day_str = "mỗi tuần"

        if interval == 1:
            return f"Hàng tuần ({day_str}) lúc {time_str}"
        return f"Mỗi {interval} tuần ({day_str}) lúc {time_str}"

    elif rec_type == "monthly":
        if days:
            day_str = ", ".join(f"ngày {d}" for d in days)
        else:
            day_str = "hàng tháng"

        if interval == 1:
            return f"Hàng tháng ({day_str}) lúc {time_str}"
        return f"Mỗi {interval} tháng ({day_str}) lúc {time_str}"

    return "Không xác định"
