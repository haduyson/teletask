# TeleTask Bot - Codebase Summary

## Overview

TeleTask Bot is a 68-file Python project (~21,666 lines) implementing a Vietnamese Telegram task management bot with advanced features like reminders, calendar sync, and reporting.

**Entry Point**: `bot.py` (290 lines)
**Language**: Python 3.11
**Key Dependencies**: python-telegram-bot, SQLAlchemy 2.0, APScheduler, asyncpg

## Directory Structure

```
teletask-bot/
├── bot.py                          # Main entry point (async initialization, polling)
├── requirements.txt                # Dependencies list
├── alembic.ini                     # Database migration config
├── ecosystem.config.js             # PM2 process management config
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Environment variable loading & validation
│
├── database/
│   ├── __init__.py                 # Database instance getter
│   ├── connection.py               # Async pool manager, session management
│   ├── models.py                   # 10 SQLAlchemy ORM models
│   └── migrations/
│       ├── env.py                  # Alembic environment config
│       ├── script.py.mako          # Migration template
│       └── versions/               # 9 database schema versions
│           ├── 20241214_0001_initial_schema.py
│           ├── 20241215_0002_recurring_templates.py
│           ├── 20251215_0003_group_tasks.py
│           ├── 20251216_0004_export_reports.py
│           ├── 20251216_0005_reminder_source.py
│           ├── 20251216_0006_calendar_sync_interval.py
│           ├── 20251217_0001_notification_settings.py
│           ├── 20251217_0007_user_reminder_prefs.py
│           └── 20251218_0009_task_id_sequence.py
│
├── handlers/                       # 15 command/callback handler modules
│   ├── __init__.py                 # Handler registration function
│   ├── start.py                    # /start command (onboarding)
│   ├── task_create.py              # Task creation handler
│   ├── task_wizard.py              # Multi-step task creation (70KB - largest)
│   ├── task_view.py                # /xemviec (view tasks by status/filter)
│   ├── task_update.py              # /xong /danglam /tiendo (status updates)
│   ├── task_assign.py              # /giaoviec (group task assignment)
│   ├── task_delete.py              # /xoa (soft delete with undo)
│   ├── callbacks.py                # 50+ inline button handlers (48KB)
│   ├── reminder.py                 # /nhacviec (set reminders)
│   ├── recurring_task.py           # /vieclaplai (recurring patterns)
│   ├── statistics.py               # /thongke (task metrics)
│   ├── export.py                   # /export (CSV/XLSX/PDF reports)
│   ├── calendar.py                 # /lichgoogle (Calendar OAuth flow)
│   └── settings.py                 # /caidat (user preferences)
│
├── services/                       # 11 business logic modules
│   ├── __init__.py                 # Service initialization
│   ├── task_service.py             # CRUD operations (P-ID/G-ID system)
│   ├── notification.py             # Telegram message formatting & sending
│   ├── reminder_service.py         # Reminder scheduling & processing
│   ├── recurring_service.py        # Recurring task pattern generation
│   ├── calendar_service.py         # Google Calendar API integration
│   ├── statistics_service.py       # Task metrics calculations
│   ├── report_service.py           # Report generation (CSV/XLSX/PDF)
│   ├── time_parser.py              # Vietnamese time parsing (natural language)
│   ├── user_service.py             # User CRUD & preferences
│   └── oauth_callback.py           # Google OAuth callback server
│
├── scheduler/                      # Background job management
│   ├── __init__.py                 # Scheduler initialization
│   ├── reminder_scheduler.py       # APScheduler job runner for reminders
│   └── report_scheduler.py         # Auto-generate weekly/monthly reports
│
├── monitoring/                     # Optional health & performance monitoring
│   ├── __init__.py
│   ├── health_check.py             # HTTP health check server
│   ├── resource_monitor.py         # CPU/memory/database monitoring
│   ├── metrics.py                  # Prometheus metrics collection
│   └── alert.py                    # Admin alert notifications
│
├── utils/                          # Utility functions & helpers
│   ├── __init__.py
│   ├── formatters.py               # Task/deadline formatting for display
│   ├── keyboards.py                # Inline keyboard builders
│   ├── messages.py                 # Vietnamese message templates
│   ├── validators.py               # Input validation
│   └── db_utils.py                 # Database helper functions
│
├── static/                         # Static assets
│   └── user-guide.html             # Web-based user guide
│
├── exports/                        # Generated reports directory (runtime)
│
├── .env                            # Environment variables (secrets)
├── .env.example                    # Template for .env
├── .repomixignore                  # Repomix ignore patterns
└── venv/                           # Python virtual environment
```

## Key Modules & Responsibilities

### Core Entry Point: `bot.py`
- Async initialization with error handling
- Telegram bot setup & handler registration
- Database connection lifecycle
- Scheduler initialization (reminders, reports)
- Monitoring/health check server startup
- OAuth callback server (Google Calendar)
- Graceful shutdown with cleanup

