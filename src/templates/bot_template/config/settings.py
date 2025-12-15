"""
Bot Settings Configuration
Loads and validates environment variables
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Telegram
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    bot_name: str = field(default_factory=lambda: os.getenv("BOT_NAME", "TeleTask"))

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "")
    )
    db_pool_min: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MIN", "2"))
    )
    db_pool_max: int = field(
        default_factory=lambda: int(os.getenv("DB_POOL_MAX", "10"))
    )

    # Timezone
    timezone: str = field(
        default_factory=lambda: os.getenv("TZ", "Asia/Ho_Chi_Minh")
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Optional[str] = field(default_factory=lambda: os.getenv("LOG_FILE"))

    # Admin
    admin_ids: List[int] = field(default_factory=list)

    # Features
    google_calendar_enabled: bool = field(
        default_factory=lambda: os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower()
        == "true"
    )
    google_credentials_file: Optional[str] = field(
        default_factory=lambda: os.getenv("GOOGLE_CREDENTIALS_FILE")
    )

    metrics_enabled: bool = field(
        default_factory=lambda: os.getenv("METRICS_ENABLED", "false").lower() == "true"
    )
    metrics_port: int = field(
        default_factory=lambda: int(os.getenv("METRICS_PORT", "9090"))
    )

    redis_enabled: bool = field(
        default_factory=lambda: os.getenv("REDIS_ENABLED", "false").lower() == "true"
    )
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

    def __post_init__(self) -> None:
        """Parse complex fields after initialization."""
        # Parse admin IDs
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            self.admin_ids = [
                int(id_.strip())
                for id_ in admin_ids_str.split(",")
                if id_.strip().isdigit()
            ]

    def validate(self) -> None:
        """Validate required settings."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")

    def is_admin(self, user_id: int) -> bool:
        """Check if user ID is an admin."""
        return user_id in self.admin_ids


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.validate()
    return settings
