# TeleTask Codebase Summary

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Codebase Version:** v1.2.0
**Total Lines of Code:** ~15,000+ (production code)

---

## 1. Tổng Quan Cấu Trúc

```
teletask/
├── src/
│   ├── templates/bot_template/
│   │   ├── handlers/                (14 modules, ~300+ lines mỗi file)
│   │   ├── services/                (10 modules, ~1000+ lines mỗi file)
│   │   ├── database/
│   │   │   ├── models.py            (Database schema & ORM)
│   │   │   ├── connection.py        (Connection pooling & management)
│   │   │   └── migrations/          (8 Alembic migration versions)
│   │   ├── scheduler/               (Job scheduling & cron)
│   │   ├── monitoring/              (Health checks, metrics, alerts)
│   │   ├── utils/                   (Utilities & helpers)
│   │   ├── config/                  (Settings & configuration)
│   │   ├── static/                  (HTML, config files)
│   │   └── main.py                  (Bot entry point)
│   ├── scripts/                     (Utility scripts)
│   └── botpanel.sh                  (CLI management: 1,222 lines)
├── install.sh                       (Auto setup: 1,280 lines)
├── update.sh                        (Bot/system updates)
├── uninstall.sh                     (Safe removal)
├── docs/                            (Documentation folder)
└── README.md                        (Project overview)
```

---

## 2. Handlers (14 Modules)

Handlers xử lý Telegram commands và callbacks. Mỗi handler quản lý một tính năng hoặc nhóm commands.

### 2.1 Core Command Handlers

| Module | Dòng | Mục Đích |
|--------|------|---------|
| **task_create.py** | 140 | Tạo công việc nhanh (/taoviec) |
| **task_wizard.py** | 1,890 | Interactive task creation wizard |
| **task_assign.py** | 520 | Giao công việc cho người khác |
| **task_view.py** | 390 | Xem chi tiết & danh sách công việc |
| **task_update.py** | 460 | Cập nhật status, tiến độ, deadline |
| **task_delete.py** | 720 | Xóa công việc, undo 10s |
| **start.py** | 310 | /start command & initialization |

### 2.2 Feature Handlers

| Module | Dòng | Mục Đích |
|--------|------|---------|
| **reminder.py** | 230 | Cài đặt nhắc nhở tùy chỉnh |
| **recurring_task.py** | 450 | Công việc lặp lại (daily/weekly/monthly) |
| **statistics.py** | 370 | Thống kê (tuần, tháng, tổng) |
| **export.py** | 630 | Export báo cáo (PDF/Excel/CSV) |
| **calendar.py** | 380 | Google Calendar OAuth & sync |
| **settings.py** | 490 | Cài đặt người dùng (múi giờ, thông báo) |
| **callbacks.py** | 1,440 | Inline button callbacks & event handling |

### 2.3 Handler Registration

File: `handlers/__init__.py`
- Register all handlers với bot instance
- Setup command descriptions & scopes
- Initialize error handlers

---

## 3. Services (10 Modules)

Services layer chứa business logic, tách biệt từ handlers.

### 3.1 Core Services

| Module | Dòng | Mục Đích |
|--------|------|---------|
| **task_service.py** | 1,650 | CRUD operations cho tasks |
| **user_service.py** | 270 | User profile & settings management |
| **group_service.py** | - | Group membership & admin |
| **notification.py** | 560 | Send notifications to users |

### 3.2 Feature Services

| Module | Dòng | Mục Đích |
|--------|------|---------|
| **reminder_service.py** | 280 | Reminder scheduling & management |
| **recurring_service.py** | 620 | Recurring task generation & updates |
| **statistics_service.py** | 380 | Calculate stats (weekly, monthly, etc) |
| **report_service.py** | 1,050 | Generate & export reports |
| **calendar_service.py** | 460 | Google Calendar API integration |
| **oauth_callback.py** | 280 | OAuth 2.0 token management |

### 3.3 Utility Services

| Module | Dòng | Mục Đích |
|--------|------|---------|
| **time_parser.py** | 330 | Vietnamese time parsing |

---

## 4. Database Layer

### 4.1 Database Models (models.py)

