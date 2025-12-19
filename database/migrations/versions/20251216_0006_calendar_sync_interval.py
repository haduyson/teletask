"""
Add calendar_sync_interval column to users table.
Allows users to set auto-sync frequency with Google Calendar.

Revision ID: 0006
Revises: 0005
Create Date: 2025-12-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add calendar_sync_interval column (24h, 12h, weekly, manual)
    # Default is 'manual' - user manually syncs when needed
    op.add_column(
        'users',
        sa.Column(
            'calendar_sync_interval',
            sa.String(20),
            server_default='manual',
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'calendar_sync_interval')
