# Database Layer Scout Report
**Date:** 2025-12-18  
**Focus:** Database models, connections, relationships, and migration structure

---

## Executive Summary

The TeleTask bot uses a PostgreSQL database with SQLAlchemy ORM (async via asyncpg) and Alembic for migrations. The schema supports task management for individual users and groups with reminders, history tracking, statistics, and Google Calendar integration. 9 core tables with cascading relationships and check constraints.

---

## 1. Database Models & Fields

### 1.1 Users (`users`)
**Purpose:** Telegram user profiles and notification preferences.

**Fields:**
- `id` (PK): Integer
- `telegram_id` (Unique, Indexed): BigInteger
- `username` (Indexed): String(255)
- `first_name`: String(255)
- `last_name`: String(255)
- `display_name`: String(500)
- `timezone`: String(50) = "Asia/Ho_Chi_Minh"
- `language`: String(10) = "vi"
- `notify_reminder`: Boolean = True
- `notify_weekly_report`: Boolean = True
- `notify_monthly_report`: Boolean = True
- `notify_all`: Boolean = True (added in migration 0008)
- `notify_task_assigned`: Boolean = True (added in migration 0008)
- `notify_task_status`: Boolean = True (added in migration 0008)
- `google_calendar_token`: Text (Phase 09 - Google Calendar)
- `google_calendar_refresh_token`: Text
- `calendar_sync_interval`: String(20) = "manual" (added in migration 0006)
- `is_active`: Boolean = True
- `created_at`: DateTime(tz)
- `updated_at`: DateTime(tz)

**Indexes:**
- `idx_users_telegram` on `telegram_id`
- `idx_users_username` on `username` (partial: username IS NOT NULL)

---

### 1.2 Groups (`groups`)
**Purpose:** Telegram group information for group task management.

**Fields:**
- `id` (PK): Integer
- `telegram_id` (Unique, Indexed): BigInteger
- `title`: String(255)
- `is_active`: Boolean = True
- `created_at`: DateTime(tz)
- `updated_at`: DateTime(tz)

**Indexes:**
- `idx_groups_telegram` on `telegram_id`

---

### 1.3 GroupMember (`group_members`)
**Purpose:** Links users to groups with role information.

**Fields:**
- `id` (PK): Integer
- `group_id` (FK → groups.id, CASCADE): Integer
- `user_id` (FK → users.id, CASCADE): Integer
- `role`: String(50) = "member" (values: 'admin', 'member')
- `joined_at`: DateTime(tz)

**Constraints:**
- Unique: `(group_id, user_id)` named `uq_group_user`

**Indexes:**
- `idx_gm_group` on `group_id`
- `idx_gm_user` on `user_id`

---

### 1.4 Task (`tasks`)
**Purpose:** Core task model storing task info, status, and relationships.

**Fields:**
- `id` (PK): Integer
- `public_id` (Unique, Indexed): String(20) — e.g., "P-1234" or "G-500"
- `group_task_id` (Indexed): String(20) — parent G-ID for group tasks
- `content` (Not Null): Text
- `description`: Text
- `status` (Default: "pending"): String(20)
  - Check: IN ('pending', 'in_progress', 'completed')
- `priority` (Default: "normal"): String(20)
  - Check: IN ('low', 'normal', 'high', 'urgent')
- `progress` (Default: 0): Integer
  - Check: >= 0 AND <= 100
- `creator_id` (FK → users.id): Integer
- `assignee_id` (FK → users.id): Integer
- `group_id` (FK → groups.id): Integer
- `deadline`: DateTime(tz)
- `completed_at`: DateTime(tz)
- `is_recurring` (Default: False): Boolean
- `recurring_pattern`: String(100) — values: 'daily', 'weekly', 'monthly', 'custom'
- `recurring_config`: JSONB — e.g., `{'interval': 1, 'days': [1,3,5]}`
- `parent_recurring_id` (FK → tasks.id): Integer — self-reference for recurring task hierarchy
- `recurring_template_id` (FK → recurring_templates.id): Integer (added in migration 0002)
- `google_event_id`: String(255)
- `is_personal` (Default: False): Boolean
- `is_deleted` (Default: False, Indexed): Boolean — soft delete flag
- `deleted_at`: DateTime(tz)
- `deleted_by` (FK → users.id): Integer
- `created_at`: DateTime(tz)
- `updated_at`: DateTime(tz)

**Indexes:**
- `idx_tasks_public` on `public_id`
- `idx_tasks_group_task` on `group_task_id` (partial: group_task_id IS NOT NULL)
- `idx_tasks_assignee_status` on `(assignee_id, status)` (partial: is_deleted = false)
- `idx_tasks_creator` on `creator_id` (partial: is_deleted = false)
- `idx_tasks_deadline` on `deadline` (partial: is_deleted = false AND status != 'completed')
- `idx_tasks_group` on `group_id` (partial: is_deleted = false)