```python
async def main():
    # Load config → Connect DB → Register handlers → Start polling
```

### Configuration: `config/settings.py`
Loads environment variables into a `Settings` dataclass:
- `BOT_TOKEN`: Telegram bot token
- `DATABASE_URL`: PostgreSQL connection string
- `ADMIN_IDS`: Comma-separated admin IDs
- `TIMEZONE`: Default timezone (Asia/Ho_Chi_Minh)
- Feature flags: `GOOGLE_CALENDAR_ENABLED`, `METRICS_ENABLED`, `REDIS_ENABLED`

### Database Layer: `database/`

**Models** (10 entities):
1. **User**: Telegram users (id, username, timezone, google_tokens)
2. **Group**: Telegram groups (id, title)
3. **GroupMember**: Group membership (user_id, group_id, role)
4. **Task**: Core entity (public_id, content, status, priority, progress, deadline)
5. **Reminder**: Notifications (task_id, remind_at, reminder_type)
6. **TaskHistory**: Audit trail (task_id, action, user_id, changed_fields)
7. **RecurringTemplate**: Recurring patterns (task_id, pattern, config)
8. **UserStatistics**: Metrics (user_id, weekly/monthly counts)
9. **DeletedTaskUndo**: Soft delete recovery (task_id, deleted_at, deleted_by)
10. **BotConfig**: Runtime config (key-value pairs)

**Connection** (`connection.py`):
- Async SQLAlchemy engine with asyncpg
- Connection pooling (min=2, max=10)
- Session factory for request-scoped access
- Database initialization & cleanup

**Migrations** (9 versions):
- Uses Alembic for version control
- Tracks schema evolution (initial → recurring → calendar → notifications)

### Handlers: `handlers/` (15 modules)

Each handler maps to one command or related set of operations:

| Module | Commands | Purpose |
|--------|----------|---------|
| `start.py` | `/start`, `/help` | Onboarding, menu |
| `task_create.py` | `/taoviec` | Quick task entry |
| `task_wizard.py` | Multi-step flow | Complex task creation (70KB) |
| `task_view.py` | `/xemviec` | Filter & display tasks |
| `task_update.py` | `/xong /danglam /tiendo` | Status updates & progress |
| `task_assign.py` | `/giaoviec /viecdagiao` | Assign tasks in groups |
| `task_delete.py` | `/xoa` | Soft delete with undo (25KB) |
| `callbacks.py` | Inline buttons | 50+ button handlers (48KB) |
| `reminder.py` | `/nhacviec` | Set task reminders |
| `recurring_task.py` | `/vieclaplai` | Create recurring patterns |
| `statistics.py` | `/thongke /thongketuan /thongkethang` | Metrics dashboard |
| `export.py` | `/export` | CSV/XLSX/PDF reports |
| `calendar.py` | `/lichgoogle` | Google Calendar OAuth |
| `settings.py` | `/caidat` | User preferences |
| `__init__.py` | N/A | Register all handlers to app |

**Handler Pattern**:
```python
# ConversationHandler (multi-step)
ConversationHandler(
    entry_points=[CommandHandler("taoviec", task_create)],
    states={...},  # STATE_TITLE, STATE_DESCRIPTION, etc.
    fallbacks=[...]
)

# CommandHandler (single step)
CommandHandler("xemviec", view_tasks)

# CallbackQueryHandler (button clicks)
CallbackQueryHandler(update_task_status, pattern="^update_task_")
```

### Services: `services/` (11 modules)

Business logic layer, called by handlers:

| Module | Responsibility |
|--------|-----------------|
| `task_service.py` | CRUD for tasks (P-ID/G-ID generation, soft delete) |
| `notification.py` | Format & send Telegram messages |
| `reminder_service.py` | Create/update/retrieve reminders |
| `recurring_service.py` | Generate recurring task instances |
| `calendar_service.py` | Google Calendar API (create/sync events) |
| `statistics_service.py` | Calculate task metrics (completed, overdue, etc.) |
| `report_service.py` | Generate CSV/XLSX/PDF files |
| `time_parser.py` | Parse Vietnamese time expressions |
| `user_service.py` | CRUD for users & preferences |
| `oauth_callback.py` | HTTP server for Google OAuth callback |

**Example Pattern**:
```python
# Handler calls service
async def view_tasks(update, context):
    tasks = await TaskService.get_user_tasks(user_id)
    message = NotificationService.format_task_list(tasks)
    await update.message.reply_text(message)
```

### Scheduler: `scheduler/` (2 modules)

Background jobs using APScheduler:

**RemindersScheduler**:
- Runs every 30 seconds
- Queries pending reminders
- Sends notifications
- Marks as sent

**ReportScheduler**:
- Runs weekly (Sunday) & monthly (1st of month)
- Generates statistics
- Exports reports
- Sends to users

### Monitoring: `monitoring/` (4 modules, optional)

Enabled only if `ADMIN_IDS` configured:

