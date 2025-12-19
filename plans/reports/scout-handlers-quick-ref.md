# Handlers Layer - Quick Reference

## Registration Call Stack
```
main.py
  ↓
register_handlers(application)
  ├─ handlers/__init__.py
  │   ├─ from .start import get_handlers()
  │   ├─ from .task_wizard import get_handlers()
  │   ├─ from .callbacks import get_handlers() ← LAST
  │   └─ for handler in get_handlers(): application.add_handler(handler)
```

## Command Routing Map

```
/start, /help, /thongtin     → start.py → CommandHandler
/taoviec (wizard)             → task_wizard.py → ConversationHandler
/taoviec (direct)             → task_create.py → CommandHandler
/giaoviec (wizard)            → task_wizard.py → ConversationHandler
/xemviec, /viecnhom           → task_view.py → CommandHandler
/xong, /danglam, /tiendo      → task_update.py → CommandHandler
/xoa                          → task_delete.py → CommandHandler
/nhacviec, /xemnhac           → reminder.py → CommandHandler
/vieclaplai                   → recurring_task.py → CommandHandler
/lichgoogle                   → calendar.py → CommandHandler
/thongke                      → statistics.py → CommandHandler
/export                       → export.py → CommandHandler
/caidat                       → settings.py → CommandHandler

Button clicks (callbacks)     → callbacks.py → CallbackQueryHandler
Text messages (edits)         → callbacks.py → MessageHandler
```

## State Flows

### Task Creation Wizard State Machine
```
/taoviec
  ↓ wizard_start()
[CONTENT] ← User input validation
  ↓ receive_content()
[DEADLINE] ← Select preset or enter custom time
  ↓ deadline_callback() or receive_deadline_custom()
[ASSIGNEE] ← Select user(s) to assign to
  ↓ assignee_callback() or receive_assignee_input()
[PRIORITY] ← Select: low/normal/high/urgent
  ↓ priority_callback()
[CONFIRM] ← Review summary, allow edits, create task
  ↓ confirm_callback(create) → create_task() → END
```

### Edit Flow (Callback triggered)
```
User clicks "Edit Priority" button
  ↓ callback: edit_priority:P0001
callbacks.py → handle_edit_priority_menu()
  ↓ Shows keyboard with priority options
User clicks "High"
  ↓ callback: set_priority:P0001:high
callbacks.py → handle_set_priority()
  ↓ Updates database
  ↓ Shows confirmation message
```

### Inline Edit Flow (Text triggered)
```
User clicks "Edit Content" button
  ↓ callback: edit_content:P0001
callbacks.py → handle_edit_content_prompt()
  ├─ Stores in context.user_data["pending_edit"] = {
  │   type: "content",
  │   task_id: "P0001",
  │   task_db_id: 123
  │ }
  └─ Prompts: "Gửi nội dung mới (REPLY tin nhắn này)"
User sends text message (reply)
  ↓ MessageHandler catches TEXT
  ↓ handle_pending_edit() checks pending_edit
  ├─ Found! type="content"
  ├─ Update task in database
  ├─ Clear context.user_data["pending_edit"]
  └─ Show success message
```

## Callback Data Format & Routing

### Format: `action:param1:param2:...`

```
Task Operations:
  task_detail:P0001
  task_complete:P0001
  task_progress:P0001
  progress:P0001:75
  task_edit:P0001
  task_delete:P0001
  task_undo:42

Editing:
  edit_content:P0001
  edit_deadline:P0001
  edit_priority:P0001
  edit_assignee:P0001
  set_priority:P0001:high

Navigation:
  task_category:personal
  task_filter:individual
  list:all:1

Delete/Undo:
  confirm:delete:P0001
  bulk_delete:all:confirm

Wizard:
  wizard_deadline:today
  wizard_assignee:self
  wizard_priority:high
  wizard_confirm:create
```

## Context User Data Structure

```
context.user_data = {
  "wizard": {
    "content": "Họp đội lúc 2h",
    "deadline": datetime(2025-12-20 23:59:00),
    "assignee_ids": [42],
    "assignee_name": "Nguyễn A",
    "priority": "high",
    "creator_id": 10
  },
  "pending_edit": {
    "type": "content",
    "task_id": "P0001",
    "task_db_id": 123
  },
  "bulk_delete_ids": ["P0001", "P0002"],
  "bulk_delete_type": "all"
}
```

## Permission Model

```
creator_id == user.id     → Can: view, edit, delete, mark complete, assign
assignee_id == user.id    → Can: view, mark complete, set progress
is_admin                  → Can: delete any, view any
Otherwise                 → Cannot access
```

## Task ID Formats

```
P-XXXX  → Personal task (single assignee, created by)
G-XXXX  → Group task parent (multiple assignees)
        → Child P-IDs created automatically for each assignee
```

Example:
```
User A creates group task for B, C, D:
  G-0001 (parent, created by A)
    ├─ P-0002 (B's copy)
    ├─ P-0003 (C's copy)
    └─ P-0004 (D's copy)

If all children marked complete → G-0001 auto-completes
```

## Validation Pipeline

