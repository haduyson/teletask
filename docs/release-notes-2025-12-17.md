# Release Notes - v1.2.0 (December 17, 2025)

## Features

### Google Calendar Integration
- Merge sync settings from `/caidat` into `/lichgoogle` command
- Add sync mode options: Auto (sync on change) / Manual (button click)
- Add calendar sync for task content update, delete, and restore
- Enhance calendar visual for completed tasks

### Notification Settings
- Add notification preferences: task assigned, task status, reminders, reports
- Reorganize `/caidat` menu structure (now only: Thong bao, Mui gio)
- Add reminder source options (Telegram, Google Calendar, Both)

### BotPanel CLI
- Use bot name as folder slug instead of `bot_001` pattern
- Add interactive menu interface with Vietnamese translation
- Add automated installation script
- Separate system installation from bot creation

### Website
- Dynamic bot name loading from `config.json`
- Rename `bot_001` to `teletask` for website static files

## Bug Fixes
- Add missing service exports (bulk_undo, bulk_restore, bulk_soft_delete)
- Add missing reminder preference migration
- Add psycopg2-binary for alembic migrations
- Fix PM2 startup in bot creation
- Add system chromium detection for ARM64

## Documentation
- Update help messages for new menu structure
- Add comprehensive installation guide
- Add quick install section to README

## Breaking Changes
- Bot folders now use slug naming (e.g., `mybot`) instead of `bot_001` pattern
- Google Calendar settings moved from `/caidat` to `/lichgoogle`
