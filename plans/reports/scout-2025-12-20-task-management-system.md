# Task Management System - Codebase Scout Report

**Date:** 2025-12-20  
**Focus:** Task viewing, assignment, notifications, statistics, chat context handling

---

## 1. /xemviec Command Handler (Task Viewing)

### File: `/home/botpanel/bots/hasontechtask/handlers/task_view.py`

**Entry Point:**
- **Function:** `xemviec_command()` @ Line 104
- **Command Aliases:** `/xemviec`, `/vic [task_id]`

**Key Logic:**
- Line 119-125: Check if task ID provided, fetch by `get_task_by_public_id()`
- Line 127-138: Detect group task (G-ID) using `is_group_task()`, display aggregated progress
- Line 139-161: Regular task (T-ID/P-ID), display individual task detail
- Line 162-171: Show category menu for browsing (personal, assigned, received, all)

**Task Filtering Queries:**
- `get_user_tasks()` - Tasks assigned to user (personal or group)
- `get_user_received_tasks()` - Tasks assigned TO user BY others  
- `get_all_user_related_tasks()` - All tasks (created, assigned, received)
- `get_group_tasks()` - All tasks in group
- `get_tasks_with_deadline()` - Tasks with upcoming deadlines

**Supporting Functions:**
- `format_group_task_detail()` @ Line 42: Formats G-ID with member progress
- `group_task_keyboard()` @ Line 86: Inline keyboard for group task actions
- `viecdanhan_command()` @ Line 294: View tasks assigned TO you
- `viecnhom_command()` @ Line 178: View all tasks in current group
- `timviec_command()` @ Line 235: Search tasks by keyword (content/description)
- `deadline_command()` @ Line 337: Show tasks with deadline within X hours

**Group Task Display:**
- Aggregates progress from all P-ID children under G-ID parent
- Shows member list with individual status icons
- Calculates completion percentage across team
- Allows viewing individual P-ID via `/xemviec [P-ID]`

---

## 2. /giaoviec Command Handler (Task Assignment)

### File: `/home/botpanel/bots/hasontechtask/handlers/task_assign.py`

**Entry Point:**
- **Function:** `giaoviec_command()` @ Line 80
- **Command:** `/giaoviec @user1 [@user2 ...] [content] [time]`

**Chat Context Detection (Line 103):**
```python
is_group = chat.type in ["group", "supergroup"]
```

**Group Registration Logic (Line 114-117):**
- Calls `get_or_create_group()` with `chat.id` and `chat.title`
- Adds creator as group member via `add_group_member()`
- Sets `group_id` for task creation

**Assignee Resolution (Line 119-205):**
1. **Reply Method** (Line 125-132): Auto-assign to replied-to user
2. **Text Mention** (Line 142-148): User clicked name (has user_id)
3. **@mention** (Line 152-165): Username mention via entity parsing
4. **Remaining Text** (Line 180-194): Extract @mentions from message text

**Task Creation Logic:**
- **Single Assignee** (Line 236-292): Create individual task (P-ID)
  - Sends confirmation to creator
  - Sends notification to assignee via `context.bot.send_message()`
  - Checks `notify_task_assigned` preference (Line 265-273)
  
- **Multiple Assignees** (Line 295-356): Create group task (G-ID + P-IDs)
  - `create_group_task()` creates parent + individual child tasks
  - Sends group confirmation to creator
  - Notifies EACH assignee with their personal P-ID (Line 322-350)
  - Checks notification preferences per assignee (Line 326-334)

**Notification Messages:**
- Creator sees: `MSG_TASK_ASSIGNED_MD` (Line 251-257)
- Assignee sees: `MSG_TASK_RECEIVED_MD` (Line 278-286)
- Group creator sees: `MSG_GROUP_TASK_CREATED_MD` (Line 310-317)
- Each group member sees: `MSG_GROUP_TASK_RECEIVED_MD` with their P-ID (Line 338-350)

