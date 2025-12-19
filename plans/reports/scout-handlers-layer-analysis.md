# Handlers Layer Scout Report

## Overview
The handlers layer is the core user interaction system. It orchestrates 15+ handler modules that manage command execution, inline callbacks, and multi-step conversations.

**Key Files**: `/home/botpanel/bots/hasontechtask/handlers/`

---

## 1. Handler Organization Pattern

### Registration Flow (`__init__.py`)
- **Pattern**: Centralized handler registration via `register_handlers(application: Application)`
- **Order**: Handlers registered in specific priority order (wizard before create, callbacks last)
- **Entry Point**: Single function that imports all `get_handlers()` from each module

```python
# Each handler module exports get_handlers() -> list
# __init__.py imports all and registers sequentially
```

### Handler Modules (15 files)
1. `start.py` - Welcome, help, info commands
2. `task_wizard.py` - 5-step task creation wizard (ConversationHandler)
3. `task_create.py` - Direct /taoviec command (legacy)
4. `task_assign.py` - Assign task to others
5. `task_view.py` - View tasks (personal, assigned, received, search)
6. `task_update.py` - Mark complete, set progress, update status
7. `task_delete.py` - Soft delete tasks with 10s undo window
8. `reminder.py` - Set custom reminders on tasks
9. `recurring_task.py` - Create and manage recurring tasks
10. `calendar.py` - Google Calendar sync
11. `statistics.py` - Weekly/monthly stats and overdue reports
12. `export.py` - Export tasks to PDF/Excel
13. `settings.py` - User preferences (timezone, notifications)
14. `callbacks.py` - Inline button routing (1,300+ lines)
15. `help.py` (implied) - Help and menu content

---

## 2. Key User Interactions & Commands

### Primary Commands
```
/start           → Welcome, user registration
/help            → Command list (private vs group aware)
/thongtin        → User stats and account info
/menu            → Main menu with inline buttons

/taoviec         → Create personal task (direct or wizard mode)
/giaoviec        → Assign task to others (wizard mode)
/xemviec [id]    → View task details
/viecnhom        → View group tasks
/timviec [text]  → Search tasks
/deadline        → View upcoming deadlines

/xong [id]       → Mark task completed
/danglam [id]    → Mark task in progress
/tiendo [id] %   → Set progress percentage
/xoa [id]        → Delete task (undo available)

/nhacviec [id]   → Set task reminder
/xemnhac         → View all reminders
/vieclaplai      → Manage recurring tasks
/lichgoogle      → Google Calendar integration
/thongke         → Weekly/monthly stats
/export          → Export tasks as report
/caidat          → User preferences
```

### Inline Button Callbacks
Format: `action:param1:param2`

**Task Actions**:
- `task_detail:P0001` → Show full task info
- `task_complete:P0001` → Mark complete with confirmation
- `task_progress:P0001` → Show progress menu
- `progress:P0001:75` → Set progress to 75%
- `task_edit:P0001` → Edit menu

**Editing**:
- `edit_content:P0001` → Prompt for new content
- `edit_deadline:P0001` → Prompt for new deadline
- `edit_priority:P0001` → Priority selection
- `edit_assignee:P0001` → Assignee input

**Navigation**:
- `task_category:personal|assigned|received|all` → Filter by category
- `task_filter:individual|group` → Filter by type
- `list:all:page` → Paginated task list

**Delete/Undo**:
- `task_delete:P0001` → Confirm delete
- `confirm:delete:P0001` → Execute delete
- `task_undo:id` → Restore deleted task (10s window)
- `bulk_delete:all|assigned:confirm|cancel` → Batch delete

**Special**:
- `cancel` → Cancel operation
- `noop` → No-op (pagination display)

---

## 3. State Management Approach

### ConversationHandler (Multi-Step Wizards)
Two main conversation flows:

#### Task Creation Wizard (`/taoviec`)
```
States: CONTENT → DEADLINE → ASSIGNEE → PRIORITY → CONFIRM
- per_user=True: One wizard per user
- per_chat=True: One wizard per chat context
- per_message=False: Can reuse message edits
```