---

### 1.5 Reminder (`reminders`)
**Purpose:** Scheduled notifications for tasks.

**Fields:**
- `id` (PK): Integer
- `task_id` (FK → tasks.id, CASCADE): Integer
- `user_id` (FK → users.id): Integer
- `remind_at` (Not Null): DateTime(tz)
- `reminder_type` (Not Null): String(50)
  - Check: IN ('before_deadline', 'after_deadline', 'custom')
- `reminder_offset`: String(20) — e.g., '3d', '24h', '1h'
- `is_sent` (Default: False): Boolean
- `sent_at`: DateTime(tz)
- `error_message`: Text
- `created_at`: DateTime(tz)

**Indexes:**
- `idx_reminders_pending` on `remind_at` (partial: is_sent = false)
- `idx_reminders_task` on `task_id`

---

### 1.6 TaskHistory (`task_history`)
**Purpose:** Audit trail for task changes.

**Fields:**
- `id` (PK): Integer
- `task_id` (FK → tasks.id, CASCADE): Integer
- `user_id` (FK → users.id): Integer
- `action` (Not Null): String(50) — values: 'created', 'updated', 'completed', 'deleted'
- `field_name`: String(100) — e.g., 'status', 'deadline', 'assignee'
- `old_value`: Text
- `new_value`: Text
- `note`: Text
- `created_at`: DateTime(tz)

**Indexes:**
- `idx_history_task` on `(task_id, created_at)`

---

### 1.7 UserStatistics (`user_statistics`)
**Purpose:** Aggregated task statistics per period (weekly/monthly).

**Fields:**
- `id` (PK): Integer
- `user_id` (FK → users.id): Integer
- `group_id` (FK → groups.id): Integer
- `period_type` (Not Null): String(20) — values: 'weekly', 'monthly'
- `period_start` (Not Null): Date
- `period_end` (Not Null): Date
- **Tasks Assigned (giao viec):**
  - `tasks_assigned_total`: Integer = 0
  - `tasks_assigned_completed`: Integer = 0
  - `tasks_assigned_overdue`: Integer = 0
- **Tasks Received (nhan viec):**
  - `tasks_received_total`: Integer = 0
  - `tasks_received_completed`: Integer = 0
  - `tasks_received_overdue`: Integer = 0
- **Personal Tasks:**
  - `tasks_personal_total`: Integer = 0
  - `tasks_personal_completed`: Integer = 0
- `created_at`: DateTime(tz)

**Constraints:**
- Unique: `(user_id, group_id, period_type, period_start)` named `uq_user_stats`

**Indexes:**
- `idx_stats_user` on `(user_id, period_type, period_start)`

---

### 1.8 DeletedTaskUndo (`deleted_tasks_undo`)
**Purpose:** Undo buffer for deleted tasks (30-second window).

**Fields:**
- `id` (PK): Integer
- `task_id` (Not Null): Integer — original task ID (not FK, to allow restoration of deleted tasks)
- `task_data` (Not Null): JSONB — full task snapshot
- `deleted_by` (FK → users.id): Integer
- `deleted_at`: DateTime(tz)
- `expires_at`: DateTime(tz) — calculated: deleted_at + 30 seconds
- `is_restored` (Default: False): Boolean

**Indexes:**
- `idx_undo_expires` on `expires_at` (partial: is_restored = false)

---

### 1.9 BotConfig (`bot_config`)
**Purpose:** Key-value store for bot settings.

**Fields:**
- `id` (PK): Integer
- `key` (Unique, Not Null): String(100)
- `value`: Text
- `description`: Text
- `updated_at`: DateTime(tz)

**Default Entries:**
```
bot_name: "Task Manager Bot"
bot_description: "He thong quan ly va nhac viec"
support_telegram: "@support"
support_phone: ""
support_email: ""
admin_telegram_id: ""
timezone: "Asia/Ho_Chi_Minh"
task_id_counter: "0"
recurring_id_counter: "0"
```

---

### 1.10 RecurringTemplate (`recurring_templates`) — From Migration 0002
**Purpose:** Stores recurring task definitions.

**Fields:**
- `id` (PK): Integer
- `public_id` (Unique, Indexed): String(20)
- `content` (Not Null): Text
- `description`: Text
- `priority` (Default: "normal"): String(20)
- `creator_id` (FK → users.id, Not Null): Integer
- `assignee_id` (FK → users.id): Integer
- `group_id` (FK → groups.id): Integer
- `is_personal` (Default: True): Boolean
- **Recurrence Config:**
  - `recurrence_type` (Not Null): String(20) — values: 'daily', 'weekly', 'monthly'
  - `recurrence_interval` (Default: 1): Integer — every N days/weeks/months
  - `recurrence_days`: ARRAY(Integer) — days of week (0-6) or month (1-31)
  - `recurrence_time`: Time — time of day for deadline
  - `recurrence_end_date`: Date — when to stop generating
  - `recurrence_count`: Integer — max instances to generate
