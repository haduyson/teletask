# Scout Report: Services, Utilities, Scheduler & Monitoring Architecture

**Date:** 2025-12-18  
**Target:** Full service layer, utilities, scheduling, and monitoring systems

## Executive Summary

Comprehensive task management bot with sophisticated service layer architecture. Well-structured business logic separation with 11 specialized services, extensive utility functions, APScheduler-based scheduling system, and Prometheus-compatible monitoring. Vietnamese-localized, async-first design.

---

## 1. SERVICE LAYER ARCHITECTURE

### 1.1 Core Services Overview

**11 Specialized Services:**
1. **task_service.py** - Task CRUD & lifecycle
2. **user_service.py** - User & group management  
3. **reminder_service.py** - Reminder logic
4. **notification.py** - Telegram notifications
5. **recurring_service.py** - Recurring task templates
6. **calendar_service.py** - Google Calendar sync
7. **report_service.py** - Report generation & export
8. **statistics_service.py** - Analytics & reporting
9. **time_parser.py** - Vietnamese time parsing
10. **oauth_callback.py** - OAuth integration
11. **notification.py** - Group task notifications

### 1.2 Task Service Architecture

**Public ID System:**
- P-IDs: Individual/personal tasks (P0001-P9999+)
- G-IDs: Group parent tasks (G0001-G9999+)
- Atomic sequence generation prevents race conditions

**Task Types:**
- Personal tasks (creator == assignee)
- Assigned tasks (creator != assignee)
- Group tasks (multi-assignee with parent/child structure)
- Recurring tasks (linked to templates)

**Key Functions:**
```
Core CRUD:
- generate_task_id() - Atomic sequence-based ID generation
- create_task() - Create with auto reminders & Calendar sync
- get_task_by_public_id(), get_task_by_id()
- update_task_status(), update_task_progress(), update_task_content()
- update_task_deadline(), update_task_priority(), update_task_assignee()

Deletion & Recovery:
- soft_delete_task() - 30-second undo window
- restore_task() - Recover from undo buffer
- bulk_soft_delete_with_undo() - Batch soft delete
- bulk_restore_tasks() - Batch restore

Filtering:
- get_user_tasks() - Tasks assigned to user
- get_user_created_tasks() - Tasks created by user
- get_user_received_tasks() - Tasks by others
- get_user_personal_tasks() - Self-created/self-assigned
- get_all_user_related_tasks() - All user involvement

Group Tasks (P-ID/G-ID System):
- create_group_task() - Parent + child P-IDs
- get_group_task_progress() - Aggregated progress
- get_child_tasks() - All P-IDs under G-ID
- check_and_complete_group_task() - Auto-complete parent
- convert_individual_to_group() - Task conversion
- update_group_assignees() - Add/remove members

Pagination & Queries:
- All listing functions support limit/offset
- Priority-ordered by: urgent→high→normal→low
- Deadline sorting (nearest first, null last)
```

**Automatic Features:**
- Default reminders on task creation (24h, 1h before deadline)
- Google Calendar sync if enabled
- Creator gets 1-minute overdue notification
- Task history logging on all changes
- Parent task auto-updates when child completes

### 1.3 User Service Architecture

**User Management:**
```
Core:
- get_or_create_user(tg_user) - Register/update from Telegram
- get_user_by_telegram_id(), get_user_by_id(), get_user_by_username()
- update_user_settings() - Timezone, language, notifications

Group Management:
- get_or_create_group() - Register/sync group
- add_group_member() - Join/update role
- find_users_by_mention() - Search by @username or name

Filtering:
- find_users_by_mention() - Find by @mention or text search
- Search limited to 5 results
```

**User Settings:**
- Allowed fields: timezone, language, notify_reminder, notify_weekly_report, notify_monthly_report
- Validates setting columns to prevent injection

### 1.4 Reminder Service Architecture

**Reminder Types:**
- `before_deadline` - Offset-based (24h, 1h, 30m, 5m)
- `after_deadline` - Overdue escalation (1h, 1d)
- `creator_overdue` - Special creator notification
- `custom` - User-defined reminders

**Key Functions:**
```
BEFORE_DEADLINE offsets: 24h, 1h, 30m, 5m
AFTER_DEADLINE offsets: 1h, 1d

- create_reminder() - Single reminder with type & offset
- get_pending_reminders() - Query due reminders respecting user prefs
- mark_reminder_sent() - Track sent reminders + errors
- delete_task_reminders() - Clean on task completion/delete
- get_task_reminders() - Query by task (pending or all)
- snooze_reminder() - Delay reminder (default 30m)
```

