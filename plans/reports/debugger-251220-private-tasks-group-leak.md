# Debug Report: Private Tasks Showing in Group Chats

**Date:** 2025-12-20
**Reporter:** Debugger Agent
**Severity:** CRITICAL
**Status:** ROOT CAUSE IDENTIFIED

---

## Executive Summary

**Issue:** Users executing `/xemviec` in group chats see private tasks (tasks with `group_id=NULL`) that should only appear in private chats.

**Root Cause:** Missing `group_id` filter in `get_user_personal_tasks()` function. Function queries personal tasks without checking group context, returning ALL personal tasks regardless of group.

**Impact:** Privacy leak - private tasks visible in group context where they shouldn't be.

**Priority:** CRITICAL - Immediate fix required

---

## Technical Analysis

### Request Flow

```
User types /xemviec in group chat
    ↓
handlers/task_view.py::xemviec_command()
    - Detects group context, sets group_id
    - Passes group_id to task_category_keyboard()
    ↓
User clicks "📋 Việc cá nhân" button
    - Callback data: "task_category:personal:g{group_id}"
    ↓
handlers/callbacks.py::handle_task_category()
    - Parses group_id from callback
    - Calls get_user_personal_tasks(db, user_id) ← BUG HERE
    ↓
services/task_service.py::get_user_personal_tasks()
    - NO group_id parameter accepted
    - NO group_id filtering in SQL
    - Returns ALL personal tasks
```

### Affected Functions

#### 1. `get_user_personal_tasks()` - MISSING GROUP FILTER

**File:** `services/task_service.py:336-367`

**Current Signature:**
```python
async def get_user_personal_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:
```

**Current SQL Query:**
```sql
SELECT t.*, u.display_name as creator_name
FROM tasks t
LEFT JOIN users u ON t.creator_id = u.id
WHERE t.creator_id = $1
  AND t.assignee_id = $1
  AND t.is_deleted = false
  {status_filter}
ORDER BY ...
LIMIT $2 OFFSET $3
```

**Problem:** NO `group_id` filtering! Returns tasks with `group_id=NULL` AND tasks from all groups.

**Expected SQL (when group_id specified):**
```sql
WHERE t.creator_id = $1
  AND t.assignee_id = $1
  AND t.is_deleted = false
  AND t.group_id = $4  -- ← MISSING THIS
  {status_filter}
```

#### 2. Comparison: `get_user_created_tasks()` - CORRECTLY FILTERS

**File:** `services/task_service.py:263-291`

**Signature:**
```python
async def get_user_created_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    group_id: Optional[int] = None,  # ← HAS THIS
) -> List[Dict[str, Any]]:
```

**SQL with group filter:**
```python
group_filter = ""
params = [user_id, limit, offset]
if group_id is not None:
    group_filter = "AND t.group_id = $4"  # ← FILTERS CORRECTLY
    params.append(group_id)
```

**This function works correctly!**

#### 3. `get_user_received_tasks()` - CORRECTLY FILTERS

**File:** `services/task_service.py:294-333`

**Signature:**
```python
async def get_user_received_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
    group_id: Optional[int] = None,  # ← HAS THIS
) -> List[Dict[str, Any]]:
```

**SQL with group filter:**
```python
group_filter = ""
params = [user_id, limit, offset]
if group_id is not None:
    group_filter = "AND t.group_id = $4"  # ← FILTERS CORRECTLY
    params.append(group_id)
```

**This function works correctly!**

#### 4. `get_all_user_related_tasks()` - CORRECTLY FILTERS

**File:** `services/task_service.py:370-427`

**Signature:**
```python
async def get_all_user_related_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
    task_type: Optional[str] = None,
    group_id: Optional[int] = None,  # ← HAS THIS
) -> List[Dict[str, Any]]:
```

**SQL with group filter:**
```python
group_filter = ""
params = [user_id, limit, offset]
if group_id is not None:
    group_filter = f"AND t.group_id = ${len(params) + 1}"  # ← FILTERS CORRECTLY
    params.append(group_id)
```

