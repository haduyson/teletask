# TeleTask System Architecture

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Architecture Style:** Modular Layered Architecture
**Scale:** Single-bot to multi-bot deployment

---

## 1. Architecture Overview

TeleTask uses a **modular layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Users                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌────────────────────┐
│ Telegram Bot API │      │ Google Calendar    │
│ (Long Polling)   │      │   OAuth 2.0 Flow   │
└────────┬─────────┘      └────────┬───────────┘
         │                         │
         └────────────┬────────────┘
                      │
        ┌─────────────▼────────────────┐
        │   TeleTask Bot Core          │
        │ (Python AsyncIO Framework)   │
        │                              │
        │  ┌────────────────────────┐  │
        │  │ Handlers Layer (14)    │  │ ← Commands & Callbacks
        │  ├────────────────────────┤  │
        │  │ Services Layer (10)    │  │ ← Business Logic
        │  ├────────────────────────┤  │
        │  │ Scheduler & Jobs       │  │ ← Background Tasks
        │  ├────────────────────────┤  │
        │  │ Monitoring & Logging   │  │
        │  ├────────────────────────┤  │
        │  │ Utils & Helpers        │  │
        │  └────────────────────────┘  │
        │         │                    │
        │         │ asyncpg            │
        │         │ (async driver)     │
        └─────────┼────────────────────┘
                  │
        ┌─────────▼────────────┐
        │   PostgreSQL 15+     │
        │  (9 tables, 8 idx)   │
        └──────────────────────┘

        ┌──────────────────────┐
        │   PM2 Process Mgr    │ ← Service Management
        └──────────────────────┘

        ┌──────────────────────┐
        │   Nginx Reverse      │ ← OAuth Callback Proxy
        │   Proxy (127.0.0.1)  │
        └──────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Handler Layer

**Responsibility:** Process Telegram commands and callbacks

**14 Handler Modules:**
```
Handlers
├── Command Handlers
│   ├── start.py              - /start, /help, /info commands
│   ├── task_create.py        - /taoviec quick creation
│   ├── task_wizard.py        - /taoviec interactive wizard
│   ├── task_view.py          - /xemviec command
│   ├── task_assign.py        - /giaoviec command
│   ├── task_update.py        - /xong, /tiendo commands
│   ├── task_delete.py        - /xoa, /xoanhieu, /xoatatca
│   ├── reminder.py           - /nhacviec, /xemnhac
│   ├── recurring_task.py     - /vieclaplai command
│   ├── statistics.py         - /thongke commands
│   ├── export.py             - /export command
│   ├── calendar.py           - /lichgoogle command
│   ├── settings.py           - /caidat command
│   └── callbacks.py          - Inline button callbacks
└── Initialization
    └── __init__.py           - Handler registration
```

**Handler Flow:**
```
User sends /command
         │
         ▼
Telegram API (bot.on_message, bot.on_command)
         │
         ▼
Handler (async function)
    │- Extract user data
    │- Validate input
    │- Call service layer
    │
    └─▶ Service Layer
         │
         └─▶ Database
```

### 2.2 Service Layer

**Responsibility:** Business logic, data validation, orchestration

**10 Service Modules:**

```
Services
├── Core Services
│   ├── task_service.py       - Task CRUD & operations
│   ├── user_service.py       - User profile & settings
│   └── notification.py       - Send notifications
├── Feature Services
│   ├── reminder_service.py   - Reminder scheduling
│   ├── recurring_service.py  - Recurring task logic
│   ├── statistics_service.py - Calculate stats
│   ├── report_service.py     - Generate reports
│   ├── calendar_service.py   - Google Calendar API
│   └── oauth_callback.py     - OAuth token handling
└── Utility Services
    └── time_parser.py        - Vietnamese time parsing
```

**Service Pattern:**
```python
class TaskService:
    def __init__(self, db_session):
        self.db = db_session

    # Operations
    async def create_task(...)     # Business logic
    async def update_task(...)     # Validation + DB
    async def delete_task(...)     # Soft delete + log

    # Internal helpers
    async def _validate_input(...)
    async def _calculate_deadline(...)
```

### 2.3 Database Layer

**Responsibility:** Data persistence, schema management, query execution

