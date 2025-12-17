"""Add user reminder preference columns

Revision ID: 0007
Revises: 0006
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reminder preference columns to users table
    op.add_column('users', sa.Column('remind_24h', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('remind_1h', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('remind_30m', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('remind_5m', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('remind_overdue', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('users', 'remind_overdue')
    op.drop_column('users', 'remind_5m')
    op.drop_column('users', 'remind_30m')
    op.drop_column('users', 'remind_1h')
    op.drop_column('users', 'remind_24h')
