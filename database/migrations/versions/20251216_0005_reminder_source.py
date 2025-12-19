"""
Add reminder_source column to users table.
Allows users to choose between Telegram, Google Calendar, or both for reminders.

Revision ID: 0005
Revises: 0004
Create Date: 2025-12-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add reminder_source column (telegram, google_calendar, both)
    # Default is 'both' to enable all reminders by default
    op.add_column(
        'users',
        sa.Column(
            'reminder_source',
            sa.String(20),
            server_default='both',
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'reminder_source')
