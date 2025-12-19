# TeleTask Bot - System Architecture

## 1. High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Telegram Client                         │
│                    (Users & Group Chats)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ▼        │        ▼
            ┌────────────────────────────────┐
            │  Telegram Bot API (HTTPS)      │
            │  Long Polling / Webhooks       │
            └───────────────┬────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │    TeleTask Bot (Python 3.11)       │
        │         Entry: bot.py               │
        │                                    │
        │  ┌──────────────────────────────┐  │
        │  │  Request Handler Layer       │  │
        │  │  - 15 handler modules        │  │
        │  │  - ConversationHandler       │  │
        │  │  - CommandHandler            │  │
        │  │  - CallbackQueryHandler      │  │
        │  └──────────────┬───────────────┘  │
        │                 │                  │
        │  ┌──────────────▼───────────────┐  │
        │  │  Service Layer               │  │
        │  │  - 11 service modules        │  │
        │  │  - TaskService               │  │
        │  │  - NotificationService       │  │
        │  │  - ReminderService           │  │
        │  │  - ReportService             │  │
        │  │  - CalendarService           │  │
        │  │  - StatisticsService         │  │
        │  └──────────────┬───────────────┘  │
        │                 │                  │
        │  ┌──────────────▼───────────────┐  │
        │  │  Data Access Layer           │  │
        │  │  - SQLAlchemy ORM            │  │
        │  │  - 10 Models                 │  │
        │  │  - Async Session Manager     │  │
        │  └──────────────┬───────────────┘  │
        │                 │                  │
        │  ┌──────────────▼───────────────┐  │
        │  │  Background Schedulers       │  │
        │  │  - APScheduler               │  │
        │  │  - Reminder Scheduler        │  │
        │  │  - Report Scheduler          │  │
        │  │  - 30s polling interval      │  │
        │  └──────────────┬───────────────┘  │
        │                 │                  │
        │  ┌──────────────▼───────────────┐  │
        │  │  Monitoring (Optional)       │  │
        │  │  - Health Check Server       │  │
        │  │  - Resource Monitor          │  │
        │  │  - Metrics Collection        │  │
        │  │  - Error Alerts              │  │
        │  └──────────────┬───────────────┘  │
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
    ▼   ▼                 ▼                  ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│  PostgreSQL  │  │  Google         │  │  Prometheus  │
│  Database    │  │  Calendar API   │  │  (optional)  │
│  async       │  │                 │  │              │
│  (asyncpg)   │  │  OAuth 2.0      │  │  Metrics     │
└──────────────┘  │  Callback       │  └──────────────┘
                  │  Server         │
                  └─────────────────┘
```

## 2. Component Architecture

### 2.1 Handler Layer (15 modules, ~250KB)

**Purpose**: Translate Telegram updates into business logic calls

```
Telegram Update
    ↓
Handler (start.py, task_wizard.py, etc.)
    ↓
Permission Check (if needed)
    ↓
Input Validation
    ↓
Call Service Layer
    ↓
Format Response
    ↓
Send to Telegram
```

**Key Handlers**:
- **start.py**: Onboarding, menu, help
- **task_wizard.py**: Multi-step task creation (70KB - largest handler)
- **task_view.py**: Filter & display tasks by status
- **task_update.py**: Status changes (pending → in_progress → completed)
- **callbacks.py**: 50+ inline button handlers (48KB)
- **reminder.py**: Schedule task reminders
- **recurring_task.py**: Create recurring patterns
- **statistics.py**: Task metrics & dashboards
- **export.py**: Report generation (CSV/XLSX/PDF)
- **calendar.py**: Google Calendar OAuth flow
- **settings.py**: User preferences (timezone, notifications)

**Handler Lifecycle**:
```python
# ConversationHandler: Multi-step flow
/taoviec → [ENTER] → task_wizard.py:start
        → [TITLE] → task_wizard.py:handle_title → STATE_DESCRIPTION
        → [DESC] → task_wizard.py:handle_desc → STATE_DEADLINE
        → [DATE] → task_wizard.py:handle_deadline → STATE_CONFIRM
        → [CONFIRM] → task_wizard.py:confirm → [EXIT]

