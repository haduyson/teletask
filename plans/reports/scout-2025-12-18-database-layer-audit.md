# Database Layer Audit Report
**Date:** 2025-12-18  
**Scope:** Database models, connection management, and migrations  
**Focus:** Indexes, cascade deletes, data integrity, connection pooling, migration safety

---

## CRITICAL ISSUES

### 1. MISSING CASCADE DELETE on Task Relationships (SEVERITY: HIGH)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py`

**Issues:**
- **Line 151-153:** Task.creator_id, Task.assignee_id, Task.group_id have no ondelete cascade
  - When a User is deleted, orphaned tasks remain pointing to NULL creator/assignee
  - When a Group is deleted, orphaned group tasks become stranded
  - No check constraints prevent orphaned records

**Impact:** Data inconsistency, orphaned records accumulate, violates referential integrity

**Details:**
```python
# Line 151-153 - MISSING CASCADE DELETE
creator_id = Column(Integer, ForeignKey("users.id"))  # ❌ No CASCADE
assignee_id = Column(Integer, ForeignKey("users.id"))  # ❌ No CASCADE
group_id = Column(Integer, ForeignKey("groups.id"))  # ❌ No CASCADE

# GroupMember has CASCADE (correct):
group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)  # ✓
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ✓
```

**Action Required:** Add ondelete="CASCADE" to Task.creator_id, assignee_id, group_id

---

### 2. MISSING CASCADE DELETE on Task Foreign Keys (SEVERITY: HIGH)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py`

**Issues:**
- **Line 172:** Task.deleted_by → users(id) - no cascade delete
- **Line 163:** Task.parent_recurring_id → tasks(id) - no cascade
- **Line 325:** DeletedTaskUndo.deleted_by → users(id) - no cascade delete
- **Line 208, 249:** Reminder.user_id and TaskHistory.user_id - no cascade delete

**Impact:** Audit trails and deleted task records break when audit users are purged

**Details:**
```python
# Line 163 - Parent recurring tasks not cascaded
parent_recurring_id = Column(Integer, ForeignKey("tasks.id"))  # ❌ Can orphan child tasks

# Line 172 - Deleted by not cascaded
deleted_by = Column(Integer, ForeignKey("users.id"))  # ❌ Orphans audit trail when user deleted
```

---

### 3. MISSING INDEX on Task.group_task_id Query Path (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:133`

**Issue:**
- Line 133: `group_task_id = Column(String(20), index=True)` - Has index ✓
- BUT: No composite index for queries like `WHERE group_id = ? AND group_task_id = ?`

**Missing Composite Index:**
```python
Index("idx_tasks_group_task_id", "group_id", "group_task_id", postgresql_where="is_deleted = false")
```

**Impact:** Group task lookups will slow down with table growth

---

### 4. MISSING INDEX on Task Deletion Queries (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:189-192`

**Issue:**
- Existing indexes include `is_deleted = false` filter ✓
- BUT missing compound index for soft-delete + date queries
- No index for finding soft-deleted tasks for cleanup

**Missing Indexes:**
```python
# For cleanup queries: DELETE WHERE is_deleted = true AND deleted_at < ?
Index("idx_tasks_deleted_cleanup", "deleted_at", "is_deleted", postgresql_where="is_deleted = true")

# For finding tasks deleted by specific user
Index("idx_tasks_deleted_by", "deleted_by", postgresql_where="is_deleted = true")
```

**Impact:** Undo buffer cleanup and deletion audits will be slow

---

### 5. MISSING INDEX on UserStatistics (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:279-280`

**Issue:**
- Line 279: `user_id` - No index
- Line 280: `group_id` - No index
- Foreign keys without indexes = full table scan on joins

**Details:**
```python
__table_args__ = (
    UniqueConstraint("user_id", "group_id", "period_type", "period_start", name="uq_user_stats"),
    Index("idx_stats_user", "user_id", "period_type", "period_start"),
    # ❌ MISSING: Index on group_id alone for group-level stats queries
)
```

**Missing Index:**
```python
Index("idx_stats_group", "group_id", "period_type", "period_start")
```

---

### 6. MISSING CONSTRAINT: Cannot Validate Recurring Task Relationships (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:163`

**Issue:**
- `parent_recurring_id = Column(Integer, ForeignKey("tasks.id"))` - No validation
- Can link a non-recurring task as parent to recurring task
- No check constraint: `parent_recurring_id IS NULL OR is_recurring = true`

**Impact:** Data inconsistency in recurring task hierarchy

---

### 7. MISSING CHECK CONSTRAINT: reminder_type Validation in Reminders (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:211-214`