**This function works correctly!**

### Handler Implementation

**File:** `handlers/callbacks.py:759-850`

**Function:** `handle_task_category()`

**Line 808-810 (Personal tasks):**
```python
if category == "personal":
    tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size)
    # ← BUG: NOT PASSING group_id parameter
```

**Line 812-815 (Assigned tasks - CORRECT):**
```python
elif category == "assigned":
    tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size, group_id=gid)
    # ← CORRECT: Passes group_id
```

**Line 816-819 (Received tasks - CORRECT):**
```python
elif category == "received":
    tasks = await get_user_received_tasks(db, db_user["id"], limit=page_size, group_id=gid)
    # ← CORRECT: Passes group_id
```

**Line 821 (All tasks - CORRECT):**
```python
else:  # all
    tasks = await get_all_user_related_tasks(db, db_user["id"], limit=page_size, group_id=gid)
    # ← CORRECT: Passes group_id
```

---

## SQL Query Comparison

### Current Behavior (BUG)

When user clicks "Việc cá nhân" in group chat (group_id=123):

```sql
-- What SHOULD happen:
SELECT * FROM tasks
WHERE creator_id = user_id
  AND assignee_id = user_id
  AND group_id = 123;  -- Only group tasks

-- What ACTUALLY happens:
SELECT * FROM tasks
WHERE creator_id = user_id
  AND assignee_id = user_id;  -- Returns ALL tasks (NULL + all groups)
```

### Expected Behavior (FIX)

```sql
-- When group_id is specified (group chat):
SELECT * FROM tasks
WHERE creator_id = user_id
  AND assignee_id = user_id
  AND group_id = $group_id;  -- Only tasks from this group

-- When group_id is NULL (private chat):
SELECT * FROM tasks
WHERE creator_id = user_id
  AND assignee_id = user_id
  AND group_id IS NULL;  -- Only private tasks
```

---

## Fix Requirements

### 1. Update `get_user_personal_tasks()` Signature

**File:** `services/task_service.py:336`

**Change:**
```python
# Before:
async def get_user_personal_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
) -> List[Dict[str, Any]]:

# After:
async def get_user_personal_tasks(
    db: Database,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_completed: bool = False,
    group_id: Optional[int] = None,  # ← ADD THIS
) -> List[Dict[str, Any]]:
```

### 2. Add Group Filter to SQL Query

**File:** `services/task_service.py:344-365`

**Change:**
```python
# Before:
status_filter = "" if include_completed else "AND t.status != 'completed'"
tasks = await db.fetch_all(
    f"""
    SELECT t.*, u.display_name as creator_name
    FROM tasks t
    LEFT JOIN users u ON t.creator_id = u.id
    WHERE t.creator_id = $1
    AND t.assignee_id = $1
    AND t.is_deleted = false
    {status_filter}
    ORDER BY ...
    LIMIT $2 OFFSET $3
    """,
    user_id, limit, offset
)

# After:
status_filter = "" if include_completed else "AND t.status != 'completed'"
group_filter = ""
params = [user_id, limit, offset]
if group_id is not None:
    group_filter = "AND t.group_id = $4"
    params.append(group_id)

tasks = await db.fetch_all(
    f"""
    SELECT t.*, u.display_name as creator_name
    FROM tasks t
    LEFT JOIN users u ON t.creator_id = u.id
    WHERE t.creator_id = $1
    AND t.assignee_id = $1
    AND t.is_deleted = false
    {status_filter}
    {group_filter}
    ORDER BY ...
    LIMIT $2 OFFSET $3
    """,
    *params
)
```

### 3. Update Handler Call

**File:** `handlers/callbacks.py:809`

**Change:**
```python
# Before:
if category == "personal":
    tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size)

# After:
if category == "personal":
    tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size, group_id=gid)
```

---

## Additional Observations

