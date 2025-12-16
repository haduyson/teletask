# Release Notes - December 16, 2025

## New Features

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

## Bug Fixes
- Fixed countdown timer using `context.application.job_queue`
- Fixed edit assignee in groups and group task display
- Fixed timezone-aware deadlines in wizard
- Fixed text overlapping in PDF/Excel reports
- Fixed `g.name -> g.title` in task queries

## Documentation
- User guide moved to `https://teletask.haduyson.com`
- Updated `/help` with all new commands
- Added Settings section to web guide

## Commits
- 28 commits merged to main
- Files changed: handlers, services, utils, static, docs