```python
# 9 SQLAlchemy models:
- User          # Telegram user profile + Google OAuth tokens
- Group         # Telegram group info
- GroupMember   # User-Group relationships
- Task          # Core task data (created, assigned, status, deadline)
- Reminder      # Task reminders (time, notification_type)
- RecurringTask # Recurring task templates
- TaskHistory   # Audit trail
- UserStatistics # Aggregate stats (weekly, monthly)
- BotConfig     # Global configuration
- DeletedTaskUndo # Soft-deleted tasks (10s window)
```

### 4.2 Relationships

```
User (1) ---< GroupMember >--- (N) Group
User (1) ---< Task (creator) (N)
User (1) ---< Task (assignee) (N)
Group (1) ---< Task (N)
Task (1) ---< Reminder (N)
Task (1) ---< TaskHistory (N)
Task (1) ---< RecurringTask (N)
User (1) ---< UserStatistics (N)
Group (1) ---< UserStatistics (N)
```

### 4.3 Migrations

Tất cả migrations được quản lý bằng Alembic:

```
migrations/versions/
├── 20241214_0001_initial_schema.py       # Core tables
├── 20241215_0002_recurring_templates.py  # Recurring support
├── 20251215_0003_group_tasks.py          # Group tasks
├── 20251216_0004_export_reports.py       # Report export
├── 20251216_0005_reminder_source.py      # Reminder sources
├── 20251216_0006_calendar_sync_interval.py
├── 20251217_0001_notification_settings.py
└── 20251217_0007_user_reminder_prefs.py
```

### 4.4 Connection Management

File: `database/connection.py`
- Connection pooling với asyncpg
- Connection lifecycle management
- Error recovery & retry logic

---

## 5. Scheduler & Jobs

Module: `scheduler/`

Chạy các background jobs không đồng bộ:

- **Reminder scheduler:** Gửi nhắc nhở theo schedule
- **Recurring task generator:** Tạo recurring tasks
- **Statistics aggregator:** Update weekly/monthly stats
- **Report cleanup:** Xóa reports cũ
- **Health checks:** Monitor system health
- **Google Calendar sync:** Periodic sync (nếu configured)

---

## 6. Monitoring & Health Checks

Module: `monitoring/`

Theo dõi sức khỏe và metrics:

| File | Mục Đích |
|------|---------|
| **health_check.py** | Check database, API connectivity |
| **resource_monitor.py** | Monitor memory, CPU, connections |
| **metrics.py** | Collect performance metrics |
| **alert.py** | Alert on critical issues |

---

## 7. Utils & Helpers

Module: `utils/`

```
utils/
├── formatters.py      # Format messages, dates, numbers
├── keyboards.py       # Generate inline/reply keyboards
├── messages.py        # Message templates
├── validators.py      # Input validation
└── __init__.py        # Common utilities
```

### 7.1 formatters.py

- Format dates theo user's timezone
- Format task status & progress
- Format statistics output
- Format currency & numbers

### 7.2 keyboards.py

- Inline buttons (1 row, 2 rows)
- Reply keyboards (custom layout)
- Pagination keyboards
- Menu builders

### 7.3 messages.py

- Message templates (f-strings)
- Error messages
- Success messages
- Help text

### 7.4 validators.py

- Validate task content
- Validate dates/times
- Validate callback data
- SQL injection prevention

---

## 8. Configuration

Module: `config/settings.py`

```python
# Environment-based configuration
- DATABASE_URL          # PostgreSQL connection
- TELEGRAM_TOKEN        # Bot token
- GOOGLE_CLIENT_ID      # OAuth client ID
- GOOGLE_CLIENT_SECRET  # OAuth secret
- WEBHOOK_URL           # For OAuth callback
- LOG_LEVEL             # Logging level
- TIMEZONE              # Server timezone
- ALLOWED_HOSTS         # CORS/security
```

---

## 9. Data Flow Patterns

### 9.1 Task Creation Flow

```
/taoviec command
    ↓
task_create.py (command handler)
    ↓
task_wizard.py (interactive steps)
    ↓
task_service.create_task() (business logic)
    ↓
database.Task.insert()
    ↓
notification.send_notification() (async)
    ↓
schedule_reminders() (APScheduler)
```