**Filtering Logic:**
- Query checks: `is_sent=false AND remind_at <= NOW()`
- Filters by task status (!= 'completed')
- Respects user notification preferences per reminder type
- Only includes active users (notify_all=true)

### 1.5 Notification Service Architecture

**Message Types:**
- `send_reminder_notification()` - Deadline reminders
- `send_reminder_by_task()` - Manual task reminders
- `send_group_task_created_notification()` - New group task alert
- `send_member_completed_notification()` - Member completion update
- `send_group_completed_notification()` - All members done
- `send_task_completed_to_assigner()` - Task completion notification

**Formatting Functions:**
```
Message Templates:
- format_upcoming_message() - Pre-deadline (24h/1h/urgent tiers)
- format_overdue_message() - Past deadline escalation
- format_creator_overdue_message() - Creator alert
- format_simple_reminder() - Minimal reminder
- format_priority() - Icon + label (🔴 Khẩn cấp)
- format_progress_bar() - Visual progress (█░ 50%)
- format_time_delta() - Vietnamese time (3 giờ 45 phút)
```

**Keyboard Builders:**
- Action buttons: Progress view, snooze 30m, mark complete
- Group task buttons: View team progress, view group
- Creator notifications: View task detail only

### 1.6 Recurring Service Architecture

**Template System:**
- ID Format: R-0001, R-0002, etc.
- Types: daily, weekly, monthly
- Interval support: Every N periods
- End conditions: end_date or max count

**Recurrence Patterns:**
```
Daily: "hàng ngày", "mỗi ngày", "mỗi 2 ngày"
Weekly: "hàng tuần", "mỗi tuần" + days (thứ 2-7, chủ nhật)
Monthly: "hàng tháng", "mỗi tháng" + days (1-31)
Time: "9h30", "14:45"

Examples:
- "hàng ngày lúc 9h" → daily at 9:00
- "thứ 2, thứ 4 lúc 14h" → weekly Mon/Wed at 14:00
- "ngày 1, ngày 15 lúc 10h" → monthly 1st & 15th at 10:00
```

**Key Functions:**
```
- create_recurring_template() - New template
- get_recurring_template() - By R-ID
- get_user_recurring_templates() - User's active
- get_due_templates() - Ready for generation
- generate_task_from_template() - Create task + schedule next
- toggle_recurring_template() - Enable/disable
- delete_recurring_template() - Remove template
- calculate_next_due() - Next generation date
- parse_recurrence_pattern() - Parse Vietnamese text
- format_recurrence_description() - Human-readable format
```

**Auto-Generation:**
- Scheduler checks every 5 minutes
- Creates task + updates next_due
- Notifies creator about new recurring task
- Tracks instances_created count

### 1.7 Report Service Architecture

**Export Formats:**
- CSV (UTF-8 with BOM)
- XLSX (Excel with charts & dashboard)
- PDF (ReportLab with Matplotlib charts)

**Report Types:**
- last7, last30, this_week, last_week, this_month, last_month, custom

**Task Filters:**
- all (created OR assigned)
- created (creator_id = user)
- assigned (creator_id = user AND assignee_id != user)
- received (assignee_id = user AND creator_id != user)

**Statistics Tracked:**
```
- tasks_created, created_completed
- tasks_assigned, assigned_completed
- tasks_received, received_completed
- personal_tasks, personal_completed
- overdue_count, completion_rate (%)
```

**Security:**
- PBKDF2-SHA256 password hashing (100k iterations)
- Random URL-safe passwords generated
- Expiration: 72 hours TTL
- Download count tracking
- Legacy SHA256 fallback support

**Key Functions:**
```
- create_export_report() - Generate & store
- generate_csv_report() - CSV export
- generate_excel_report() - Excel with charts
- generate_pdf_report() - PDF with matplotlib
- get_report_by_id() - Retrieve by ID
- increment_download_count() - Track downloads
- cleanup_expired_reports() - Delete expired
- verify_password() - Check access
```

### 1.8 Statistics Service

Provides analytics for weekly/monthly reports:
- User performance metrics
- Group rankings
- Completion rates & trends
- Previous period comparisons

---

## 2. UTILITY FUNCTIONS LAYER

### 2.1 Message Templates (messages.py)

**Categories:**
- Command responses (start, help, info)
- Task notifications (created, assigned, received, completed, deleted, restored)
- Reminder messages (24h, 1h, overdue)
- Error messages (13+ error templates)
- Status/Priority labels
- Icons & emojis