**Issue:**
- Line 211-214: `reminder_type` column has check constraint ✓
- BUT: Migration `20251217_0001_notification_settings.py:21-23` adds new boolean columns
- No validation that notify_* columns don't conflict with reminder_source logic

**Details:**
```python
# Line 211-214 - Properly constrained
reminder_type = Column(String(50), nullable=False)
# Check constraint: reminder_type IN ('before_deadline', 'after_deadline', 'custom')

# BUT migrations add contradictory settings:
# Migration 0008:21-23: notify_all, notify_task_assigned, notify_task_status
# Migration 0005:22-29: reminder_source = 'both'|'telegram'|'google_calendar'
# Migration 0006:24-29: calendar_sync_interval = 'manual'|'12h'|'24h'|'weekly'
# ❌ No validation preventing conflicting combinations
```

**Impact:** Contradictory notification settings can be set simultaneously

---

## CONNECTION POOL ISSUES

### 8. TRANSACTION METHOD Missing Proper Context Management (SEVERITY: HIGH)
**File:** `/home/botpanel/bots/hasontechtask/database/connection.py:152-166`

**Issue:**
- Line 152-166: `transaction()` method acquires connection but doesn't use async context manager
- Connection is NOT returned to pool on exception
- No automatic rollback on failure

**Details:**
```python
async def transaction(self) -> Connection:
    """Get connection for manual transaction management."""
    pool = await self._ensure_pool()
    conn = await pool.acquire()
    return conn  # ❌ No context manager! Connection leak on exception
```

**Correct Usage Required:**
```python
async with db.transaction() as conn:
    await conn.execute(...)  # Must NOT raise exception or connection is lost!
```

**Impact:** Connection pool exhaustion under error conditions

**Fix Needed:**
```python
@asynccontextmanager
async def transaction(self):
    pool = await self._ensure_pool()
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)
```

---

### 9. POOL TIMEOUT Not Documented (SEVERITY: LOW)
**File:** `/home/botpanel/bots/hasontechtask/database/connection.py:31,55`

**Issue:**
- Default command_timeout = 60 seconds (hardcoded)
- No documentation on when this timeout triggers
- asyncpg distinguishes: connection acquisition timeout vs. command timeout

**Details:**
```python
async def connect(
    self,
    dsn: str,
    min_size: int = 2,
    max_size: int = 10,
    timeout: float = 60.0,  # ❌ Only affects command_timeout, not acquire timeout
    timezone: str = "Asia/Ho_Chi_Minh",
)
```

**Missing:** `connection_timeout` parameter for pool.acquire() operations

---

## MIGRATION ISSUES

### 10. MIGRATION: Duplicate Revision IDs (SEVERITY: HIGH)
**Files:**
- `20251217_0001_notification_settings.py` - revision = '0008'
- `20251217_0007_user_reminder_prefs.py` - revision = '0007'
- `20251218_0009_task_id_sequence.py` - revision = '0009'

**Issue:**
- Migration naming is inconsistent with revision IDs
- File: `20251217_0001_notification_settings.py` has revision = '0008' (should be 0008 or 0001)
- File: `20251217_0007_user_reminder_prefs.py` has revision = '0007'
- This creates ambiguous revision chain

**Details:**
```
Expected chain:
0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009

Actual (inferred):
20241214_0001_initial → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009
                        but files named 0001, 0002, ... 0007, 0001, 0009 (jumps, duplicates)
```

**Impact:** Migration failures, cannot rollback properly, sequence violations

---

### 11. MIGRATION: Sequence Creation without Error Handling (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/migrations/versions/20251218_0009_task_id_sequence.py:31`

**Issue:**
- Line 31: Uses f-string for SQL injection risk
- No validation that `start_value` is valid
- Downgrade logic doesn't handle sequence in use

**Details:**
```python
def upgrade() -> None:
    # Line 28: Can throw if result is None or has invalid value
    start_value = int(result[0]) + 1 if result else 1
    
    # Line 31: ❌ SQL injection via f-string
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS task_id_seq START WITH {start_value}")
    
    # Should use:
    # op.execute(f"CREATE SEQUENCE IF NOT EXISTS task_id_seq START WITH {int(start_value)}")
```

**Risk:** Integer overflow, SQL injection (low risk since start_value is from DB, but bad practice)

---

### 12. MIGRATION: Missing Cascade Delete in Recurring Templates (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/migrations/versions/20241215_0002_recurring_templates.py:48`

**Issue:**
- recurring_templates table references users, groups without cascade delete
- Migration adds foreign key to tasks.recurring_template_id without cascade

**Details:**
```python
sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),  # ❌ No ondelete
sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),  # ❌ No ondelete
sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),  # ❌ No ondelete
```

