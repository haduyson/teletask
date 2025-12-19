# Code Review: Database Models & Connection

**Date**: 2025-12-18
**Reviewer**: Claude Code Review Agent
**Files**: `database/models.py`, `database/connection.py`

## Scope

- **Files reviewed**: 2 files
  - `/home/botpanel/bots/hasontechtask/database/models.py` (356 lines)
  - `/home/botpanel/bots/hasontechtask/database/connection.py` (217 lines)
- **Lines of code**: ~573 lines
- **Review focus**: Model design, relationships, indexes, constraints, connection pooling, security, SQLAlchemy 2.0 patterns
- **Context**: Telegram task management bot with async PostgreSQL backend

## Overall Assessment

**Quality Score**: 7.5/10

Code demonstrates solid understanding of SQLAlchemy ORM patterns with comprehensive indexes, constraints, and relationships. Connection pooling follows best practices with proper async patterns. However, several critical security issues (plaintext token storage), missing cascades, potential performance concerns, and type safety gaps need addressing.

**Strengths**:
- Comprehensive partial indexes for query optimization
- Check constraints for data integrity
- Proper soft delete pattern
- Well-documented models with docstrings
- Connection pool configuration with sensible defaults

**Weaknesses**:
- **CRITICAL**: Plaintext OAuth token storage
- Missing cascade behaviors on several foreign keys
- Inconsistent nullable field definitions
- Transaction context manager not properly implemented
- Missing connection pool metrics/health indicators

---

## Critical Issues

### 1. **SECURITY VULNERABILITY: Plaintext OAuth Token Storage**

**File**: `database/models.py:57-58`

```python
google_calendar_token = Column(Text)
google_calendar_refresh_token = Column(Text)
```

**Impact**: OAuth tokens stored as plaintext in database. If database compromised, attacker gains full access to users' Google Calendar accounts.

**Risk**: HIGH - Data breach, unauthorized access, compliance violation (GDPR, OAuth 2.0 Security Best Practices)

**Recommendation**:
- Encrypt tokens at rest using AES-256 or similar (e.g., `cryptography.fernet`)
- Store encryption key in environment variable, NOT in database
- Consider token rotation policies
- Add audit logging for token access

**Example fix**:
```python
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

# In settings.py
ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")  # Must be 32-byte key

# In models.py
google_calendar_token = Column(
    EncryptedType(Text, ENCRYPTION_KEY, AesEngine, 'pkcs5')
)
google_calendar_refresh_token = Column(
    EncryptedType(Text, ENCRYPTION_KEY, AesEngine, 'pkcs5')
)
```

### 2. **CRITICAL: Missing CASCADE on User-Related Foreign Keys**

**File**: `database/models.py:151-153`

```python
creator_id = Column(Integer, ForeignKey("users.id"))
assignee_id = Column(Integer, ForeignKey("users.id"))
group_id = Column(Integer, ForeignKey("groups.id"))
```

**Impact**: If user/group deleted, orphaned tasks remain. Soft delete pattern exists but FK constraints don't enforce cleanup.

**Risk**: HIGH - Data integrity violation, orphaned records, broken relationships

**Recommendation**:
- Add `ondelete="SET NULL"` for creator/assignee (preserve task history)
- Add `ondelete="CASCADE"` for group_id (group tasks should delete with group)
- Document behavior in model docstring

**Example fix**:
```python
creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
```

### 3. **CRITICAL: Missing CASCADE on Reminder.user_id**

**File**: `database/models.py:208`

```python
user_id = Column(Integer, ForeignKey("users.id"))
```

**Impact**: User deletion leaves orphaned reminders. Reminder has `task_id` with CASCADE but not `user_id`.

**Risk**: MEDIUM-HIGH - Orphaned data, potential notification failures

**Recommendation**:
```python
user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
```

Allows reminder to fire even if user deleted (task still exists). Alternatively, use CASCADE if reminders should delete with user.

---

## High Priority Findings

### 4. **Missing Transaction Context Manager**

**File**: `database/connection.py:152-166`

```python
async def transaction(self) -> Connection:
    """Get connection for manual transaction management."""
    pool = await self._ensure_pool()
    conn = await pool.acquire()
    return conn
```

**Issue**: Returns raw connection without transaction context. Caller must manually manage `conn.release()`, leading to connection leaks.

**Impact**: Connection pool exhaustion, memory leaks

**Current usage pattern** (likely incorrect):
```python
conn = await db.transaction()
await conn.execute(...)  # No transaction started, no release!
```

**Recommendation**: Implement async context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def transaction(self):
    """Transaction context manager with auto-commit/rollback.

    Usage:
        async with db.transaction() as conn:
            await conn.execute(...)
            await conn.execute(...)
            # Auto-commit on success, rollback on exception
    """
    pool = await self._ensure_pool()
    conn = await pool.acquire()
    tx = conn.transaction()
    try:
        await tx.start()
        yield conn
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise
    finally:
        await pool.release(conn)
