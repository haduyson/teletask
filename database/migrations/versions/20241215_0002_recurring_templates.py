"""Add recurring_templates table

Revision ID: 0002
Revises: 0001
Create Date: 2024-12-15

Creates recurring_templates table for storing recurring task definitions.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Recurring templates table
    op.create_table(
        "recurring_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("is_personal", sa.Boolean(), server_default="true"),
        # Recurrence config
        sa.Column("recurrence_type", sa.String(20), nullable=False),  # daily, weekly, monthly
        sa.Column("recurrence_interval", sa.Integer(), server_default="1"),  # every N days/weeks/months
        sa.Column("recurrence_days", postgresql.ARRAY(sa.Integer()), nullable=True),  # days of week (0-6) or month (1-31)
        sa.Column("recurrence_time", sa.Time(), nullable=True),  # time of day for deadline
        sa.Column("recurrence_end_date", sa.Date(), nullable=True),  # when to stop generating
        sa.Column("recurrence_count", sa.Integer(), nullable=True),  # max instances to generate
        # Tracking
        sa.Column("last_generated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due", sa.DateTime(timezone=True), nullable=True),
        sa.Column("instances_created", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.CheckConstraint(
            "recurrence_type IN ('daily', 'weekly', 'monthly')",
            name="ck_recurrence_type"
        ),
    )
    op.create_index("idx_recurring_creator", "recurring_templates", ["creator_id"])
    op.create_index("idx_recurring_next", "recurring_templates", ["next_due"], postgresql_where="is_active = true")
    op.create_index("idx_recurring_public", "recurring_templates", ["public_id"])

    # Add recurring template reference to tasks
    op.add_column(
        "tasks",
        sa.Column("recurring_template_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_task_recurring_template",
        "tasks", "recurring_templates",
        ["recurring_template_id"], ["id"]
    )

    # Add counter for recurring IDs
    op.execute("""
        INSERT INTO bot_config (key, value, description) VALUES
        ('recurring_id_counter', '0', 'Counter cho recurring task ID')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_constraint("fk_task_recurring_template", "tasks", type_="foreignkey")
    op.drop_column("tasks", "recurring_template_id")
    op.drop_table("recurring_templates")
    op.execute("DELETE FROM bot_config WHERE key = 'recurring_id_counter';")
