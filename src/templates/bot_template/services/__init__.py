"""
Bot Services Module
Business logic and data access services

Services:
- user_service: User CRUD operations
- task_service: Task CRUD operations
- time_parser: Vietnamese time parsing
- reminder_service: Reminder management
- notification: Send notifications
"""

from .time_parser import (
    VietnameseTimeParser,
    parse_vietnamese_time,
)

from .user_service import (
    get_or_create_user,
    get_user_by_telegram_id,
    get_user_by_id,
    get_user_by_username,
    find_users_by_mention,
    update_user_settings,
    get_or_create_group,
    add_group_member,
)

from .task_service import (
    generate_task_id,
    create_task,
    get_task_by_public_id,
    get_task_by_id,
    get_user_tasks,
    get_user_created_tasks,
    get_user_received_tasks,
    get_user_personal_tasks,
    get_all_user_related_tasks,
    get_group_tasks,
    update_task_status,
    update_task_progress,
    update_task_content,
    update_task_deadline,
    update_task_priority,
    update_task_assignee,
    soft_delete_task,
    restore_task,
    add_task_history,
    create_default_reminders,
    get_tasks_with_deadline,
    # Group task functions (G-ID/P-ID system)
    create_group_task,
    get_group_task_progress,
    get_child_tasks,
    check_and_complete_group_task,
    is_group_task,
    convert_individual_to_group,
    update_group_assignees,
    # Bulk delete functions
    get_tasks_created_by_user,
    get_tasks_assigned_to_others,
    bulk_delete_tasks,
    bulk_soft_delete_with_undo,
)

from .recurring_service import (
    create_recurring_template,
    get_recurring_template,
    get_user_recurring_templates,
    get_due_templates,
    generate_task_from_template,
    toggle_recurring_template,
    delete_recurring_template,
    parse_recurrence_pattern,
    format_recurrence_description,
)

from .report_service import (
    create_export_report,
    get_report_by_id,
    increment_download_count,
    cleanup_expired_reports,
    verify_password as verify_report_password,
    REPORT_TTL_HOURS,
)

# Reminder and notification services are imported directly where needed
# to avoid circular imports with scheduler

__all__ = [
    # Time parser
    "VietnameseTimeParser",
    "parse_vietnamese_time",
    # User service
    "get_or_create_user",
    "get_user_by_telegram_id",
    "get_user_by_id",
    "get_user_by_username",
    "find_users_by_mention",
    "update_user_settings",
    "get_or_create_group",
    "add_group_member",
    # Task service
    "generate_task_id",
    "create_task",
    "get_task_by_public_id",
    "get_task_by_id",
    "get_user_tasks",
    "get_user_created_tasks",
    "get_user_received_tasks",
    "get_user_personal_tasks",
    "get_all_user_related_tasks",
    "get_group_tasks",
    "update_task_status",
    "update_task_progress",
    "update_task_content",
    "update_task_deadline",
    "update_task_priority",
    "update_task_assignee",
    "soft_delete_task",
    "restore_task",
    "add_task_history",
    "create_default_reminders",
    "get_tasks_with_deadline",
    # Group task functions
    "create_group_task",
    "get_group_task_progress",
    "get_child_tasks",
    "check_and_complete_group_task",
    "is_group_task",
    "convert_individual_to_group",
    "update_group_assignees",
    # Bulk delete functions
    "get_tasks_created_by_user",
    "get_tasks_assigned_to_others",
    "bulk_delete_tasks",
    "bulk_soft_delete_with_undo",
    # Recurring service
    "create_recurring_template",
    "get_recurring_template",
    "get_user_recurring_templates",
    "get_due_templates",
    "generate_task_from_template",
    "toggle_recurring_template",
    "delete_recurring_template",
    "parse_recurrence_pattern",
    "format_recurrence_description",
    # Report service
    "create_export_report",
    "get_report_by_id",
    "increment_download_count",
    "cleanup_expired_reports",
    "verify_report_password",
    "REPORT_TTL_HOURS",
]
