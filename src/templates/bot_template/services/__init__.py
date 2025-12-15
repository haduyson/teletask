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
    get_group_tasks,
    update_task_status,
    update_task_progress,
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
    "get_group_tasks",
    "update_task_status",
    "update_task_progress",
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
]
