"""Initial schema - Create all tables

Revision ID: 0001
Revises:
Create Date: 2024-12-14

Creates:
- users: Telegram users
- groups: Telegram groups
- group_members: User-group relationships
- tasks: Main task table
- reminders: Scheduled reminders
- task_history: Audit trail
- user_statistics: Aggregated stats
- deleted_tasks_undo: Undo buffer
- bot_config: Key-value settings
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(500), nullable=True),
        sa.Column("timezone", sa.String(50), server_default="Asia/Ho_Chi_Minh"),
        sa.Column("language", sa.String(10), server_default="vi"),
        sa.Column("notify_reminder", sa.Boolean(), server_default="true"),
        sa.Column("notify_weekly_report", sa.Boolean(), server_default="true"),
        sa.Column("notify_monthly_report", sa.Boolean(), server_default="true"),
        sa.Column("google_calendar_token", sa.Text(), nullable=True),
        sa.Column("google_calendar_refresh_token", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("idx_users_telegram", "users", ["telegram_id"])
    op.create_index("idx_users_username", "users", ["username"], postgresql_where="username IS NOT NULL")

    # 2. Groups table
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("idx_groups_telegram", "groups", ["telegram_id"])

    # 3. Group members table
    op.create_table(
        "group_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )
    op.create_index("idx_gm_group", "group_members", ["group_id"])
    op.create_index("idx_gm_user", "group_members", ["user_id"])

    # 4. Tasks table
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(20), nullable=False),
        sa.Column("group_task_id", sa.String(20), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), server_default="false"),
        sa.Column("recurring_pattern", sa.String(100), nullable=True),
        sa.Column("recurring_config", postgresql.JSONB(), nullable=True),
        sa.Column("parent_recurring_id", sa.Integer(), nullable=True),
        sa.Column("google_event_id", sa.String(255), nullable=True),
        sa.Column("is_personal", sa.Boolean(), server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["parent_recurring_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"]),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name="ck_task_status"),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="ck_task_priority"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_task_progress"),
    )
    op.create_index("idx_tasks_public", "tasks", ["public_id"])
    op.create_index("idx_tasks_group_task", "tasks", ["group_task_id"], postgresql_where="group_task_id IS NOT NULL")
    op.create_index("idx_tasks_assignee_status", "tasks", ["assignee_id", "status"], postgresql_where="is_deleted = false")
    op.create_index("idx_tasks_creator", "tasks", ["creator_id"], postgresql_where="is_deleted = false")
    op.create_index("idx_tasks_deadline", "tasks", ["deadline"], postgresql_where="is_deleted = false AND status != 'completed'")
    op.create_index("idx_tasks_group", "tasks", ["group_id"], postgresql_where="is_deleted = false")

    # 5. Reminders table
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_type", sa.String(50), nullable=False),
        sa.Column("reminder_offset", sa.String(20), nullable=True),
        sa.Column("is_sent", sa.Boolean(), server_default="false"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint("reminder_type IN ('before_deadline', 'after_deadline', 'custom', 'creator_overdue')", name="ck_reminder_type"),
    )
    op.create_index("idx_reminders_pending", "reminders", ["remind_at"], postgresql_where="is_sent = false")
    op.create_index("idx_reminders_task", "reminders", ["task_id"])

    # 6. Task history table
    op.create_table(
        "task_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_history_task", "task_history", ["task_id", "created_at"])

    # 7. User statistics table
    op.create_table(
        "user_statistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("tasks_assigned_total", sa.Integer(), server_default="0"),
        sa.Column("tasks_assigned_completed", sa.Integer(), server_default="0"),
        sa.Column("tasks_assigned_overdue", sa.Integer(), server_default="0"),
        sa.Column("tasks_received_total", sa.Integer(), server_default="0"),
        sa.Column("tasks_received_completed", sa.Integer(), server_default="0"),
        sa.Column("tasks_received_overdue", sa.Integer(), server_default="0"),
        sa.Column("tasks_personal_total", sa.Integer(), server_default="0"),
        sa.Column("tasks_personal_completed", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.UniqueConstraint("user_id", "group_id", "period_type", "period_start", name="uq_user_stats"),
    )
    op.create_index("idx_stats_user", "user_statistics", ["user_id", "period_type", "period_start"])

    # 8. Deleted tasks undo table
    op.create_table(
        "deleted_tasks_undo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("task_data", postgresql.JSONB(), nullable=False),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_restored", sa.Boolean(), server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"]),
    )
    op.create_index("idx_undo_expires", "deleted_tasks_undo", ["expires_at"], postgresql_where="is_restored = false")

    # 9. Bot config table
    op.create_table(
        "bot_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # Insert default config
    op.execute("""
        INSERT INTO bot_config (key, value, description) VALUES
        ('bot_name', 'Task Manager Bot', 'Ten hien thi'),
        ('bot_description', 'He thong quan ly va nhac viec', 'Mo ta bot'),
        ('support_telegram', '@support', 'Telegram ho tro'),
        ('support_phone', '', 'SDT ho tro'),
        ('support_email', '', 'Email ho tro'),
        ('admin_telegram_id', '', 'Admin ID nhan alert'),
        ('timezone', 'Asia/Ho_Chi_Minh', 'Timezone mac dinh'),
        ('task_id_counter', '0', 'Counter cho task ID');
    """)


def downgrade() -> None:
    # Drop in reverse order
    op.drop_table("bot_config")
    op.drop_table("deleted_tasks_undo")
    op.drop_table("user_statistics")
    op.drop_table("task_history")
    op.drop_table("reminders")
    op.drop_table("tasks")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")
