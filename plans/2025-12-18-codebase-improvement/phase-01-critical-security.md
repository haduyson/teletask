# Phase 01: Critical Security Fixes

**Priority**: CRITICAL
**Status**: PENDING
**Issues**: 8
**Estimated**: 12 hours

## Context Links
- [Main Plan](./plan.md)
- [Task Service Review](../reports/code-reviewer-251218-task-service-review.md)
- [Database Audit](../reports/scout-2025-12-18-database-layer-audit.md)

## Overview

| Metric | Value |
|--------|-------|
| Date | 2025-12-18 |
| Priority | CRITICAL |
| Files Affected | 4 |
| Tests Required | Yes |

## Key Insights

1. OAuth tokens stored in plaintext - full account compromise risk
2. No input validation on task mutations - injection vectors
3. Missing permission checks - unauthorized access
4. Transaction manager leaks connections on errors

## Requirements

- Encrypt OAuth tokens without data loss
- Add input validation to all mutation functions
- Implement permission checks before any data modification
- Fix connection pool leak in transaction context

## Architecture

```
Current:                         After:
┌─────────────────┐             ┌─────────────────┐
│ Handler         │             │ Handler         │
│ (no validation) │             │ + Input Valid   │
└────────┬────────┘             └────────┬────────┘
         │                               │
         ▼                               ▼
┌─────────────────┐             ┌─────────────────┐
│ Service         │             │ Service         │
│ (no permission) │             │ + Permission    │
└────────┬────────┘             │ + Validation    │
         │                      └────────┬────────┘
         ▼                               │
┌─────────────────┐                      ▼
│ Database        │             ┌─────────────────┐
│ (plaintext)     │             │ Database        │
└─────────────────┘             │ + Encrypted     │
                                │ + Safe Txns     │
                                └─────────────────┘
```

## Related Code Files

- `database/models.py:57-58` - OAuth token columns
- `database/connection.py:152-166` - Transaction context
- `services/task_service.py:216-242` - Dynamic queries
- `handlers/callbacks.py:274,424,583` - Missing validation

## Implementation Steps

### 1. Encrypt OAuth Tokens (3 hours)

**File**: `database/models.py`
**Lines**: 57-58

```python
# BEFORE
google_calendar_token = Column(Text, nullable=True)
google_calendar_refresh_token = Column(Text, nullable=True)

# AFTER - use sqlalchemy_utils.EncryptedType
from sqlalchemy_utils import EncryptedType
from config import settings

google_calendar_token = Column(
    EncryptedType(String, settings.encryption_key),
    nullable=True
)
google_calendar_refresh_token = Column(
    EncryptedType(String, settings.encryption_key),
    nullable=True
)
```

Migration needed for existing data.

### 2. Fix Transaction Context Manager (2 hours)

**File**: `database/connection.py`
**Lines**: 152-166

```python
# BEFORE - Connection leak on exception
def transaction(self):
    return self._engine.connect()

# AFTER - Proper async context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def transaction(self):
    async with self._engine.begin() as conn:
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
```

### 3. Add Input Validation (4 hours)

**File**: `services/task_service.py`

Create validation decorator:

```python
from functools import wraps
from utils.validators import (
    validate_content,
    validate_priority,
    validate_status,
    validate_progress
)

def validate_task_input(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'content' in kwargs:
            valid, msg = validate_content(kwargs['content'])
            if not valid:
                raise ValueError(f"Invalid content: {msg}")
        if 'priority' in kwargs:
            valid, msg = validate_priority(kwargs['priority'])
            if not valid:
                raise ValueError(f"Invalid priority: {msg}")
        # ... more validations
        return await func(*args, **kwargs)
    return wrapper

@validate_task_input
async def create_task(...):
    ...
```

### 4. Add Permission Checks (3 hours)

**File**: `services/task_service.py`

```python
async def update_task(
    task_id: int,
    user_id: int,  # Add user context
    **kwargs
) -> Optional[Task]:
    """Update task with permission check."""
    task = await get_task(task_id)

    # Permission check
    if not can_modify_task(task, user_id):
        raise PermissionError(f"User {user_id} cannot modify task {task_id}")

    # Proceed with update
    ...

def can_modify_task(task: Task, user_id: int) -> bool:
    """Check if user can modify task."""
    return (
        task.creator_id == user_id or
        task.assignee_id == user_id
    )
```

## Todo List

- [ ] Add encryption key to settings.py
- [ ] Install sqlalchemy_utils dependency
- [ ] Create migration for encrypted columns
- [ ] Migrate existing token data
- [ ] Fix transaction() context manager
- [ ] Add validation decorator
- [ ] Apply validation to all mutation functions
- [ ] Add permission checks to task_service.py
- [ ] Update handlers to pass user_id
- [ ] Write unit tests for validation
- [ ] Write integration tests for permissions

## Success Criteria

- [ ] OAuth tokens encrypted at rest
- [ ] No connection pool leaks under load test
- [ ] All task mutations validate input
- [ ] Permission errors raised for unauthorized access
- [ ] 100% test coverage on security functions

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token migration fails | Medium | HIGH | Backup before migration |
| Breaking existing flows | Medium | HIGH | Comprehensive testing |
| Performance impact | Low | MEDIUM | Benchmark encryption overhead |

## Security Considerations

- Encryption key MUST be in environment variable
- Never log plaintext tokens
- Rate limit failed permission checks
- Audit log all permission denials

## Next Steps

After completion:
1. Deploy to staging
2. Run security scan
3. Proceed to Phase 02 (Data Integrity)
