# Handlers Layer Code Quality Scout Report

**Analyzed:** task_wizard.py, callbacks.py, task_delete.py, task_update.py, task_view.py
**Date:** 2025-12-18

---

## Critical Issues (Must Fix)

### 1. Duplicate Database Queries in Wizard - MAJOR PERFORMANCE ISSUE
**File:** task_wizard.py
**Lines:** 316-333, 376-393, 859-876, 932-949, 1120-1137, 1703-1713, 1765-1781

**Issue:** Same SQL query executed multiple times identically - fetches recent assignees.
```sql
SELECT DISTINCT u.id, u.display_name, u.username
FROM users u
JOIN tasks t ON t.assignee_id = u.id
WHERE t.creator_id = $1 AND u.id != $1
ORDER BY t.created_at DESC
LIMIT 3
```

Appears in: `deadline_callback()`, `receive_deadline_custom()`, `edit_callback()`, `back_callback()`, `assign_receive_content()`, `assign_edit_callback()`, `assign_back_callback()`

**Impact:** N+1 query pattern when user navigates wizard steps. With 50+ daily active users, creates 300+ redundant queries.

**Severity:** CRITICAL (Performance)

**Fix:** Cache in context or extract to reusable function.

---

### 2. Missing Input Validation - SQL Injection Risk
**File:** callbacks.py
**Lines:** 274, 424, 583, 909, 1178

**Issue:** Callback data split and used without format validation before SQL operations.
```python
# Line 274 - deadline_callback
action = query.data.split(":")[1] if ":" in query.data else ""
# No validation that action is a valid deadline option
```

**Example vulnerable path:**
- User sends malformed callback: `wizard_deadline:'; DROP TABLE tasks; --`
- While parser validates task IDs with regex, deadline/priority actions only check string equality

**Severity:** HIGH (Security)

---

### 3. Overly Broad Exception Handling - Silent Failures
**File:** task_wizard.py  
**Lines:** 335-336, 395-396, 1139-1140, 1215-1216, 1782-1784

**Pattern:**
```python
except Exception:
    recent_users = None
```

**Issue:** Swallows real errors (DB connection loss, API errors) without logging.
- If `db.fetch_all()` fails, user gets no notification and wizard continues with None values
- Makes debugging impossible - error lost silently

**Lines:** 335-336 in `deadline_callback`, 395-396 in `receive_deadline_custom`, similar in 4 other locations

**Severity:** HIGH (Reliability)

---

## High Priority Issues

### 4. Massive Code Duplication - receive_assignee_input vs assign_receive_recipient
**File:** task_wizard.py
**Lines:** 483-569 vs 1231-1315

**Issue:** ~86 lines of IDENTICAL code (user mention parsing) duplicated.

**Duplication includes:**
- Message entity parsing (text_mention/mention)
- Fallback username extraction
- Error handling and validation
- User lookup and deduplication

**Severity:** HIGH (Maintainability)

**Cost:** If bug found in mention parsing, must fix in 2+ places. Already happened - both functions have same logic.

---

### 5. Unvalidated Dynamic SQL in calendar.py
**File:** calendar.py  
**Lines:** 57-65

**Code:**
```python
validated_column = validate_user_setting_column(column)
await db.execute(
    f"UPDATE users SET {validated_column} = $1 WHERE telegram_id = $2",
    value, telegram_id
)
```

**Issue:** While `validate_user_setting_column()` attempts validation, f-string SQL construction is risky pattern.

**Severity:** HIGH (Security - Code smell)

---

### 6. Missing Permission Checks in Multiple Locations
**File:** task_update.py
**Lines:** 201-203 (danglam_command)

**Code:**
```python
# Only assignee can update status
if task["assignee_id"] != db_user["id"]:
    continue  # Silently skips with NO error message
```

**Issue:** 
- No user feedback when permission denied
- User thinks task updated when it didn't
- Different from other commands which send `ERR_NO_PERMISSION` message

**Affected:** danglam_command (line 201-203)

**Severity:** MEDIUM (Security/UX)

---

### 7. Inconsistent Error Handling Pattern
**File:** callbacks.py, task_delete.py, task_update.py  
**Pattern:** Different error responses across similar operations

Examples:
- `handle_complete()` (line 390-410): Logs permission denied via UI
- `danglam_command()` (task_update.py:201-203): Silently continues
- `tiendo_command()` (task_update.py:261-263): Sends error message

**Impact:** Unpredictable UX, hard to trace why commands fail

**Severity:** MEDIUM (Maintainability/UX)

---

## Medium Priority Issues

### 8. Long Functions with Multiple Concerns
**File:** task_wizard.py

Functions exceeding 100 lines mixing multiple responsibilities:

| Function | Lines | Issues |
|----------|-------|--------|
| `confirm_callback` | 200+ | Task creation + 4 types of notifications + logging |
| `assign_confirm_callback` | 170+ | Same - 4 concerns |
| `receive_assignee_input` | 87 | Parsing + lookup + dedup + response |
| `assign_receive_recipient` | 85 | Identical to above |
| `handle_pending_edit` | 244 | 5 different edit types in one function |

**Severity:** MEDIUM (Maintainability)

---

### 9. Swallowed Exceptions in Job Scheduling
**File:** callbacks.py
**Lines:** 549-551, 577-579

**Code:**
```python
except Exception as e:
    logger.debug(f"Could not update countdown: {e}")
```

