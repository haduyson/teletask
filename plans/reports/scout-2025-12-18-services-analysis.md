# Services Layer Code Quality Scout Report
**Date:** 2025-12-18
**Scope:** `/services/` directory - Core business logic layer
**Focus:** Code quality, database patterns, error handling, security

---

## CRITICAL ISSUES

### 1. Missing Error Handling in Core Functions
**Severity:** HIGH
**Pattern:** 60+ database operations with no try-catch in task_service.py

- **task_service.py:48-148** - `create_task()` - No error handling on 14 sequential DB operations
- **task_service.py:397-529** - `update_task_status()` - No try-catch around status update, history add, or parent updates
- **task_service.py:1337-1435** - `create_group_task()` - 10+ DB calls unprotected, loops create P-IDs without validation
- **task_service.py:1600-1698** - `convert_individual_to_group()` - No validation that assignees list has 2+ members before conversion

**Impact:** Silent failures, orphaned records, inconsistent state
**Fix:** Wrap operations in try-except blocks, add transaction rollback logic

---

## CODE QUALITY ISSUES

### 2. Severe Duplicate Code - Query Patterns
**Severity:** HIGH
**Count:** 18+ identical LEFT JOIN patterns across functions

**Duplicates:**
- **task_service.py:164-169, 181-186, 227-228, 256-257, 281-282, 315-316, 351-353, 385-387** 
  - All repeat: `LEFT JOIN users u ON t.assignee_id = u.id, LEFT JOIN users c ON t.creator_id = c.id, LEFT JOIN groups g ON t.group_id = g.id`
- **report_service.py:135-137** - Same 3-table join pattern
- **notification.py:383-385** - Same pattern in sibling query

**Impact:** 1.5KB+ duplicate SQL, maintenance nightmare, inconsistent result formatting
**Fix:** Extract to helper/view or database function

### 3. Missing Function Documentation
**Severity:** MEDIUM
**Examples:**
- **task_service.py:177** - `get_task_by_id()` - No docstring
- **task_service.py:243-300** - 4 similar get_*_tasks() functions lack detailed parameter docs
- **notification.py:259-275** - Helper functions (format_priority, format_progress_bar) missing docs

---

## DATABASE QUERY PATTERNS

### 4. N+1 Query Risk - Parent Task Updates
**Severity:** MEDIUM
**Location:** task_service.py:472-527

```python
# Lines 477-483: Fetches ALL child tasks
children = await db.fetch_all("""
    SELECT status, progress FROM tasks WHERE parent_task_id = $1
""", parent_id)
# Then loops through to calculate progress - OK
# BUT: No index check on parent_task_id
```

**Risk:** If parent has 1000 children, full table scan on every child status update
**Fix:** Add compound index `(parent_task_id, status, progress)` on tasks table

### 5. Inefficient Recurring Task Generation
**Severity:** MEDIUM
**Location:** recurring_service.py:436-464

```python
# get_due_templates() - Joins users but only uses telegram_id
# All 11 recurring_templates fields fetched for simple loop
```

**Impact:** Over-fetching columns not used in caller context
**Fix:** Select only needed columns, lazy-load user data

### 6. Unindexed Filtering in get_user_tasks
**Severity:** MEDIUM
**Location:** task_service.py:216-242

Dynamic WHERE clause construction without index hints:
```python
# Multiple conditions but no guidance on filtering order
conditions = ["t.assignee_id = $1", "t.is_deleted = false", "t.status = 'X'"]
```

**Fix:** Ensure index order: `(assignee_id, is_deleted, status)` on tasks

---

## ERROR HANDLING PATTERNS

### 7. Inconsistent Exception Handling
**Severity:** MEDIUM
**Count:** Varies by service

**Inconsistencies:**
- **report_service.py:56-67** - Catches `ValueError, AttributeError` on password hash but falls back silently
- **report_service.py:506-509** - Catches generic `Exception` for font loading, continues
- **task_service.py:144-145** - Calendar sync errors logged as warnings but silently skip
- **task_service.py:526-527** - Parent task updates fail silently without notification
- **notification.py:347-348, 429-430** - Notification failures swallow errors with `.warning()` logs

**Issue:** No alerting on transactional failures; users unaware of partial state changes
**Fix:** Log ERROR for transaction failures, add monitoring/alerting

### 8. Missing Null/Type Validation
**Severity:** MEDIUM
**Examples:**

- **task_service.py:427** - `completed_at = datetime.now()` without timezone; task_service uses pytz but this doesn't
- **task_service.py:745, 751** - Gets old_assignee with no null check before accessing `["display_name"]`
- **notification.py:156-157** - Assumes `deadline.strftime()` works without null/timezone check
- **report_service.py:143** - `dict(r) if r else None` converts record but doesn't validate required fields

---

## SECURITY ISSUES

### 9. SQL Parameter Construction
**Severity:** LOW (uses parameterized queries)
**Location:** task_service.py:220, 1318; report_service.py:105, 110

```python
# Dynamic parameter indexing could be error-prone
conditions.append(f"t.status = ${len(params) + 1}")
```

**Analysis:** Uses positional params correctly, but manual index management is fragile
**Risk:** Off-by-one errors in complex queries
**Fix:** Use named parameters (if asyncpg supports) or query builder

