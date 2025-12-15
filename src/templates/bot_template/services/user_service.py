"""
User Service
CRUD operations for Telegram users
"""

import logging
from typing import Any, Dict, List, Optional

from telegram import User as TelegramUser

from database.connection import Database

logger = logging.getLogger(__name__)


async def get_or_create_user(db: Database, tg_user: TelegramUser) -> Dict[str, Any]:
    """
    Get existing user or create new one.

    Args:
        db: Database connection
        tg_user: Telegram User object

    Returns:
        User record as dict
    """
    # Try to find existing user
    user = await db.fetch_one(
        "SELECT * FROM users WHERE telegram_id = $1",
        tg_user.id
    )

    if user:
        # Update user info if changed
        display_name = _build_display_name(tg_user)
        if (
            user["username"] != tg_user.username
            or user["first_name"] != tg_user.first_name
            or user["last_name"] != tg_user.last_name
        ):
            await db.execute(
                """
                UPDATE users SET
                    username = $2,
                    first_name = $3,
                    last_name = $4,
                    display_name = $5,
                    updated_at = NOW()
                WHERE telegram_id = $1
                """,
                tg_user.id,
                tg_user.username,
                tg_user.first_name,
                tg_user.last_name,
                display_name,
            )
            # Refresh user data
            user = await db.fetch_one(
                "SELECT * FROM users WHERE telegram_id = $1",
                tg_user.id
            )
        return dict(user)

    # Create new user
    display_name = _build_display_name(tg_user)
    user = await db.fetch_one(
        """
        INSERT INTO users (telegram_id, username, first_name, last_name, display_name)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        tg_user.id,
        tg_user.username,
        tg_user.first_name,
        tg_user.last_name,
        display_name,
    )

    logger.info(f"Created new user: {tg_user.id} ({display_name})")
    return dict(user)


async def get_user_by_telegram_id(db: Database, telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by Telegram ID.

    Args:
        db: Database connection
        telegram_id: Telegram user ID

    Returns:
        User record or None
    """
    user = await db.fetch_one(
        "SELECT * FROM users WHERE telegram_id = $1 AND is_active = true",
        telegram_id
    )
    return dict(user) if user else None


async def get_user_by_id(db: Database, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by internal ID.

    Args:
        db: Database connection
        user_id: Internal user ID

    Returns:
        User record or None
    """
    user = await db.fetch_one(
        "SELECT * FROM users WHERE id = $1 AND is_active = true",
        user_id
    )
    return dict(user) if user else None


async def get_user_by_username(db: Database, username: str) -> Optional[Dict[str, Any]]:
    """
    Get user by Telegram username.

    Args:
        db: Database connection
        username: Telegram username (without @)

    Returns:
        User record or None
    """
    # Remove @ if present
    username = username.lstrip("@")

    user = await db.fetch_one(
        "SELECT * FROM users WHERE LOWER(username) = LOWER($1) AND is_active = true",
        username
    )
    return dict(user) if user else None


async def find_users_by_mention(
    db: Database,
    group_telegram_id: int,
    usernames: List[str],
    name_text: str = ""
) -> List[Dict[str, Any]]:
    """
    Find users by @mentions or name search.

    Args:
        db: Database connection
        group_telegram_id: Telegram group ID
        usernames: List of @usernames to find
        name_text: Optional text to search for names

    Returns:
        List of user records
    """
    users = []

    # Find by usernames
    for username in usernames:
        user = await get_user_by_username(db, username)
        if user and user not in users:
            users.append(user)

    # Find by name in group members
    if name_text and not users:
        # Get group
        group = await db.fetch_one(
            "SELECT id FROM groups WHERE telegram_id = $1",
            group_telegram_id
        )

        if group:
            # Search by display name in group
            found = await db.fetch_all(
                """
                SELECT u.* FROM users u
                JOIN group_members gm ON u.id = gm.user_id
                WHERE gm.group_id = $1
                AND (
                    LOWER(u.display_name) LIKE LOWER($2)
                    OR LOWER(u.first_name) LIKE LOWER($2)
                )
                AND u.is_active = true
                LIMIT 5
                """,
                group["id"],
                f"%{name_text}%"
            )
            users.extend([dict(u) for u in found])

    return users


async def update_user_settings(
    db: Database,
    user_id: int,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update user settings.

    Args:
        db: Database connection
        user_id: Internal user ID
        settings: Settings to update

    Returns:
        Updated user record
    """
    allowed_fields = {
        "timezone", "language",
        "notify_reminder", "notify_weekly_report", "notify_monthly_report"
    }

    # Filter to allowed fields
    updates = {k: v for k, v in settings.items() if k in allowed_fields}

    if not updates:
        user = await get_user_by_id(db, user_id)
        return user

    # Build update query
    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    values = [user_id] + list(updates.values())

    user = await db.fetch_one(
        f"""
        UPDATE users SET {set_clauses}, updated_at = NOW()
        WHERE id = $1
        RETURNING *
        """,
        *values
    )

    return dict(user) if user else None


async def get_or_create_group(db: Database, telegram_id: int, title: str) -> Dict[str, Any]:
    """
    Get existing group or create new one.

    Args:
        db: Database connection
        telegram_id: Telegram group ID
        title: Group title

    Returns:
        Group record as dict
    """
    group = await db.fetch_one(
        "SELECT * FROM groups WHERE telegram_id = $1",
        telegram_id
    )

    if group:
        # Update title if changed
        if group["title"] != title:
            await db.execute(
                "UPDATE groups SET title = $2, updated_at = NOW() WHERE telegram_id = $1",
                telegram_id,
                title
            )
        return dict(group)

    # Create new group
    group = await db.fetch_one(
        """
        INSERT INTO groups (telegram_id, title)
        VALUES ($1, $2)
        RETURNING *
        """,
        telegram_id,
        title
    )

    logger.info(f"Created new group: {telegram_id} ({title})")
    return dict(group)


async def add_group_member(
    db: Database,
    group_id: int,
    user_id: int,
    role: str = "member"
) -> None:
    """
    Add user to group.

    Args:
        db: Database connection
        group_id: Internal group ID
        user_id: Internal user ID
        role: Member role (admin/member)
    """
    await db.execute(
        """
        INSERT INTO group_members (group_id, user_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (group_id, user_id) DO UPDATE SET role = $3
        """,
        group_id,
        user_id,
        role
    )


def _build_display_name(tg_user: TelegramUser) -> str:
    """Build display name from Telegram user."""
    if tg_user.first_name and tg_user.last_name:
        return f"{tg_user.first_name} {tg_user.last_name}"
    elif tg_user.first_name:
        return tg_user.first_name
    elif tg_user.username:
        return f"@{tg_user.username}"
    else:
        return f"User {tg_user.id}"