**Issue:** 
- Uses `logger.debug()` - won't appear in production logs
- Message edit failures silently ignored
- User sees stale countdown button

**Severity:** MEDIUM (Debugging)

---

### 10. Circular Import Risk
**File:** task_wizard.py
**Lines:** 31, 1075

**Code:**
```python
from handlers.calendar import sync_task_to_calendar
from handlers.task_assign import giaoviec_command
```

**Issue:**
- task_wizard imports task_assign
- Line 1075 dynamically imports inside function (slow)
- While functional, circular dependency pattern

**Alternative:** task_assign and task_wizard both need to import from parent module first

**Severity:** MEDIUM (Code smell)

---

### 11. Inconsistent Timezone Handling
**File:** task_wizard.py  
**Lines:** 277-291, 1348-1356

**Issue:** Hardcoded timezone "Asia/Ho_Chi_Minh" in 2 functions.

Should use: `context.user_data.get("timezone", "Asia/Ho_Chi_Minh")` or fetch from DB

**Severity:** MEDIUM (Correctness)

---

### 12. No Pagination in Bulk Operations
**File:** callbacks.py  
**Line:** 759

**Code:**
```python
all_tasks = await get_all_user_related_tasks(db, db_user["id"], limit=50)
```

**Issue:** Hardcoded limit=50 for bulk filter. User with 100+ tasks only sees first 50.

**Severity:** MEDIUM (Functionality)

---

## Low Priority Issues

### 13. Non-standard Logging Levels
**File:** task_delete.py, callbacks.py

Using `logger.debug()` for temporary failures that might need attention:
- Line 404, 432 (task_delete.py): "Could not update countdown"
- Line 551, 579 (callbacks.py): Same

**Fix:** Use `logger.warning()` for expected edge cases, `logger.error()` for unexpected failures

**Severity:** LOW (Observability)

---

### 14. Magic Numbers and String Constants
**File:** Multiple files

Examples:
- `range(9, 0, -1)` for countdown (line 343, 493, 615 - appears 6+ times)
- `limit=50` (line 759)
- `LIMIT 3` for recent users (appears 7+ times)
- `[:100]`, `[:10]`, `[:40]` - truncation widths scattered

**Improvement:** Extract to module-level constants

**Severity:** LOW (Maintainability)

---

### 15. Empty `pass` Statements
**File:** callbacks.py
**Lines:** 280, 353 (implicit)

- Line 280: `elif action == "noop": pass` - acceptable
- No-op patterns can be intentional but should be documented

**Severity:** LOW (Code clarity)

---

### 16. Inconsistent Import Organization
**File:** Multiple files

Patterns vary:
```python
# Type 1: grouped
from database import get_db
from services import (...many imports...)

# Type 2: scattered
from handlers.task_delete import ...
from utils import ...
from handlers.calendar import ...
```

**Suggestion:** Use isort for consistent ordering

**Severity:** LOW (Style)

---

### 17. Missing Type Hints on Complex Returns
**File:** task_wizard.py

Functions returning complex structures without type hints:

```python
def format_wizard_summary(data: dict) -> str:  # ✓ Good
def format_group_task_detail(task: dict, progress_info: dict, child_tasks: list) -> str:  # ✓ Good

# But:
async def handle_pending_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Modifies context.user_data without type hints
```

**Severity:** LOW (Type safety)

---

### 18. String Escaping Issues in Markdown
**File:** task_update.py
**Lines:** 114, 116, 139, 141

**Code:**
```python
text=f"🎉 *VIỆC NHÓM ĐÃ HOÀN THÀNH\\!*\n\n"
```

**Issue:** Escapes `!` with `\!` (incorrect for Markdown). Should be unescaped.

- Line 114, 116 (xong_command) - wrong escaping
- Telegram Markdown doesn't require escaping `!`

**Severity:** LOW (Formatting)

---

## Summary Table

| Category | Count | Severity |
|----------|-------|----------|
| Critical (Security/Performance) | 2 | Critical |
| High (Security/Reliability) | 5 | High |
| Medium (Maintainability) | 5 | Medium |
| Low (Code smell) | 6 | Low |
| **Total Issues** | **18** | - |

---

## Quick Fix Priority

**Week 1 (Critical):**
1. Extract duplicate DB query to helper function
2. Add validation to deadline/priority callback actions
3. Replace broad `except Exception` with specific exceptions + logging

**Week 2 (High):**
4. DRY up `receive_assignee_input()` / `assign_receive_recipient()`
5. Add silent permission check feedback in `danglam_command()`
6. Fix circular imports with lazy loading pattern

**Week 3+ (Medium/Low):**
7. Refactor 100+ line functions
8. Extract magic numbers to constants
9. Standardize logging levels

---

## Files Requiring Attention

| File | Issues | Priority |
|------|--------|----------|
| task_wizard.py | 7 | Critical + High |
| callbacks.py | 4 | Critical + High |
| task_update.py | 3 | Medium + Low |
| task_delete.py | 2 | Low |
| task_view.py | 2 | Low |

---

## Unresolved Questions

1. Is the circular import between task_wizard and task_assign intentional or legacy?
2. Should bulk operations be limited to 50 tasks, or is pagination needed?
3. Is `logger.debug()` for countdown failures intended, or should it be `warning`?
4. Are the hardcoded timezone references user-specific or global?