### 9.2 Reminder Flow

```
APScheduler triggers
    ↓
reminder_service.send_due_reminders()
    ↓
task_service.fetch_due_tasks()
    ↓
For each task:
  - Check reminder settings
  - notification.send_reminder()
  - Update reminder status
```

### 9.3 Google Calendar Sync Flow

```
/lichgoogle command
    ↓
OAuth authorization
    ↓
calendar_service.get_oauth_url()
    ↓
oauth_callback handler (webhook)
    ↓
Store google_calendar_token
    ↓
calendar_service.sync_all_tasks()
    ↓
Insert/update events on Google Calendar
```

---

## 10. Command Mapping

### 10.1 Task Commands

```
/taoviec                    → task_create.py
/taoviec <content> <time>   → task_wizard.py (fast mode)
/giaoviec                   → task_assign.py (wizard)
/xemviec                    → task_view.py (list)
/xemviec <code>            → task_view.py (detail)
/xong <code>               → task_update.py (complete)
/tiendo <code> <%>         → task_update.py (progress)
/xoa <code>                → task_delete.py (single)
/xoanhieu <codes>          → task_delete.py (bulk)
/xoatatca                  → task_delete.py (all)
```

### 10.2 Other Commands

```
/start                      → start.py
/help                       → start.py
/menu                       → callbacks.py (menu)
/nhacviec                   → reminder.py
/xemnhac                    → reminder.py
/vieclaplai                 → recurring_task.py
/thongke                    → statistics.py
/export                     → export.py
/lichgoogle                 → calendar.py
/caidat                     → settings.py
/thongtin                   → start.py
```

---

## 11. File Organization Principles

### 11.1 Naming Conventions

- **Files:** snake_case.py (e.g., task_service.py)
- **Classes:** PascalCase (e.g., TaskService)
- **Functions:** snake_case (e.g., create_task)
- **Constants:** UPPER_CASE (e.g., MAX_RETRY_COUNT)

### 11.2 Module Structure

Mỗi module theo pattern:

```python
"""Module docstring explaining purpose"""

# 1. Imports (standard lib, third-party, local)
# 2. Constants & configuration
# 3. Logger setup
# 4. Classes & functions
# 5. Main logic
```

### 11.3 Handler Pattern

```python
async def handle_task_create(update, context):
    """Handler function docstring"""
    try:
        # 1. Validate input
        # 2. Extract data
        # 3. Call service layer
        # 4. Send response
        # 5. Log action
    except SpecificException as e:
        # Handle specific error
    except Exception as e:
        # Handle generic error
        await update.message.reply_text("An error occurred")
```

### 11.4 Service Pattern

```python
class TaskService:
    """Service docstring"""

    def __init__(self, db_session):
        self.db = db_session

    async def create_task(self, user_id, content, deadline):
        """Create task with validation"""
        # Validate input
        # Query DB
        # Perform business logic
        # Return result
        # Raise exception if error
```

---

## 12. Key Technologies Used

### 12.1 Python Libraries

```
python-telegram-bot==20.x         # Bot framework
sqlalchemy==2.0.x                  # ORM
asyncpg==0.x                       # PostgreSQL driver
alembic==1.x                       # DB migrations
apscheduler==3.x                   # Job scheduling
google-auth-oauthlib==1.x          # Google OAuth
google-api-python-client==2.x      # Google APIs
reportlab==4.x                     # PDF generation
openpyxl==3.x                      # Excel generation
python-dateutil==2.x               # Date utilities
pytz==2024.x                       # Timezone support
python-dotenv==1.x                 # Environment variables
```

### 12.2 Async Patterns

- **asyncio:** Concurrent execution
- **asyncpg:** Non-blocking database access
- **APScheduler:** Async job scheduling
- **python-telegram-bot:** Async handlers

---

## 13. Error Handling Patterns

### 13.1 Database Errors

```python
try:
    await db.commit()
except IntegrityError:
    await db.rollback()
    raise ValidationError("Data conflict")
except OperationalError:
    await db.rollback()
    raise DatabaseError("Connection failed")
```

### 13.2 Handler Errors

