"""
Database Module
PostgreSQL connection and models with Alembic migrations

Tables:
- users: Telegram users
- groups: Telegram groups
- group_members: User-group relationships
- tasks: Main task table
- reminders: Scheduled reminders
- task_history: Audit trail
- user_statistics: Aggregated stats
- deleted_tasks_undo: 30-second undo buffer
- bot_config: Key-value settings
"""

from .connection import Database, db, init_database, close_database, get_db
from .models import (
    Base,
    User,
    Group,
    GroupMember,
    Task,
    Reminder,
    TaskHistory,
    UserStatistics,
    DeletedTaskUndo,
    BotConfig,
)

__all__ = [
    # Connection
    "Database",
    "db",
    "init_database",
    "close_database",
    "get_db",
    # Models
    "Base",
    "User",
    "Group",
    "GroupMember",
    "Task",
    "Reminder",
    "TaskHistory",
    "UserStatistics",
    "DeletedTaskUndo",
    "BotConfig",
]
