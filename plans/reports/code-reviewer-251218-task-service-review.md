# Code Review: task_service.py

**Date**: 2025-12-18
**Reviewer**: Code Review Agent
**File**: `/home/botpanel/bots/hasontechtask/services/task_service.py`
**Lines of Code**: 1786

---

## Code Review Summary

### Scope
- **Files reviewed**: services/task_service.py
- **Lines analyzed**: 1786
- **Review focus**: Full file review - code quality, security, performance, error handling, best practices

### Overall Assessment

**Quality Score**: 6.5/10

Service contains comprehensive task management logic with good async patterns and proper SQL parameterization. However, significant issues exist:
- **DRY violations**: Repeated calendar sync code blocks (~150 lines duplicated)
- **Missing error handling**: No try-catch in many functions
- **Security gaps**: No input validation, permission checks
- **Performance issues**: N+1 query patterns, missing transaction boundaries
- **Type safety**: Inconsistent type hints on dict returns

---

## Critical Issues

### 1. SQL Injection Risk via Dynamic Query Building
**Severity**: CRITICAL
**Location**: Lines 216-242, 277-299, 311-333, 1321-1329

**Issue**:
```python
# Line 220-229
conditions.append(f"t.status = ${len(params) + 1}")  # String interpolation
query = f"""
    SELECT t.*, u.display_name as creator_name
    FROM tasks t
    LEFT JOIN users u ON t.creator_id = u.id
    WHERE {' AND '.join(conditions)}  # Interpolated WHERE clause
    ...
"""
```

**Risk**: While using parameterized queries for values, query structure built via string interpolation creates attack surface if `status` param ever sourced from untrusted input.

**Recommendation**:
```python
# Use explicit conditions instead
base_conditions = ["t.assignee_id = $1", "t.is_deleted = false"]
if status:
    base_conditions.append("t.status = $2")
    params = [user_id, status, limit, offset]
else:
    if not include_completed:
        base_conditions.append("t.status != 'completed'")
    params = [user_id, limit, offset]
```

---

### 2. Missing Permission Checks
**Severity**: CRITICAL
**Location**: Lines 397-530, 557-724, 776-852

**Issue**: Functions like `update_task_status`, `update_task_content`, `soft_delete_task` have NO permission validation. Any user can modify any task if they know the ID.

**Example**:
```python
# Line 397-403
async def update_task_status(
    db: Database,
    task_id: int,
    status: str,
    user_id: int,  # user_id passed but NEVER validated
    progress: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
```

**Recommendation**: Add permission checks at start of every mutation function:
```python
async def update_task_status(...):
    current = await get_task_by_id(db, task_id)
    if not current:
        return None

    # PERMISSION CHECK
    if current["creator_id"] != user_id and current["assignee_id"] != user_id:
        raise PermissionError(f"User {user_id} cannot update task {task_id}")

    # ... rest of logic
```

---

### 3. Missing Input Validation
**Severity**: CRITICAL
**Location**: Lines 48-148, 557-612, 692-724

**Issue**: No validation on user inputs before DB insertion.

**Examples**:
```python
# Line 48-59: No content validation
async def create_task(
    db: Database,
    content: str,  # Could be empty, 10MB, contain SQL, etc.
    creator_id: int,
    assignee_id: int,
    ...
```

**Recommendation**:
```python
async def create_task(...):
    # Validate inputs
    if not content or not content.strip():
        raise ValueError("Task content cannot be empty")
    if len(content) > 500:
        raise ValueError("Task content exceeds 500 character limit")

    # Validate priority
    valid_priorities = ["low", "normal", "high", "urgent"]
    if priority not in valid_priorities:
        raise ValueError(f"Invalid priority: {priority}")

    # Validate deadline is future
    if deadline and deadline <= datetime.now():
        raise ValueError("Deadline must be in the future")
```

---

## High Priority Findings

### 4. DRY Violation - Calendar Sync Code Duplication
**Severity**: HIGH
**Location**: Lines 117-145, 452-470, 589-610, 647-687, 830-850, 909-938

**Issue**: Calendar sync logic duplicated 6+ times (~150 lines total). Identical try-except blocks.