# CommandHandler: Single step
/xemviec → view_tasks.py:view_tasks → TaskService.get_user_tasks() → reply

# CallbackQueryHandler: Button click
[Update Status] button → callbacks.py:button_update_task → [popup response]
```

### 2.2 Service Layer (11 modules, ~180KB)

**Purpose**: Business logic, database operations, integrations

```
Handler
  ↓
TaskService (CRUD)
  ├─ create_task()
  ├─ get_task() / get_user_tasks()
  ├─ update_task()
  └─ soft_delete_task()
  ↓
[NotificationService, ReminderService, etc.]
  ↓
Database Layer
```

**Core Services**:

| Service | Responsibility | Key Methods |
|---------|-----------------|------------|
| `task_service.py` (51KB) | Task CRUD with P-ID/G-ID | create_task, get_user_tasks, update_task, soft_delete_task, list_overdue |
| `notification.py` | Message formatting & sending | format_task_summary, send_notification, send_bulk |
| `reminder_service.py` | Reminder CRUD & scheduling | create_reminder, get_pending_reminders, mark_sent |
| `recurring_service.py` (18KB) | Generate recurring task instances | generate_next_occurrence, apply_pattern |
| `calendar_service.py` (17KB) | Google Calendar API integration | sync_task_to_calendar, get_calendar_events |
| `statistics_service.py` | Calculate task metrics | get_user_stats, get_weekly_stats, get_monthly_stats |
| `report_service.py` (31KB) | Generate reports | generate_csv, generate_xlsx, generate_pdf |
| `time_parser.py` | Parse Vietnamese time expressions | parse_datetime (e.g., "ngày mai", "25/12") |
| `user_service.py` | User CRUD & preferences | get_or_create_user, update_preferences |
| `oauth_callback.py` | Google OAuth callback server | Start/stop OAuth server, handle callback |

**Service Pattern**:
```python
# Stateless service (static methods)
class TaskService:
    @staticmethod
    async def create_task(...) -> Task:
        db = get_db()
        async with db.session() as session:
            # Database operation
            return task

    @staticmethod
    async def get_user_tasks(...) -> List[Task]:
        # Query with filters
        return tasks
```

### 2.3 Database Layer (Models + Connection Management)

**10 Core Models**:

```
┌─────────────────┐         ┌──────────────────┐
│     User        │         │     Group        │
├─────────────────┤         ├──────────────────┤
│ id              │         │ id               │
│ telegram_id     │         │ telegram_id      │
│ username        │         │ title            │
│ first_name      │         │ is_active        │
│ timezone        │────┬────┤ created_at       │
│ google_tokens   │    │    │ updated_at       │
│ notify_prefs    │    │    └──────────────────┘
│ created_at      │    │
└────────┬────────┘    │    ┌──────────────────┐
         │             ├───→│  GroupMember     │
         │             │    ├──────────────────┤
         │             │    │ group_id (FK)    │
         │             │    │ user_id (FK)     │
         │             │    │ role (admin|mem) │
         │             │    │ joined_at        │
         │             │    └──────────────────┘
         │             │
         │             │    ┌──────────────────┐
         │             ├───→│      Task        │
         │                  ├──────────────────┤
         │                  │ id               │
         │                  │ public_id (P/G)  │
         │                  │ content          │
         │                  │ status           │
         │                  │ priority         │
         │                  │ progress (%)     │
         │                  │ creator_id (FK)  │
         │                  │ assignee_id (FK) │
         │                  │ group_id (FK)    │
         │                  │ deadline         │
         │                  │ completed_at     │
         │                  │ is_deleted       │
         │                  │ google_event_id  │
         │                  └────────┬─────────┘
         │                           │
         ├──────────────────────────┤
         │                          │
    ▼    ▼                      ▼   ▼
┌──────────────────┐  ┌──────────────────┐
│   Reminder       │  │   TaskHistory    │
├──────────────────┤  ├──────────────────┤
│ id               │  │ id               │
│ task_id (FK)     │  │ task_id (FK)     │
│ user_id (FK)     │  │ user_id (FK)     │
│ remind_at        │  │ action           │
│ reminder_type    │  │ changed_fields   │
│ is_sent          │  │ created_at       │
│ sent_at          │  └──────────────────┘
│ error_message    │
└──────────────────┘