**Supporting Commands:**
- `viecdagiao_command()` @ Line 363: List tasks user assigned to others

---

## 3. Task Service - Query Functions

### File: `/home/botpanel/bots/hasontechtask/services/task_service.py`

**Task Retrieval by ID:**
- `get_task_by_public_id()` @ Line 156: Fetch task by P-ID or G-ID
  - Query @ Line 167-178: Joins users for creator/assignee names, group name
  - Filters `is_deleted = false`

- `get_task_by_id()` @ Line 182: Fetch task by internal ID

**User Task Queries:**

| Function | Line | Filter | Returns |
|----------|------|--------|---------|
| `get_user_tasks()` | 199 | `assignee_id = $1` | Tasks assigned to user |
| `get_user_created_tasks()` | 251 | `creator_id = $1, assignee_id != $1` | Tasks user assigned to others |
| `get_user_received_tasks()` | 274 | `assignee_id = $1, creator_id != $1` | Tasks from others to user |
| `get_user_personal_tasks()` | 308 | `creator_id = $1, assignee_id = $1` | Self-created personal tasks |
| `get_all_user_related_tasks()` | 342 | `assignee_id = $1 OR creator_id = $1` | All related tasks (union) |

**Filtering Options (All Functions):**
- `status`: Filter by pending/in_progress/completed
- `limit`, `offset`: Pagination
- `include_completed`: Include/exclude completed tasks
- `task_type`: Filter by 'individual' (P-*), 'group' (G-*), or all

**Ordering (Default across all):**
```
Priority: urgent > high > normal > low
Deadline: earliest first (ASC NULLS LAST)
Created: newest first (DESC)
```

**Group Task Queries:**

| Function | Line | Purpose |
|----------|------|---------|
| `get_group_tasks()` | 392 | Fetch all tasks in group |
| `is_group_task()` | 1521 | Check if public_id starts with G- |
| `get_child_tasks()` | 1421 | Fetch all P-IDs under G-ID @ Line 1435 |
| `get_group_task_progress()` | 1370 | Aggregated progress for G-ID @ Line 1384 |
| `create_group_task()` | 1269 | Create G-ID parent + P-ID children @ Line 1299 |

**Group Task Progress (Line 1384-1417):**
```sql
COUNT(*) as total
COUNT(*) FILTER (WHERE status = 'completed') as completed
COALESCE(AVG(progress), 0) as avg_progress
```
Returns: `{total, completed, progress, members, is_complete}`

**Child Tasks Query (Line 1435-1444):**
- Joins with assignee to get user info
- Orders by `created_at` (preserves assignment order)
- Returns full task dict + assignee name/username/telegram_id

---

## 4. Statistics/Thongke Handler

### File: `/home/botpanel/bots/hasontechtask/handlers/statistics.py`

**Entry Points:**
- `thongke_command()` @ Line 33: Overview stats
- `thongketuan_command()` @ Line 66: Weekly stats
- `thongkethang_command()` @ Line 99: Monthly stats
- `viectrehan_command()` @ Line 181: Overdue tasks by period
- `handle_stats_callback()` @ Line 132: Button callbacks (weekly/monthly)
- `handle_overdue_callback()` @ Line 261: Overdue task list callbacks

**Stats Calculation (statistics_service.py):**

**All-Time Stats (Line 67-93):**
```python
calculate_all_time_stats(db, user_id)
Returns: {
    total_assigned, assigned_done,
    total_received, received_done,
    total_personal, personal_done
}
```

**Period Stats (Line 19-64):**
```python
calculate_user_stats(db, user_id, period_type, period_start, period_end, group_id=None)
Returns: {
    assigned_total, assigned_completed, assigned_overdue,
    received_total, received_completed, received_overdue,
    personal_total, personal_completed
}
```

