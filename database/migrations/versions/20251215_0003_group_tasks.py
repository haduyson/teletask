"""Add parent_task_id for group tasks (G-ID/P-ID system)

Revision ID: 20251215_0003
Revises: 20241215_0002
Create Date: 2025-12-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_task_id column for G-ID/P-ID group task relationships
    op.add_column(
        'tasks',
        sa.Column('parent_task_id', sa.Integer(), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'tasks_parent_task_id_fkey',
        'tasks',
        'tasks',
        ['parent_task_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for faster child task lookups
    op.create_index(
        'ix_tasks_parent_task_id',
        'tasks',
        ['parent_task_id']
    )


def downgrade() -> None:
    op.drop_index('ix_tasks_parent_task_id', table_name='tasks')
    op.drop_constraint('tasks_parent_task_id_fkey', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'parent_task_id')