- **Tracking:**
  - `last_generated`: DateTime(tz)
  - `next_due`: DateTime(tz)
  - `instances_created` (Default: 0): Integer
  - `is_active` (Default: True): Boolean
- `created_at`: DateTime(tz)
- `updated_at`: DateTime(tz)

**Indexes:**
- `idx_recurring_creator` on `creator_id`
- `idx_recurring_next` on `next_due` (partial: is_active = true)
- `idx_recurring_public` on `public_id`

---

## 2. Model Relationships

### Relationship Graph:
```
User
├── created_tasks: Task (back_populates="creator")
├── assigned_tasks: Task (back_populates="assignee")
├── group_memberships: GroupMember (back_populates="user")
└── statistics: UserStatistics (back_populates="user")

Group
├── members: GroupMember (back_populates="members")
├── tasks: Task (back_populates="group")
└── statistics: UserStatistics (back_populates="group")

GroupMember
├── group: Group (back_populates="members")
└── user: User (back_populates="group_memberships")

Task
├── creator: User (foreign_keys=[creator_id])
├── assignee: User (foreign_keys=[assignee_id])
├── group: Group (back_populates="tasks")
├── reminders: Reminder (cascade="all, delete-orphan")
├── history: TaskHistory (cascade="all, delete-orphan")
└── parent_recurring: Task (remote_side=[id], self-reference)

Reminder
├── task: Task (back_populates="reminders")
└── user: User (no back_populates)

TaskHistory
├── task: Task (back_populates="history")
└── user: User (no back_populates)

UserStatistics
├── user: User (back_populates="statistics")
└── group: Group (back_populates="statistics")

DeletedTaskUndo
└── user: User (no back_populates)

RecurringTemplate
├── creator: User
├── assignee: User
└── group: Group
```

### Cascade Delete Rules:
- `GroupMember` → CASCADE delete when Group or User deleted
- `Reminder` → CASCADE delete when Task deleted
- `TaskHistory` → CASCADE delete when Task deleted

---

## 3. Database Connection Strategy

**Strategy:** Async PostgreSQL with connection pooling via `asyncpg`

### Connection Module (`connection.py`)
**File:** `/home/botpanel/bots/hasontechtask/database/connection.py`

**Implementation:**
- **Class:** `Database` — singleton instance `db`
- **Connection Type:** Async pool-based (asyncpg)
- **Pool Configuration:**
  - `min_size` (default: 2)
  - `max_size` (default: 10)
  - `command_timeout` (default: 60.0 seconds)
  - `timezone` (default: "Asia/Ho_Chi_Minh")

**Key Methods:**
| Method | Purpose |
|--------|---------|
| `async connect(dsn, min_size, max_size, timeout, timezone)` | Initialize connection pool |
| `async close()` | Close pool |
| `async fetch_one(query, *args)` | Fetch single row |
| `async fetch_all(query, *args)` | Fetch all rows |
| `async fetch_val(query, *args)` | Fetch single value |
| `async execute(query, *args)` | Execute without return |
| `async execute_many(query, args_list)` | Batch execute |
| `async transaction()` | Get connection for manual transaction |
| `async health_check()` | Check database accessibility |
| `is_connected` (property) | Check if pool exists |

**Usage Pattern:**
```python
from database import init_database, get_db

# Initialize on startup
await init_database(dsn="postgresql://user:pass@localhost/db")

# Use singleton
db = get_db()
result = await db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)

# Close on shutdown
await close_database()
```

**Strengths:**
- ✅ Fully async (non-blocking)
- ✅ Connection pooling for efficiency
- ✅ Singleton pattern for app-wide access
- ✅ Built-in health check
- ✅ Raw SQL query interface

---

## 4. Migration Structure

**Tool:** Alembic v1.x  
**Location:** `/home/botpanel/bots/hasontechtask/database/migrations/`

### Migration Files Overview

| Revision | Date | File | Description |
|----------|------|------|-------------|
| 0001 | 2024-12-14 | `20241214_0001_initial_schema.py` | Create all 9 tables: users, groups, group_members, tasks, reminders, task_history, user_statistics, deleted_tasks_undo, bot_config |
| 0002 | 2024-12-15 | `20241215_0002_recurring_templates.py` | Add recurring_templates table + recurring_template_id FK to tasks |
| 0003 | 2025-12-15 | `20251215_0003_group_tasks.py` | (Not read, but inferred: group task enhancements) |
| 0004 | 2025-12-16 | `20251216_0004_export_reports.py` | (Not read, but inferred: export/report features) |
| 0005 | 2025-12-16 | `20251216_0005_reminder_source.py` | (Not read, but inferred: reminder source tracking) |
| 0006 | 2025-12-16 | `20251216_0006_calendar_sync_interval.py` | Add `calendar_sync_interval` to users table (default: 'manual') |
| 0007 | 2025-12-17 | `20251217_0007_user_reminder_prefs.py` | (Not read, but inferred: user reminder preferences) |
| 0008 | 2025-12-17 | `20251217_0001_notification_settings.py` | Add `notify_all`, `notify_task_assigned`, `notify_task_status` to users |
| 0009 | 2025-12-18 | `20251218_0009_task_id_sequence.py` | Create PostgreSQL sequence `task_id_seq` for atomic ID generation (fixes race condition) |

