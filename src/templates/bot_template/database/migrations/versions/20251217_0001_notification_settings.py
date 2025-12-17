"""
Add notification settings columns

Migration: 20251217_0001_notification_settings
Created: 2025-12-17
"""

from database.connection import Database


async def upgrade(db: Database) -> None:
    """Add notification settings columns to users table."""
    await db.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_all BOOLEAN NOT NULL DEFAULT true;
    """)
    await db.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_task_assigned BOOLEAN NOT NULL DEFAULT true;
    """)
    await db.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_task_status BOOLEAN NOT NULL DEFAULT true;
    """)


async def downgrade(db: Database) -> None:
    """Remove notification settings columns."""
    await db.execute("ALTER TABLE users DROP COLUMN IF EXISTS notify_all;")
    await db.execute("ALTER TABLE users DROP COLUMN IF EXISTS notify_task_assigned;")
    await db.execute("ALTER TABLE users DROP COLUMN IF EXISTS notify_task_status;")