```

### 5. **UserStatistics: Nullable Foreign Keys Without Constraints**

**File**: `database/models.py:279-280`

```python
user_id = Column(Integer, ForeignKey("users.id"))
group_id = Column(Integer, ForeignKey("groups.id"))
```

**Issue**: Both nullable, but unique constraint requires combination. Stats can exist for deleted users/groups.

**Recommendation**:
```python
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))  # Keep nullable for personal stats
```

Add check constraint:
```python
CheckConstraint(
    "user_id IS NOT NULL OR group_id IS NOT NULL",
    name="ck_stats_owner"
)
```

### 6. **DeletedTaskUndo: Missing Cleanup Logic**

**File**: `database/models.py:315-338`

**Issue**: Model tracks `expires_at` but no automated cleanup mechanism mentioned. Expired records accumulate.

**Recommendation**:
- Add database trigger/scheduled job to delete expired records
- Add index on `expires_at` for efficient cleanup (already exists: line 334)
- Document cleanup strategy in docstring

**Example cleanup function**:
```python
# In scheduler or maintenance job
async def cleanup_expired_undo():
    """Delete undo records older than 30 seconds."""
    await db.execute(
        "DELETE FROM deleted_tasks_undo WHERE expires_at < NOW() AND is_restored = false"
    )
```

### 7. **Task.deleted_by: Missing Foreign Key Constraint**

**File**: `database/models.py:172`

```python
deleted_by = Column(Integer, ForeignKey("users.id"))
```

**Issue**: No `ondelete` behavior. If deleting user deleted, `deleted_by` orphaned.

**Recommendation**:
```python
deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
```

Preserve audit trail even if user deleted.

### 8. **Connection Pool: Missing Health Metrics**

**File**: `database/connection.py:170-182`

**Issue**: `health_check()` only tests query execution, not pool state (active connections, wait times).

**Recommendation**: Add pool metrics:

```python
async def health_check(self) -> dict:
    """Comprehensive health check with pool metrics."""
    try:
        pool = await self._ensure_pool()
        start = time.time()
        result = await self.fetch_val("SELECT 1")
        latency_ms = (time.time() - start) * 1000

        return {
            "healthy": result == 1,
            "latency_ms": round(latency_ms, 2),
            "pool_size": pool.get_size(),
            "pool_free": pool.get_idle_size(),
            "pool_max": pool._maxsize,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"healthy": False, "error": str(e)}
```

---

## Medium Priority Improvements

### 9. **Inconsistent Nullable Definitions**

**File**: `database/models.py` (multiple)

**Examples**:
- `User.username` (line 42): No `nullable` → defaults to `nullable=True`
- `User.first_name` (line 43): No `nullable` → defaults to `nullable=True`
- `Task.description` (line 136): No `nullable` → defaults to `nullable=True`

**Issue**: Implicit nullable behavior. Unclear if intentional or oversight.

**Recommendation**: Explicitly set `nullable=True` or `nullable=False` for clarity:

```python
username = Column(String(255), nullable=True, index=True)  # Telegram usernames optional
first_name = Column(String(255), nullable=True)  # User may not have first name
description = Column(Text, nullable=True)  # Optional task description
```

### 10. **Task.status/priority: Check Constraints Only**

**File**: `database/models.py:138-147, 186-187`

**Issue**: Status/priority values enforced by check constraints but not Python enums. Prone to typos in application code.

**Recommendation**: Add Python enums for type safety:

```python
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# In Task model
status = Column(
    String(20),
    default=TaskStatus.PENDING.value,
    nullable=False,
)
```

Usage in services:
```python
task.status = TaskStatus.COMPLETED.value  # IDE autocomplete, type checking
```

### 11. **Task.recurring_config: No Schema Validation**

**File**: `database/models.py:162`

```python
recurring_config = Column(JSONB)  # {'interval': 1, 'days': [1,3,5], ...}
```

**Issue**: Freeform JSONB. Schema can drift, cause errors in recurring logic.

**Recommendation**: Add Pydantic model for validation:

```python
from pydantic import BaseModel, Field

class RecurringConfig(BaseModel):
    interval: int = Field(ge=1, le=365)
    days: list[int] = Field(default_factory=list)  # 1-7 for weekdays
    time: str = Field(regex=r'^\d{2}:\d{2}$')  # HH:MM format