**Components:**
```
Database Layer
├── Models (models.py)
│   ├── User            - User profile + OAuth tokens
│   ├── Group           - Group metadata
│   ├── GroupMember     - User-Group relationships
│   ├── Task            - Core task data
│   ├── Reminder        - Reminder configuration
│   ├── RecurringTask   - Recurring task template
│   ├── TaskHistory     - Audit trail
│   ├── UserStatistics  - Aggregated stats
│   ├── DeletedTaskUndo - Soft-deleted tasks
│   └── BotConfig       - Global settings
│
├── Connection (connection.py)
│   ├── Connection pooling
│   ├── Session management
│   └── Error recovery
│
└── Migrations (alembic)
    ├── 20241214 - Initial schema
    ├── 20241215 - Recurring support
    ├── 20251215 - Group tasks
    ├── 20251216 - Reports, reminders
    └── 20251217 - Notification settings
```

### 2.4 Scheduler Layer

**Responsibility:** Background job execution, periodic tasks

**Jobs:**
```
APScheduler
├── Reminder notifications
│   ├── Check due reminders every 1 minute
│   ├── Send notifications
│   └── Update reminder status
│
├── Recurring task generation
│   ├── Generate daily/weekly/monthly tasks
│   └── Create associated reminders
│
├── Statistics aggregation
│   ├── Weekly stats (every Sunday)
│   ├── Monthly stats (every 1st)
│   └── All-time updates
│
├── Google Calendar sync
│   ├── Periodic sync (if configured)
│   └── Event to task sync
│
├── Health checks
│   ├── Database connectivity
│   ├── Telegram API health
│   └── Memory usage monitoring
│
└── Cleanup jobs
    ├── Delete expired undo logs
    ├── Archive old reports
    └── Cleanup temp files
```

### 2.5 Monitoring Layer

**Responsibility:** Health monitoring, metrics, alerting

**Components:**
```
Monitoring
├── Health Check (health_check.py)
│   ├── Database connectivity
│   ├── API response times
│   └── Uptime verification
│
├── Resource Monitor (resource_monitor.py)
│   ├── CPU usage
│   ├── Memory usage
│   ├── Connection pool status
│   └── Queue depth
│
├── Metrics (metrics.py)
│   ├── Command execution time
│   ├── Database query time
│   ├── API response time
│   └── Error rates
│
└── Alerting (alert.py)
    ├── Critical error alerts
    ├── Performance degradation
    └── Resource exhaustion
```

### 2.6 Utils Layer

**Responsibility:** Shared utilities and helpers

```
Utils
├── formatters.py
│   ├── Format dates (user timezone)
│   ├── Format numbers
│   ├── Format task status
│   └── Format currency
│
├── keyboards.py
│   ├── Inline button builders
│   ├── Reply keyboard builders
│   ├── Pagination helpers
│   └── Menu generators
│
├── messages.py
│   ├── Message templates
│   ├── Error messages
│   └── Help text
│
└── validators.py
    ├── Task content validation
    ├── Date/time validation
    ├── Email validation
    └── SQL injection prevention
```

---

## 3. Data Flow Diagrams

### 3.1 Task Creation Flow

```
User: /taoviec
      │
      ▼
task_wizard.py (handler)
    │- Request content from user
    │- Store in context.user_data
    │
    ▼ (User provides content)
task_wizard.py (wizard step 1)
    │- Request deadline
    │
    ▼ (User selects deadline)
task_wizard.py (wizard step 2)
    │- Request recipient (self/other)
    │
    ▼ (User selects)
task_wizard.py (wizard step 3)
    │- Request priority
    │
    ▼ (User selects)
task_wizard.py (wizard step 4)
    │- Show confirmation
    │
    ▼ (User confirms)
task_service.create_task()
    │- Validate input
    │- Generate task ID (P-xxx or G-xxx)
    │- Insert into database
    │
    ▼
Database: Task inserted
    │
    ▼
reminder_service.schedule_reminders()
    │- Create default reminders (4 pre + 2 post)
    │
    ▼
notification.send_notification()
    │- Send confirmation to user
    │- Send assignment notification (if group)
    │
    ▼
Task created successfully
```

### 3.2 Reminder Notification Flow

```
APScheduler (every 1 minute)
    │
    ▼
reminder_service.send_due_reminders()
    │
    ▼
Query: tasks with due reminders
    │
    ▼
For each due reminder:
    │
    ├─▶ Check notification preferences
    │   └─▶ Should notify? (Telegram &/or Google Calendar)
    │
    ├─▶ notification.send_reminder()
    │   └─▶ Format message
    │   └─▶ Send via Telegram
    │
    └─▶ Update reminder status
        └─▶ Mark as sent
        └─▶ Set next notification time

Notification delivered to user
```

### 3.3 Google Calendar Sync Flow