```
Callback received
  ↓ parse_callback_data() → ("action", ["param1", "param2"])
  ↓ Switch on action
  ├─ If task_id param: validate_task_id() → regex P/G[0-9]{4,8}
  ├─ If int param: validate_int(min, max)
  ├─ If priority: validate_priority()
  └─ If list_type: validate_list_type(default="all")
  ↓ If valid → Call handler
  └─ If invalid → edit_message_text("Error: ...")
```

## Keyboard Lifecycle

```
User clicks button
  ↓ query = update.callback_query
  ├─ query.answer() → Toast notification
  ├─ Extract data from query.data
  └─ Route to handler
Handler processes
  ├─ query.edit_message_text(new_text, reply_markup=new_keyboard)
  │  OR
  └─ update.message.reply_text(text, reply_markup=keyboard)
New keyboard shown to user
  ↓ User clicks new button
  └─ → Cycle repeats
```

## Vietnamese Time Parsing

```
Input Text → parse_vietnamese_time()
├─ "14h30" → 14:30 today
├─ "ngày mai 9h" → 9:00 tomorrow
├─ "thứ 6" → Friday this week
├─ "20/12 9h" → Dec 20, 9:00
├─ "cuối tuần" → Sunday 23:59
└─ Unsupported → (None, original_text)

Returns: (datetime with TZ=Asia/Ho_Chi_Minh, remaining_text)
```

## Error Handling Flow

```
try:
  ├─ Handler logic
  └─ If error → logger.error(f"Full traceback")
except Exception:
  ├─ logger.error()
  ├─ await query.edit_message_text("Lỗi hệ thống. Vui lòng thử lại.")
  └─ Conversation remains in current state for retry
```

## Group vs Private Detection

```
update.effective_chat.type == "private"
  → Direct to user with inline buttons

update.effective_chat.type in ["group", "supergroup"]
  → Add "⚠️ REPLY tin nhắn này khi nhập (vuốt phải)"
  → Send DM to user for confirmations
  → Hide sensitive info from group chat
```

## Undo System Timeline

```
User deletes task
  ↓ process_delete()
  ├─ Mark task as soft_deleted
  ├─ Create deleted_tasks_undo record
  └─ undo_id = 42
  ↓ query.edit_message_text() with undo button
  ↓ Show message: "🗑️ Đã xóa việc P0001!
                   Bấm nút bên dưới để hoàn tác."
  ↓ Schedule countdown jobs (10 total)
  ├─ T+1s: Update button "Hoàn tác (9s)"
  ├─ T+2s: Update button "Hoàn tác (8s)"
  ├─ ...
  ├─ T+9s: Update button "Hoàn tác (1s)"
  └─ T+10s: Edit message "⏰ Đã hết thời gian hoàn tác."
  ↓ If user clicks before expiry → process_restore() → Task restored
  └─ If timeout → Undo entry marked is_restored=true
```

## Main Handler Files

| File | Type | Pattern | Entry |
|------|------|---------|-------|
| `start.py` | CommandHandler | Command → Function | `/start` |
| `task_wizard.py` | ConversationHandler | Multi-step flow | `/taoviec`, `/giaoviec` |
| `task_create.py` | CommandHandler | Direct creation | `/taoviec` (with args) |
| `callbacks.py` | CallbackQueryHandler + MessageHandler | Button + Text | Inline buttons |
| `task_view.py` | CommandHandler | View tasks | `/xemviec`, `/deadline` |
| `task_update.py` | CommandHandler | Mark complete | `/xong`, `/danglam` |
| `task_delete.py` | CommandHandler | Delete + restore | `/xoa` |
| `reminder.py` | CommandHandler | Set reminders | `/nhacviec` |
| `recurring_task.py` | CommandHandler | Recurring logic | `/vieclaplai` |
| `calendar.py` | CommandHandler | Google sync | `/lichgoogle` |
| `statistics.py` | CommandHandler + CallbackQueryHandler | Stats view | `/thongke` |
| `export.py` | CommandHandler | Export report | `/export` |
| `settings.py` | CommandHandler | Preferences | `/caidat` |

---

## Handler Return Pattern

```python
# Each module returns list of handlers
def get_handlers() -> list:
    return [
        CommandHandler("command", function),
        CallbackQueryHandler(function, pattern=r"^pattern:"),
        MessageHandler(filters.TEXT, function),
        ConversationHandler(
            entry_points=[...],
            states={STATE: [handlers...]},
            fallbacks=[...]
        )
    ]

# In __init__.py
for handler in get_command_handlers():
    application.add_handler(handler)
```

---

## Quick Debug Tips

```
# Check if wizard is active
if "wizard" in context.user_data:
    print(context.user_data["wizard"])

# Check pending edit
if "pending_edit" in context.user_data:
    print(context.user_data["pending_edit"])

# Logs
logger.info(f"User {user.id} triggered {action}")
logger.warning(f"Unknown callback action: {action}")
logger.error(f"Error: {e}")

# Task lookup
task = await get_task_by_public_id(db, "P0001")
# None if not found, dict if exists
```

