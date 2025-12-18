"""Add PostgreSQL sequence for atomic task ID generation.

Revision ID: 0009
Revises: 0008
Create Date: 2025-12-18

Fixes race condition where concurrent task creation could get duplicate IDs.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get current counter value from bot_config
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT value FROM bot_config WHERE key = 'task_id_counter'")
    ).fetchone()

    # Start sequence from current counter + 1 to avoid duplicates
    start_value = int(result[0]) + 1 if result else 1

    # Create sequence for atomic task ID generation
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS task_id_seq START WITH {start_value}")


def downgrade() -> None:
    # Get current sequence value before dropping
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT last_value FROM task_id_seq")).fetchone()

    if result:
        # Store value back in bot_config
        conn.execute(
            sa.text("UPDATE bot_config SET value = :val WHERE key = 'task_id_counter'"),
            {"val": str(result[0])}
        )

    op.execute("DROP SEQUENCE IF EXISTS task_id_seq")