Plus:
- RecurringTemplate: Recurring task patterns
- UserStatistics: Weekly/monthly metrics
- DeletedTaskUndo: Soft delete recovery (30s window)
- BotConfig: Runtime configuration
```

**Database Connection Management**:
```python
# Singleton pattern for database access
class Database:
    def __init__(self, url: str):
        self._engine = create_async_engine(url, poolclass=AsyncPool)
        self._pool_config = AsyncSessionLocal(...)

    async def session(self) -> AsyncSessionLocal:
        """Get session with automatic cleanup."""
        yield session

# Global accessor
_db_instance = None

def get_db() -> Database:
    """Get singleton database instance."""
    global _db_instance
    return _db_instance
```

**Async Query Pattern**:
```python
async with db.session() as session:
    result = await session.execute(select(Task).where(...))
    tasks = result.scalars().all()
    # Session auto-closed
```

### 2.4 Scheduler Layer (APScheduler)

**Reminder Scheduler** (30-second interval):
```
Every 30 seconds
    ↓
Query reminders WHERE remind_at <= NOW() AND is_sent = false
    ↓
For each pending reminder:
    ├─ NotificationService.send_reminder()
    ├─ Mark as sent
    └─ Log to TaskHistory
    ↓
Update metrics
```

**Report Scheduler** (Weekly & Monthly):
```
Every Sunday at 00:00 (Weekly)
    ↓
StatisticsService.calculate_stats(user_id, 'weekly')
    ↓
ReportService.generate_xlsx(stats)
    ↓
Send file to user via Telegram
    ↓

Every 1st of month at 00:00 (Monthly)
    ↓
Same process with monthly stats
```

**Job Failures**:
- Retries: Up to 3 attempts with exponential backoff
- Error logging to database
- Admin alerts (if monitoring enabled)

### 2.5 Monitoring Layer (Optional, if ADMIN_IDS configured)

**Health Check Server** (port 8080):
```
GET /health
    ↓
Check:
├─ Database connectivity (timeout 5s)
├─ Scheduler running (last job < 5 min ago)
└─ Uptime
    ↓
Return: { status: "healthy", uptime_seconds: 3600 }
```

**Resource Monitor** (every 60 seconds):
```
Measure:
├─ CPU usage (target < 30%)
├─ Memory usage (target < 200MB)
├─ Database connections (target < 8 of max 10)
└─ Error rate (target < 0.1%)
    ↓
If threshold exceeded:
    └─ Alert admin via Telegram
```

**Error Alert** (on exception):
```
Unhandled exception in handler
    ↓
Log to logger
    ↓
AlertService.alert_bot_crash(error)
    ↓
Send to all admin_ids with:
├─ Error type & message
├─ Stack trace
└─ Timestamp
```

## 3. Data Flow Examples

### 3.1 Creating a Task (Personal)

```
User: /taoviec
    ↓
handlers/task_wizard.py:task_wizard_start()
    ├─ Check user exists (get_or_create_user)
    └─ Ask for title → STATE_TITLE
    ↓
User: "Buy groceries"
    ↓
task_wizard_title()
    ├─ Store in context.user_data["title"]
    └─ Ask for description → STATE_DESCRIPTION
    ↓
[User continues through wizard...]
    ↓
task_wizard_confirm()
    ├─ Validate all fields
    ├─ Call TaskService.create_task()
    │   ├─ Insert into Task table
    │   ├─ Generate P-ID (P-0042)
    │   └─ Return created Task
    ├─ Call NotificationService.format_task_summary(task)
    └─ Send confirmation message with task details
    ↓
User sees:
✅ Việc tạo thành công
📋 P-0042: Buy groceries
Hạn: [deadline]
```

### 3.2 Setting a Reminder

```
User: /nhacviec P-0042
    ↓
reminder.py:set_reminder_wizard()
    ├─ Parse public ID P-0042
    ├─ Load task via TaskService.get_task_by_public_id()
    └─ Check permission (creator/assignee)
    ↓
[Multi-step wizard for reminder time]
    ↓