Steps:
1. **CONTENT**: Validate task description (3+ chars)
2. **DEADLINE**: Choose preset or enter custom
   - Presets: today, tomorrow, nextweek, nextmonth, skip
   - Custom: Vietnamese natural language parsing (14h30, ngày mai 9h, etc.)
3. **ASSIGNEE**: Choose self or mention users (@username or text_mention)
   - Multiple users → group task with G-ID
   - Single user → personal P-ID task
4. **PRIORITY**: low, normal, high, urgent
5. **CONFIRM**: Review summary, allow editing before creation

#### Assignment Wizard (`/giaoviec`)
```
States: ASSIGN_CONTENT → ASSIGN_RECIPIENT → ASSIGN_DEADLINE → ASSIGN_PRIORITY → ASSIGN_CONFIRM
- Similar flow to creation but no "self" option in recipient step
- Always creates assigned task (no personal option)
```

### User Data Context Storage
- `context.user_data["wizard"]` → Active wizard state and collected data
- `context.user_data["pending_edit"]` → Tracks which field is being edited
  - Stores: type (content/deadline/priority/assignee), task_id, task_db_id
  - Cleared after edit completes or user cancels
- Lifecycle: Initialized on wizard start, cleared on completion/cancellation

### Persistent State (Database)
Tasks tracked with:
- `public_id`: P-XXXX (personal) or G-XXXX (group)
- `status`: pending, in_progress, completed, deleted
- `progress`: 0-100 percentage
- `deadline`: Optional timestamp
- `priority`: low, normal, high, urgent
- `creator_id` + `assignee_id` → Ownership tracking
- `parent_id` + `group_task_id` → Hierarchy for group tasks

### Undo System
```
deleted_tasks_undo table:
- 10 second window to restore
- Countdown timer updates every second (job_queue)
- Expired auto-removes undo option
- Jobs named: undo_countdown_{undo_id}_{seconds}, undo_expired_{undo_id}
```

---

## 4. Handler Registration Details

### Registration Order (Priority)
```python
1. Start handlers    → /start, /help, /thongtin
2. Task wizard       → /taoviec (ConversationHandler)
3. Task create       → /taoviec direct mode (legacy CommandHandler)
4. Task assign       → /giaoviec (ConversationHandler)
5. Task view         → /xemviec, /viecnhom, /timviec, /deadline
6. Task update       → /xong, /danglam, /tiendo
7. Task delete       → /xoa
8. Reminder          → /nhacviec, /xemnhac
9. Statistics        → /thongke, overdue callbacks
10. Recurring tasks  → /vieclaplai, /danhsachvieclaplai
11. Calendar         → /lichgoogle, cal_* callbacks
12. Export           → (report generation)
13. Settings         → /caidat
14. Callbacks        → All inline button handlers (MUST BE LAST)
```

**Key Note**: Callback handlers registered last to capture unmapped patterns.

### Handler Return Values
Each module exports: `get_handlers() -> list`
- Returns list of `CommandHandler`, `CallbackQueryHandler`, `ConversationHandler`, `MessageHandler`
- Each added individually to application: `application.add_handler(handler)`

### Filters Used
- `CommandHandler("command", func)` → Matches /command
- `CallbackQueryHandler(func, pattern=r"^action:")` → Regex pattern matching
- `MessageHandler(filters.TEXT & ~filters.COMMAND, func)` → Text without slash
- `MessageHandler(filters.TEXT & filters.REPLY, func)` → Reply to message (group context)

---

## 5. Key Implementation Patterns

### Callback Data Format
**Safe parsing with validation**:
```python
def parse_callback_data(data: str) -> Tuple[str, list]:
    # Max 200 chars
    # Format: "action:param1:param2"
    # Returns: ("action", ["param1", "param2"])
```

**Validation functions**:
- `validate_task_id(task_id)` → Regex P/G[0-9]{4,8}
- `validate_int(value, min, max)` → Bounded integer
- `validate_priority(priority)` → One of 4 levels
- `validate_list_type(list_type)` → Default to "all"

### Edit Flow Pattern
1. User clicks "Edit" → Shows edit menu keyboard
2. User selects field → Prompt sent with context set
3. Message stored in `pending_edit` in context.user_data
4. Next user message caught by `handle_pending_edit()` (MessageHandler)
5. Edit processed → context cleared
6. Support for /huy (cancel) at any prompt