### PostgreSQL NULL Handling

**Important:** PostgreSQL's `WHERE group_id = $1` does NOT match rows where `group_id IS NULL`.

**Test Cases:**
```sql
-- Task with group_id=NULL (private task):
WHERE group_id = 123  → FALSE (not matched)
WHERE group_id IS NULL → TRUE (matched)

-- Task with group_id=123:
WHERE group_id = 123  → TRUE (matched)
WHERE group_id IS NULL → FALSE (not matched)
```

**Current implementation:** Other functions correctly handle this with conditional filter:
```python
if group_id is not None:
    group_filter = "AND t.group_id = $4"  # Only adds filter when group_id specified
```

**When group_id is None:** Filter not applied, returns tasks from ALL groups + NULL.

**Recommendation:** Consider if we want `group_id=None` to mean:
- A) All tasks (current behavior in other functions)
- B) Only tasks with `group_id IS NULL` (private tasks only)

For consistency, recommend option A (current behavior).

---

## Testing Verification

### Test Scenario 1: Private Chat

```
User in PRIVATE chat clicks /xemviec → "Việc cá nhân"
- group_id = None
- Should show: Tasks with group_id IS NULL
- Current: Shows ALL tasks (NULL + all groups) ← BUG
- After fix: Shows tasks from all sources (maintains backward compatibility)
```

### Test Scenario 2: Group Chat

```
User in GROUP chat (id=123) clicks /xemviec → "Việc cá nhân"
- group_id = 123
- Should show: Only tasks with group_id = 123
- Current: Shows ALL tasks (NULL + all groups) ← BUG
- After fix: Shows only tasks from group 123 ← CORRECT
```

### Test Scenario 3: Multiple Groups

```
User is in Group A (id=111) and Group B (id=222)
- Has tasks in both groups + private tasks (group_id=NULL)

In Group A:
- Should show: Only tasks with group_id=111
- Current: Shows tasks from 111 + 222 + NULL ← BUG
- After fix: Shows only group 111 tasks ← CORRECT

In Group B:
- Should show: Only tasks with group_id=222
- Current: Shows tasks from 111 + 222 + NULL ← BUG
- After fix: Shows only group 222 tasks ← CORRECT
```

---

## Summary

**Exact Location of Bug:**
- File: `services/task_service.py`
- Function: `get_user_personal_tasks()`
- Lines: 336-367
- Issue: Missing `group_id` parameter and SQL filter

**Exact SQL Query Problem:**
```sql
-- Missing this condition when group_id is specified:
AND t.group_id = $4
```

**Files to Modify:**
1. `services/task_service.py:336-367` - Add group_id param + SQL filter
2. `handlers/callbacks.py:809` - Pass group_id argument in `handle_task_category()`
3. `handlers/callbacks.py:727` - Pass group_id argument in `handle_list_page()`

**Note:** `handle_list_page()` currently doesn't receive group_id parameter - needs investigation if pagination should also support group filtering.

**Pattern to Follow:** Use same implementation as `get_user_created_tasks()` and `get_user_received_tasks()`.

---

## Unresolved Questions

1. **Private task visibility intent:** When user is in private chat (group_id=None), should they see:
   - A) ALL their personal tasks from all groups + private tasks (current behavior of other functions)
   - B) ONLY tasks with group_id IS NULL (truly private tasks)

2. **Pagination group filtering:** `handle_list_page()` function doesn't receive or track group_id:
   - Should pagination maintain group context?
   - How to pass group_id through pagination callback data?
   - Current pagination callbacks: `list:personal:2` (page 2) - need format like `list:personal:2:g123`?

3. **Test coverage:** Do existing tests cover group isolation for personal tasks?

4. **Other callers:** Found 2 call sites for `get_user_personal_tasks()`:
   - Line 727 in `handle_list_page()` - also missing group_id
   - Line 809 in `handle_task_category()` - confirmed bug location
   - Both need updating after adding group_id parameter