**Query Logic (statistics_service.py Line 29-51):**
- Splits tasks by role: creator_id vs assignee_id
- Calculates: total, completed, overdue (deadline < now)
- Distinguishes: assigned (tasks user gives), received (tasks others give), personal (self-created)
- Filters by `is_deleted = false`, date range

**Overdue Task Periods:**
- `viectrehan_command()` @ Line 181: Displays current month overdue by default
- `get_overdue_tasks()`: Fetches for day/week/month/all periods
- `get_overdue_stats()`: Quick count of overdue tasks

**Keyboard Navigation:**
- Weekly/Monthly buttons allow switching views
- Overdue period buttons (today/week/month/all)

---

## 5. Chat Context & Group Handling

### Group Detection (handlers/task_assign.py Line 103)
```python
chat = update.effective_chat
is_group = chat.type in ["group", "supergroup"]
```

### Group Registration (Line 114-117)
```python
if is_group:
    group = await get_or_create_group(db, chat.id, chat.title or "Unknown")
    group_id = group["id"]
    await add_group_member(db, group_id, creator_id, "member")
```

### Group Context Usage:
- **task_assign.py**: Stores `group_id` when creating tasks in group (Line 246, 303)
- **task_view.py**: `viecnhom_command()` @ Line 178 checks `chat.type == "private"` (Line 190)
- **task_view.py**: `get_group_tasks()` @ Line 207 filters by group ID

### Telegram ID vs User ID:
- **telegram_id** (users.telegram_id): Telegram user ID for `context.bot.send_message(chat_id=...)`
- **user_id** (users.id): Database internal ID for queries
- **group_id** (groups.id): Internal group database ID (not Telegram chat_id)

### Notification Sending (task_assign.py):
```python
# Line 276-286: Send to assignee's private chat
await context.bot.send_message(
    chat_id=assignee["telegram_id"],  # Telegram ID (not DB ID)
    text=...,
    reply_markup=...,
)
```

### Notification Preferences (Line 265-273):
```python
assignee_prefs = await db.fetch_one(
    "SELECT notify_all, notify_task_assigned FROM users WHERE id = $1",
    assignee["id"]
)
should_notify = (
    assignee_prefs.get("notify_all", True) 
    and assignee_prefs.get("notify_task_assigned", True)
)
```

---

## 6. Database Model: Task

### File: `/home/botpanel/bots/hasontechtask/database/models.py` @ Line 124

**Key Columns:**
```python
public_id: P-XXXX or G-XXXX (unique public identifier)
group_task_id: Parent G-ID for multi-assigned tasks
content: Task description
status: pending/in_progress/completed
priority: low/normal/high/urgent
progress: 0-100%

creator_id: User who created task
assignee_id: User assigned task
group_id: Telegram group where task was created
deadline: Task deadline
completed_at: When task was marked complete

parent_task_id: FK for parent task (group structure)
is_personal: Whether creator == assignee
is_deleted: Soft delete flag
```

**Indexes:**
- `idx_tasks_assignee_status`: Fast lookup by assignee + status
- `idx_tasks_creator`: Fast lookup by creator
- `idx_tasks_deadline`: Upcoming deadline queries
- `idx_tasks_group`: Group task queries

---

## 7. Message Flow Example

### Single Assignee Flow
```
User: /giaoviec @nam Fix bug 17h
  ↓
giaoviec_command() extracts @nam, parses "Fix bug 17h"
  ↓
create_task() creates P-XXXX with:
  creator_id=user, assignee_id=nam_id, group_id=null/group_id
  ↓
Creator sees: ✅ Đã giao việc {P-XXXX} cho @nam
  ↓
Bot checks: nam.notify_task_assigned = true
  ↓
Nam receives (private): 📬 Bạn có việc mới {P-XXXX}
```

