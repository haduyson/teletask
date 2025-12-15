"""
Google Calendar Service
Per-user calendar integration for task sync
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Environment variables for OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")


def is_calendar_enabled() -> bool:
    """Check if Google Calendar integration is enabled."""
    enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
    has_credentials = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    return enabled and has_credentials


def get_oauth_url(user_id: int) -> Optional[str]:
    """
    Generate OAuth authorization URL for user.

    Args:
        user_id: Telegram user ID to include in state

    Returns:
        Authorization URL or None if not configured
    """
    if not is_calendar_enabled():
        return None

    try:
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )

        # Include user_id in state for callback
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=str(user_id)
        )

        return auth_url

    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        return None


async def exchange_code_for_tokens(code: str) -> Optional[Dict[str, str]]:
    """
    Exchange authorization code for access/refresh tokens.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Dict with access_token and refresh_token
    """
    if not is_calendar_enabled():
        return None

    try:
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        }

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
        }

    except Exception as e:
        logger.error(f"Error exchanging code for tokens: {e}")
        return None


def get_calendar_service(token_data: Dict[str, str]):
    """
    Build Google Calendar API service with user credentials.

    Args:
        token_data: Dict with access_token, refresh_token, etc.

    Returns:
        Google Calendar API service
    """
    try:
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        service = build("calendar", "v3", credentials=credentials)
        return service

    except Exception as e:
        logger.error(f"Error building calendar service: {e}")
        return None


async def create_calendar_event(
    token_data: Dict[str, str],
    task_id: str,
    title: str,
    deadline: datetime,
    description: str = "",
    priority: str = "normal",
) -> Optional[str]:
    """
    Create a calendar event for a task.

    Args:
        token_data: User's OAuth token data
        task_id: Task public ID
        title: Event title (task content)
        deadline: Task deadline
        description: Optional description
        priority: Task priority for color coding

    Returns:
        Google Calendar event ID or None
    """
    service = get_calendar_service(token_data)
    if not service:
        return None

    try:
        # Color based on priority (Google Calendar colorId)
        color_map = {
            "urgent": "11",  # Red
            "high": "6",     # Orange
            "normal": "7",   # Cyan
            "low": "2",      # Green
        }

        # Create event
        event = {
            "summary": f"[{task_id}] {title}",
            "description": f"TeleTask: {task_id}\n\n{description}" if description else f"TeleTask: {task_id}",
            "start": {
                "dateTime": deadline.isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "end": {
                "dateTime": (deadline + timedelta(hours=1)).isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "colorId": color_map.get(priority, "7"),
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 1440},  # 24h
                ],
            },
        }

        result = service.events().insert(
            calendarId="primary",
            body=event
        ).execute()

        logger.info(f"Created calendar event for task {task_id}: {result.get('id')}")
        return result.get("id")

    except HttpError as e:
        logger.error(f"Calendar API error creating event: {e}")
        return None
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return None


async def update_calendar_event(
    token_data: Dict[str, str],
    event_id: str,
    task_id: str,
    title: str,
    deadline: datetime,
    description: str = "",
    priority: str = "normal",
    status: str = "pending",
) -> bool:
    """
    Update an existing calendar event.

    Args:
        token_data: User's OAuth token data
        event_id: Google Calendar event ID
        task_id: Task public ID
        title: Event title
        deadline: Task deadline
        description: Optional description
        priority: Task priority
        status: Task status

    Returns:
        True if updated successfully
    """
    service = get_calendar_service(token_data)
    if not service:
        return False

    try:
        color_map = {
            "urgent": "11",
            "high": "6",
            "normal": "7",
            "low": "2",
        }

        # Mark completed tasks with strikethrough
        summary = f"[{task_id}] {title}"
        if status == "completed":
            summary = f"✅ {summary}"

        event = {
            "summary": summary,
            "description": f"TeleTask: {task_id}\n\n{description}" if description else f"TeleTask: {task_id}",
            "start": {
                "dateTime": deadline.isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "end": {
                "dateTime": (deadline + timedelta(hours=1)).isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "colorId": color_map.get(priority, "7"),
        }

        service.events().update(
            calendarId="primary",
            eventId=event_id,
            body=event
        ).execute()

        logger.info(f"Updated calendar event for task {task_id}")
        return True

    except HttpError as e:
        logger.error(f"Calendar API error updating event: {e}")
        return False
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        return False


async def delete_calendar_event(
    token_data: Dict[str, str],
    event_id: str,
) -> bool:
    """
    Delete a calendar event.

    Args:
        token_data: User's OAuth token data
        event_id: Google Calendar event ID

    Returns:
        True if deleted successfully
    """
    service = get_calendar_service(token_data)
    if not service:
        return False

    try:
        service.events().delete(
            calendarId="primary",
            eventId=event_id
        ).execute()

        logger.info(f"Deleted calendar event: {event_id}")
        return True

    except HttpError as e:
        if e.resp.status == 404:
            # Event already deleted
            return True
        logger.error(f"Calendar API error deleting event: {e}")
        return False
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        return False


async def get_user_token_data(db, user_id: int) -> Optional[Dict[str, str]]:
    """
    Get user's stored Google Calendar token data.

    Args:
        db: Database connection
        user_id: Database user ID

    Returns:
        Token data dict or None
    """
    try:
        user = await db.fetch_one(
            "SELECT google_calendar_token, google_calendar_refresh_token FROM users WHERE id = $1",
            user_id
        )

        if not user or not user["google_calendar_token"]:
            return None

        return {
            "access_token": user["google_calendar_token"],
            "refresh_token": user["google_calendar_refresh_token"],
        }

    except Exception as e:
        logger.error(f"Error getting user token data: {e}")
        return None


async def save_user_tokens(
    db,
    user_id: int,
    access_token: str,
    refresh_token: str,
) -> bool:
    """
    Save user's Google Calendar tokens.

    Args:
        db: Database connection
        user_id: Database user ID
        access_token: OAuth access token
        refresh_token: OAuth refresh token

    Returns:
        True if saved successfully
    """
    try:
        await db.execute(
            """
            UPDATE users SET
                google_calendar_token = $2,
                google_calendar_refresh_token = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id, access_token, refresh_token
        )
        return True

    except Exception as e:
        logger.error(f"Error saving user tokens: {e}")
        return False


async def disconnect_calendar(db, user_id: int) -> bool:
    """
    Disconnect user's Google Calendar.

    Args:
        db: Database connection
        user_id: Database user ID

    Returns:
        True if disconnected successfully
    """
    try:
        await db.execute(
            """
            UPDATE users SET
                google_calendar_token = NULL,
                google_calendar_refresh_token = NULL,
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id
        )
        return True

    except Exception as e:
        logger.error(f"Error disconnecting calendar: {e}")
        return False


async def is_user_connected(db, user_id: int) -> bool:
    """
    Check if user has connected Google Calendar.

    Args:
        db: Database connection
        user_id: Database user ID

    Returns:
        True if connected
    """
    try:
        user = await db.fetch_one(
            "SELECT google_calendar_token FROM users WHERE id = $1",
            user_id
        )
        return bool(user and user["google_calendar_token"])

    except Exception as e:
        logger.error(f"Error checking user connection: {e}")
        return False