reminder.py:confirm_reminder()
    ├─ Parse time expression (e.g., "1 ngày trước hạn")
    ├─ Calculate remind_at = deadline - 1 day
    ├─ Call ReminderService.create_reminder()
    │   ├─ Insert into Reminder table
    │   ├─ Set reminder_type = "before_deadline"
    │   └─ Return created Reminder
    └─ Send confirmation
    ↓
Scheduler runs every 30s:
    ├─ Query: SELECT * FROM reminders WHERE remind_at <= NOW() AND is_sent = false
    ├─ For reminder found:
    │   ├─ Load task details
    │   ├─ NotificationService.send_reminder(task, user_id)
    │   │   └─ Send formatted message to user
    │   ├─ Update: reminder.is_sent = true, reminder.sent_at = NOW()
    │   └─ Log to TaskHistory
    └─ Metrics update
```

### 3.3 Soft Delete with Undo

```
User: /xoa P-0042
    ↓
task_delete.py:delete_task()
    ├─ Get task
    ├─ Check permission (creator)
    └─ Show 2 options: [Delete] [Cancel]
    ↓
User: [Delete]
    ↓
task_delete.py:confirm_delete()
    ├─ TaskService.soft_delete_task(task_id, user_id)
    │   ├─ UPDATE tasks SET is_deleted=true, deleted_at=NOW()
    │   ├─ INSERT into deleted_task_undo(task_id, deleted_by, deleted_at)
    │   └─ Return deleted Task
    ├─ Show message with [Restore] button (30s timer)
    └─ Send confirmation
    ↓
[Within 30 seconds]
User: [Restore]
    ├─ task_delete.py:undo_delete()
    ├─ TaskService.restore_task(task_id)
    │   └─ UPDATE tasks SET is_deleted=false WHERE id=?
    └─ Confirm restored
    ↓
[After 30 seconds]
    ├─ Scheduler runs cleanup
    ├─ DELETE FROM deleted_task_undo WHERE deleted_at < NOW() - INTERVAL '30s'
    └─ [Restore] button disabled
```

### 3.4 Weekly Statistics Report

```
Every Sunday at 00:00 (APScheduler)
    ↓
report_scheduler.py:generate_weekly_reports()
    ├─ Query: SELECT * FROM users WHERE notify_weekly_report = true
    ↓
For each user:
    ├─ StatisticsService.calculate_stats(user_id, period='weekly')
    │   ├─ Query: SELECT COUNT(*) WHERE status='completed' AND week_of_year=current_week
    │   ├─ Query for overdue, in_progress, pending counts
    │   └─ Return stats object
    ├─ ReportService.generate_xlsx(stats)
    │   ├─ Create workbook with matplotlib charts
    │   ├─ Save to exports/weekly_[user_id]_[date].xlsx
    │   └─ Return file path
    ├─ NotificationService.send_file()
    │   └─ Upload XLSX to Telegram
    └─ Log to metrics
    ↓
User receives:
📊 Báo cáo tuần này
[XLSX file attachment with charts]
```

## 4. Database Schema Overview

### Indexes (Performance Optimization)

```sql
-- Most critical for task queries
CREATE INDEX idx_tasks_assignee_status ON tasks(assignee_id, status)
    WHERE is_deleted = false;

-- For deadline detection
CREATE INDEX idx_tasks_deadline ON tasks(deadline)
    WHERE is_deleted = false AND status != 'completed';

-- For scheduler (reminders)
CREATE INDEX idx_reminders_pending ON reminders(remind_at)
    WHERE is_sent = false;

-- For group tasks
CREATE INDEX idx_tasks_group ON tasks(group_id)
    WHERE is_deleted = false;

-- For history audit trail
CREATE INDEX idx_task_history_task ON task_history(task_id);
```

### Constraints & Data Integrity

```sql
-- Task status enum
CHECK (status IN ('pending', 'in_progress', 'completed'))

-- Priority levels
CHECK (priority IN ('low', 'normal', 'high', 'urgent'))

-- Progress range
CHECK (progress >= 0 AND progress <= 100)

-- Reminder type
CHECK (reminder_type IN ('before_deadline', 'after_deadline', 'custom'))

