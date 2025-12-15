"""
Bot Handlers Module
Command and callback handlers for Telegram bot

Handlers:
- start: /start, /help, /thongtin
- task_create: /taoviec, /vieccanhan
- task_assign: /giaoviec, /viecdagiao
- task_view: /xemviec, /viecnhom, /timviec, /deadline
- task_update: /xong, /danglam, /tiendo
- task_delete: /xoa
- reminder: /nhacviec, /xemnhac
- recurring_task: /vieclaplai, /danhsachvieclaplai
- calendar: /lichnhatky
- callbacks: Inline button handlers
"""

from telegram.ext import Application

from .start import get_handlers as get_start_handlers
from .task_create import get_handlers as get_task_create_handlers
from .task_assign import get_handlers as get_task_assign_handlers
from .task_view import get_handlers as get_task_view_handlers
from .task_update import get_handlers as get_task_update_handlers
from .task_delete import get_handlers as get_task_delete_handlers
from .reminder import get_handlers as get_reminder_handlers
from .statistics import get_handlers as get_statistics_handlers
from .recurring_task import get_handlers as get_recurring_handlers
from .calendar import get_handlers as get_calendar_handlers
from .callbacks import get_handlers as get_callback_handlers


def register_handlers(application: Application) -> None:
    """Register all bot handlers."""
    # Start/Help handlers
    for handler in get_start_handlers():
        application.add_handler(handler)

    # Task create handlers
    for handler in get_task_create_handlers():
        application.add_handler(handler)

    # Task assign handlers
    for handler in get_task_assign_handlers():
        application.add_handler(handler)

    # Task view handlers
    for handler in get_task_view_handlers():
        application.add_handler(handler)

    # Task update handlers
    for handler in get_task_update_handlers():
        application.add_handler(handler)

    # Task delete handlers
    for handler in get_task_delete_handlers():
        application.add_handler(handler)

    # Reminder handlers
    for handler in get_reminder_handlers():
        application.add_handler(handler)

    # Statistics handlers
    for handler in get_statistics_handlers():
        application.add_handler(handler)

    # Recurring task handlers
    for handler in get_recurring_handlers():
        application.add_handler(handler)

    # Calendar handlers
    for handler in get_calendar_handlers():
        application.add_handler(handler)

    # Callback handlers (must be last)
    for handler in get_callback_handlers():
        application.add_handler(handler)


__all__ = ["register_handlers"]