# Validate before insert
config_data = {"interval": 1, "days": [1, 3, 5], "time": "09:00"}
config = RecurringConfig(**config_data)  # Raises ValidationError if invalid
task.recurring_config = config.dict()
```

### 12. **BotConfig: No Type Enforcement**

**File**: `database/models.py:341-355`

```python
value = Column(Text)
```

**Issue**: All config values stored as text. No way to distinguish types (bool, int, JSON).

**Recommendation**: Add `value_type` column or use JSONB:

```python
key = Column(String(100), unique=True, nullable=False)
value = Column(JSONB)  # Store as {"type": "int", "data": 42}
description = Column(Text)
```

Or simpler:
```python
value_text = Column(Text)
value_int = Column(Integer)
value_bool = Column(Boolean)
value_json = Column(JSONB)
```

### 13. **Connection Pool: Hardcoded Timezone**

**File**: `database/connection.py:32, 56`

```python
timezone: str = "Asia/Ho_Chi_Minh",
```

**Issue**: Default timezone hardcoded. Not configurable without code change.

**Recommendation**: Use environment variable:

```python
from config.settings import settings  # settings.TIMEZONE from env

async def connect(
    self,
    dsn: str,
    min_size: int = 2,
    max_size: int = 10,
    timeout: float = 60.0,
    timezone: str = None,
) -> None:
    timezone = timezone or settings.TIMEZONE or "UTC"
    # ...
```

### 14. **Missing Index on Task.completed_at**

**File**: `database/models.py:157`

**Issue**: No index on `completed_at`. Reports/statistics likely query by completion date.

**Recommendation**: Add partial index:

```python
Index("idx_tasks_completed", "completed_at", postgresql_where="completed_at IS NOT NULL"),
```

Place in `__table_args__` (line 185).

### 15. **TaskHistory: Missing Composite Index**

**File**: `database/models.py:264`

```python
Index("idx_history_task", "task_id", "created_at"),
```

**Issue**: Good composite index, but queries likely filter by action type too.

**Recommendation**: Add second index for action-based queries:

```python
Index("idx_history_action", "action", "created_at"),
```

Supports queries like "all completed actions in last week".

---

## Low Priority Suggestions

### 16. **Model __repr__ Methods: Include More Fields**

**File**: `database/models.py:70-71, 120-121, etc.`

**Example**:
```python
def __repr__(self):
    return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
```

**Suggestion**: Add status for easier debugging:

```python
def __repr__(self):
    return f"<User(id={self.id}, tg_id={self.telegram_id}, user={self.username}, active={self.is_active})>"

def __repr__(self):
    return f"<Task(id={self.id}, public_id={self.public_id}, status={self.status}, creator={self.creator_id})>"
```

### 17. **Connection Pool: Log DSN Without Credentials**

**File**: `database/connection.py:58`

```python
logger.info(f"Database pool created (min={min_size}, max={max_size})")
```

**Suggestion**: Add sanitized DSN for debugging (hide password):

```python
safe_dsn = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', dsn)
logger.info(f"Pool created: {safe_dsn} (min={min_size}, max={max_size})")
```

### 18. **Missing Type Hints in Models**

**File**: `database/models.py` (various)

**Issue**: SQLAlchemy columns don't have Python type hints for IDE support.

**Suggestion**: Add type annotations (SQLAlchemy 2.0 style):

```python
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
```

Benefits: Better IDE autocomplete, type checking with mypy.

### 19. **DeletedTaskUndo.task_data: No Compression**

**File**: `database/models.py:324`

```python
task_data = Column(JSONB, nullable=False)  # Full task snapshot
```

**Issue**: JSONB can be large for tasks with long descriptions. 30-second window means short retention.

**Suggestion**: If storage concern, compress JSON:

```python
import zlib, base64

# Before insert
compressed = base64.b64encode(zlib.compress(json_data.encode())).decode()

# Or use PostgreSQL's pg_compress extension
```

Likely not needed unless tasks are massive.

### 20. **Connection.is_connected: Check Pool Health**

**File**: `database/connection.py:185-187`

```python
@property
def is_connected(self) -> bool:
    """Check if pool exists."""
    return self.pool is not None
```

**Issue**: Only checks if pool object exists, not if pool is healthy.

**Suggestion**:
```python
@property
def is_connected(self) -> bool:
    """Check if pool exists and is not closed."""
    return self.pool is not None and not self.pool._closed