**Impact:** Orphaned recurring templates when users/groups deleted

---

### 13. MIGRATION: Check Constraint Without Enforcement (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/migrations/versions/20251216_0005_reminder_source.py:26`

**Issue:**
- Migration adds `reminder_source` column with no check constraint
- Allows invalid values: anything except 'both', 'telegram', 'google_calendar'

**Expected:**
```python
sa.CheckConstraint(
    "reminder_source IN ('both', 'telegram', 'google_calendar')",
    name="ck_reminder_source"
)
```

---

## DATA INTEGRITY CONSTRAINTS

### 14. MISSING: Check Constraints for Notification Preferences (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:48-54`

**Issue:**
- User notification columns lack consistency checks
- No constraint: `notify_reminder OR notify_weekly_report OR notify_monthly_report = true`
- User could have all notifications disabled with no validation

---

### 15. MISSING: Validation for Task Progress vs Status (SEVERITY: MEDIUM)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:148,138-142`

**Issue:**
- Line 148: `progress` (0-100) can be set without constraining by status
- No check: `(status = 'completed' AND progress = 100) OR (status != 'completed' AND progress < 100)`

**Impact:** Inconsistent states: completed task at 50% progress

---

### 16. MISSING: OnDelete Behavior for DeletedTaskUndo Records (SEVERITY: LOW)
**File:** `/home/botpanel/bots/hasontechtask/database/models.py:325`

**Issue:**
- DeletedTaskUndo stores `task_id` (integer, not FK) and `task_data` (JSONB copy)
- But `deleted_by` is FK without cascade
- If undo record stays but user is deleted, orphaned record remains

**Note:** This is low priority since undo records expire (30 seconds), but still violates referential integrity

---

## RECOMMENDATIONS SUMMARY

### Immediate Fixes (CRITICAL)
1. Add `ondelete="CASCADE"` to Task.creator_id, assignee_id, group_id
2. Fix transaction() method to use async context manager
3. Fix migration revision ID chain (20251217_0001 should be 0008, not 0001)

### High Priority
4. Add missing composite indexes for group_task_id queries
5. Add cascade delete to all remaining FK relationships
6. Add check constraints for reminder_source, calendar_sync_interval values

### Medium Priority
7. Add missing indexes on UserStatistics.group_id
8. Add validation constraints for notification settings conflicts
9. Fix migration 0002 recurring_templates cascade deletes
10. Add check constraint for task progress vs status consistency

### Low Priority
11. Document connection pool timeout behavior
12. Add connection_timeout parameter to pool configuration
13. Improve migration SQL injection protection

---

## INVENTORY OF FOREIGN KEYS

### WITH CASCADE DELETE ✓
- GroupMember.group_id → groups(id)
- GroupMember.user_id → users(id)
- Reminder.task_id → tasks(id)
- TaskHistory.task_id → tasks(id)
- ExportReports.user_id → users(id)
- Task.reminders (relationship cascade)
- Task.history (relationship cascade)

### WITHOUT CASCADE DELETE ❌
- Task.creator_id → users(id)
- Task.assignee_id → users(id)
- Task.group_id → groups(id)
- Task.deleted_by → users(id)
- Task.parent_recurring_id → tasks(id)
- Reminder.user_id → users(id)
- TaskHistory.user_id → users(id)
- UserStatistics.user_id → users(id)
- UserStatistics.group_id → groups(id)
- DeletedTaskUndo.deleted_by → users(id)

---

## INVENTORY OF INDEXES

### EXISTING ✓
- User.telegram_id (unique)
- User.username
- Group.telegram_id (unique)
- Task.public_id (unique, indexed)
- Task.group_task_id (indexed)
- Task.is_deleted (indexed)
- GroupMember: idx_gm_group, idx_gm_user
- Task: idx_tasks_assignee_status, idx_tasks_creator, idx_tasks_deadline, idx_tasks_group
- Reminder: idx_reminders_pending, idx_reminders_task
- TaskHistory: idx_history_task
- UserStatistics: idx_stats_user
- DeletedTaskUndo: idx_undo_expires

### MISSING ❌
- Tasks (group_id, group_task_id) composite
- Tasks (deleted_at, is_deleted) for cleanup queries
- Tasks (deleted_by) for audit queries
- UserStatistics.group_id (direct index)

---

## UNRESOLVED QUESTIONS
1. What is the intended behavior when a User is deleted? Should their created/assigned tasks be cascaded or orphaned?
2. Should DeletedTaskUndo records be cleaned up automatically or retained for audit purposes?
3. What is the conflict resolution strategy for notify_* columns vs reminder_source setting?
4. Are there planned indexes for full-text search on Task.content?
