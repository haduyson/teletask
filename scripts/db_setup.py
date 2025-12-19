#!/usr/bin/env python3
"""
Database Setup Script
Initialize a clean database with schema only (no dev data)

Usage:
    python scripts/db_setup.py              # Apply all migrations
    python scripts/db_setup.py --reset      # Reset and recreate schema
    python scripts/db_setup.py --check      # Check database connection
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


async def check_connection():
    """Test database connection."""
    from database.connection import Database

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment")
        return False

    db = Database()
    try:
        await db.connect(db_url)
        result = await db.fetch_val("SELECT 1")
        await db.close()

        if result == 1:
            print("SUCCESS: Database connection OK")
            return True
        else:
            print("ERROR: Unexpected result from database")
            return False
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False


async def apply_migrations():
    """Apply all pending migrations using Alembic."""
    import subprocess

    migrations_dir = Path(__file__).parent.parent / "database" / "migrations"

    # Check if alembic is available
    try:
        result = subprocess.run(
            ["alembic", "--version"],
            capture_output=True,
            text=True,
            cwd=migrations_dir
        )
        if result.returncode != 0:
            print("ERROR: Alembic not found. Install with: pip install alembic")
            return False
    except FileNotFoundError:
        print("ERROR: Alembic not found. Install with: pip install alembic")
        return False

    # Apply migrations
    print("Applying database migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=migrations_dir
    )

    if result.returncode == 0:
        print("SUCCESS: Migrations applied successfully")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"ERROR: Migration failed:\n{result.stderr}")
        return False


async def reset_database():
    """Drop all tables and recreate schema."""
    from database.connection import Database

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return False

    print("WARNING: This will delete ALL data in the database!")
    confirm = input("Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Cancelled.")
        return False

    db = Database()
    try:
        await db.connect(db_url)

        # Drop all tables
        print("Dropping all tables...")
        await db.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)

        # Drop alembic version table
        await db.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")

        await db.close()
        print("SUCCESS: All tables dropped")

        # Reapply migrations
        return await apply_migrations()

    except Exception as e:
        print(f"ERROR: Reset failed: {e}")
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="TeleTask Database Setup")
    parser.add_argument("--reset", action="store_true", help="Reset database (drops all data)")
    parser.add_argument("--check", action="store_true", help="Check database connection only")
    args = parser.parse_args()

    print("=" * 60)
    print("TeleTask Database Setup")
    print("=" * 60)

    if args.check:
        success = asyncio.run(check_connection())
    elif args.reset:
        success = asyncio.run(reset_database())
    else:
        # First check connection, then apply migrations
        if asyncio.run(check_connection()):
            success = asyncio.run(apply_migrations())
        else:
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