### 10. Sensitive Data in Task History
**Severity:** MEDIUM
**Location:** task_service.py:1230-1239

```python
async def add_task_history(..., old_value, new_value):
    # Stores old/new values in plaintext, including:
    # - old_content, new_content (full task text)
    # - assignee names
    # - deadlines
```

**Issue:** No masking of PII or sensitive fields in audit logs
**Risk:** Audit log leakage, compliance issues (GDPR)
**Fix:** Add field-level data masking, separate sensitive audit logging

### 11. OAuth State Replay Prevention - In-Memory Only
**Severity:** MEDIUM
**Location:** calendar_service.py:50-56, 99-156

```python
_used_states: Dict[str, float] = {}  # In-memory store
# Prevents replay in single process, but:
# - Lost on restart
# - No persistence across instances
# - No distributed session support
```

**Impact:** Multi-instance deployments have no replay protection
**Fix:** Persist used states to database with TTL

---

## ARCHITECTURAL ISSUES

### 12. Circular Imports Risk
**Severity:** MEDIUM
**Location:** task_service.py:119-124, 455-460, 650-656, 833-837, 912-917

```python
# Late imports inside functions to avoid circular deps
from services.calendar_service import (
    is_calendar_enabled,
    ...
)
```

**Issue:** Modules import each other at runtime; fragile and slow
**Architecture debt:** recurring_service.py:481 imports task_service internally
**Fix:** Restructure with dependency injection or facade pattern

### 13. Global State in Calendar Service
**Severity:** LOW-MEDIUM
**Location:** calendar_service.py:40

```python
_used_states: Dict[str, float] = {}  # Global mutable state
```

**Issue:** Not thread-safe; should use asyncio.Lock for concurrent access
**Fix:** Add locking or use database for state

---

## MISSING INDEX RECOMMENDATIONS

Based on query patterns found:

```sql
-- task_service.py GET queries
CREATE INDEX idx_tasks_assignee_deleted_status ON tasks(assignee_id, is_deleted, status);
CREATE INDEX idx_tasks_creator_deleted ON tasks(creator_id, is_deleted);
CREATE INDEX idx_tasks_parent_status_progress ON tasks(parent_task_id, status, progress);
CREATE INDEX idx_tasks_group_task_id ON tasks(group_task_id, is_deleted);
CREATE INDEX idx_tasks_deadline_status ON tasks(deadline, status) WHERE is_deleted = false;

-- recurring_service.py
CREATE INDEX idx_recurring_next_due_active ON recurring_templates(next_due, is_active)
  WHERE is_active = true;

-- report_service.py
CREATE INDEX idx_tasks_created_deleted ON tasks(created_at DESC, is_deleted);
```

---

## CODE DUPLICATION METRICS

| Pattern | Count | Files | Total Lines |
|---------|-------|-------|------------|
| 3-table LEFT JOIN | 8 | 3 | 24 |
| Priority formatting | 3 | 3 | 9 |
| Status formatting | 3 | 2 | 6 |
| Datetime formatting | 5 | 4 | 15 |
| Task fetch + name joins | 12 | 1 | 36 |

**Total Duplicate Lines:** 90+ (extractable to 20 lines)

---

## FUNCTION COMPLEXITY ISSUES

### Over-Large Functions

- **task_service.py:48-148** - `create_task()` - 100 lines, 5 async DB calls, calendar sync, history, reminder creation
- **task_service.py:1337-1435** - `create_group_task()` - 98 lines, loop over assignees, 2 DB inserts per item
- **report_service.py:468-709** - `generate_pdf_report()` - 241 lines, chart generation, styling, complex table formatting

**Issue:** Single Responsibility Principle violations; hard to test/debug
**Suggestion:** Break into smaller functions with clear responsibilities

---

## MISSING ERROR SCENARIOS

**Not Handled:**
- task_service.py - What if `get_user_token_data()` returns None? Continues silently (line 127)
- task_service.py - What if calendar event creation fails? Task created but not synced (line 144)
- notification.py - What if bot.send_message() fails? No retry logic (line 342)
- report_service.py - What if file write fails? No disk space handling (line 250)
- recurring_service.py - What if next_due calculation fails? No fallback (line 507)

---

## RECOMMENDED FIXES (Priority Order)

1. **HIGH (Do First):**
   - Wrap database operations in transactions with rollback in task_service.py
   - Extract duplicate JOIN pattern to database view or helper function
   - Add null/type validation for critical paths

2. **MEDIUM (Sprint 2):**
   - Implement retry logic for notification sends
   - Mask sensitive data in task_history
   - Add database indexes per recommendations
   - Add proper error logging (ERROR level for failures)

3. **LOW (Technical Debt):**
   - Refactor circular imports
   - Make OAuth state persistent (multi-instance safe)
   - Break down 100+ line functions
   - Add comprehensive docstrings

---

## UNRESOLVED QUESTIONS

1. Are there SLA requirements for task creation? Missing transaction handling could cause data loss.
2. Is calendar sync considered critical path? Current design continues silently on failures.
3. What's the retention policy for task_history? Unlimited growth of plaintext audit logs?
4. Are there multi-instance deployments? OAuth replay protection assumes single instance.
5. Is notification failure acceptable? Currently silent failures in send_message().