```

---

## Positive Observations

1. **Excellent use of partial indexes** (lines 189-192): Filters on `is_deleted = false` reduce index size and improve query performance.

2. **Comprehensive check constraints** (lines 186-188): Enforce data integrity at database level (status, priority, progress range).

3. **Proper soft delete pattern** (lines 169-172): `is_deleted`, `deleted_at`, `deleted_by` with undo buffer is well-designed.

4. **Unique constraints prevent duplicates** (line 115, 307): `uq_group_user`, `uq_user_stats` enforce business rules.

5. **Timezone-aware timestamps** (line 61-62): `DateTime(timezone=True)` with `func.now()` ensures UTC storage.

6. **Connection pool configuration** (lines 51-57): Sensible defaults (2-10 connections, 60s timeout) with `command_timeout` to prevent hung queries.

7. **Async context manager for queries** (lines 90, 105, 120): Proper resource cleanup with `async with pool.acquire()`.

8. **Self-referential relationship** (line 183): `parent_recurring` correctly uses `remote_side=[id]` for task hierarchy.

9. **Cascade on child tables** (lines 105-106, 207): GroupMember and Reminder properly cascade delete.

10. **Docstrings on all models**: Clear documentation of purpose, relationships, and usage.

---

## Recommended Actions

**Immediate (Critical)**:
1. ✅ **Encrypt OAuth tokens** (models.py:57-58) - Use `sqlalchemy_utils.EncryptedType` or custom encryption
2. ✅ **Add CASCADE/SET NULL** to all foreign keys (models.py:151-153, 172, 208, 279-280)
3. ✅ **Fix transaction() method** (connection.py:152-166) - Implement async context manager

**Short-term (High Priority)**:
4. ✅ Add pool health metrics to `health_check()` (connection.py:170-182)
5. ✅ Add Python enums for Task status/priority (models.py:138-147)
6. ✅ Implement DeletedTaskUndo cleanup job
7. ✅ Add explicit `nullable=True/False` to all columns

**Medium-term (Improvements)**:
8. ✅ Add schema validation for `recurring_config` JSONB (Pydantic)
9. ✅ Add index on `Task.completed_at`
10. ✅ Refactor BotConfig value storage (type enforcement)
11. ✅ Add composite index on TaskHistory.action
12. ✅ Make timezone configurable (connection.py:32)

**Long-term (Nice-to-have)**:
13. Migrate to SQLAlchemy 2.0 `Mapped` type hints
14. Add compression for DeletedTaskUndo.task_data if needed
15. Enhance `__repr__` methods with more debugging info

---

## Metrics

- **Type Coverage**: ~40% (no type hints on columns, only function signatures)
- **Test Coverage**: Not evaluated (no test files provided)
- **Linting Issues**: 0 syntax errors (Python compilation passed)
- **Security Issues**: 1 critical (plaintext OAuth tokens)
- **Performance Issues**: 2 high (missing indexes, transaction context manager)
- **Data Integrity Issues**: 5 high (missing cascades, nullable inconsistencies)

---

## SQLAlchemy 2.0 Pattern Compliance

**Current State**: Hybrid (SQLAlchemy 1.4 → 2.0 transition)

**Compliance**:
- ✅ Using `select()` construct (assumed from connection usage)
- ✅ Async session support (asyncpg driver)
- ✅ Declarative base with `DeclarativeBase`
- ❌ Not using `Mapped` type hints (SQLAlchemy 2.0 recommended pattern)
- ❌ Not using `mapped_column()` (new in 2.0)
- ✅ Using `relationship()` with `back_populates`

**Recommendation**: Gradually migrate to SQLAlchemy 2.0 style for better type safety:

```python
# Current (1.4 style)
id = Column(Integer, primary_key=True)
username = Column(String(255), index=True)

# Recommended (2.0 style)
id: Mapped[int] = mapped_column(primary_key=True)
username: Mapped[str | None] = mapped_column(String(255), index=True)
```

Provides mypy support and clearer intent.

---

## Unresolved Questions

1. **OAuth token rotation**: Are refresh tokens rotated? If Google revokes, how handled?
2. **Database backups**: Are encrypted backups configured for OAuth token protection?
3. **Connection pool tuning**: Are 2-10 connections sufficient for production load? Monitor `pool_size` metrics.
4. **Migration strategy**: Are migrations tested in staging before production?
5. **Soft delete cleanup**: Do soft-deleted tasks ever get hard-deleted? Or kept indefinitely?
6. **Recurring task cleanup**: When parent_recurring task deleted, are child tasks cleaned up?
7. **TaskHistory retention**: Is there a retention policy (e.g., delete history >1 year)?
8. **JSONB indexing**: Do queries filter by `recurring_config` fields? If so, add GIN index.
9. **Timezone handling**: Are all timestamps stored in UTC? Confirmed by `timezone=True` but verify application logic.
10. **Database connection string**: Is DSN passed securely (env var)? Not hardcoded in settings.py?

---

**Review Status**: COMPLETE
**Next Steps**: Address critical security issue (OAuth encryption) and foreign key cascades before production deployment.

**Estimated Effort**:
- Critical fixes: 4-6 hours
- High priority: 6-8 hours
- Medium priority: 8-12 hours
- Total: ~20 hours for full compliance

---

**Last Updated**: 2025-12-18 23:20
**Review Version**: 1.0