-- Group membership uniqueness
UNIQUE (group_id, user_id)

-- Foreign key cascades
ON DELETE CASCADE for all task-related entities
```

## 5. External Integrations

### 5.1 Telegram Bot API

**Protocol**: HTTPS
**Method**: Long polling (not webhooks for reliability)
**Rate Limits**: 30 messages/second per user
**Error Handling**: Exponential backoff retry (3 attempts)

```python
# Connection
Application.builder().token(bot_token).build()

# Update handlers
application.add_handler(CommandHandler("start", start_handler))

# Message sending
await bot.send_message(chat_id, text, parse_mode="HTML")
```

### 5.2 Google Calendar API (Optional)

**Protocol**: HTTPS
**OAuth 2.0 Flow**:
```
User: /lichgoogle
    ↓
calendar.py:initiate_oauth()
    ├─ Generate auth URL with scope: calendar.events
    └─ Send link to user
    ↓
User clicks link → Google OAuth approval
    ↓
oauth_callback.py:oauth_callback()
    ├─ Receive auth code
    ├─ Exchange for tokens (access + refresh)
    ├─ Store in User.google_calendar_token
    └─ Confirm to user
    ↓
Subsequent task completion:
    ├─ Notification check: user has tokens?
    ├─ CalendarService.sync_task_to_calendar(task)
    │   ├─ Create Google Calendar event
    │   ├─ Store google_event_id
    │   └─ Return event details
    └─ Confirm to user in Telegram
```

### 5.3 PostgreSQL Async Driver (asyncpg)

**Connection Pool**:
- Min: 2 connections
- Max: 10 connections
- Timeout: 30s

**Session Management**:
```python
# Scoped to request
async with db.session() as session:
    result = await session.execute(...)
    # Auto-rollback on exception
```

## 6. Deployment Architecture

### Single Bot Instance
```
┌─────────────────────────────────┐
│  PM2 Process Manager            │
├─────────────────────────────────┤
│  Single Process (bot.py)        │
├─────────────────────────────────┤
│  Event Loop (async/await)       │
│  - Telegram polling             │
│  - APScheduler jobs             │
│  - Handlers                      │
│  - Services                      │
└─────────────────────────────────┘
        ↓        ↓        ↓
    PostgreSQL  Google   Optional
    (async)     APIs     Services
```

**No Horizontal Scaling** (single bot instance per token)

### Environment Configuration

```env
# Required
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/teletask

# Optional
ADMIN_IDS=123456789,987654321
TIMEZONE=Asia/Ho_Chi_Minh
GOOGLE_CALENDAR_ENABLED=false
METRICS_ENABLED=false
LOG_LEVEL=INFO
```

## 7. Reliability & Failure Scenarios

### Database Failure
```
Connection lost
    ↓
Handler receives ConnectionError
    ↓
Retry with exponential backoff (3 attempts, 1s/2s/4s)
    ↓
If still failing: Send error message to user
    ↓
Log error for monitoring
    ↓
Admin alert (if monitoring enabled)
```

### Telegram API Failure
```
Send message fails
    ↓
Catch exception (timeout, rate limit, etc.)
    ↓
Exponential backoff (max 3 retries)
    ↓
If persistent: Skip notification, log error
    ↓
Continue processing other tasks
```

### Scheduler Job Failure
```
Reminder query fails
    ↓
Skip that batch, log error
    ↓
Retry in next 30s iteration
    ↓
If recurring failure: Alert admin
    ↓
Reminders will retry on next schedule
```

## 8. Performance Characteristics

### Response Times (Measured)
- Command response: 100-500ms (depends on DB query)
- Task creation: 200-800ms (with validation)
- Report generation: 2-5s (XLSX with charts)
- Reminder processing: 50-100ms per reminder

### Resource Usage
- **Memory**: 100-150MB steady state
- **CPU**: <5% idle, <20% during reports
- **Database connections**: 2-6 of 10 max (typical)

### Scaling Limits
- Single process: ~100 concurrent users
- ~1000 tasks manageable
- ~50 reminders per minute without issues

---

**Last Updated**: 2024-12-18
**Architecture Version**: 1.0
**Status**: ACTIVE