### Permission Checking
```
- Creator can: view, edit, delete, assign, complete
- Assignee can: view, mark complete, update progress
- Others: Cannot access
- Checked via: creator_id == user_id or assignee_id == user_id
```

### Group vs Private Chat Awareness
```
- Group chat: Show REPLY instruction, send private DM for confirmations
- Private chat: Direct messages, no REPLY hint needed
- Detected: update.effective_chat.type in ["group", "supergroup"]
```

### Vietnamese Time Parsing
- Service: `parse_vietnamese_time(text) -> (datetime, remaining_text)`
- Supports: "14h30", "ngày mai 9h", "thứ 6", "20/12", "cuối tuần"
- Timezone: Asia/Ho_Chi_Minh (pytz)
- Used in: wizard deadline step, reminder scheduling

---

## 6. Error Handling

### Validation Errors
- Sent to user with correction guidance
- Conversation state maintained for retry

### Permission Errors
- `ERR_NO_PERMISSION` → User cannot perform action
- `ERR_TASK_NOT_FOUND` → Task ID invalid
- `ERR_ALREADY_COMPLETED` → Cannot re-complete task

### Database Errors
- Caught with try/except
- User sees: `ERR_DATABASE` generic message
- Logged with full traceback

### Callback Safety
- All callback data validated before use
- Invalid callback → edit_message_text with error
- No crashes, graceful degradation

---

## 7. State Machine Example: Task Wizard

```
START
  ↓
Command: /taoviec (entry_points)
  ↓
wizard_start() → Initialize context["wizard"] = {}
  ↓
CONTENT STATE
  ├─ receive_content() → Validate & store to wizard["content"]
  ├─ /huy command → Cancel, clear wizard, END
  └─ valid text → → DEADLINE
      ↓
DEADLINE STATE
  ├─ deadline_callback() + pattern wizard_deadline: → Store deadline to wizard["deadline"]
  │                       → Fetch recent assignees from DB
  │                       → ASSIGNEE
  ├─ wizard_back: → CONTENT (for edit)
  └─ wizard_cancel → Cancel, clear, END
      ↓
ASSIGNEE STATE
  ├─ assignee_callback() → Store selected user(s) to wizard["assignee_ids"]
  │                     → PRIORITY
  ├─ receive_assignee_input() → Parse @mentions, query DB, validate users → PRIORITY
  ├─ wizard_back: → DEADLINE
  └─ wizard_cancel → Cancel, clear, END
      ↓
PRIORITY STATE
  ├─ priority_callback() → Store wizard["priority"]
  │                     → Format summary for review
  │                     → CONFIRM
  ├─ wizard_back: → ASSIGNEE
  └─ wizard_cancel → Cancel, clear, END
      ↓
CONFIRM STATE
  ├─ confirm_callback(create) → create_task() or create_group_task()
  │                           → Send notifications
  │                           → clear_wizard_data()
  │                           → END
  ├─ confirm_callback(cancel) → clear_wizard_data(), END
  ├─ edit_callback() → Navigate back to specific state
  └─ wizard_cancel → Cancel, clear, END

FALLBACKS: /huy, /cancel commands at any state
```

---

## 8. Callback Router Architecture

**File**: `callbacks.py` (1,319 lines)

Main function: `callback_router(update, context) -> None`

**Routing Pattern**:
1. Parse callback data: "action:params"
2. Validate all parameters with typed validators
3. Route to specific async handler
4. Each handler edits message or sends reply
5. All handlers catch exceptions individually

**Handlers** (50+):
- `handle_complete()` - Mark task done
- `handle_progress_update()` - Set progress %
- `handle_detail()` - Show task info
- `handle_delete_confirm()` - Confirm delete
- `handle_delete()` - Execute delete with countdown
- `handle_undo()` - Restore within 10s window
- `handle_list_page()` - Paginated navigation
- `handle_task_category()` - Filter by category
- `handle_task_filter()` - Filter by type (P-ID/G-ID)
- `handle_edit_menu()` - Show edit options
- `handle_edit_content_prompt()` - Ask for content
- `handle_edit_deadline_prompt()` - Ask for deadline
- `handle_edit_priority_menu()` - Show priority options
- `handle_set_priority()` - Apply priority
- `handle_edit_assignee_prompt()` - Ask for new assignee
- `handle_pending_edit()` - Process text input from edit
- `handle_bulk_delete()` - Batch delete with confirm
- Pagination and statistics callbacks routed here too

