"""
Database Connection Module
Async PostgreSQL connection pooling with asyncpg
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import asyncpg
from asyncpg import Pool, Connection, Record

logger = logging.getLogger(__name__)


class Database:
    """
    Async PostgreSQL database connection manager.
    Uses connection pooling for efficient resource usage.
    """

    def __init__(self):
        self.pool: Optional[Pool] = None
        self._dsn: Optional[str] = None

    async def connect(
        self,
        dsn: str,
        min_size: int = 2,
        max_size: int = 10,
        timeout: float = 60.0,
        timezone: str = "Asia/Ho_Chi_Minh",
    ) -> None:
        """
        Initialize connection pool.

        Args:
            dsn: PostgreSQL connection string
            min_size: Minimum pool connections
            max_size: Maximum pool connections
            timeout: Command timeout in seconds
            timezone: Database timezone
        """
        if self.pool is not None:
            logger.warning("Pool already exists, closing existing pool")
            await self.close()

        self._dsn = dsn

        try:
            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=min_size,
                max_size=max_size,
                command_timeout=timeout,
                server_settings={"timezone": timezone},
            )
            logger.info(f"Database pool created (min={min_size}, max={max_size})")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def close(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database pool closed")

    async def _ensure_pool(self) -> Pool:
        """Ensure pool exists."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return self.pool

    # Query methods

    async def fetch_one(self, query: str, *args: Any) -> Optional[Record]:
        """
        Fetch single row.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Record or None
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args: Any) -> list[Record]:
        """
        Fetch all rows.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            List of records
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetch_val(self, query: str, *args: Any) -> Any:
        """
        Fetch single value.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Single value or None
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        """
        Execute query without return.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Status string (e.g., 'INSERT 0 1')
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args_list: list[tuple]) -> None:
        """
        Execute query with multiple parameter sets.

        Args:
            query: SQL query
            args_list: List of parameter tuples
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            await conn.executemany(query, args_list)

    # Transaction support

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Connection, None]:
        """
        Get connection for manual transaction management with auto commit/rollback.

        Usage:
            async with db.transaction() as conn:
                await conn.execute(...)
                await conn.execute(...)
            # Auto-commits on success, auto-rollbacks on exception

        Yields:
            Connection with transaction started
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    # Health check

    async def health_check(self) -> bool:
        """
        Check if database is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            result = await self.fetch_val("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """Check if pool exists."""
        return self.pool is not None


# Singleton instance
db = Database()


async def init_database(dsn: str, **kwargs) -> Database:
    """
    Initialize database connection.

    Args:
        dsn: PostgreSQL connection string
        **kwargs: Additional pool options

    Returns:
        Database instance
    """
    await db.connect(dsn, **kwargs)
    return db


async def close_database() -> None:
    """Close database connection."""
    await db.close()


def get_db() -> Database:
    """Get database instance."""
    return db
