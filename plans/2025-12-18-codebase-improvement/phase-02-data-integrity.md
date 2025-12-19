# Phase 02: Data Integrity & Database Fixes

**Priority**: HIGH
**Status**: PENDING
**Issues**: 12
**Estimated**: 10 hours

## Context Links
- [Main Plan](./plan.md)
- [Database Audit](../reports/scout-2025-12-18-database-layer-audit.md)
- [Database Review](../reports/code-reviewer-251218-2320-database-models-connection.md)

## Overview

| Metric | Value |
|--------|-------|
| Date | 2025-12-18 |
| Priority | HIGH |
| Files Affected | 5 |
| Migrations Required | 2 |

## Key Insights

1. 10 foreign keys missing CASCADE/SET NULL - orphaned records risk
2. Migration revision IDs don't match filenames - broken chain
3. Missing check constraints on reminder_source
4. No composite indexes for common query patterns

## Requirements

- All FKs must have explicit ondelete behavior
- Fix migration chain for safe rollbacks
- Add missing check constraints
- Create composite indexes for performance

## Related Code Files

- `database/models.py:151-153, 163, 172, 208, 249, 279-280, 325`
- `database/migrations/versions/*` - All migration files
- `alembic.ini` - Migration config

## Implementation Steps

### 1. Add CASCADE to Foreign Keys (3 hours)

**File**: `database/models.py`

```python
# Task model - lines 151-153, 163, 172
creator_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True
)
assignee_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True
)
group_id = Column(
    BigInteger,
    ForeignKey("groups.id", ondelete="CASCADE"),
    nullable=True
)
parent_recurring_id = Column(
    BigInteger,
    ForeignKey("tasks.id", ondelete="SET NULL"),
    nullable=True
)
deleted_by = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True
)

# Reminder model - line 208
user_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False
)

# TaskHistory model - line 249
user_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True
)

# UserStatistics model - lines 279-280
user_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False
)
group_id = Column(
    BigInteger,
    ForeignKey("groups.id", ondelete="CASCADE"),
    nullable=True
)

# DeletedTaskUndo model - line 325
deleted_by = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True
)
```

### 2. Fix Migration Revision IDs (2 hours)

Current state has mismatched filenames/revisions:
- `20251217_0001_notification_settings.py` has revision `0008`
- `20251218_0009_task_id_sequence.py` has revision `0009`

Fix by renaming files to match revisions or vice versa.

### 3. Add Check Constraints (2 hours)

Create new migration:

```python
# database/migrations/versions/20251218_0010_add_check_constraints.py

def upgrade():
    # Add reminder_source constraint
    op.create_check_constraint(
        'ck_tasks_reminder_source',
        'tasks',
        "reminder_source IN ('both', 'telegram', 'google_calendar')"
    )

    # Add progress vs status consistency (optional)
    op.create_check_constraint(
        'ck_tasks_progress_status',
        'tasks',
        "(status != 'completed' OR progress = 100)"
    )

def downgrade():
    op.drop_constraint('ck_tasks_reminder_source', 'tasks')
    op.drop_constraint('ck_tasks_progress_status', 'tasks')
```

### 4. Add Missing Indexes (3 hours)

```python
# database/migrations/versions/20251218_0011_add_indexes.py

def upgrade():
    # Composite index for group task queries
    op.create_index(
        'idx_tasks_group_task_id',
        'tasks',
        ['group_id', 'group_task_id'],
        postgresql_where=text("group_id IS NOT NULL")
    )

    # Index for soft delete cleanup
    op.create_index(
        'idx_tasks_deleted_cleanup',
        'tasks',
        ['deleted_at', 'is_deleted'],
        postgresql_where=text("is_deleted = true")
    )

    # Index for UserStatistics group queries
    op.create_index(
        'idx_user_statistics_group',
        'user_statistics',
        ['group_id'],
        postgresql_where=text("group_id IS NOT NULL")
    )

    # Index for audit queries
    op.create_index(
        'idx_deleted_task_undo_deleted_by',
        'deleted_task_undo',
        ['deleted_by']
    )

    # Index for completed task reports
    op.create_index(
        'idx_tasks_completed_at',
        'tasks',
        ['completed_at'],
        postgresql_where=text("status = 'completed'")
    )

def downgrade():
    op.drop_index('idx_tasks_group_task_id')
    op.drop_index('idx_tasks_deleted_cleanup')
    op.drop_index('idx_user_statistics_group')
    op.drop_index('idx_deleted_task_undo_deleted_by')
    op.drop_index('idx_tasks_completed_at')
```

## Todo List

- [ ] Add ondelete to Task.creator_id
- [ ] Add ondelete to Task.assignee_id
- [ ] Add ondelete to Task.group_id
- [ ] Add ondelete to Task.parent_recurring_id
- [ ] Add ondelete to Task.deleted_by
- [ ] Add ondelete to Reminder.user_id
- [ ] Add ondelete to TaskHistory.user_id
- [ ] Add ondelete to UserStatistics FKs
- [ ] Add ondelete to DeletedTaskUndo.deleted_by
- [ ] Fix migration revision chain
- [ ] Create check constraints migration
- [ ] Create indexes migration
- [ ] Test migrations up/down
- [ ] Run on staging DB

## Success Criteria

- [ ] All 10 FKs have ondelete behavior
- [ ] Migration chain passes `alembic check`
- [ ] Check constraints enforced at DB level
- [ ] All indexes created
- [ ] Migrations reversible

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing orphans block FK | Medium | HIGH | Clean orphans first |
| Check constraints fail existing data | Medium | HIGH | Validate data before migration |
| Index creation locks table | Low | MEDIUM | Use CONCURRENTLY |

## Next Steps

After completion proceed to Phase 03 (Code Quality).