```python
async def handle_command(update, context):
    try:
        # Process command
    except ValueError as e:
        await update.message.reply_text(f"Invalid input: {e}")
    except PermissionError as e:
        await update.message.reply_text("You don't have permission")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("An error occurred")
```

---

## 14. Security Patterns

### 14.1 Input Validation

```python
def validate_task_content(content: str) -> None:
    if not content or len(content) > 500:
        raise ValueError("Invalid content length")
    if "<script>" in content.lower():
        raise ValueError("Invalid characters")
```

### 14.2 SQL Injection Prevention

- Use SQLAlchemy ORM (parameterized queries)
- Avoid raw SQL strings
- Use bind parameters for dynamic queries

### 14.3 OAuth Security

```python
# OAuth callback binding to localhost only
WEBHOOK_HOST = "127.0.0.1"
WEBHOOK_PORT = 8080

# Token encryption
google_calendar_token = encrypt_token(token)
```

### 14.4 Password Hashing

```python
# Report PDF password protection
from hashlib import pbkdf2_hmac

hashed = pbkdf2_hmac(
    'sha256',
    password.encode(),
    salt,
    100000  # iterations
)
```

---

## 15. Testing & Quality

### 15.1 Current Status

- Unit tests: Not fully implemented
- Integration tests: Basic coverage
- Type hints: Partial coverage (Python 3.11+)
- Code style: PEP 8 (should use Black for formatting)

### 15.2 Code Quality Tools

Khuyến nghị:
- **Black:** Code formatter
- **Pylint:** Code analysis
- **Mypy:** Type checking
- **Pytest:** Unit testing

---

## 16. Performance Considerations

### 16.1 Database Optimization

- Connection pooling với asyncpg
- Indexes trên frequently queried fields
- Pagination cho large result sets
- Bulk operations cho batch updates

### 16.2 Caching

- In-memory cache cho user settings
- Redis cache (recommended for future)
- Message caching để tránh duplicate sends

### 16.3 API Rate Limiting

- Telegram Bot API: 30 messages/second
- Google Calendar API: Quotas per project
- APScheduler: Stagger job execution

---

## 17. Deployment Structure

### 17.1 Installation Script (install.sh)

7 phases:
1. System dependencies check
2. Python environment setup
3. Database initialization
4. Bot configuration
5. Google OAuth setup
6. PM2 service registration
7. Nginx reverse proxy config

### 17.2 Bot Panel Management (botpanel.sh)

30+ commands in 6 categories:
- **Service:** start, stop, restart, status
- **Logging:** logs, log-bot, log-monitor
- **Backup:** backup-db, restore-db
- **Updates:** update, update-system
- **Config:** config, config-show, reset
- **Help:** help, version

### 17.3 Update Process (update.sh)

- Backup database
- Pull latest code
- Run migrations
- Restart services
- Verify health

---

## 18. Logging & Debugging

### 18.1 Log Levels

```python
# Python logging configuration
CRITICAL - System failures (database down)
ERROR    - Handler failures (permission denied)
WARNING  - Unusual conditions (timeout, retry)
INFO     - Normal operations (task created, user joined)
DEBUG    - Detailed diagnostic info
```

### 18.2 Structured Logging

```python
logger.info(f"Task created", extra={
    "user_id": user_id,
    "task_id": task_id,
    "deadline": deadline
})
```

---

## 19. Future Improvements

### 19.1 Recommended Refactoring

- [ ] Add full unit test coverage (target: 80%)
- [ ] Add type hints throughout (using MyPy)
- [ ] Extract constants to config
- [ ] Add API documentation (OpenAPI)
- [ ] Implement Redis caching

### 19.2 Planned Features

- [ ] REST API for integrations
- [ ] Webhook support
- [ ] Admin dashboard (web UI)
- [ ] Team/workspace features
- [ ] Custom automation rules

---

## 20. Document Navigation

- **Architecture:** `docs/system-architecture.md`
- **Code Standards:** `docs/code-standards.md`
- **Deployment:** `docs/deployment-guide.md`
- **PDR & Vision:** `docs/project-overview-pdr.md`
- **Roadmap:** `docs/project-roadmap.md`
- **User Guide:** `docs/user-guide.md`

---

**End of Document**
