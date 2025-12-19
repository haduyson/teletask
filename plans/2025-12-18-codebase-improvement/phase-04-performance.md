# Phase 04: Performance & UX Improvements

**Priority**: LOW
**Status**: ✅ COMPLETE
**Issues**: 12
**Estimated**: 8 hours

## Context Links
- [Main Plan](./plan.md)
- [Services Analysis](../reports/scout-2025-12-18-services-analysis.md)
- [Callbacks Review](../reports/code-reviewer-251218-callbacks-handler-review.md)

## Overview

| Metric | Value |
|--------|-------|
| Date | 2025-12-18 |
| Priority | LOW |
| Files Affected | 6 |
| Tests Required | Yes |

## Key Insights

1. N+1 query patterns in task updates
2. Missing query timeouts
3. In-memory filtering instead of SQL
4. No rate limiting on callbacks
5. Hardcoded timezone ignoring user settings

## Implementation Steps

### 1. Fix N+1 Query Pattern (2 hours)

**File**: `services/task_service.py`
**Current**: Fetching parent task, then children separately

```python
# BEFORE - N+1 pattern
parent = await get_task(parent_id)
children = await get_child_tasks(parent_id)  # Separate query
for child in children:
    child.assignee = await get_user(child.assignee_id)  # N queries!

# AFTER - Single query with joins
async def get_task_with_children(task_id: int) -> Task:
    """Get task with children and assignees in single query."""
    db = get_db()
    async with db.session() as session:
        result = await session.execute(
            select(Task)
            .options(
                selectinload(Task.children),
                joinedload(Task.assignee)
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
```

### 2. Add Query Timeouts (1 hour)

**File**: `database/connection.py`

```python
# Add timeout to session creation
async def session(self, timeout: float = 30.0):
    """Get session with timeout."""
    async with asyncio.timeout(timeout):
        async with self._session_factory() as session:
            yield session
```

### 3. Fix In-Memory Filtering (2 hours)

**File**: `handlers/callbacks.py`
**Current**: Filtering lists in Python instead of SQL

```python
# BEFORE - O(n) in memory
tasks = await get_all_user_tasks(user_id)
pending_tasks = [t for t in tasks if t.status == 'pending']

# AFTER - Filter in SQL
pending_tasks = await get_user_tasks(user_id, status='pending')
```

### 4. Add Rate Limiting (2 hours)

**File**: `handlers/callbacks.py`

```python
from functools import wraps
from collections import defaultdict
import time

# Simple in-memory rate limiter
_rate_limits = defaultdict(list)
RATE_LIMIT = 10  # requests
RATE_WINDOW = 60  # seconds

def rate_limit(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()

        # Clean old entries
        _rate_limits[user_id] = [
            t for t in _rate_limits[user_id]
            if now - t < RATE_WINDOW
        ]

        if len(_rate_limits[user_id]) >= RATE_LIMIT:
            await update.callback_query.answer(
                "Too many requests. Please wait.",
                show_alert=True
            )
            return

        _rate_limits[user_id].append(now)
        return await func(update, context)
    return wrapper

@rate_limit
async def callback_router(update, context):
    ...
```

### 5. Fix Hardcoded Timezone (1 hour)

**File**: `utils/formatters.py:32`

```python
# BEFORE - Hardcoded
TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# AFTER - Use config
from config import get_settings

def get_timezone():
    settings = get_settings()
    return pytz.timezone(settings.timezone)

def format_datetime(dt: datetime, user: Optional[User] = None) -> str:
    """Format datetime in user's timezone or default."""
    tz = pytz.timezone(user.timezone) if user else get_timezone()
    return dt.astimezone(tz).strftime("%H:%M %d/%m/%Y")
```

## Todo List

- [ ] Implement get_task_with_children with eager loading
- [ ] Replace N+1 patterns in task_service.py
- [ ] Add timeout parameter to session()
- [ ] Add timeout to critical queries
- [ ] Replace in-memory filtering with SQL filters
- [ ] Implement rate_limit decorator
- [ ] Apply rate limiting to callback_router
- [ ] Fix hardcoded timezone in formatters.py
- [ ] Update format_datetime to accept user
- [ ] Benchmark before/after

## Success Criteria

- [ ] No N+1 queries (verified with query logging)
- [ ] All queries timeout after 30s
- [ ] Rate limiting active (10 req/min)
- [ ] Timezone respects user settings
- [ ] Response time <500ms P95

## Metrics to Track

| Metric | Before | Target |
|--------|--------|--------|
| Avg response time | ~300ms | <200ms |
| P95 response time | ~800ms | <500ms |
| DB queries/request | ~5 | ~2 |
| Memory usage | ~150MB | ~120MB |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limit too aggressive | Medium | MEDIUM | Make configurable |
| Timeout too short | Low | MEDIUM | Start with 30s |
| Breaking eager loads | Low | MEDIUM | Test thoroughly |

## Next Steps

After all phases complete:
1. Run full test suite
2. Deploy to staging
3. Monitor metrics
4. Create production deployment plan