### 2.2 Formatters (formatters.py)

```
Core Formatting:
- format_status() - Status label (Chờ xử lý, Đang làm, Hoàn thành)
- format_priority() - Priority icon+label (🔴 Khẩn cấp)
- get_status_icon() - Icon emoji
- format_datetime() - Localized Vietnamese date
- format_task_detail() - Full task display
- format_task_list() - Batch task display

Analytics:
- format_stats_overview() - Summary stats
- format_weekly_report() - Weekly breakdown
- format_monthly_report() - Monthly breakdown

Utilities:
- truncate() - Limit length
- escape_html() - HTML safe
- escape_markdown() - Markdown safe
- progress_bar() - Visual bar (█░░░)
- mention_user() - @username mention
- mention_user_html() - HTML mention
```

### 2.3 Keyboards (keyboards.py)

**Interactive Buttons:**
```
Task Operations:
- task_actions_keyboard() - Basic actions
- task_detail_keyboard() - Full detail view
- task_category_keyboard() - Filter by type
- progress_keyboard() - Progress selection
- priority_keyboard() - Priority selection

Deletion:
- undo_keyboard() - Single task undo
- bulk_undo_keyboard() - Batch undo
- bulk_delete_confirm_keyboard() - Delete confirmation

Pagination:
- pagination_keyboard() - Previous/Next/Close
- task_list_with_pagination() - Full list + pagination

Wizards:
- wizard_deadline_keyboard() - Set deadline
- wizard_assignee_keyboard() - Select assignee
- wizard_priority_keyboard() - Set priority
- wizard_confirm_keyboard() - Confirm action
- wizard_cancel_keyboard() - Cancel action

Filters:
- task_type_filter_keyboard() - Filter options
- confirm_keyboard() - Yes/No
- edit_menu_keyboard() - Edit options
- edit_priority_keyboard() - Priority options
```

### 2.4 Validators (validators.py)

```
Extraction:
- extract_mentions() - Parse @usernames from text

Validation:
- validate_task_content() - Content checks
- validate_priority() - Priority enum
- validate_status() - Status enum
- validate_progress() - 0-100 range

Parsing:
- parse_task_command() - Command syntax
- is_valid_public_id() - P-ID or G-ID format

Security:
- sanitize_html() - Remove dangerous HTML
```

### 2.5 Database Utilities (db_utils.py)

```
Column Validation:
- validate_user_setting_column() - Whitelist columns
- get_report_column() - Map column names
- InvalidColumnError - Custom exception

Safe Fields:
USER_SETTING_COLUMNS = {
    'timezone', 'language',
    'notify_reminder', 'notify_weekly_report', 'notify_monthly_report',
    'remind_24h', 'remind_1h', 'remind_30m', 'remind_5m', 'remind_overdue',
    'notify_all', 'notify_task_assigned', 'notify_task_status'
}
```

---

## 3. SCHEDULING SYSTEM

### 3.1 Reminder Scheduler (reminder_scheduler.py)

**APScheduler-based async scheduling:**

```
Global Instance:
- reminder_scheduler = ReminderScheduler() singleton
- init_scheduler(bot, db) - Start globally
- stop_scheduler() - Shutdown

Scheduled Jobs (APScheduler AsyncIOScheduler):
1. process_reminders - Every minute (*) 
   → get_pending_reminders()
   → send_reminder_notification()
   → mark_reminder_sent()

2. cleanup_undo - Every 5 minutes (*/5)
   → Delete expired undo records (expires_at < NOW())

3. process_recurring - Every 5 minutes (*/5)
   → get_due_templates()
   → generate_task_from_template()
   → Notify creator about new recurring task

Custom Reminder Management:
- add_custom_reminder(task_id, user_id, remind_at)
  → Creates DateTrigger job
  → Job ID: custom_{task_id}_{user_id}_{timestamp}
  
- cancel_reminder(job_id) → Remove scheduled job
- _send_single_reminder() → Single reminder send
```

**Error Handling:**
- Logs errors per reminder
- Marks reminder as sent with error message
- Continues on failure

### 3.2 Report Scheduler (report_scheduler.py)