```
User: /lichgoogle
      │
      ▼
calendar.py (handler)
    │
    ├─▶ Check if already authenticated
    │   └─▶ If yes: show sync options
    │   └─▶ If no: start OAuth
    │
    ▼ (User clicks: Connect to Google)
    │
    ▼
oauth_callback.py
    │- Generate OAuth URL
    │- Send user to Google login
    │
    ▼ (User logs into Google)
    │
    ▼
oauth_callback.py (callback handler)
    │- Receive authorization code
    │- Exchange for tokens
    │- Store encrypted tokens in database
    │
    ▼
calendar_service.sync_all_tasks()
    │- Fetch all user tasks
    │- Create events on Google Calendar
    │
    ▼
Google Calendar events created
    │
    ▼
Schedule periodic sync (if enabled)
    │- Every 1 hour: sync new tasks
    │- Every 4 hours: full sync
```

### 3.4 Statistics Generation Flow

```
APScheduler (weekly: Sunday 23:00)
                    (monthly: 1st 23:00)
      │
      ▼
statistics_service.calculate_weekly_stats()
statistics_service.calculate_monthly_stats()
      │
      ▼
Query: tasks for time period
    │- count_total
    │- count_completed
    │- count_overdue
    │- avg_completion_time
    │- completion_rate
      │
      ▼
Insert into UserStatistics table
      │
      ▼
notification.send_weekly_report() (if enabled)
      │
      ▼
Report delivered to user
```

---

## 4. Database Schema

### 4.1 Core Tables

```sql
-- Users: Telegram users + Google OAuth
users
├── id (PK)
├── telegram_id (UNIQUE) ← Telegram user ID
├── username
├── first_name, last_name
├── timezone
├── language
├── notify_reminder
├── notify_weekly_report
├── notify_monthly_report
├── google_calendar_token ← Encrypted OAuth token
├── google_calendar_refresh_token
├── is_active
├── created_at, updated_at
└── Indexes: telegram_id, username

-- Groups: Telegram groups
groups
├── id (PK)
├── telegram_id (UNIQUE) ← Telegram group ID
├── title
├── is_active
├── created_at, updated_at
└── Indexes: telegram_id

-- GroupMembers: User-Group relationships
group_members
├── id (PK)
├── user_id (FK) ← users.id
├── group_id (FK) ← groups.id
├── role ← 'admin', 'member'
├── joined_at
└── Indexes: (user_id, group_id)

-- Tasks: Core task data
tasks
├── id (PK) ← "P-001", "G-001"
├── creator_id (FK) ← users.id
├── assignee_id (FK) ← users.id
├── group_id (FK) ← groups.id (if group task)
├── content
├── status ← 'pending', 'in_progress', 'completed'
├── priority ← 'low', 'normal', 'high'
├── deadline
├── progress_percent
├── is_recurring
├── recurring_pattern
├── is_deleted (soft delete)
├── created_at, updated_at
├── completed_at
└── Indexes: creator_id, assignee_id, status, deadline

-- Reminders: Task reminders
reminders
├── id (PK)
├── task_id (FK) ← tasks.id
├── reminder_time
├── notification_type ← 'telegram', 'calendar', 'both'
├── is_sent
├── sent_at
├── created_at
└── Indexes: task_id, reminder_time

-- RecurringTasks: Recurring task templates
recurring_tasks
├── id (PK)
├── task_id (FK) ← tasks.id
├── pattern ← 'daily', 'weekly', 'monthly'
├── next_occurrence
├── is_active
├── created_at
└── Indexes: task_id, next_occurrence

-- TaskHistory: Audit trail
task_history
├── id (PK)
├── task_id (FK) ← tasks.id
├── action ← 'created', 'updated', 'completed', 'deleted'
├── old_values (JSONB)
├── new_values (JSONB)
├── changed_by (FK) ← users.id
├── timestamp
└── Indexes: task_id, timestamp

-- UserStatistics: Aggregated stats
user_statistics
├── id (PK)
├── user_id (FK) ← users.id
├── group_id (FK) ← groups.id (optional)
├── period ← 'weekly', 'monthly', 'all_time'
├── total_tasks
├── completed_tasks
├── overdue_tasks
├── avg_completion_time
├── completion_rate
├── updated_at
└── Indexes: (user_id, period), (group_id, period)

-- DeletedTaskUndo: Soft-deleted tasks (10s undo window)
deleted_tasks_undo
├── id (PK)
├── task_id (FK) ← tasks.id
├── task_snapshot (JSONB)
├── deleted_at
├── expires_at
└── Indexes: task_id, expires_at

-- BotConfig: Global configuration
bot_config
├── id (PK)
├── key
├── value
├── updated_at
└── Indexes: key
```