**Example**:
```python
# Lines 117-145 (create_task)
try:
    from services.calendar_service import (
        is_calendar_enabled,
        get_user_token_data,
        create_calendar_event,
        get_user_reminder_source,
    )
    if is_calendar_enabled():
        token_data = await get_user_token_data(db, assignee_id)
        if token_data:
            reminder_source = await get_user_reminder_source(db, assignee_id)
            event_id = await create_calendar_event(...)
            # ... update google_event_id
except Exception as e:
    logger.warning(f"Calendar sync failed for task {public_id}: {e}")
```

**Same pattern repeated** at lines 452-470, 589-610, 647-687, 830-850, 909-938.

**Recommendation**: Extract to helper function:
```python
async def _sync_to_calendar(
    db: Database,
    task: Dict[str, Any],
    operation: str = "create",  # create/update/delete
) -> Optional[str]:
    """Sync task to Google Calendar. Returns event_id or None."""
    try:
        from services.calendar_service import (
            is_calendar_enabled,
            get_user_token_data,
            create_calendar_event,
            update_calendar_event,
            delete_calendar_event,
            get_user_reminder_source,
        )

        if not is_calendar_enabled():
            return None

        assignee_id = task.get("assignee_id")
        token_data = await get_user_token_data(db, assignee_id)
        if not token_data:
            return None

        if operation == "create":
            reminder_source = await get_user_reminder_source(db, assignee_id)
            return await create_calendar_event(
                token_data, task["public_id"], task["content"],
                task.get("deadline"), task.get("description", ""),
                task.get("priority", "normal"), reminder_source
            )
        elif operation == "update":
            event_id = task.get("google_event_id")
            if event_id:
                await update_calendar_event(...)
                return event_id
        elif operation == "delete":
            # ... delete logic

    except Exception as e:
        logger.warning(f"Calendar sync failed for task {task.get('public_id')}: {e}")
        return None

# Usage:
event_id = await _sync_to_calendar(db, task, "create")
if event_id:
    await db.execute("UPDATE tasks SET google_event_id = $2 WHERE id = $1", task_id, event_id)
```

**Impact**: Reduces code by ~120 lines, centralizes error handling, easier testing.

---

### 5. N+1 Query Pattern
**Severity**: HIGH
**Location**: Lines 727-772 (update_task_assignee)

**Issue**: Fetches user data in separate queries instead of JOIN.

```python
# Lines 740-752
old_assignee = await db.fetch_one(
    "SELECT display_name FROM users WHERE id = $1",
    old_assignee_id
)
old_name = old_assignee["display_name"] if old_assignee else str(old_assignee_id)

new_assignee = await db.fetch_one(
    "SELECT display_name FROM users WHERE id = $1",
    new_assignee_id
)
new_name = new_assignee["display_name"] if new_assignee else str(new_assignee_id)
```

**Recommendation**: Single query with CASE:
```python
users = await db.fetch_all(
    "SELECT id, display_name FROM users WHERE id = ANY($1)",
    [old_assignee_id, new_assignee_id]
)
user_map = {u["id"]: u["display_name"] for u in users}
old_name = user_map.get(old_assignee_id, str(old_assignee_id))
new_name = user_map.get(new_assignee_id, str(new_assignee_id))
```

---

### 6. Missing Transaction Boundaries
**Severity**: HIGH
**Location**: Lines 776-852 (soft_delete_task), 1337-1435 (create_group_task)

**Issue**: Multiple DB operations without explicit transaction - risk of partial commits.

**Example**:
```python
# Lines 776-852 (soft_delete_task)
async def soft_delete_task(...):
    # 1. Insert into undo table
    undo = await db.fetch_one("INSERT INTO deleted_tasks_undo ...")  # Commits

    # 2. Mark task deleted
    await db.execute("UPDATE tasks SET is_deleted = true ...")  # Commits

    # 3. Add history
    await add_task_history(db, task_id, user_id, ...)  # Commits

    # 4. Delete calendar event (may fail)
    # If calendar delete fails, task already deleted but history logged
```

**Risk**: If step 3 or 4 fails, task is deleted but history incomplete or calendar out of sync.

**Recommendation**: Use transaction:
```python
async def soft_delete_task(...):
    # Get connection for transaction
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            # All operations in single transaction
            undo = await conn.fetchrow("INSERT INTO deleted_tasks_undo ...")
            await conn.execute("UPDATE tasks SET is_deleted ...")
            await conn.execute("INSERT INTO task_history ...")

    # Calendar sync AFTER commit (non-critical)
    try:
        await _sync_to_calendar(db, task, "delete")
    except Exception as e:
        logger.warning(f"Calendar delete failed: {e}")
```

