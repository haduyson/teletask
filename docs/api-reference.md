# TeleTask Bot - API Reference & Handler Documentation

**Last Updated:** 2025-12-20
**Version:** 1.0

---

## Overview

Complete reference for all Telegram commands, handlers, and service layer APIs available in TeleTask Bot.

---

## Table of Contents

1. [User Commands](#user-commands)
2. [Task Management Commands](#task-management-commands)
3. [Group Commands](#group-commands)
4. [Statistics & Reporting](#statistics--reporting)
5. [Settings & Preferences](#settings--preferences)
6. [Service Layer APIs](#service-layer-apis)
7. [Database Models](#database-models)

---

## User Commands

### `/start`
**Handler:** `handlers/start.py:start_command()`
**Purpose:** Bot onboarding, registration, help menu
**Input:** None
**Output:**
- Registers user in database if new
- Shows main menu with command buttons
- Returns bot description

```python
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    user = await get_or_create_user(update.effective_user)
    await update.message.reply_text(msg_welcome, reply_markup=main_menu_keyboard())
```

---

### `/help`
**Handler:** `handlers/start.py:help_command()`
**Purpose:** Display command help & usage guide
**Input:** Optional command name
**Output:** Detailed help text with examples

---

## Task Management Commands

### `/taoviec` (Create Task)
**Handler:** `handlers/task_create.py` / `handlers/task_wizard.py`
**Type:** ConversationHandler (multi-step wizard)
**Purpose:** Create a new personal or group task

**Conversation States:**
```
START → TITLE → DESCRIPTION → DEADLINE → PRIORITY → ASSIGN → CONFIRM → END
```

**Parameters Collected:**
1. **Title** (required): Task content/description
2. **Description** (optional): Detailed task description
3. **Deadline** (optional): Task due date/time (Vietnamese parsing)
4. **Priority** (optional): low/normal/high/urgent
5. **Assignee** (optional): @username or user mention
6. **Reminders** (optional): Custom reminder times

**Response:**
```json
{
  "status": "success",
  "task_id": "P-0042",
  "content": "Fix login bug",
  "deadline": "2025-12-25 14:00",
  "priority": "high",
  "assignee": null
}
```

**Service Called:** `TaskService.create_task()`

---

### `/xemviec [task_id]` (View Task)
**Handler:** `handlers/task_view.py:xemviec_command()`
**Type:** CommandHandler
**Purpose:** View task details or list personal/group tasks

**Parameters:**
- `[task_id]` (optional): Specific task ID to view (P-0042, G-0001, etc.)

**Query Types:**
- No params: Show category menu (personal, assigned, received, all)
- `P-XXXX`: Show individual task detail
- `G-XXXX`: Show group task with aggregated progress & member list

**Related Commands:**
- `/viecdanhan` - Tasks assigned TO you by others
- `/viecnhom` - All tasks in current group (group chat only)
- `/timviec [keyword]` - Search tasks by content/description
- `/deadline [hours]` - Tasks with deadline within X hours

**Response Format:**
```
📋 P-0042: Fix login bug
━━━━━━━━━━━━━━━━━━━━
Trạng thái: Đang làm
Ưu tiên: 🔴 Khẩn cấp
Tiến độ: 75%
Hạn: Thứ năm, 25/12/2025 14:00
Giao cho: @john
Người tạo: @admin

[View] [Edit] [Complete] [Delete]
```

---

### `/giaoviec @user1 [@user2 ...] [content] [time]` (Assign Task)
**Handler:** `handlers/task_assign.py:giaoviec_command()`
**Type:** CommandHandler (text parsing)
**Purpose:** Assign task(s) to one or more users

**Parsing Rules:**
1. **Single Assignee:** `/giaoviec @nam Fix bug` → Creates P-XXXX
2. **Multiple Assignees:** `/giaoviec @nam @linh @hoa Code review` → Creates G-XXXX + P-YYYYs
3. **Deadline:** `/giaoviec @nam Task 18h30` → Parses time via time_parser
4. **Group Context:** Can be used in group chats (auto-registers group)

**Assignee Resolution:**
1. Reply method: `/giaoviec [content]` while replying to user
2. Text mention: Click user's name (has user_id from Telegram)
3. @mention: `/giaoviec @username ...`
4. Username in text: Extracted from message body

**Notifications:**
- Creator: ✅ Đã giao việc P-XXXX cho @user
- Assignee: 📬 Bạn có việc mới P-XXXX
- (respects `notify_task_assigned` preference)

**Related:**
- `/viecdagiao` - List tasks you assigned to others

---

### `/xong [task_id]` (Complete Task)
**Handler:** `handlers/task_update.py:xong_command()`
**Type:** CommandHandler
**Purpose:** Mark task as completed
**Status:** pending/in_progress → **completed**
**Triggers:** Auto-notification to creator, parent task check

---

### `/danglam [task_id]` (In Progress)
**Handler:** `handlers/task_update.py:danglam_command()`
**Type:** CommandHandler
**Purpose:** Mark task as currently being worked on
**Status:** pending → **in_progress**

---

### `/tiendo [task_id] [percentage]` (Update Progress)
**Handler:** `handlers/task_update.py:tiendo_command()`
**Type:** CommandHandler
**Purpose:** Update task progress percentage
**Parameters:**
- `[task_id]`: Task to update
- `[percentage]`: 0-100 progress value

**Example:** `/tiendo P-0042 75` → Sets P-0042 progress to 75%

---

### `/xoa [task_id]` (Delete Task)
**Handler:** `handlers/task_delete.py:xoa_command()`
**Type:** CommandHandler
**Purpose:** Soft-delete task with 30-second undo window

**Process:**
1. Soft-delete (mark `is_deleted = true`)
2. Add to `DeletedTaskUndo` buffer
3. Show undo button (30-second countdown)
4. Auto-cleanup after 30 seconds

**Related:**
- Undo button appears in confirmation message
- Can bulk-undo with `/undo_all`

---

### `/nhacviec [task_id] [time]` (Set Reminder)
**Handler:** `handlers/reminder.py:nhacviec_command()`
**Type:** CommandHandler
**Purpose:** Add custom reminder for task

**Reminder Types:**
- **before_deadline**: 24h, 1h, 30m, 5m before deadline
- **after_deadline**: 1h, 1d after missed deadline
- **creator_overdue**: Special creator notification (1h after deadline)
- **custom**: User-specified time

**Example:**
- `/nhacviec P-0042 1h` - Remind 1 hour before deadline
- `/nhacviec P-0042 custom 2025-12-25 10:00` - Custom time

**Database:** Creates entry in `reminders` table
**Scheduler:** APScheduler runs `ReminderScheduler.process_reminders()` every 1 minute

---

### `/vieclaplai [pattern]` (Recurring Task)
**Handler:** `handlers/recurring_task.py:vieclaplai_command()`
**Type:** CommandHandler
**Purpose:** Create recurring task template

**Vietnamese Patterns:**
```
Daily:    "hàng ngày", "mỗi ngày", "mỗi 2 ngày lúc 9h"
Weekly:   "thứ 2, thứ 4 lúc 14h", "hàng tuần"
Monthly:  "ngày 1, ngày 15 lúc 10h", "hàng tháng"
```

**Database:** Creates `RecurringTemplate` with pattern
**Scheduler:** `process_recurring` job (every 5 min) generates instances

---

## Statistics & Reporting

### `/thongke` (Overview Stats)
**Handler:** `handlers/statistics.py:thongke_command()`
**Purpose:** All-time task statistics

**Metrics Returned:**
```json
{
  "total_assigned": 42,
  "assigned_done": 35,
  "total_received": 28,
  "received_done": 24,
  "total_personal": 15,
  "personal_done": 12
}
```

---

### `/thongketuan` (Weekly Stats)
**Handler:** `handlers/statistics.py:thongketuan_command()`
**Purpose:** This week vs previous week breakdown

**Comparison:**
- Tasks created/received (this week vs last week)
- Completion rate
- Overdue tasks
- Performance trend (↑ ↓ →)

---

### `/thongkethang` (Monthly Stats)
**Handler:** `handlers/statistics.py:thongkethang_command()`
**Purpose:** This month vs previous month analysis

---

### `/viectrehan [period]` (Overdue Tasks)
**Handler:** `handlers/statistics.py:viectrehan_command()`
**Purpose:** List overdue tasks by period

**Periods:**
- Today
- This week
- This month
- All overdue

---

### `/export [format] [period]` (Report Export)
**Handler:** `handlers/export.py:export_command()`
**Type:** CommandHandler
**Purpose:** Generate & download task report

**Formats:**
- `csv` - Comma-separated values (UTF-8 BOM)
- `xlsx` - Excel with charts & pivot tables
- `pdf` - PDF with matplotlib charts

**Periods:**
- `last7` - Last 7 days
- `last30` - Last 30 days
- `this_week` - Current week
- `last_week` - Previous week
- `this_month` - Current month
- `last_month` - Previous month
- `custom` - Custom date range

**Response:**
- File generated & stored with 72-hour TTL
- Password-protected download link
- Password sent separately

**Service:** `ReportService.create_export_report()`

---

## Settings & Preferences

### `/caidat` (User Settings)
**Handler:** `handlers/settings.py:settings_command()`
**Purpose:** Configure personal preferences

**Configurable Settings:**
```python
{
  "timezone": "Asia/Ho_Chi_Minh",        # Timezone for deadline display
  "language": "vi",                      # Vietnamese (only option currently)
  "notify_all": true,                    # Master notification toggle
  "notify_task_assigned": true,          # New task assignment notifications
  "notify_task_status": true,            # Task status change notifications
  "notify_reminder": true,               # Reminder notifications
  "notify_weekly_report": true,          # Weekly report auto-send
  "notify_monthly_report": true,         # Monthly report auto-send
  "remind_24h": true,                    # 24h before deadline reminders
  "remind_1h": true,                     # 1h before deadline reminders
  "remind_30m": false,                   # 30m before deadline reminders
  "remind_5m": false,                    # 5m before deadline reminders
  "remind_overdue": true,                # After deadline reminders
}
```

**Update Example:**
```
User selects: Timezone → Asia/Bangkok → Saved
Service called: `UserService.update_user_settings(user_id, {"timezone": "Asia/Bangkok"})`
```

---

### `/lichgoogle` (Google Calendar Integration)
**Handler:** `handlers/calendar.py:calendar_command()`
**Type:** CommandHandler
**Purpose:** Connect/sync Google Calendar (OAuth 2.0)

**Process:**
1. User: `/lichgoogle`
2. Bot generates OAuth URL
3. User clicks link → Google consent screen
4. Google redirects to callback server
5. Token stored in database (encrypted)
6. Tasks synced to calendar

**Service:** `CalendarService.sync_task_to_calendar()`
**Storage:** `User.google_tokens` (encrypted)

---

## Service Layer APIs

### TaskService

```python
# Core CRUD
async create_task(
    user_id: int,
    content: str,
    deadline: Optional[datetime] = None,
    priority: str = "normal",
    group_id: Optional[int] = None,
    assignee_id: Optional[int] = None
) -> Task:
    """Create new task with auto-generated P-ID or G-ID."""

async get_task_by_public_id(public_id: str) -> Optional[Task]:
    """Fetch task by P-XXXX or G-XXXX."""

async get_user_tasks(
    user_id: int,
    status: Optional[str] = None,
    task_type: str = "all",  # 'individual', 'group', 'all'
    limit: int = 10,
    offset: int = 0,
    include_completed: bool = False
) -> List[Task]:
    """Get tasks assigned to user, ordered by priority → deadline."""

async get_user_received_tasks(user_id: int, ...) -> List[Task]:
    """Get tasks assigned TO user BY others."""

async update_task_status(task_id: int, status: str) -> Task:
    """Update task status (pending/in_progress/completed)."""

async update_task_progress(task_id: int, progress: int) -> Task:
    """Update progress (0-100)."""

async soft_delete_task(task_id: int, user_id: int) -> None:
    """Soft delete with 30-second undo window."""

# Group tasks
async create_group_task(
    creator_id: int,
    content: str,
    assignee_ids: List[int],
    group_id: int,
    deadline: Optional[datetime] = None
) -> Task:
    """Create G-ID parent + P-ID children for each assignee."""

async get_group_task_progress(group_task_id: int) -> Dict:
    """Get aggregated progress {total, completed, progress, members}."""

async get_child_tasks(parent_task_id: int) -> List[Task]:
    """Get all P-IDs under G-ID."""
```

### NotificationService

```python
async send_reminder_notification(
    bot,
    user_id: int,
    task: Task,
    reminder_type: str,  # 'before_deadline', 'overdue', 'creator_overdue'
    offset: str = "1h"
) -> bool:
    """Format & send reminder message."""

async send_group_task_created_notification(
    bot,
    user_id: int,
    group_task_id: str,
    personal_task_id: str
) -> bool:
    """Notify member of new group task."""

async send_member_completed_notification(
    bot,
    creator_id: int,
    member_name: str,
    personal_task_id: str
) -> bool:
    """Notify creator when member completes task."""
```

### ReminderService

```python
async create_reminder(
    task_id: int,
    user_id: int,
    remind_at: datetime,
    reminder_type: str = "custom"
) -> Reminder:
    """Create reminder record."""

async get_pending_reminders() -> List[Reminder]:
    """Get reminders WHERE remind_at <= NOW() AND is_sent = false."""

async mark_reminder_sent(reminder_id: int, error: Optional[str] = None) -> None:
    """Mark as sent and log result."""

async snooze_reminder(reminder_id: int, delay_minutes: int = 30) -> None:
    """Delay reminder by N minutes."""
```

### StatisticsService

```python
async calculate_all_time_stats(user_id: int) -> Dict:
    """Calculate lifetime statistics."""

async calculate_user_stats(
    user_id: int,
    period_type: str,  # 'day', 'week', 'month'
    period_start: datetime,
    period_end: datetime,
    group_id: Optional[int] = None
) -> Dict:
    """Calculate period stats {assigned, received, personal, completed, overdue}."""
```

### ReportService

```python
async create_export_report(
    user_id: int,
    format: str,  # 'csv', 'xlsx', 'pdf'
    period_type: str,
    period_start: datetime,
    period_end: datetime
) -> ExportReport:
    """Generate report file with password protection."""

async generate_csv_report(tasks: List[Task], stats: Dict) -> bytes:
    """Return CSV bytes (UTF-8 with BOM)."""

async generate_excel_report(tasks: List[Task], stats: Dict) -> bytes:
    """Return XLSX bytes with charts."""

async generate_pdf_report(tasks: List[Task], stats: Dict) -> bytes:
    """Return PDF bytes with ReportLab."""
```

### UserService

```python
async get_or_create_user(tg_user: User) -> User:
    """Register or update user from Telegram."""

async get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Fetch user by Telegram ID."""

async find_users_by_mention(
    text: str,
    group_id: Optional[int] = None,
    limit: int = 5
) -> List[User]:
    """Search users by @username or name (limited to 5 results)."""

async update_user_settings(user_id: int, settings: Dict) -> User:
    """Update user preferences with column validation."""
```

### TimeParser

```python
def parse_datetime(
    text: str,
    base_time: Optional[datetime] = None
) -> Optional[datetime]:
    """Parse Vietnamese time expressions.

    Examples:
    - "ngày mai" → tomorrow 9:00
    - "25/12" → this year, Dec 25, 9:00
    - "25/12 14:30" → specific time
    - "14h30" → today at 14:30
    """
```

---

## Database Models

### Task Model

```python
class Task(Base):
    __tablename__ = "tasks"

    id: int                          # Internal ID
    public_id: str                   # P-XXXX or G-XXXX (unique)
    content: str                     # Task title/description
    status: str                      # pending, in_progress, completed
    priority: str                    # low, normal, high, urgent
    progress: int                    # 0-100 percentage

    creator_id: int (FK User)        # Who created task
    assignee_id: int (FK User)       # Who task assigned to
    group_id: int (FK Group)         # Which group (null if personal)
    parent_task_id: int (FK Task)    # Parent G-ID for P-IDs
    group_task_id: str               # String ref to parent G-ID

    deadline: datetime               # Due date/time
    completed_at: datetime           # When completed
    is_personal: bool                # creator_id == assignee_id
    is_deleted: bool                 # Soft delete flag
    is_recurring: bool               # Generated from template

    google_event_id: str             # Google Calendar event ID
    created_at: datetime
    updated_at: datetime

    # Indexes
    idx_tasks_assignee_status        # Fast assignee queries
    idx_tasks_deadline               # Overdue detection
    idx_tasks_creator                # List created tasks
    idx_tasks_group                  # Group task queries
```

### User Model

```python
class User(Base):
    __tablename__ = "users"

    id: int                          # Internal ID
    telegram_id: int                 # Unique Telegram ID
    username: str                    # @username if available
    first_name: str
    last_name: str

    timezone: str                    # Asia/Ho_Chi_Minh (default)
    language: str                    # vi (Vietnamese)

    # Notification preferences
    notify_all: bool                 # Master toggle
    notify_task_assigned: bool       # New task notifications
    notify_task_status: bool         # Status change notifications
    notify_reminder: bool            # Reminder notifications
    notify_weekly_report: bool       # Auto weekly report
    notify_monthly_report: bool      # Auto monthly report

    # Reminder preference per type
    remind_24h: bool
    remind_1h: bool
    remind_30m: bool
    remind_5m: bool
    remind_overdue: bool

    # Google Calendar
    google_tokens: str               # Encrypted OAuth token
    google_sync_enabled: bool

    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### Reminder Model

```python
class Reminder(Base):
    __tablename__ = "reminders"

    id: int
    task_id: int (FK Task)
    user_id: int (FK User)

    remind_at: datetime              # When to send reminder
    reminder_type: str               # before_deadline, after_deadline, custom, creator_overdue
    offset: str                      # "24h", "1h", "30m", "5m" (null for custom)

    is_sent: bool
    sent_at: datetime
    error_message: str               # If notification failed

    # Index for scheduler query
    idx_reminders_pending            # Query due reminders
```

### Group Model

```python
class Group(Base):
    __tablename__ = "groups"

    id: int
    telegram_id: int                 # Telegram group ID
    title: str                       # Group name
    is_active: bool
    created_at: datetime
```

---

## Error Responses

### Common HTTP/Response Errors

**Invalid Task ID:**
```
❌ Không tìm thấy việc P-0042
```

**Permission Denied:**
```
❌ Bạn không có quyền truy cập việc này
Chỉ người tạo hoặc người được giao mới có thể xem
```

**Invalid Input:**
```
❌ Dữ liệu không hợp lệ
Vui lòng cung cấp ID việc: /cmd P-XXXX
```

**Database Error:**
```
❌ Lỗi hệ thống, vui lòng thử lại sau
(Logged internally with details)
```

---

## Rate Limiting & Quotas

- **No explicit rate limiting** (todo: implement)
- **Soft limits by nature:**
  - 30-second soft delete undo window
  - 72-hour report download TTL
  - Max 5 user search results
  - Default page size: 10 tasks

---

## Deprecated/Removed APIs

*None currently documented. All APIs listed above are active.*

---

**API Version:** 1.0
**Status:** ACTIVE
**Last Review:** 2025-12-20