### 4.2 Relationships

```
User (1) ──────< (N) GroupMember
  │                      │
  │                      └─────────────────┐
  │                                        │
  ├────────────< (N) Task (creator_id)     │
  │                    │                   │
  │                    ├─────────────┐     │
  │                    │             │     │
  │                    ▼             ▼     ▼
  │              Reminder      TaskHistory
  │                    │             │
  │                    └─────┬───────┘
  │                          │
  │              RecurringTask (from Task)
  │
  ├────────────< (N) Task (assignee_id)
  │
  ├────────────< (N) UserStatistics
  │
  └────────────< (N) DeletedTaskUndo


Group (1) ──────< (N) GroupMember ──────< (N) User

Group (1) ──────< (N) Task ──────┬──────< (N) Reminder
                                 ├──────< (N) TaskHistory
                                 └──────< (N) RecurringTask

Group (1) ──────< (N) UserStatistics
```

---

## 5. API Integration Points

### 5.1 Telegram Bot API

**Connection Type:** Long Polling (UpdateQueue-based)
**Rate Limit:** 30 messages/second
**Callbacks:**
- Message handlers
- Command handlers
- Callback query handlers
- Error handlers

**Example:**
```python
from telegram.ext import Application, CommandHandler

app = Application.builder().token(TELEGRAM_TOKEN).build()

# Register handlers
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler("taoviec", task_create_handler))
app.add_handler(CallbackQueryHandler(button_callback))

# Start polling
app.run_polling()
```

### 5.2 Google Calendar API

**Authentication:** OAuth 2.0 (3-legged)
**Endpoint:** https://www.googleapis.com/calendar/v3/
**Scopes:**
- `https://www.googleapis.com/auth/calendar` - Read/write access
- `https://www.googleapis.com/auth/userinfo.profile` - User profile

**Operations:**
```python
# Create event
service.events().insert(
    calendarId='primary',
    body={
        'summary': task.content,
        'start': {'dateTime': deadline},
        'end': {'dateTime': deadline},
        'description': f"Task ID: {task.id}"
    }
).execute()

# List events
events = service.events().list(
    calendarId='primary',
    timeMin=datetime.now().isoformat(),
    singleEvents=True,
    orderBy='startTime'
).execute()['items']
```

### 5.3 PostgreSQL

**Connection:** asyncpg with SQLAlchemy ORM
**Pool Size:** 10-20 connections
**Connection Timeout:** 30 seconds

**Example:**
```python
async_engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost/teletask",
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)

async with async_engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

---

## 6. Deployment Architecture

### 6.1 Single Bot Deployment

```
┌─────────────────────────────────────────┐
│           Linux Server                  │
│  (Ubuntu 20.04+, Python 3.11+)          │
│                                         │
│  ┌────────────────────────────────────┐ │
│  │ Nginx (Reverse Proxy)              │ │
│  │ Port: 80/443                       │ │
│  │ - OAuth callback routing           │ │
│  │ - SSL termination                  │ │
│  └────────────┬───────────────────────┘ │
│               │                         │
│  ┌────────────▼───────────────────────┐ │
│  │ TeleTask Bot (Python Process)      │ │
│  │ Port: 8080 (OAuth callback)        │ │
│  │ - Managed by PM2                   │ │
│  │ - Auto-restart on failure          │ │
│  └────────────┬───────────────────────┘ │
│               │                         │
│  ┌────────────▼───────────────────────┐ │
│  │ PostgreSQL Database                │ │
│  │ Port: 5432                         │ │
│  │ - Data persistence                 │ │
│  │ - Connection pool                  │ │
│  └────────────────────────────────────┘ │
│                                         │
│  System Resources:                      │
│  - CPU: 1-2 cores (varies)             │
│  - RAM: 512MB - 2GB                    │
│  - Disk: 10GB+ (for backups)           │
└─────────────────────────────────────────┘
```

### 6.2 Multi-Bot Deployment (Future)

```
┌───────────────────────────────────────────────────────┐
│                 Load Balancer                         │
│              (Nginx or HAProxy)                       │
└────┬──────────────────────────┬──────────────────────┘
     │                          │
     ▼                          ▼
