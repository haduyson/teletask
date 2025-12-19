"""
Google Calendar Service
Per-user calendar integration for task sync
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.security import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Environment variables for OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

# Secret for signing OAuth state (must be set in .env for security)
OAUTH_STATE_SECRET = os.getenv("OAUTH_STATE_SECRET", "")

# State expiration time in seconds (5 minutes)
OAUTH_STATE_EXPIRY = 300

# In-memory store for used states (prevents replay attacks)
# Format: {state_token: expiry_timestamp}
_used_states: Dict[str, float] = {}


def is_calendar_enabled() -> bool:
    """Check if Google Calendar integration is enabled."""
    enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
    has_credentials = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    return enabled and has_credentials


def _cleanup_expired_states() -> None:
    """Remove expired states from memory."""
    current_time = time.time()
    expired = [token for token, expiry in _used_states.items() if current_time > expiry]
    for token in expired:
        del _used_states[token]


def generate_oauth_state(user_id: int) -> str:
    """
    Generate a cryptographically signed OAuth state parameter.

    The state contains:
    - user_id: Telegram user ID
    - timestamp: Creation time for expiration check
    - nonce: Random token for uniqueness

    Format: base64(user_id.timestamp.nonce.signature)

    Args:
        user_id: Telegram user ID

    Returns:
        Signed state string
    """
    if not OAUTH_STATE_SECRET:
        logger.warning("OAUTH_STATE_SECRET not set, using fallback (insecure)")
        # Fallback to old behavior if secret not configured
        return str(user_id)

    # Create state payload
    timestamp = int(time.time())
    nonce = secrets.token_hex(16)
    payload = f"{user_id}.{timestamp}.{nonce}"

    # Sign with HMAC-SHA256
    signature = hmac.new(
        OAUTH_STATE_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # Combine payload and signature
    state_data = f"{payload}.{signature}"

    # Base64 encode for URL safety
    return base64.urlsafe_b64encode(state_data.encode()).decode()


def verify_oauth_state(state: str) -> Tuple[bool, Optional[int], str]:
    """
    Verify and decode an OAuth state parameter.

    Checks:
    - Signature validity (HMAC)
    - Expiration (5 minutes)
    - One-time use (prevents replay)

    Args:
        state: The state parameter from OAuth callback

    Returns:
        Tuple of (is_valid, user_id, error_message)
    """
    if not OAUTH_STATE_SECRET:
        # Fallback: treat state as plain user_id (legacy behavior)
        try:
            return True, int(state), ""
        except (ValueError, TypeError):
            return False, None, "Invalid state format"

    try:
        # Decode base64
        state_data = base64.urlsafe_b64decode(state.encode()).decode()
        parts = state_data.split(".")

        if len(parts) != 4:
            return False, None, "Invalid state format"

        user_id_str, timestamp_str, nonce, signature = parts

        # Verify signature
        payload = f"{user_id_str}.{timestamp_str}.{nonce}"
        expected_sig = hmac.new(
            OAUTH_STATE_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            logger.warning(f"OAuth state signature mismatch for user {user_id_str}")
            return False, None, "Invalid signature"

        # Check expiration
        timestamp = int(timestamp_str)
        if time.time() - timestamp > OAUTH_STATE_EXPIRY:
            return False, None, "State expired"

        # Check one-time use
        state_key = f"{user_id_str}.{nonce}"
        if state_key in _used_states:
            logger.warning(f"OAuth state replay attempt for user {user_id_str}")
            return False, None, "State already used"

        # Mark as used (with expiry for cleanup)
        _used_states[state_key] = time.time() + OAUTH_STATE_EXPIRY

        # Cleanup old states periodically
        _cleanup_expired_states()

        return True, int(user_id_str), ""

    except Exception as e:
        logger.error(f"Error verifying OAuth state: {e}")
        return False, None, "Verification failed"


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

        # Generate cryptographically signed state with user_id
        secure_state = generate_oauth_state(user_id)

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=secure_state
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
        import requests

        # Direct token exchange via HTTP (more flexible with scopes)
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            return None

        tokens = response.json()

        return {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_uri": token_url,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
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
    reminder_source: str = "both",
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
        reminder_source: User's reminder source setting (telegram/google_calendar/both)

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
        }

        # Set Google Calendar reminders based on user preference
        if reminder_source in ("google_calendar", "both"):
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 5},     # 5 minutes before
                    {"method": "popup", "minutes": 30},    # 30 minutes before
                    {"method": "popup", "minutes": 60},    # 1 hour before
                    {"method": "popup", "minutes": 1440},  # 24 hours before
                ],
            }
        else:
            # telegram only - no Google Calendar reminders
            event["reminders"] = {
                "useDefault": False,
                "overrides": [],
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
            "urgent": "11",  # Red
            "high": "6",     # Orange
            "normal": "7",   # Cyan
            "low": "2",      # Green
        }

        # Mark completed tasks visually
        summary = f"[{task_id}] {title}"
        if status == "completed":
            summary = f"✅ [DONE] {title}"
            color_id = "8"  # Gray for completed
        else:
            color_id = color_map.get(priority, "7")

        event = {
            "summary": summary,
            "description": f"TeleTask: {task_id}\nStatus: {status.upper()}\n\n{description}" if description else f"TeleTask: {task_id}\nStatus: {status.upper()}",
            "start": {
                "dateTime": deadline.isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "end": {
                "dateTime": (deadline + timedelta(hours=1)).isoformat(),
                "timeZone": "Asia/Ho_Chi_Minh",
            },
            "colorId": color_id,
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

        # Decrypt tokens (handles both encrypted and plaintext for backward compatibility)
        return {
            "access_token": decrypt_token(user["google_calendar_token"]),
            "refresh_token": decrypt_token(user["google_calendar_refresh_token"]) if user["google_calendar_refresh_token"] else None,
        }

    except Exception as e:
        logger.error(f"Error getting user token data: {e}")
        return None


async def get_user_reminder_source(db, user_id: int) -> str:
    """
    Get user's reminder source setting.

    Args:
        db: Database connection
        user_id: Database user ID

    Returns:
        Reminder source: 'telegram', 'google_calendar', or 'both'
    """
    try:
        user = await db.fetch_one(
            "SELECT reminder_source FROM users WHERE id = $1",
            user_id
        )
        return user["reminder_source"] if user and user["reminder_source"] else "both"

    except Exception as e:
        logger.error(f"Error getting user reminder source: {e}")
        return "both"


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
        # Encrypt tokens before storing
        encrypted_access = encrypt_token(access_token) if access_token else None
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None

        await db.execute(
            """
            UPDATE users SET
                google_calendar_token = $2,
                google_calendar_refresh_token = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id, encrypted_access, encrypted_refresh
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
