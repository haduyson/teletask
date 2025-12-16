# TeleTask Bot - User Guide

Vietnamese Task Management Bot for Telegram groups and personal use.

## Quick Start

1. Start the bot: `/start`
2. Create a task: `/taoviec` (wizard mode)
3. Assign a task: `/giaoviec` (wizard mode)
4. View tasks: `/xemviec`

---

## Task Creation Wizard (`/taoviec`)

Step-by-step task creation with button navigation.

### How to Use

1. **Start wizard**: Type `/taoviec` (no arguments)
2. **Step 1 - Content**: Enter task description
3. **Step 2 - Deadline**: Select from buttons or enter custom time
4. **Step 3 - Assignee**: Choose "Cho mình" (self) or "Giao người khác" (others)
5. **Step 4 - Priority**: Select priority level
6. **Step 5 - Confirm**: Review and create task

### Quick Mode (Direct Creation)

Skip wizard by providing content directly:
```
/taoviec Hoàn thành báo cáo 17h
```

### Deadline Options

| Button | Meaning |
|--------|---------|
| Hôm nay | End of today (23:59) |
| Ngày mai | End of tomorrow (23:59) |
| Tuần sau | 7 days from now |
| Tháng sau | 30 days from now |
| Nhập thời gian | Custom time input |
| Bỏ qua | No deadline |

### Custom Time Format

```
14h30          → Today 14:30
ngày mai 10h   → Tomorrow 10:00
thứ 6 15h      → This Friday 15:00
20/12 9h       → December 20th 09:00
```

---

## Task Assignment Wizard (`/giaoviec`)

Assign tasks to one or multiple people.

### How to Use

1. **Start wizard**: Type `/giaoviec` (no arguments)
2. **Step 1 - Content**: Enter task description
3. **Step 2 - Recipients**: Tag or mention users
4. **Step 3 - Deadline**: Select deadline
5. **Step 4 - Priority**: Select priority
6. **Step 5 - Confirm**: Review and assign

### Quick Mode (Direct Assignment)

```
/giaoviec @user Nội dung việc 14h
/giaoviec @user1 @user2 Việc nhóm 17h
```

### Mentioning Users

**Two ways to mention:**

1. **@username** - For users with Telegram username
   ```
   @myduyenn2202 @xuanson319
   ```

2. **Text mention** - For users WITHOUT username
   - Tap on member's name in group
   - Select "Mention" from popup
   - Works even if user has no @username

### Group Chat Notes

In group chats, you must **REPLY** to the bot's message when entering text:
- Swipe right on bot's message → Reply
- This is due to Telegram's bot privacy mode

---

## Task Types & IDs

| ID Format | Type | Description |
|-----------|------|-------------|
| T-xxx | Individual Task | Single assignee task |
| G-xxx | Group Task | Multi-assignee parent task |
| P-xxx | Personal Task | Child task of group task |

---

## Priority Levels

| Level | Icon | Description |
|-------|------|-------------|
| Khẩn cấp | 🔴 | Urgent - immediate attention |
| Cao | 🟠 | High priority |
| Bình thường | 🟡 | Normal (default) |
| Thấp | 🟢 | Low priority |

---

## Other Commands

| Command | Description |
|---------|-------------|
| `/xemviec` | View tasks with category menu |
| `/xemviec T-123` | View specific task details |
| `/xong T-123` | Mark task as completed |
| `/danglam T-123` | Mark task as in progress |
| `/xoa T-123` | Delete a task |
| `/viecdagiao` | View tasks you assigned to others |
| `/vieccanhan` | Create personal task |
| `/nhacviec T-123 14h` | Set reminder |
| `/thongtin` | Bot information |

---

## Statistics Commands

| Command | Description |
|---------|-------------|
| `/thongke` | Overview statistics (all time) |
| `/thongketuan` | This week's statistics |
| `/thongkethang` | This month's statistics |

### Statistics Categories

- **Việc đã giao**: Tasks you assigned to others
- **Việc được giao**: Tasks assigned to you
- **Việc cá nhân**: Personal tasks (self-assigned)

---

## Overdue Tasks (`/viectrehan`)

View overdue tasks filtered by current month by default.

### How to Use

```
/viectrehan
```

Shows overdue tasks for the **current month** with filter buttons:
- 📅 **Hôm nay** - Today's overdue tasks
- 📆 **Tuần này** - This week's overdue tasks
- 📊 **Tất cả** - All overdue tasks (all time)

### Monthly Reset

The overdue count resets automatically at the start of each new month. This helps track monthly performance without carrying over old overdue tasks.

---

## Private Notifications

When tasks are created in **group chats**, assignees receive private DM notifications from the bot.

### How It Works

1. Creator assigns task in group: `/giaoviec @user1 @user2 Nội dung`
2. Bot replies in group with confirmation
3. Each assignee receives a **private message** with task details

### Benefits

- Assignees don't miss tasks even if they mute the group
- Task details available in private chat for easy reference
- Works for both single and multiple assignees

---

## Editing Tasks

After viewing a task with `/xemviec T-123`, use the edit menu buttons.

### Edit Options

| Button | Function |
|--------|----------|
| 📝 Sửa nội dung | Edit task content |
| 📅 Sửa deadline | Change deadline |
| 👤 Sửa người nhận | Change assignee(s) |
| 🔔 Sửa độ ưu tiên | Change priority |

### Editing Assignee ("Sửa người nhận")

**Two ways to change assignee:**

1. **@username** - Type username directly
   ```
   @newuser
   ```

2. **Text mention** - For users WITHOUT @username
   - Tap on member's name in group
   - Select "Mention" from popup
   - Reply to bot's edit prompt

**Converting task types:**
- 1 assignee → Individual task (P-ID)
- Multiple assignees → Group task (G-ID with P-IDs)

**Notes:**
- Reply (vuốt phải) to bot message when entering text
- Clickable mention links in confirmation messages

---

## Bulk Delete

Delete multiple tasks at once. Only the task creator can delete.

| Command | Description |
|---------|-------------|
| `/xoahet` | Delete all tasks you created |
| `/xoaviecdagiao` | Delete tasks you assigned to others |

### How It Works

1. Run the command
2. Bot shows list of tasks to be deleted (preview max 5)
3. Press **"Xác nhận"** to delete or **"Hủy"** to cancel

⚠️ **Warning:** Bulk delete cannot be undone!

### Example

```
/xoahet
→ Shows: "Bạn có 3 việc sẽ bị xóa"
→ • P-0001: Hoàn thành báo cáo...
→ • P-0002: Gửi email...
→ • T-0003: Review code...
→ [Xác nhận xóa 3 việc] [Hủy]
```

---

## Tips

1. **Use wizard mode** for complex tasks with multiple options
2. **Use quick mode** for simple, fast task creation
3. **Text mention** works for users without @username
4. **Reply to bot messages** in group chats when entering text
5. **Clickable mentions** in task confirmations notify assignees
