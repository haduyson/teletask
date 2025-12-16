# Release Notes - December 2025

## v1.1.1 - December 17, 2025

### Automated Installation
- **One-command install**: `curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash`
- Auto-installs PostgreSQL, Python 3.11, Node.js, PM2
- Creates database and runs migrations automatically
- Interactive bot token configuration
- Creates `botpanel` CLI management tool

### botpanel CLI
| Command | Description |
|---------|-------------|
| `botpanel start/stop/restart` | Bot management |
| `botpanel status` | Check bot status |
| `botpanel logs` | View live logs |
| `botpanel db-backup/db-restore` | Database backup |
| `botpanel update` | Update to latest version |
| `botpanel config` | Edit configuration |

### Documentation
- Comprehensive installation guide (`installation.md`)
- Quick install section in README
- Troubleshooting guide

### Fixes
- Dynamic database credentials from DATABASE_URL
- Prompt before overwriting existing botpanel (with backup option)

---

## v1.1.0 - December 16, 2025

### Reminder Source Options
- Choose notification source: Telegram / Google Calendar / Both
- `✈️ Telegram` - Bot sends reminders via Telegram
- `📅 Google Calendar` - Google Calendar sends popup notifications
- `✈️ + 📅` - Both sources active

### Granular Reminder Settings
- 24 giờ trước deadline
- 1 giờ trước deadline
- 30 phút trước deadline
- 5 phút trước deadline
- Khi trễ hạn

### Google Calendar Sync Settings
- New menu "Cài đặt đồng bộ Google Calendar"
- Sync interval: 24h / 12h / Weekly / Manual
- Manual sync button for immediate sync
- Conditional popup reminders based on user's source setting

### Database Migrations
- `20251216_0005_reminder_source.py` - Added `reminder_source` column
- `20251216_0006_calendar_sync_interval.py` - Added `calendar_sync_interval` column

### Bug Fixes
- PTBUserWarning suppression for ConversationHandlers
- Reminder filtering respects user preferences

---

## v1.0.0 - December 16, 2025

### Task Management
- Step-by-step wizard for task creation (`/taoviec`) with deadline, assignee, and priority selection
- Bulk delete commands: `/xoahet` (all tasks), `/xoaviecdagiao` (assigned tasks), `/xoatatca`
- Task category menu in `/xemviec` with filters (Personal P-ID / Group G-ID)
- Convert between individual and group tasks
- Edit assignee with text_mention and clickable mention links

### User Interface
- `/menu` command - Interactive feature buttons
- Bold labels in task details (**Trạng thái:**, **Tiến độ:**, **Nhóm:**, etc.)
- Clean task list display (buttons only, no duplicate text)
- 10-second undo countdown with cancel button for deletes
- MacOS-style web interface for user guide

### Statistics & Reports
- Overdue tasks tracking with monthly filter (`/viectrehan`)
- Export reports in PDF/Excel/CSV with custom date ranges
- Admin reports functionality

### Settings & Reminders
- `/caidat` - Granular reminder settings (24h, 1h before deadline)
- ON/OFF indicators for reminder toggles

### Integrations
- Google Calendar integration (`/lichgoogle`)
- OAuth authentication for calendar sync

### Bug Fixes
- Fixed countdown timer using `context.application.job_queue`
- Fixed edit assignee in groups and group task display
- Fixed timezone-aware deadlines in wizard
- Fixed text overlapping in PDF/Excel reports
- Fixed `g.name -> g.title` in task queries

### Documentation
- User guide at `https://teletask.haduyson.com`
- Updated `/help` with all commands
- Settings section in web guide

---

## Statistics

| Version | Commits | Files Changed |
|---------|---------|---------------|
| v1.1.1 | 5 | install.sh, installation.md, README.md |
| v1.1.0 | 3 | handlers/settings.py, services/*, migrations |
| v1.0.0 | 28 | handlers, services, utils, static, docs |