**Special Handler**: `handle_pending_edit()`
- Triggered by MessageHandler on all TEXT messages
- Checks if `context.user_data["pending_edit"]` exists
- If not, passes through to other handlers
- Handles: content edit, deadline edit, assignee edit
- Supports: individual→group conversion, group→individual conversion

---

## 9. Database Integration

All handlers use:
- `get_db()` → AsyncPG connection pool
- Service functions from `services/`
- No direct SQL in handlers
- Consistent error handling: `try/except + logger + user message`

Common service calls:
```
get_or_create_user()
get_user_by_id()
get_user_by_username()
get_task_by_public_id()
create_task()
create_group_task()
update_task_*() - content, status, progress, deadline, priority, assignee
soft_delete_task() / restore_task()
parse_vietnamese_time()
```

---

## 10. Keyboard & UI Patterns

### Inline Keyboards
Used for all multi-option selections:
- `wizard_deadline_keyboard()` - Preset dates
- `wizard_priority_keyboard()` - 4 priority levels
- `wizard_assignee_keyboard()` - Recents + input
- `task_detail_keyboard()` - View, edit, complete
- `edit_menu_keyboard()` - Content, deadline, priority, assignee
- `undo_keyboard(undo_id, seconds)` - Countdown display

### Message Editing
- `query.edit_message_text()` - Update inline keyboard
- `query.answer()` - Toast notification
- `update.message.reply_text()` - New message

### Keyboard Formatting
- Emoji icons: 📋 📤 📥 ✅ ❌ 🔔 ⏰ 👥 etc.
- Vietnamese labels
- Max 2 buttons per row typically
- Navigation buttons: « Quay lại, ❌ Hủy, ✅ Xác nhận

---

## 11. Logging & Debugging

Logger: `logging.getLogger(__name__)` in each module

Logged events:
- User commands: `f"User {user.id} created task {task['public_id']}"`
- Callback routing: Unknown action warnings
- Errors: Full exception with context
- Pending edits: State transitions

No sensitive data logged (messages sanitized).

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Handler modules | 15 |
| Total commands | 20+ |
| Callback action types | 50+ |
| ConversationHandler states | 13 (7 task creation + 6 assignment) |
| Lines of code | 3,000+ |
| Main callback router | 1,319 lines |
| Validation functions | 6 |
| Permission checks | Consistent |

---

## Architecture Strengths

1. **Modular**: Each command in separate file with `get_handlers()`
2. **Safe**: All callbacks validated before use
3. **Scalable**: ConversationHandler per-user state isolation
4. **User-friendly**: Group vs private chat aware
5. **Reversible**: Undo system with 10s window
6. **Vietnamese-native**: Natural time parsing, Vietnamese labels
7. **Hierarchical**: Personal (P-ID) vs Group (G-ID) task support
8. **Responsive**: Inline buttons for quick actions
9. **Logged**: Full audit trail of commands
10. **Graceful**: No crashes, all errors caught

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 98 | Handler registration, import all modules |
| `callbacks.py` | 1,319 | Inline button routing and execution |
| `task_wizard.py` | 1,885 | 5-step creation & assignment wizards |
| `task_create.py` | 100+ | Legacy direct command mode |
| `task_view.py` | 200+ | View, search, filter tasks |
| `task_update.py` | 150+ | Mark complete, progress, status |
| `task_delete.py` | 100+ | Soft delete with undo |
| `reminder.py` | 100+ | Custom reminders |
| `task_assign.py` | 200+ | Assign to others |
| `statistics.py` | 200+ | Stats and reports |
| `calendar.py` | 200+ | Google Calendar sync |
| `export.py` | 150+ | Export tasks |
| `settings.py` | 150+ | User preferences |
| `start.py` | 100+ | Welcome and help |

