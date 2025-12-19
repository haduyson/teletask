"""
Database Utilities
Security validations for dynamic SQL operations
"""

from typing import Set

# Whitelist of columns allowed for dynamic user setting updates
USER_SETTING_COLUMNS: Set[str] = {
    # Notification settings
    "notify_reminder",
    "notify_weekly_report",
    "notify_monthly_report",
    "notify_task_assigned",
    "notify_task_status",
    "notify_all",
    # Reminder settings
    "remind_24h",
    "remind_1h",
    "remind_30m",
    "remind_5m",
    "remind_overdue",
    "reminder_source",
    # Other settings
    "timezone",
    "calendar_sync_interval",
}

# Whitelist for report type columns
REPORT_TYPE_MAP = {
    "weekly": "notify_weekly_report",
    "monthly": "notify_monthly_report",
}


class InvalidColumnError(ValueError):
    """Raised when column name is not in whitelist."""
    pass


def validate_user_setting_column(column: str) -> str:
    """
    Validate column name against whitelist.

    Args:
        column: Column name to validate

    Returns:
        Validated column name

    Raises:
        InvalidColumnError: If column not in whitelist
    """
    if column not in USER_SETTING_COLUMNS:
        raise InvalidColumnError(f"Invalid column: {column}")
    return column


def get_report_column(report_type: str) -> str:
    """
    Get validated column name for report type.

    Args:
        report_type: 'weekly' or 'monthly'

    Returns:
        Column name

    Raises:
        InvalidColumnError: If invalid report type
    """
    if report_type not in REPORT_TYPE_MAP:
        raise InvalidColumnError(f"Invalid report type: {report_type}")
    return REPORT_TYPE_MAP[report_type]