┌────────────────┐      ┌────────────────┐
│  Bot Instance 1│      │  Bot Instance 2│  (Multiple bots)
│  (PM2 process) │      │  (PM2 process) │
└────────┬───────┘      └────────┬───────┘
         │                       │
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────▼────────────┐
         │ PostgreSQL Database    │
         │ (Shared backend)       │
         │ Connection Pool        │
         └───────────────────────┘
```

---

## 7. Process Flow & State Management

### 7.1 Task State Machine

```
                    ┌──────────────────┐
                    │   NOT_CREATED    │
                    └────────┬─────────┘
                             │
                    /taoviec command
                             │
                             ▼
                    ┌──────────────────┐
         ┌──────────│    PENDING       │◄────────┐
         │          └────────┬─────────┘         │
         │                   │                   │
         │          /xong    │      /tiendo      │
         │                   │        (update)   │
         │                   ▼                   │
         │          ┌──────────────────┐         │
         │     ┌───►│   IN_PROGRESS    │────────┘
         │     │    └────────┬─────────┘
         │     │             │
         │     │    /xong    │
         │     │      or      │
         │     │  deadline    │
         │     │   reached    │
         │     │             │
         │     │             ▼
         │     │    ┌──────────────────┐
         │     └────│   COMPLETED      │
         │          └────────┬─────────┘
         │                   │
         │            /xoa   │
         │                   ▼
         │          ┌──────────────────┐
         │          │     DELETED      │
         │          │  (soft delete)   │
         │          └────────┬─────────┘
         │                   │
         │          (10 sec undo)
         │                   │
         └───────────────────┘
```

### 7.2 User Session State

```
context.user_data {
    "task_wizard_step": 1-5,
    "task_content": "...",
    "task_deadline": datetime,
    "task_recipient": user_id,
    "task_priority": "low|normal|high",
    "reminder_settings": {...},
    "google_auth_token": "...",
    "pending_confirmation": {...}
}
```

---

## 8. Error Handling Architecture

### 8.1 Error Flow

```
Handler Exception
         │
         ▼
Catch SpecificException
         │
    ├─→ ValidationError      ──→ Send error message to user
    ├─→ DatabaseError        ──→ Log error, notify admin
    ├─→ GoogleCalendarError  ──→ Send retry message
    ├─→ RateLimitError       ──→ Exponential backoff
    │
    └─→ Exception (unhandled) ──→ Log with stacktrace, generic error msg
```

### 8.2 Retry Logic

```
For critical operations (database, API):