| Module | Purpose |
|--------|---------|
| `health_check.py` | HTTP server (port 8080) for liveness checks |
| `resource_monitor.py` | Track CPU/memory/DB connections |
| `metrics.py` | Prometheus metrics (opt-in via flag) |
| `alert.py` | Send admin alerts for crashes |

### Utils: `utils/` (5 modules)

Helper functions:

| Module | Functions |
|--------|-----------|
| `formatters.py` | Format task display, deadlines, progress bars |
| `keyboards.py` | Build inline/reply keyboards |
| `messages.py` | Vietnamese message templates |
| `validators.py` | Validate task fields, dates, etc. |
| `db_utils.py` | Database query helpers |

## Database Schema Highlights

### Task Public ID System
```python
# Personal task: P-0001, P-0042, P-9999
personal_id = f"P-{task.id:04d}"

# Group task: G-0001, G-0500
group_id = f"G-{group_task_id:04d}"
```

### Indexes for Performance
```python
# Most important queries are indexed:
Index("idx_tasks_assignee_status", "assignee_id", "status")
Index("idx_tasks_deadline", "deadline")  # For overdue detection
Index("idx_reminders_pending", "remind_at")  # For scheduler
```

### Soft Delete Pattern
```sql
-- Task marked deleted, not actually removed
UPDATE tasks SET is_deleted = TRUE, deleted_at = NOW()
WHERE id = ?;

-- Can undo within 30 seconds
DELETE FROM deleted_task_undo WHERE deleted_at < NOW() - INTERVAL '30s';
```

## Key Files by Size

| File | Lines | Purpose |
|------|-------|---------|
| `handlers/task_wizard.py` | 70KB | Multi-step task creation |
| `handlers/callbacks.py` | 48KB | 50+ inline button handlers |
| `services/task_service.py` | 51KB | Core task CRUD |
| `services/report_service.py` | 31KB | Report generation |
| `handlers/task_delete.py` | 25KB | Soft delete with recovery |

## Async/Await Architecture

All I/O operations are async:
```python
# Database queries
async with db.session() as session:
    result = await session.execute(select(...))

# Telegram API
await update.message.reply_text(...)

# HTTP requests (Google Calendar)
async with aiohttp.ClientSession() as session:
    async with session.get(...) as resp:
        ...
```

## Error Handling Strategy

- Global error handler in `bot.py` catches all exceptions
- Per-handler try-catch for Telegram API errors
- Database rollback on transaction failure
- Alerts sent to admins if monitoring enabled
- Logging at appropriate levels (DEBUG → ERROR)

## Dependencies

### Core
- `python-telegram-bot>=21.0`: Telegram API
- `asyncpg>=0.29.0`: PostgreSQL async driver
- `sqlalchemy>=2.0.0`: ORM
- `alembic>=1.13.0`: Database migrations

### Scheduling & Timing
- `APScheduler>=3.10.0`: Background jobs
- `python-dateutil>=2.8.0`: Date utilities
- `pytz>=2024.1`: Timezone support

### Integration
- `google-auth-oauthlib>=1.1.0`: Google OAuth
- `google-api-python-client>=2.100.0`: Google Calendar API
- `aiohttp>=3.9.0`: Async HTTP client

### Reporting
- `openpyxl>=3.1.0`: XLSX generation
- `reportlab>=4.0.0`: PDF generation
- `matplotlib>=3.8.0`: Chart generation

### Optional
- `redis>=5.0.0`: Caching (disabled by default)
- `prometheus-client>=0.19.0`: Metrics (disabled by default)

## Testing & Development

**Test Structure** (not included in production):
- Unit tests for services (task_service, time_parser, etc.)
- Integration tests for handlers
- Database fixture setup

**Linting & Formatting**:
- Black for code formatting
- Flake8 for linting
- Type hints with mypy

## Deployment

**PM2 Configuration** (`ecosystem.config.js`):
```javascript
module.exports = {
  apps: [{
    name: 'teletask-bot',
    script: './bot.py',
    interpreter: 'python3',
    instances: 1,
    watch: false,
    env: { NODE_ENV: 'production' }
  }]
};
```

**Environment Setup**:
1. `python3.11 -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env && edit .env`
4. `pm2 start ecosystem.config.js`

## Performance Characteristics

- **Single-threaded event loop** (async/await)
- **~10 concurrent users** with default pool (2-10 connections)
- **Response time** typically 100-500ms (database dependent)
- **Memory footprint**: ~100-150MB steady state
- **CPU**: <5% idle, <20% during report generation

## Security Considerations

- No credentials in logs (filtered at debug level)
- OAuth 2.0 for Google Calendar (no password storage)
- Telegram API tokens validated at startup
- User data isolation (queries scoped to user_id/group_id)
- SQL injection prevention (SQLAlchemy parameterized queries)

---

**Last Updated**: 2024-12-18
**Generated By**: Repomix + Manual Analysis
**Status**: CURRENT