### Alembic Configuration (`env.py`)
**Features:**
- Supports offline mode (SQL script generation)
- Supports online mode (direct execution)
- Auto-loads models from `database.models.Base`
- Reads `DATABASE_URL` from environment
- Handles timezone settings

**Migration Methods:**
- SQLAlchemy ORM (DDL via `op.*`)
- Raw SQL execution (via `op.execute()`)

---

## 5. Key Design Patterns

### 5.1 Soft Delete Pattern
Tasks use logical deletion:
- `is_deleted: Boolean` flag
- `deleted_at: DateTime` timestamp
- `deleted_by: Integer` user reference
- **Queries must filter:** `is_deleted = false` (enforced via partial indexes)
- 30-second undo window via `DeletedTaskUndo` buffer

### 5.2 Public ID Pattern
Each task has a `public_id` (e.g., "P-1234", "G-500"):
- User-friendly identifier (vs internal `id`)
- Unique constraint + index
- Counter stored in `bot_config` table
- Latest migration (0009) adds PostgreSQL sequence for atomic generation

### 5.3 Recurring Task Pattern
Two approaches supported:
1. **Template-Based:** `RecurringTemplate` defines recurrence rules; instances created separately
2. **Self-Referencing:** Task.parent_recurring_id links to parent task

### 5.4 Audit Trail
`TaskHistory` table tracks all changes:
- Action type (created, updated, completed, deleted)
- Field-level tracking (old_value, new_value)
- User attribution
- Indexed by (task_id, created_at) for fast history queries

### 5.5 Role-Based Group Membership
`GroupMember.role` supports: 'admin', 'member'
- Enables fine-grained access control at application level

---

## 6. Performance Considerations

### Optimized Indexes
- **Partial indexes** on soft-deleted queries reduce index size
- **Composite indexes** on common query patterns (e.g., assignee+status)
- **JSONB support** for flexible recurring configs

### Query Optimization Tips
1. Filter by `is_deleted = false` to leverage partial indexes
2. Use `(assignee_id, status)` composite for user task queries
3. Defer timezone conversions to application layer
4. Use sequences for atomic ID generation (migration 0009)

### Potential Hotspots
- `task_id_counter` read/write contention → solved by sequence in migration 0009
- Statistics aggregation (weekly/monthly) → denormalized in UserStatistics table
- Recurring task generation → separate table + tracking columns

---

## 7. Exports & Initialization

**File:** `/home/botpanel/bots/hasontechtask/database/__init__.py`

**Exports:**
- Connection: `Database`, `db`, `init_database()`, `close_database()`, `get_db()`
- Models: `Base`, `User`, `Group`, `GroupMember`, `Task`, `Reminder`, `TaskHistory`, `UserStatistics`, `DeletedTaskUndo`, `BotConfig`

**Typical Startup:**
```python
from database import init_database, Base, get_db
from database.connection import db

# Initialize database
await init_database(dsn="postgresql://...")

# Access instance
db = get_db()
```

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Database Type** | PostgreSQL (async asyncpg) |
| **ORM** | SQLAlchemy 2.x with declarative_base |
| **Migration Tool** | Alembic |
| **Tables** | 10 (users, groups, group_members, tasks, reminders, task_history, user_statistics, deleted_tasks_undo, bot_config, recurring_templates) |
| **Total Migrations** | 9 (0001-0009) |
| **Relationships** | ~15 relationships with cascade delete support |
| **Connection Model** | Async pool (min=2, max=10) |
| **Key Features** | Soft delete, public IDs, audit trails, recurring tasks, Google Calendar integration, atomic ID sequences |
| **Constraints** | Check constraints on status/priority/progress, unique constraints on public_id, composite uniqueness on stats |

---

## Unresolved Questions

1. What is the schema of migrations 0003, 0004, 0005, 0007? (Not provided but inferred from filenames)
2. How are task IDs (P-1234, G-500) formatted? Is the prefix determined by context (personal vs group)?
3. What is the exact structure of `recurring_config` JSONB field? (Partially known from schema but not detailed)
4. How are email/export reports stored (migration 0004)?
5. How is `reminder_source` tracked (migration 0005)?

