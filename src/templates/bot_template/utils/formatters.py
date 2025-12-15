"""
Message Formatters
Format task data for display
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import pytz

from .messages import (
    MSG_TASK_DETAIL,
    MSG_TASK_LIST,
    MSG_TASK_LIST_EMPTY,
    MSG_TASK_LIST_ITEM,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_HIGH,
    PRIORITY_URGENT,
    ICON_PENDING,
    ICON_IN_PROGRESS,
    ICON_COMPLETED,
    ICON_OVERDUE,
    ICON_URGENT,
    ICON_HIGH,
)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def format_status(status: str) -> str:
    """Format status to Vietnamese label."""
    status_map = {
        "pending": STATUS_PENDING,
        "in_progress": STATUS_IN_PROGRESS,
        "completed": STATUS_COMPLETED,
        "cancelled": STATUS_CANCELLED,
    }
    return status_map.get(status, status)


def format_priority(priority: str) -> str:
    """Format priority to Vietnamese label."""
    priority_map = {
        "low": PRIORITY_LOW,
        "normal": PRIORITY_NORMAL,
        "high": PRIORITY_HIGH,
        "urgent": PRIORITY_URGENT,
    }
    return priority_map.get(priority, priority)


def get_status_icon(task: Dict[str, Any]) -> str:
    """Get icon based on task status and deadline."""
    status = task.get("status", "pending")
    priority = task.get("priority", "normal")
    deadline = task.get("deadline")

    # Completed
    if status == "completed":
        return ICON_COMPLETED

    # Check overdue
    if deadline and isinstance(deadline, datetime):
        now = datetime.now(TZ)
        if deadline.tzinfo is None:
            deadline = TZ.localize(deadline)
        else:
            deadline = deadline.astimezone(TZ)
        if deadline < now:
            return ICON_OVERDUE

    # Priority icons
    if priority == "urgent":
        return ICON_URGENT
    elif priority == "high":
        return ICON_HIGH

    # Status icons
    if status == "in_progress":
        return ICON_IN_PROGRESS

    return ICON_PENDING


def format_datetime(dt: Optional[datetime], relative: bool = False) -> str:
    """Format datetime for display in Vietnam timezone."""
    if not dt:
        return "Không có"

    # Convert to Vietnam timezone
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
    else:
        dt = dt.astimezone(TZ)

    # Format: HH:MM [weekday], DD/MM/YYYY
    time_str = dt.strftime("%H:%M")
    date_str = dt.strftime("%d/%m/%Y")
    weekdays = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
    weekday_str = weekdays[dt.weekday()]

    if relative:
        now = datetime.now(TZ)
        delta = (dt.date() - now.date()).days

        if delta == 0:
            return f"{time_str} Hôm nay, {date_str}"
        elif delta == 1:
            return f"{time_str} Ngày mai, {date_str}"
        elif delta == 2:
            return f"{time_str} Ngày kia, {date_str}"
        elif delta == -1:
            return f"{time_str} Hôm qua, {date_str}"

    return f"{time_str} {weekday_str}, {date_str}"


def format_task_detail(task: Dict[str, Any]) -> str:
    """Format task for detailed view."""
    return MSG_TASK_DETAIL.format(
        task_id=task.get("public_id", ""),
        content=task.get("content", ""),
        status=format_status(task.get("status", "pending")),
        progress=task.get("progress", 0),
        priority=format_priority(task.get("priority", "normal")),
        creator=task.get("creator_name", "N/A"),
        assignee=task.get("assignee_name", "N/A"),
        deadline=format_datetime(task.get("deadline"), relative=True),
        created_at=format_datetime(task.get("created_at")),
        updated_at=format_datetime(task.get("updated_at")),
    )


def format_task_list(
    tasks: List[Dict[str, Any]],
    title: str,
    page: int = 1,
    page_size: int = 10,
    total: Optional[int] = None,
) -> str:
    """Format task list for display."""
    if not tasks:
        return MSG_TASK_LIST_EMPTY

    total = total or len(tasks)
    total_pages = (total + page_size - 1) // page_size

    task_lines = []
    for task in tasks:
        icon = get_status_icon(task)
        deadline_str = format_datetime(task.get("deadline"), relative=True)

        content = task.get("content", "")
        if len(content) > 30:
            content = content[:27] + "..."

        line = MSG_TASK_LIST_ITEM.format(
            icon=icon,
            task_id=task.get("public_id", ""),
            content=content,
            deadline=deadline_str,
        )
        task_lines.append(line)

    return MSG_TASK_LIST.format(
        title=title,
        tasks="\n".join(task_lines),
        page=page,
        total_pages=total_pages,
        total=total,
    )


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def mention_user(user: Dict[str, Any]) -> str:
    """
    Create Telegram mention link for user.
    Format: [Display Name](tg://user?id=telegram_id)
    Works even if user has no username.
    """
    display_name = user.get("display_name") or user.get("username") or "User"
    telegram_id = user.get("telegram_id")

    if telegram_id:
        return f"[{display_name}](tg://user?id={telegram_id})"
    return display_name


def mention_user_html(user: Dict[str, Any]) -> str:
    """
    Create Telegram mention link for user (HTML format).
    Format: <a href="tg://user?id=telegram_id">Display Name</a>
    """
    display_name = user.get("display_name") or user.get("username") or "User"
    telegram_id = user.get("telegram_id")

    if telegram_id:
        return f'<a href="tg://user?id={telegram_id}">{display_name}</a>'
    return display_name


def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for char in chars:
        text = text.replace(char, f"\\{char}")
    return text


def progress_bar(percentage: float, width: int = 10) -> str:
    """Create a visual progress bar."""
    filled = int(width * percentage / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def format_stats_overview(stats: Dict[str, Any], name: str) -> str:
    """Format all-time statistics overview."""
    total_assigned = stats.get("total_assigned", 0)
    assigned_done = stats.get("assigned_done", 0)
    total_received = stats.get("total_received", 0)
    received_done = stats.get("received_done", 0)
    total_personal = stats.get("total_personal", 0)
    personal_done = stats.get("personal_done", 0)

    assigned_rate = (assigned_done / max(total_assigned, 1)) * 100
    received_rate = (received_done / max(total_received, 1)) * 100
    personal_rate = (personal_done / max(total_personal, 1)) * 100

    total = total_assigned + total_received + total_personal
    completed = assigned_done + received_done + personal_done
    overall_rate = (completed / max(total, 1)) * 100

    return f"""📊 THỐNG KÊ TỔNG HỢP
👤 {name}

--- VIỆC BẠN ĐÃ GIAO ---
📊 Tổng: {total_assigned} việc
✅ Hoàn thành: {assigned_done} ({assigned_rate:.0f}%)
📈 {progress_bar(assigned_rate)} {assigned_rate:.0f}%

--- VIỆC BẠN NHẬN ---
📊 Tổng: {total_received} việc
✅ Hoàn thành: {received_done} ({received_rate:.0f}%)
📈 {progress_bar(received_rate)} {received_rate:.0f}%

--- VIỆC CÁ NHÂN ---
📊 Tổng: {total_personal} việc
✅ Hoàn thành: {personal_done} ({personal_rate:.0f}%)
📈 {progress_bar(personal_rate)} {personal_rate:.0f}%

────────────────────────
💪 Hiệu suất tổng: {overall_rate:.0f}%"""


def format_weekly_report(
    name: str,
    stats: Dict[str, Any],
    start,
    end,
    group_rankings: Optional[Dict] = None,
    prev_stats: Optional[Dict] = None,
) -> str:
    """Format weekly report."""
    assigned_total = stats.get("assigned_total", 0)
    assigned_completed = stats.get("assigned_completed", 0)
    assigned_overdue = stats.get("assigned_overdue", 0)

    received_total = stats.get("received_total", 0)
    received_completed = stats.get("received_completed", 0)
    received_overdue = stats.get("received_overdue", 0)

    personal_total = stats.get("personal_total", 0)
    personal_completed = stats.get("personal_completed", 0)

    assigned_rate = (assigned_completed / max(assigned_total, 1)) * 100
    received_rate = (received_completed / max(received_total, 1)) * 100
    personal_rate = (personal_completed / max(personal_total, 1)) * 100

    total = assigned_total + received_total + personal_total
    completed = assigned_completed + received_completed + personal_completed
    overall_rate = (completed / max(total, 1)) * 100

    # Comparison with previous week
    change_text = ""
    if prev_stats:
        prev_total = (
            prev_stats.get("assigned_total", 0)
            + prev_stats.get("received_total", 0)
            + prev_stats.get("personal_total", 0)
        )
        prev_completed = (
            prev_stats.get("assigned_completed", 0)
            + prev_stats.get("received_completed", 0)
            + prev_stats.get("personal_completed", 0)
        )
        prev_rate = (prev_completed / max(prev_total, 1)) * 100
        diff = overall_rate - prev_rate
        if diff > 0:
            change_text = f"\n📈 So với tuần trước: +{diff:.0f}%"
        elif diff < 0:
            change_text = f"\n📉 So với tuần trước: {diff:.0f}%"

    # Rankings text
    rank_text = ""
    if group_rankings:
        rank_lines = [f"🏆 {g}: #{r[0]}/{r[1]}" for g, r in group_rankings.items()]
        rank_text = "\n" + "\n".join(rank_lines)

    return f"""📊 BÁO CÁO CÔNG VIỆC TUẦN
📅 {start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}
👤 {name}

--- VIỆC BẠN ĐÃ GIAO ---
📊 Tổng: {assigned_total} việc
✅ Hoàn thành: {assigned_completed} ({assigned_rate:.0f}%)
🚨 Trễ deadline: {assigned_overdue}
📈 {progress_bar(assigned_rate)} {assigned_rate:.0f}%

--- VIỆC BẠN NHẬN ---
📊 Tổng: {received_total} việc
✅ Hoàn thành: {received_completed} ({received_rate:.0f}%)
🚨 Trễ deadline: {received_overdue}
📈 {progress_bar(received_rate)} {received_rate:.0f}%

--- VIỆC CÁ NHÂN ---
📊 Tổng: {personal_total} việc
✅ Hoàn thành: {personal_completed} ({personal_rate:.0f}%)
📈 {progress_bar(personal_rate)} {personal_rate:.0f}%

────────────────────────
💪 Hiệu suất tuần: {overall_rate:.0f}%{change_text}{rank_text}"""


def format_monthly_report(
    name: str,
    stats: Dict[str, Any],
    prev_stats: Optional[Dict],
    start,
    end,
) -> str:
    """Format monthly report."""
    assigned_total = stats.get("assigned_total", 0)
    assigned_completed = stats.get("assigned_completed", 0)
    assigned_overdue = stats.get("assigned_overdue", 0)

    received_total = stats.get("received_total", 0)
    received_completed = stats.get("received_completed", 0)
    received_overdue = stats.get("received_overdue", 0)

    personal_total = stats.get("personal_total", 0)
    personal_completed = stats.get("personal_completed", 0)

    assigned_rate = (assigned_completed / max(assigned_total, 1)) * 100
    received_rate = (received_completed / max(received_total, 1)) * 100
    personal_rate = (personal_completed / max(personal_total, 1)) * 100

    total = assigned_total + received_total + personal_total
    completed = assigned_completed + received_completed + personal_completed
    overall_rate = (completed / max(total, 1)) * 100

    # Comparison with previous month
    change_text = ""
    if prev_stats:
        prev_total = (
            prev_stats.get("assigned_total", 0)
            + prev_stats.get("received_total", 0)
            + prev_stats.get("personal_total", 0)
        )
        prev_completed = (
            prev_stats.get("assigned_completed", 0)
            + prev_stats.get("received_completed", 0)
            + prev_stats.get("personal_completed", 0)
        )
        prev_rate = (prev_completed / max(prev_total, 1)) * 100
        diff = overall_rate - prev_rate
        if diff > 0:
            change_text = f"\n📈 So với tháng trước: +{diff:.0f}%"
        elif diff < 0:
            change_text = f"\n📉 So với tháng trước: {diff:.0f}%"

    month_name = start.strftime("%m/%Y")

    return f"""📊 BÁO CÁO CÔNG VIỆC THÁNG {month_name}
👤 {name}

--- VIỆC BẠN ĐÃ GIAO ---
📊 Tổng: {assigned_total} việc
✅ Hoàn thành: {assigned_completed} ({assigned_rate:.0f}%)
🚨 Trễ deadline: {assigned_overdue}
📈 {progress_bar(assigned_rate)} {assigned_rate:.0f}%

--- VIỆC BẠN NHẬN ---
📊 Tổng: {received_total} việc
✅ Hoàn thành: {received_completed} ({received_rate:.0f}%)
🚨 Trễ deadline: {received_overdue}
📈 {progress_bar(received_rate)} {received_rate:.0f}%

--- VIỆC CÁ NHÂN ---
📊 Tổng: {personal_total} việc
✅ Hoàn thành: {personal_completed} ({personal_rate:.0f}%)
📈 {progress_bar(personal_rate)} {personal_rate:.0f}%

────────────────────────
💪 Hiệu suất tháng: {overall_rate:.0f}%{change_text}"""
