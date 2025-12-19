# TeleTask Bot

A Vietnamese-language task management Telegram bot for personal and group collaboration. Create tasks, set reminders, sync with Google Calendar, and generate reports—all within Telegram.

**Status**: Active | **Language**: Python 3.11 | **Database**: PostgreSQL

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Telegram bot token (from @BotFather)

### Automated Installation (Recommended)

```bash
# Full stack install with nginx and SSL
sudo ./install.sh --domain teletask.example.com --email admin@example.com

# Then configure your bot token
nano .env  # Set BOT_TOKEN and ADMIN_IDS

# Start the bot
pm2 start ecosystem.config.js
pm2 save
```

The installer automatically sets up:
- Python 3.11 virtual environment
- PostgreSQL database
- Nginx reverse proxy with SSL (Let's Encrypt)
- PM2 process manager
- Environment configuration

**Installer Options:**
```
./install.sh --help              # Show all options
./install.sh --skip-nginx        # Skip nginx (use existing proxy)
./install.sh --skip-db           # Skip database (use external DB)
./install.sh --skip-ssl          # Skip SSL (for local testing)
```

### Manual Installation

```bash
# 1. Clone and setup
git clone <repo-url>
cd teletask-bot
python3.11 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials:
#   BOT_TOKEN=your_token_here
#   DATABASE_URL=postgresql+asyncpg://user:password@localhost/teletask

# 4. Setup database (if first run)
alembic upgrade head

# 5. Start bot
python bot.py

# Or use PM2 for production
pm2 start ecosystem.config.js
pm2 save
```

## Environment Variables

**Required**:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `DATABASE_URL`: PostgreSQL async connection string (asyncpg driver)

**Optional**:
- `TIMEZONE`: Default timezone (default: Asia/Ho_Chi_Minh)
- `ADMIN_IDS`: Comma-separated admin user IDs for monitoring (enables health check, alerts)
- `BOT_NAME`: Bot display name (default: TeleTask Bot)
- `BOT_DOMAIN`: Domain for web interface (e.g., https://tasks.example.com)
- `HEALTH_PORT`: Port for health check and web interface (default: 8080)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FILE`: Path to log file (optional)
- `GOOGLE_CALENDAR_ENABLED`: true/false (default: false)
- `GOOGLE_CREDENTIALS_FILE`: Path to Google OAuth credentials JSON
- `OAUTH_CALLBACK_PORT`: Port for OAuth callback server (default: 8081)
- `METRICS_ENABLED`: true/false for Prometheus (default: false)
- `REDIS_ENABLED`: true/false for caching (default: false)

Example `.env`:
```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/teletask
TIMEZONE=Asia/Ho_Chi_Minh
ADMIN_IDS=123456789,987654321
BOT_NAME=TeleTask Bot
BOT_DOMAIN=https://tasks.example.com
LOG_LEVEL=INFO
```

## Core Commands (Vietnamese)

| Command | Description | Type |
|---------|-------------|------|
| `/taoviec` | Create new task (wizard) | Personal/Group |
| `/xemviec` | View tasks (filtered) | Personal/Group |
| `/xong` | Mark task complete | Personal/Group |
| `/danglam` | Set status to in-progress | Personal/Group |
| `/tiendo` | Update progress (%) | Personal/Group |
| `/giaoviec` | Assign task to someone | Group only |
| `/xoa` | Delete task (soft delete, 30s undo) | Personal/Group |
| `/nhacviec` | Set task reminder | Personal/Group |
| `/vieclaplai` | Create recurring task | Personal/Group |
| `/thongke` | View statistics | Personal/Group |
| `/export` | Export report (CSV/XLSX/PDF) | Personal/Group |
| `/lichgoogle` | Sync with Google Calendar | Personal only |
| `/caidat` | User settings (timezone, notifications) | Personal only |

See full documentation in [`docs/`](./docs) for detailed feature descriptions.

## Architecture

```
Telegram ↔ TeleTask Bot (async/await)
          ├─ 15 Handler Modules (commands & callbacks)
          ├─ 11 Service Modules (business logic)
          ├─ 10 Database Models (SQLAlchemy ORM)
          ├─ APScheduler (reminders every 30s, reports weekly/monthly)
          └─ Monitoring (optional: health checks, alerts)
             ↓
          PostgreSQL (async pool, 2-10 connections)
          Google Calendar API (optional)
          Prometheus Metrics (optional)
```

For detailed architecture, see [`docs/system-architecture.md`](./docs/system-architecture.md).

## Project Structure

```
teletask-bot/
├── bot.py                    # Entry point
├── requirements.txt          # Dependencies
├── ecosystem.config.js       # PM2 configuration
│
├── config/
│   └── settings.py           # Environment & config management
│
├── database/
│   ├── models.py             # 10 SQLAlchemy ORM models
│   ├── connection.py         # Async connection pool
│   └── migrations/           # Alembic schema versions
│
├── handlers/                 # 15 command handlers
│   ├── task_wizard.py        # Multi-step task creation
│   ├── callbacks.py          # 50+ button handlers
│   ├── task_view.py          # View & filter tasks
│   ├── task_update.py        # Status/progress updates
│   ├── task_delete.py        # Soft delete with undo
│   └── ... (more handlers)
│
├── services/                 # 11 business logic modules
│   ├── task_service.py       # Task CRUD (P-ID/G-ID system)
│   ├── notification.py       # Message formatting
│   ├── reminder_service.py   # Reminder scheduling
│   ├── report_service.py     # CSV/XLSX/PDF generation
│   └── ... (more services)
│
├── scheduler/
│   ├── reminder_scheduler.py # Run reminders every 30s
│   └── report_scheduler.py   # Weekly/monthly reports
│
├── monitoring/               # Health check & alerts (optional)
├── utils/                    # Helpers: formatters, keyboards, validators
├── docs/                     # Comprehensive documentation
│   ├── project-overview-pdr.md
│   ├── codebase-summary.md
│   ├── code-standards.md
│   ├── system-architecture.md
│   └── ...
└── exports/                  # Generated report files
```

## Database Models

10 core entities:
1. **User**: Telegram users with timezone, notification preferences, Google tokens
2. **Group**: Telegram groups for shared tasks
3. **GroupMember**: Group membership with roles (admin/member)
4. **Task**: Core entity (status, priority, progress, deadline, P-ID/G-ID)
5. **Reminder**: Scheduled notifications (before/after deadline, custom)
6. **TaskHistory**: Audit trail of all task changes
7. **RecurringTemplate**: Recurring task patterns
8. **UserStatistics**: Weekly/monthly task metrics
9. **DeletedTaskUndo**: Soft delete recovery buffer (30s window)
10. **BotConfig**: Runtime configuration

**Public ID System**:
- Personal tasks: `P-0001`, `P-0042`, etc.
- Group tasks: `G-0001`, `G-0500`, etc.

See [`docs/codebase-summary.md`](./docs/codebase-summary.md) for full schema details.

## Key Features

### Task Management
- Create, view, update, delete personal & group tasks
- Status tracking: pending → in_progress → completed
- Priority levels: low, normal, high, urgent
- Progress tracking (0-100%)
- Soft delete with 30-second undo window

### Reminders & Automation
- Custom reminders (before/after deadline)
- Automatic reminder delivery every 30 seconds
- Recurring tasks (daily, weekly, monthly, custom patterns)
- Timezone-aware scheduling

### Reporting & Insights
- Weekly & monthly statistics (auto-generated)
- Export formats: CSV, XLSX (with charts), PDF
- Task metrics: completed, overdue, in-progress counts

### Google Calendar Sync (Optional)
- OAuth 2.0 integration
- Sync completed tasks to calendar
- Calendar event creation for task deadlines

### Administration & Monitoring (Optional)
- Health check endpoint (port 8080)
- Resource monitoring (CPU, memory, DB connections)
- Error alerts for admins
- Prometheus metrics collection

## Development

### Code Standards
See [`docs/code-standards.md`](./docs/code-standards.md) for:
- File naming & organization
- Async/await patterns
- Type hints requirements
- Handler patterns (ConversationHandler, CommandHandler, CallbackQuery)
- Service layer design
- Database access patterns
- Error handling guidelines
- Vietnamese language conventions

### Type Hints & Async
```python
# All functions require type hints
async def create_task(user_id: int, content: str) -> Task:
    # All I/O is async
    async with db.session() as session:
        result = await session.execute(select(...))
        return result.scalar_one_or_none()
```

### Testing
```bash
# Run tests (if present)
pytest tests/

# Run specific test
pytest tests/services/test_task_service.py::test_create_task
```

### Database Migrations
```bash
# Create migration after model changes
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Deployment

### Using PM2 (Recommended)
```bash
# Install PM2
npm install -g pm2

# Start bot
pm2 start ecosystem.config.js

# View logs
pm2 logs teletask-bot

# Restart on reboot
pm2 startup
pm2 save
```

### Manual Start
```bash
source venv/bin/activate
python bot.py
```

### Production Checklist
- [ ] BOT_TOKEN configured (don't commit .env)
- [ ] DATABASE_URL points to production database
- [ ] ADMIN_IDS configured for monitoring
- [ ] LOG_LEVEL set to INFO or WARNING
- [ ] Backups configured (daily recommended)
- [ ] Health checks passing (`curl http://localhost:8080/health`)

## Monitoring

### Health Check & Web Interface
```bash
# Health check endpoint
curl http://localhost:8080/health
# Response: { "status": "healthy", "uptime_seconds": 3600, "db": "connected" }

# User guide pages (served automatically when BOT_DOMAIN configured)
# http://localhost:8080/           → Main user guide
# http://localhost:8080/user-guide.html → Full documentation
# http://localhost:8080/config.json     → Bot configuration (name, domain)
```

The web interface is automatically generated on bot startup when `ADMIN_IDS` is configured. The `static/config.json` file is regenerated with the current `BOT_NAME` and `BOT_DOMAIN` values.

### Logs
```bash
# View logs with bot running
pm2 logs teletask-bot

# Or check log file if configured
tail -f $LOG_FILE
```

### Metrics (Optional)
If `METRICS_ENABLED=true` and `ADMIN_IDS` configured:
- CPU usage, memory usage tracked
- Database connection pool monitored
- Error rates recorded
- Admin alerts on threshold breach

## Troubleshooting

### Database Connection Error
```
Error: could not connect to server
```
- Check PostgreSQL is running: `sudo service postgresql status`
- Verify DATABASE_URL in .env
- Test connection: `psql $DATABASE_URL`

### Bot Token Error
```
Error: Invalid bot_token
```
- Verify BOT_TOKEN from @BotFather
- No spaces or typos

### Task Not Visible
- Check task isn't soft-deleted (`is_deleted=true`)
- Verify user owns or is assigned the task
- Check task status filter in /xemviec

### Reminder Not Firing
- Verify reminder time is in future
- Check remind_at stored in database
- View scheduler logs for errors
- Restart bot if scheduler stuck

## Documentation

Complete documentation in `./docs/`:
- **[project-overview-pdr.md](./docs/project-overview-pdr.md)**: Goals, features, requirements, metrics
- **[codebase-summary.md](./docs/codebase-summary.md)**: Code structure, modules, dependencies, architecture
- **[code-standards.md](./docs/code-standards.md)**: Naming, patterns, async/await, error handling, tests
- **[system-architecture.md](./docs/system-architecture.md)**: Component architecture, data flow, database schema

## Contributing

1. Follow code standards in [`docs/code-standards.md`](./docs/code-standards.md)
2. Type hints required on all functions
3. Update docs when changing features
4. Run database migrations for schema changes
5. Test before committing

## Performance

- **Response time**: 100-500ms (database dependent)
- **Concurrent users**: ~100 with single instance
- **Memory**: 100-150MB steady state
- **CPU**: <5% idle, <20% during heavy operations

## License

[Your License Here]

## Support

For issues, questions, or feature requests:
- Check documentation in `./docs/`
- Review code standards in `./docs/code-standards.md`
- File an issue on GitHub

---

**Last Updated**: 2024-12-18
**Status**: Production Ready
**Version**: 1.0