def retry_operation(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except TemporaryError:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # exponential backoff
                await asyncio.sleep(wait)
            else:
                raise
```

---

## 9. Security Architecture

### 9.1 Authentication & Authorization

```
Telegram User
         │
         ▼
Update.effective_user.id (Telegram ID)
         │
         ▼
Check in Users table
         │
    ├─→ Exists  → Load user settings
    │
    └─→ New user → Create user record
```

### 9.2 OAuth Flow

```
┌──────────┐                     ┌──────────┐
│  TeleTask│                     │  Google  │
│   Bot    │                     │  OAuth   │
└────┬─────┘                     └─────┬────┘
     │                                 │
     │─ /lichgoogle ─────────────────►│
     │                                 │
     │◄─── Authorization URL ─────────│
     │                                 │
     │  Send URL to user               │
     │                                 │
     │  User clicks & authorizes       │
     │                                 │
     │                                 │
     │◄─ Callback with code ──────────│
     │                                 │
     │─ Exchange code for tokens ────►│
     │                                 │
     │◄─ Access + Refresh tokens ─────│
     │                                 │
     │  Store encrypted tokens in DB  │
```

### 9.3 Data Protection

```
Sensitive Data:
├── Google OAuth tokens
│   └─→ PBKDF2-SHA256 encryption
│       └─→ 100,000 iterations
│       └─→ Random salt per token
│
├── User passwords (future)
│   └─→ bcrypt with cost factor 12
│
├── Report passwords
│   └─→ PBKDF2-SHA256
│       └─→ 100,000 iterations
│
└── Logs (never log)
    ├── Tokens
    ├── Passwords
    ├── OAuth credentials
    └── Personal data
```

---

## 10. Scalability Considerations

### 10.1 Current Limitations

- Single process (one bot instance)
- Single PostgreSQL database
- Long polling (not webhooks)
- In-memory task scheduling (no persistence)

### 10.2 Future Scaling

```
For 100K+ users:

1. Multiple bot instances (horizontal)
   - Load balancer
   - Shared database

2. Database optimization
   - Read replicas
   - Connection pooling (PgBouncer)
   - Caching layer (Redis)

3. Job scheduling
   - Celery instead of APScheduler
   - Redis queue
   - Multiple worker processes

4. Webhooks instead of polling
   - Lower API overhead
   - Real-time updates
```

---

## 11. Deployment Pipeline

### 11.1 Installation Flow

```
1. System Check
   ├─ OS (Ubuntu 20.04+)
   ├─ Python (3.11+)
   ├─ PostgreSQL (15+)
   └─ Nginx (optional)

2. Dependencies
   ├─ pip install -r requirements.txt
   ├─ APScheduler, SQLAlchemy
   ├─ python-telegram-bot
   └─ Google API client

3. Database Setup
   ├─ Create database
   ├─ Create user with permissions
   ├─ Run Alembic migrations
   └─ Initialize schema

4. Configuration
   ├─ .env file (secrets)
   ├─ Bot token
   ├─ Database URL
   ├─ Google OAuth credentials
   └─ Webhook URL

5. PM2 Registration
   ├─ Create PM2 ecosystem.config.js
   ├─ PM2 start
   └─ PM2 save

6. Nginx Setup
   ├─ Configure reverse proxy
   ├─ OAuth callback routing
   ├─ SSL/TLS (optional)
   └─ Service restart

7. Verification
   ├─ Health check
   ├─ Database connection
   ├─ Telegram API connection
   └─ Google OAuth URL test
```

---

## 12. Monitoring & Observability

### 12.1 Logs

```
Log Levels:
├── CRITICAL - System failures (database down)
├── ERROR    - Handler failures
├── WARNING  - Unusual conditions (timeout)
├── INFO     - Normal operations (task created)
└── DEBUG    - Diagnostic info (query time)

Log Rotation:
├── Daily rotation
├── Keep last 7 days
├── Compress old logs
└── /var/log/teletask/bot.log
```

### 12.2 Metrics to Monitor

```
Performance:
├── Command response time (p50, p95, p99)
├── Database query time
├── Memory usage
├── CPU usage
└── Connection pool status

Business:
├── Active users
├── Tasks created/day
├── Completion rate
├── Overdue tasks
└── Calendar sync success rate

Health:
├── Uptime percentage
├── Error rate
├── Database availability
├── API connectivity
└── Job queue depth
```

---

## 13. Architecture Decision Records (ADRs)

### 13.1 Why AsyncIO + asyncpg?

**Decision:** Use async/await pattern with asyncpg for non-blocking I/O

**Rationale:**
- Single process can handle 1000+ concurrent users
- No thread overhead
- Better resource utilization
- Natural fit for Telegram Bot API

### 13.2 Why SQLAlchemy ORM?

**Decision:** Use SQLAlchemy 2.0+ with async support

**Rationale:**
- SQL injection prevention
- Type-safe queries
- Easy migrations with Alembic
- Support for complex relationships
- Async-first design

### 13.3 Why APScheduler?

**Decision:** Use APScheduler for background jobs (instead of Celery)

**Rationale:**
- Lightweight (no Redis required)
- In-process scheduling
- Suitable for single bot instance
- Easy to configure
- Sufficient for current scale

### 13.4 Why Telegram Long Polling?

**Decision:** Long polling instead of webhooks

**Rationale:**
- No public IP required
- NAT/firewall compatible
- Simpler setup
- Lower operational overhead
- Sufficient for current scale

---

## 14. Network Diagram

```
Internet
   │
   ├─────► Telegram Data Centers
   │       (getUpdates polling)
   │
   └─────┐
         │
         ▼
      Router
    (NAT/Firewall)
         │
         ▼
   ┌─────────────────────────┐
   │  Linux Server (teletask)│
   │  ├─ 0.0.0.0:8080       │ ← OAuth callback (127.0.0.1 in code)
   │  └─ Postgres: 5432      │
   └─────────────────────────┘
         │
         └────────┐
                  │
         ┌────────▼────────┐
         │  Google APIs    │
         │  (OAuth, Cal)   │
         └─────────────────┘
```

---

## 15. Component Interaction Diagram

```
Task Creation Sequence:
─────────────────────

User ──────/taoviec──────► task_wizard.py (handler)
                               │
                               ▼
                          Validate input
                               │
                               ▼
                          task_service.create_task()
                               │
                               ├──► task_service._validate_input()
                               │
                               └──► Task.insert() (database)
                                        │
                                        ├──► reminder_service.schedule_reminders()
                                        │
                                        └──► notification.send_notification()
                                             │
                                             └──► User (message)
```

---

**End of Document**