### Multi-Assignee Group Task Flow
```
User: /giaoviec @nam @linh @hoa Code review 18h
  ↓
giaoviec_command() extracts 3 assignees
  ↓
create_group_task() creates:
  - G-XXXX parent (creator_id=user, no assignee_id)
  - P-YYYY for @nam (creator_id=user, assignee_id=nam_id)
  - P-ZZZZ for @linh (creator_id=user, assignee_id=linh_id)
  - P-WWWW for @hoa (creator_id=user, assignee_id=hoa_id)
  ↓
Creator sees: ✅ Đã tạo việc nhóm {G-XXXX} cho @nam, @linh, @hoa
  ↓
Each assignee receives (private):
  📬 Bạn có việc nhóm {G-XXXX}
     Việc của bạn: {P-YYYY/ZZZZ/WWWW}
```

---

## 8. Key Function Reference

### Task Operations
| Function | File | Line | Purpose |
|----------|------|------|---------|
| `create_task()` | task_service.py | 66 | Create single task (P-ID) |
| `create_group_task()` | task_service.py | 1269 | Create group task (G-ID + P-IDs) |
| `update_task_status()` | task_service.py | 416 | Mark complete/change status |
| `get_task_by_public_id()` | task_service.py | 156 | Fetch task by P-ID or G-ID |

### Task Queries
| Function | File | Line | Purpose |
|----------|------|------|---------|
| `get_user_tasks()` | task_service.py | 199 | Tasks assigned to user |
| `get_user_received_tasks()` | task_service.py | 274 | Tasks from others |
| `get_all_user_related_tasks()` | task_service.py | 342 | All related tasks |
| `get_group_tasks()` | task_service.py | 392 | Tasks in group |
| `get_child_tasks()` | task_service.py | 1421 | P-IDs under G-ID |
| `get_group_task_progress()` | task_service.py | 1370 | Aggregated progress |

### Statistics
| Function | File | Line | Purpose |
|----------|------|------|---------|
| `calculate_all_time_stats()` | statistics_service.py | 67 | Lifetime stats |
| `calculate_user_stats()` | statistics_service.py | 19 | Period stats |
| `get_overdue_tasks()` | statistics_service.py | ? | Overdue by period |
| `get_overdue_stats()` | statistics_service.py | ? | Overdue count |

### Handlers
| Handler | File | Line | Purpose |
|---------|------|------|---------|
| `xemviec_command()` | task_view.py | 104 | View task/list |
| `giaoviec_command()` | task_assign.py | 80 | Assign task |
| `thongke_command()` | statistics.py | 33 | Overview stats |
| `handle_stats_callback()` | statistics.py | 132 | Stats navigation |

---

## 9. Key Implementation Details

### Task ID Generation (task_service.py Line 38-63)
- Uses PostgreSQL `task_id_seq` sequence
- Prevents race conditions with atomic increment
- Format: P0001, P0002, ... or G0001, G0002, ...
- Prefix determines task type

### Group Task Completion Logic (task_service.py Line 1448-1517)
- `check_and_complete_group_task()` called when child task status changes
- Checks if ALL children are `completed`
- Auto-completes parent G-ID when all P-IDs done
- Updates parent progress = AVG(child progress)

### Notification Preference Check (task_assign.py Line 265-273)
- Checks `notify_all` AND `notify_task_assigned` flags
- Only sends private notification if BOTH true
- Logs warning if send fails (doesn't block task creation)

---

## Unresolved Questions

1. **Parent Task ID Column**: Database has both `group_task_id` (string) and `parent_task_id` (FK int). What's the distinction?
2. **Soft Delete Handling**: Are deleted tasks hidden in all queries? Check if `is_deleted = false` is in every query.
3. **Recurring Tasks**: Are `/vieclaplai` and recurring logic implemented? (models.py has `is_recurring` field)
4. **Google Calendar Sync**: Full flow unclear - when/how tasks sync to calendar?
5. **Mention System**: How are @mentions resolved across different groups/chats?

---

**Report Generated:** 2025-12-20  
**Scan Depth:** Handlers (task_view.py, task_assign.py, statistics.py), Services (task_service.py, statistics_service.py, notification.py), Database (models.py)