---

### 7. Inconsistent Type Hints
**Severity**: HIGH
**Location**: Throughout file - all functions returning dicts

**Issue**: Functions return `Optional[Dict[str, Any]]` but could use typed dataclass/Pydantic model for type safety.

**Example**:
```python
# Line 151
async def get_task_by_public_id(db: Database, public_id: str) -> Optional[Dict[str, Any]]:
    # Returns dict with unknown structure
```

**Recommendation**: Define Task model:
```python
from typing import TypedDict

class TaskDict(TypedDict, total=False):
    id: int
    public_id: str
    content: str
    description: Optional[str]
    creator_id: int
    assignee_id: int
    status: str
    priority: str
    progress: int
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    google_event_id: Optional[str]
    assignee_name: Optional[str]
    creator_name: Optional[str]
    group_name: Optional[str]

async def get_task_by_public_id(db: Database, public_id: str) -> Optional[TaskDict]:
    ...
```

---

### 8. Error Handling - Generic Exception Catching
**Severity**: HIGH
**Location**: Lines 144-145, 469-470, 526-527, 609-610, 686-687, 849-850

**Issue**: Bare `except Exception` catches swallows all errors including programming errors.

**Example**:
```python
# Line 144-145
except Exception as e:
    logger.warning(f"Calendar sync failed for task {public_id}: {e}")
```

**Issue**: Catches `KeyError`, `AttributeError`, etc. that indicate bugs, not expected failures.

**Recommendation**: Catch specific exceptions:
```python
from googleapiclient.errors import HttpError
from google.auth.exceptions import GoogleAuthError

try:
    # ... calendar sync
except (HttpError, GoogleAuthError) as e:
    logger.warning(f"Calendar sync failed: {e}")
except Exception as e:
    # Unexpected error - should alert/raise
    logger.error(f"Unexpected error in calendar sync: {e}", exc_info=True)
    # Consider raising or alerting on call
```

---

### 9. Missing Error Handling in Core Functions
**Severity**: HIGH
**Location**: Lines 194-243, 246-266, 269-300, 303-334, 337-370, 373-394

**Issue**: Query functions have NO try-catch. If DB query fails, exception propagates uncaught.

**Example**:
```python
# Lines 194-243
async def get_user_tasks(...) -> List[Dict[str, Any]]:
    # No try-catch - DB errors propagate raw
    tasks = await db.fetch_all(query, *params, limit, offset)
    return [dict(t) for t in tasks]
```

**Recommendation**: Add error handling:
```python
async def get_user_tasks(...) -> List[Dict[str, Any]]:
    try:
        tasks = await db.fetch_all(query, *params, limit, offset)
        return [dict(t) for t in tasks]
    except asyncpg.PostgresError as e:
        logger.error(f"Database error fetching user tasks: {e}")
        raise  # Re-raise to handler level
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

---

### 10. Progress Calculation - Integer Division Error
**Severity**: MEDIUM
**Location**: Line 487

**Issue**: Using integer division `//` loses precision.

```python
# Line 487
avg_progress = sum(c["progress"] or 0 for c in children) // total
```

**Issue**: `avg_progress = (50 + 60 + 70) // 3 = 180 // 3 = 60`, but should be rounded.

**Recommendation**: Use proper rounding:
```python
avg_progress = round(sum(c["progress"] or 0 for c in children) / total)
```

---

## Medium Priority Improvements

### 11. Magic Strings - Status/Priority Values
**Severity**: MEDIUM
**Location**: Throughout file

**Issue**: Status/priority values hardcoded as strings.

**Recommendation**: Use enums:
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

# Usage:
if status == TaskStatus.COMPLETED:
    completed_at = datetime.now()
```

---

### 12. Inconsistent Datetime Handling
**Severity**: MEDIUM
**Location**: Lines 17, 427, 1259, 1307

**Issue**: Mix of timezone-aware and naive datetimes.

**Example**:
```python
# Line 17: Timezone defined
TZ = pytz.timezone("Asia/Ho_Chi_Minh")

# Line 427: Naive datetime used
completed_at = datetime.now()  # No timezone

