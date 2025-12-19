# Phase 03: Code Quality & DRY Violations

**Priority**: MEDIUM
**Status**: PENDING
**Issues**: 15
**Estimated**: 12 hours

## Context Links
- [Main Plan](./plan.md)
- [Handlers Analysis](../reports/scout-handlers-analysis.md)
- [Services Analysis](../reports/scout-2025-12-18-services-analysis.md)
- [Callbacks Review](../reports/code-reviewer-251218-callbacks-handler-review.md)

## Overview

| Metric | Value |
|--------|-------|
| Date | 2025-12-18 |
| Priority | MEDIUM |
| Files Affected | 8 |
| Tests Required | Yes |

## Key Insights

1. ~250 lines of duplicate code across handlers/services
2. callback_router is 167 lines with cyclomatic complexity ~25
3. 30+ functions missing type hints
4. Inconsistent error handling patterns

## Requirements

- Extract duplicate code into shared utilities
- Refactor complex functions to <50 lines
- Add type hints to all public APIs
- Standardize error handling

## Implementation Steps

### 1. Extract Duplicate "Recent Users" Query (2 hours)

**Current**: Same query in 7+ places in task_wizard.py

**File**: `services/user_service.py` (new function)

```python
async def get_recent_group_users(
    group_id: int,
    limit: int = 10
) -> List[User]:
    """Get users who recently interacted with group tasks.

    Args:
        group_id: Telegram group ID
        limit: Max users to return

    Returns:
        List of User objects ordered by recent activity
    """
    db = get_db()
    async with db.session() as session:
        result = await session.execute(
            select(User)
            .join(Task, Task.assignee_id == User.id)
            .where(Task.group_id == group_id)
            .order_by(Task.updated_at.desc())
            .distinct()
            .limit(limit)
        )
        return result.scalars().all()
```

Then replace all 7 instances in task_wizard.py.

### 2. Extract Duplicate HTML Escape (1 hour)

**Current**: Two functions doing same thing
- `utils/formatters.py:191` - `escape_html()`
- `utils/validators.py:199` - `sanitize_html()`

**Fix**: Keep one in formatters.py, delete from validators.py

```python
# utils/formatters.py
import html

def escape_html(text: str) -> str:
    """Escape HTML special characters for safe display.

    Args:
        text: Raw text that may contain HTML

    Returns:
        Escaped text safe for HTML display
    """
    return html.escape(text)

# utils/validators.py - DELETE sanitize_html(), import from formatters
from utils.formatters import escape_html
```

### 3. Refactor callback_router (4 hours)

**File**: `handlers/callbacks.py`
**Current**: 167 lines, 50+ if-elif branches

**Strategy**: Use dictionary dispatch pattern

```python
# handlers/callbacks.py

# Define handler mapping
CALLBACK_HANDLERS = {
    'view_task': handle_view_task,
    'edit_task': handle_edit_task,
    'delete_task': handle_delete_task,
    'complete_task': handle_complete_task,
    # ... more handlers
}

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    data = query.data

    # Parse action from callback data
    action = data.split(':')[0] if ':' in data else data

    # Get handler
    handler = CALLBACK_HANDLERS.get(action)
    if handler:
        await handler(update, context)
    else:
        logger.warning(f"Unknown callback action: {action}")
        await query.answer("Unknown action")
```

### 4. Extract Duplicate Calendar Sync Code (2 hours)

**Current**: Calendar sync duplicated 6+ times in task_service.py

**File**: `services/calendar_service.py` (extend)

```python
async def sync_task_to_calendar_if_enabled(
    task: Task,
    user_id: int,
    action: str = 'create'
) -> Optional[str]:
    """Sync task to Google Calendar if user has it enabled.

    Args:
        task: Task to sync
        user_id: User who owns the calendar
        action: 'create', 'update', or 'delete'

    Returns:
        Google Calendar event ID or None
    """
    user = await UserService.get_user(user_id)
    if not user or not user.google_calendar_token:
        return None

    try:
        if action == 'create':
            return await create_calendar_event(task, user)
        elif action == 'update':
            return await update_calendar_event(task, user)
        elif action == 'delete':
            return await delete_calendar_event(task, user)
    except GoogleCalendarError as e:
        logger.warning(f"Calendar sync failed: {e}")
        return None
```

### 5. Add Type Hints (3 hours)

**Files to update**:
- `handlers/callbacks.py` - 11 functions
- `services/task_service.py` - 15 functions
- `utils/validators.py` - 8 functions

Example:

```python
# BEFORE
async def create_task(user_id, content, deadline=None, group_id=None):
    pass

# AFTER
async def create_task(
    user_id: int,
    content: str,
    deadline: Optional[datetime] = None,
    group_id: Optional[int] = None,
) -> Task:
    pass
```

## Todo List

- [ ] Create get_recent_group_users() in user_service.py
- [ ] Replace 7 duplicate queries in task_wizard.py
- [ ] Delete sanitize_html() from validators.py
- [ ] Update imports to use escape_html from formatters
- [ ] Create CALLBACK_HANDLERS dispatch dict
- [ ] Refactor callback_router to use dispatch
- [ ] Create sync_task_to_calendar_if_enabled()
- [ ] Replace 6 calendar sync duplicates
- [ ] Add type hints to callbacks.py (11 functions)
- [ ] Add type hints to task_service.py (15 functions)
- [ ] Add type hints to validators.py (8 functions)
- [ ] Run mypy to verify type coverage

## Success Criteria

- [ ] No duplicate code blocks >20 lines
- [ ] All functions <50 lines
- [ ] Type hints on all public APIs
- [ ] mypy passes with 0 errors
- [ ] Existing tests still pass

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking handler routing | Medium | HIGH | Comprehensive testing |
| Type hint errors | Low | LOW | Run mypy incrementally |
| Import cycles | Low | MEDIUM | Check import structure |

## Next Steps

After completion proceed to Phase 04 (Performance).
