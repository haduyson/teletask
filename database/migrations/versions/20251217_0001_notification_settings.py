"""Add notification settings columns

Revision ID: 0008
Revises: 0007
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notification settings columns to users table
    op.add_column('users', sa.Column('notify_all', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('notify_task_assigned', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('notify_task_status', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('users', 'notify_task_status')
    op.drop_column('users', 'notify_task_assigned')
    op.drop_column('users', 'notify_all')