# Line 1259: Timezone-aware
now = datetime.now(TZ)
```

**Recommendation**: Consistent timezone usage:
```python
def now_tz() -> datetime:
    """Get current time in configured timezone."""
    return datetime.now(TZ)

# Usage:
completed_at = now_tz()
```

---

### 13. Function Complexity - create_task
**Severity**: MEDIUM
**Location**: Lines 48-148

**Issue**: 100-line function doing create + history + reminders + calendar sync.

**Recommendation**: Split into smaller functions:
```python
async def create_task(...) -> Dict[str, Any]:
    # Validate inputs
    _validate_task_inputs(content, priority, deadline)

    # Generate ID and insert
    task = await _insert_task(db, ...)

    # Post-creation actions
    await _add_creation_history(db, task)
    if deadline:
        await _create_task_reminders(db, task, assignee_id, deadline, creator_id)
        await _sync_to_calendar(db, task, "create")

    return task
```

---

### 14. Logging - Inconsistent Levels
**Severity**: MEDIUM
**Location**: Throughout file

**Issue**: Mix of info/warning/error inconsistently.

**Examples**:
```python
logger.info(f"Created task {public_id}")  # Line 147 - Good
logger.warning(f"Calendar sync failed")  # Line 145 - Should be debug/info
logger.info(f"Updated parent task")  # Line 525 - Too verbose
```

**Recommendation**: Consistent logging strategy:
- `DEBUG`: Detailed trace (query params, full objects)
- `INFO`: Important business events (task created, status changed)
- `WARNING`: Recoverable errors (calendar sync failed, external service down)
- `ERROR`: Critical failures (DB errors, data corruption)

---

### 15. Missing Index Hints in Queries
**Severity**: MEDIUM
**Location**: Lines 162-173, 346-369, 998-1023

**Issue**: Complex queries without index usage consideration.

**Example**:
```python
# Lines 998-1023
SELECT DISTINCT t.*,
       COALESCE(u.display_name, 'Nhóm') as assignee_name
FROM tasks t
LEFT JOIN users u ON t.assignee_id = u.id
WHERE t.creator_id = $1
  AND t.is_deleted = false
  AND t.parent_task_id IS NULL
  AND (
      (t.assignee_id IS NOT NULL AND t.assignee_id != $1)
      OR
      EXISTS (SELECT 1 FROM tasks child WHERE child.parent_task_id = t.id ...)
  )
ORDER BY t.created_at DESC
```

**Recommendation**: Add comments about required indexes:
```python
# Requires indexes:
# - tasks(creator_id, is_deleted, parent_task_id)
# - tasks(parent_task_id, assignee_id, is_deleted)
# - tasks(created_at DESC)
```

---

## Low Priority Suggestions

### 16. Code Comments - Missing Business Logic Explanation
**Severity**: LOW
**Location**: Lines 473-528, 1516-1586

**Issue**: Complex business logic without explanation.

**Example**:
```python
# Lines 473-528 (update parent task progress)
if current.get("parent_task_id"):
    try:
        parent_id = current["parent_task_id"]
        children = await db.fetch_all(...)
        # Complex logic - no comments explaining WHY
        if children:
            total = len(children)
            completed = sum(1 for c in children if c["status"] == "completed")
            # ... more calculations
```

**Recommendation**: Add comments:
```python
# Update parent task progress when child completes
# Parent progress = average of all children's progress
# Parent status = completed only when ALL children completed
if current.get("parent_task_id"):
    # ...
```

---

### 17. Function Naming - Inconsistent Prefixes
**Severity**: LOW
**Location**: Throughout file

**Issue**: Mix of `get_`, `create_`, `update_` but also no prefix (`is_group_task`).

**Recommendation**: Consistent naming:
- `get_*`: Queries (read-only)
- `create_*`: Insertions
- `update_*`: Updates
- `delete_*`: Deletions
- `check_*`: Boolean checks
- `_internal_*`: Private helpers

---

### 18. Unused Parameters - description in create_default_reminders
**Severity**: LOW
**Location**: Line 1242

**Issue**: Function signature doesn't use all data it could.

```python
async def create_default_reminders(
    db: Database,
    task_id: int,
    assignee_id: int,
    deadline: datetime,
    creator_id: Optional[int] = None,  # Only used conditionally
) -> None:
```

**Recommendation**: Document when params are optional:
```python
async def create_default_reminders(
    db: Database,
    task_id: int,
    assignee_id: int,
    deadline: datetime,
    creator_id: Optional[int] = None,  # Required only for delegated tasks
) -> None:
    """
    Create default reminders for a task.

    Creates:
    - 24h before deadline (assignee)
    - 1h before deadline (assignee)
    - 1min after deadline (creator, only if creator != assignee)
    """