```
Global Instance:
- report_scheduler = ReportScheduler() singleton
- init_report_scheduler(scheduler, bot, db)

Scheduled Jobs:
1. weekly_reports - Saturday 17:00 VN time
   → Calculate week stats (this week + previous week)
   → Get user groups & rankings
   → format_weekly_report() + send

2. monthly_reports - Last day of month 17:00 VN time
   → Calculate month stats (this + previous)
   → format_monthly_report() + send

3. admin_summary - Daily 08:00 VN time (if ADMIN_IDS set)
   → Total users, tasks, completion rate
   → Today's creation & completion
   → Overdue count
   → Send to admin IDs (personal or group)

Statistics:
- Calculate user_stats() with date ranges
- Store stats in DB for trending
- Group rankings per group per week
```

**Admin Configuration:**
- Parse ADMIN_IDS from environment (comma-separated)
- Supports personal (-123456) & group (123456) IDs
- Sends to all recipients on schedule

---

## 4. MONITORING SYSTEM

### 4.1 Health Check Server (health_check.py)

**HTTP Endpoints (aiohttp):**

```
GET /health - System health status
├─ Database connectivity check
├─ Process uptime calculation
├─ Memory usage (RSS in MB)
├─ CPU usage percentage
├─ Today's task stats
└─ Response: JSON with status

GET /metrics - Prometheus format metrics
└─ Delegates to metrics.get_metrics_text()

GET /report/{report_id} - Password page
├─ Checks report exists
├─ Verifies not expired
└─ Serves HTML form (macOS-style)

POST /report/{report_id} - Download handler
├─ Password verification
├─ Expiration check
├─ File serving (CSV/XLSX/PDF)
├─ Increments download count
└─ Sets proper content-type & filename
```

**Response Format:**
```json
{
  "status": "healthy|degraded",
  "bot_name": "TeleTask",
  "uptime": "5d 12h 30m",
  "uptime_seconds": 475800,
  "memory_mb": 256.5,
  "cpu_percent": 2.3,
  "database": "connected|disconnected",
  "last_activity": "2025-12-18T17:30:00",
  "tasks_today": 42,
  "completed_today": 15
}
```

**UI Design:**
- macOS-style window with traffic lights
- Password form with error display
- File badge showing format & description
- 72-hour expiration notice
- Bootstrap compatibility

### 4.2 Metrics System (metrics.py)

**Prometheus Integration (optional):**
- prometheus_client optional dependency
- Fallback to text format if unavailable

**Metrics Tracked:**

```
Gauges (point-in-time):
- bot_uptime_seconds - Current uptime
- bot_memory_bytes - Memory usage
- bot_cpu_percent - CPU percentage
- tasks_overdue_current - Active overdue count

Counters (cumulative):
- tasks_created_total - All created
- tasks_completed_total - All completed
- messages_received_total - Incoming messages
- messages_sent_total - Outgoing messages
- errors_total - Error count by type
```

**Recording Functions:**
```
Task Metrics:
- record_task_created()
- record_task_completed()

Message Metrics:
- record_message_received()
- record_message_sent()

System Metrics:
- update_system_metrics(uptime, memory, cpu)
- update_overdue_tasks(count)

Error Tracking:
- record_error(error_type)
```

**Output Formats:**
- Prometheus text format if available
- Fallback basic text format
- Bot name in all labels

---

## 5. KEY ARCHITECTURAL PATTERNS

### 5.1 Service Layer Patterns

**Async-First Design:**
- All functions are `async def`
- Database calls use `await db.fetch_one()`, `await db.fetch_all()`
- No blocking operations in service layer

**Database Abstraction:**
- All DB operations through `Database` connection object
- Parameterized queries prevent SQL injection
- Transaction support available

**Error Handling:**
- Logging at service level
- Graceful degradation (e.g., Calendar sync failures)
- Exception propagation to handlers

**Separation of Concerns:**
- Services: Business logic only
- Handlers: Telegram command processing
- Utils: Formatting, validation, keyboards
- Monitoring: Health & metrics

### 5.2 Notification Patterns

**Multi-Channel:**
- Telegram Bot API (primary)
- Google Calendar (optional sync)
- Email (through templates)
- Preference-aware (respects user settings)

**Smart Notifications:**
- Creator vs Assignee different messages
- Group task: All members notified
- Completion: Cascade notifications
- Overdue: Escalating urgency

### 5.3 Data Integrity Patterns

**Soft Deletes:**
- Tasks never hard-deleted
- 30-second undo window
- Bulk undo support
- Cascade soft-delete to children

**Audit Trail:**
- task_history table logs all changes
- Tracks: action, field, old_value, new_value, timestamp
- Links to user performing change

**Atomic Operations:**
- Sequence-based ID generation
- Transaction support for related updates
- Parent/child consistency checks