```

---

## Positive Observations

1. **SQL Parameterization**: All queries use proper `$1, $2` parameterization - NO string interpolation of values ✅
2. **Async Pattern Consistency**: All functions properly use `async/await` ✅
3. **Soft Delete Implementation**: Good undo mechanism with 30-second window ✅
4. **Comprehensive CRUD**: Complete set of operations for all task types ✅
5. **Audit Trail**: History logging for all mutations ✅
6. **ID Generation**: Atomic sequence usage prevents race conditions ✅

---

## Recommended Actions

### Immediate (Fix Before Production)
1. **Add permission checks** to all mutation functions (update, delete, reassign)
2. **Add input validation** for content length, priority values, deadline future-check
3. **Fix transaction boundaries** in soft_delete_task and create_group_task
4. **Extract calendar sync** to single helper function (DRY)

### High Priority (This Sprint)
5. **Add error handling** to all query functions
6. **Fix N+1 queries** in update_task_assignee
7. **Use typed returns** instead of `Dict[str, Any]`
8. **Fix progress calculation** integer division bug
9. **Add specific exception catching** instead of bare `except Exception`

### Medium Priority (Next Sprint)
10. **Extract constants** for status/priority values (use Enum)
11. **Standardize datetime** handling (always use TZ-aware)
12. **Refactor create_task** into smaller functions
13. **Add index hints** as comments in complex queries
14. **Consistent logging** levels and messages

### Low Priority (Backlog)
15. **Add business logic comments** to complex calculations
16. **Standardize function naming** convention
17. **Improve docstrings** with Examples section
18. **Add type aliases** for common return types

---

## Security Checklist

- [ ] **Input Validation**: MISSING - Add content length, priority enum, deadline validation
- [ ] **Permission Checks**: MISSING - Add creator/assignee checks in mutations
- [ ] **SQL Injection**: SAFE - Using parameterized queries
- [ ] **Error Exposure**: SAFE - No raw exceptions to users (logged only)
- [ ] **Sensitive Data Logging**: SAFE - No tokens/passwords logged
- [ ] **Transaction Safety**: PARTIAL - Add explicit transactions for multi-step operations

---

## Performance Metrics

- **N+1 Queries**: 1 detected (update_task_assignee)
- **Missing Indexes**: Recommend indexes on `(creator_id, is_deleted, parent_task_id)`, `(parent_task_id, assignee_id)`
- **Large Function Count**: 3 functions > 80 lines (create_task, update_task_status, create_group_task)
- **Code Duplication**: ~150 lines duplicated (calendar sync blocks)

---

## Test Coverage Gaps

Functions without obvious error path testing:
- `generate_task_id` - What if sequence exhausted?
- `create_group_task` - What if assignee list empty?
- `update_task_status` - What if invalid status string?
- `create_default_reminders` - What if deadline in past?

Recommend test cases:
```python
@pytest.mark.asyncio
async def test_create_task_empty_content():
    with pytest.raises(ValueError, match="content cannot be empty"):
        await create_task(db, "", creator_id=1, assignee_id=1)

@pytest.mark.asyncio
async def test_update_task_permission_denied():
    task = await create_task(db, "Test", creator_id=1, assignee_id=2)
    with pytest.raises(PermissionError):
        await update_task_status(db, task["id"], "completed", user_id=999)
```

---

## Unresolved Questions

1. **Calendar sync failures** - Should tasks be created even if calendar sync fails? (Current: yes, with warning log)
2. **Permission model** - Should group admins be able to modify any group task? (Current: no explicit group admin checks)
3. **Deadline timezone** - Are deadlines stored in UTC or user timezone? (Code mixes both)
4. **Task ID sequence** - What happens when sequence reaches max int? (No overflow handling)
5. **Bulk operations** - Should bulk_delete have transaction? (Current: no, uses individual updates)

---

**Review Status**: COMPLETE
**Next Steps**: Implement immediate fixes, schedule high-priority items for current sprint