### 5.4 Time Zone Handling

**Vietnamese Timezone:**
- All services use `Asia/Ho_Chi_Minh`
- Database stores UTC internally
- Conversion on read/display
- Handles DST automatically

---

## 6. DATABASE INTEGRATION POINTS

### 6.1 Tables Used

```
Primary:
- tasks - Core task data
- users - User profiles
- groups - Group data
- group_members - Membership
- reminders - Reminder scheduling
- task_history - Audit trail
- deleted_tasks_undo - 30s recovery buffer

Templates:
- recurring_templates - Recurring tasks
- export_reports - Generated reports

Configuration:
- bot_config - Bot settings

Calendar:
- user_oauth_tokens - Google Calendar tokens
```

### 6.2 Query Patterns

**High-Performance:**
- Indexed lookups by telegram_id, user_id, task_id
- Filtered queries with status, deadline, priority
- Aggregation for statistics
- Batch operations for bulk actions

**Pagination:**
- LIMIT/OFFSET for list views
- Sorting by priority → deadline → created_at
- Configurable page sizes

---

## 7. CONFIGURATION & ENVIRONMENT

### 7.1 Environment Variables Used

```
Bot Configuration:
- BOT_NAME - Bot identifier
- BOT_TOKEN - Telegram bot token
- ADMIN_IDS - Comma-separated admin list
- WEBHOOK_URL - For webhook mode

Database:
- DATABASE_URL - Connection string

Features:
- CALENDAR_ENABLED - Google Calendar sync
- REPORT_TTL_HOURS - Report expiration (default 72)
```

### 7.2 Constants

```
Timers:
- Reminder offsets: 24h, 1h, 30m, 5m before; 1h, 1d after
- Scheduler: Every 1 minute (reminders), 5 minutes (recurring/cleanup)
- Soft delete: 30 seconds
- Report TTL: 72 hours

Vietnamese Localization:
- All messages in Vietnamese
- Date format: dd/mm/yyyy
- Time format: HH:mm
- Weekend names: T2-T7, CN
```

---

## 8. UNRESOLVED QUESTIONS & GAPS

1. **OAuth Implementation** - oauth_callback.py not fully reviewed (Google Calendar integration details)
2. **Statistics Service** - calculate_user_stats(), store_user_stats() implementation not inspected
3. **Time Parser** - Vietnamese time parsing algorithm not reviewed
4. **Error Recovery** - How are partial transaction failures handled (e.g., reminder sent but DB failed)?
5. **Rate Limiting** - No visible rate limiting on notification sends
6. **Concurrent Scheduling** - How are duplicate jobs prevented across multiple bot instances?
7. **Report Cleanup** - Automatic cleanup of expired reports runs, but no manual trigger visible
8. **Metrics Persistence** - Prometheus metrics stored in memory, lost on restart

---

## 9. QUALITY METRICS

**Code Organization:**
- Clear service separation (11 focused modules)
- Consistent async patterns
- Comprehensive error handling
- Extensive logging throughout

**Database Design:**
- Normalization with foreign keys
- Audit trails (task_history)
- Soft delete recovery (undo buffer)
- Indexed lookups

**Scalability Considerations:**
- Async-first for concurrency
- Batch operations for bulk tasks
- Pagination support
- Metrics for monitoring

**Security:**
- Parameterized queries (SQL injection prevention)
- PBKDF2 password hashing
- User setting whitelist validation
- Permission checks in handlers

---

## 10. SERVICE ENTRY POINTS

All services imported from `services/__init__.py`:

**Top-level imports for handlers:**
```python
from services import (
    # Users
    get_or_create_user, get_user_by_telegram_id,
    # Tasks  
    create_task, get_task_by_public_id, update_task_status,
    # Reminders
    get_pending_reminders, mark_reminder_sent,
    # Recurring
    get_due_templates, generate_task_from_template,
    # Reports
    create_export_report, get_report_by_id,
)

from services.notification import (
    send_reminder_notification, send_group_task_created_notification
)
```

**Scheduler initialization:**
```python
from scheduler import init_scheduler, stop_scheduler
from scheduler.report_scheduler import init_report_scheduler

init_scheduler(bot, db)
init_report_scheduler(reminder_scheduler.scheduler, bot, db)
```

**Monitoring startup:**
```python
from monitoring.health_check import HealthCheckServer

health_server = HealthCheckServer(app, db, port=8080)
await health_server.start()
```

---

**Report Generated:** 2025-12-18  
**Scout Status:** Complete
