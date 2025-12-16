# TeleTask

Vietnamese Task Management Bot for Telegram - Manage tasks in groups and personal chats with Vietnamese language support.

## Features

- **Task Creation Wizard** - Step-by-step task creation with button navigation
- **Task Assignment** - Assign tasks to individuals or groups
- **Vietnamese Time Parsing** - Natural language time input (`ngày mai 10h`, `thứ 6 15h`)
- **Text Mention Support** - Mention users with or without @username
- **Group Task Management** - Create tasks for multiple assignees (G-ID/P-ID system)
- **Reminders** - Set task reminders with Vietnamese time expressions
- **Progress Tracking** - Track task status and completion

## Quick Start

```bash
# Clone repository
git clone https://github.com/haduyson/teletask.git
cd teletask

# Copy template to deployment
cp -r src/templates/bot_template /home/botpanel/bots/bot_001

# Configure environment
cd /home/botpanel/bots/bot_001
cp .env.example .env
# Edit .env with your bot token and database credentials

# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start bot
python bot.py
```

## Bot Commands

### Task Creation
| Command | Description |
|---------|-------------|
| `/taoviec` | Create task (wizard mode) |
| `/taoviec <content>` | Create task (quick mode) |
| `/vieccanhan <content>` | Create personal task |

### Task Assignment
| Command | Description |
|---------|-------------|
| `/giaoviec` | Assign task (wizard mode) |
| `/giaoviec @user <content>` | Assign to single user |
| `/giaoviec @user1 @user2 <content>` | Assign to multiple users |
| `/viecdagiao` | View tasks you assigned |

### Task Management
| Command | Description |
|---------|-------------|
| `/xemviec` | View tasks with category menu |
| `/xemviec <ID>` | View specific task details |
| `/xong <ID>` | Mark task as completed |
| `/danglam <ID>` | Mark task as in progress |
| `/xoa <ID>` | Delete a task |

### Reminders
| Command | Description |
|---------|-------------|
| `/nhacviec <ID> <time>` | Set reminder |
| `/xemnhac` | View active reminders |

### Other
| Command | Description |
|---------|-------------|
| `/start` | Start bot / Show help |
| `/thongtin` | Bot information |
| `/timviec <keyword>` | Search tasks |

## Task ID System

| Format | Type | Description |
|--------|------|-------------|
| `T-xxx` | Individual | Single assignee task |
| `G-xxx` | Group | Multi-assignee parent task |
| `P-xxx` | Personal | Child task of group task |

## Project Structure

```
teletask/
├── src/
│   └── templates/
│       └── bot_template/       # Bot source code
│           ├── bot.py          # Main entry point
│           ├── handlers/       # Command handlers
│           │   ├── task_wizard.py    # Wizard flows
│           │   ├── task_create.py    # Task creation
│           │   ├── task_assign.py    # Task assignment
│           │   ├── task_view.py      # Task viewing
│           │   ├── task_update.py    # Task updates
│           │   └── callbacks.py      # Button callbacks
│           ├── services/       # Business logic
│           │   ├── task_service.py   # Task operations
│           │   ├── user_service.py   # User management
│           │   └── time_parser.py    # Vietnamese time parsing
│           ├── database/       # Database layer
│           │   ├── connection.py     # DB connection
│           │   └── migrations/       # Alembic migrations
│           ├── utils/          # Utilities
│           │   ├── keyboards.py      # Inline keyboards
│           │   ├── formatters.py     # Message formatting
│           │   └── validators.py     # Input validation
│           └── scheduler/      # Background jobs
├── docs/                       # Documentation
│   └── user-guide.md          # User guide
└── plans/                      # Development plans
```

## Configuration

Create `.env` file with:

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:pass@localhost:5432/teletask
ADMIN_IDS=123456789,987654321
TIMEZONE=Asia/Ho_Chi_Minh
```

## Tech Stack

- **Python 3.10+**
- **python-telegram-bot** - Telegram Bot API wrapper
- **PostgreSQL** - Database
- **Alembic** - Database migrations
- **APScheduler** - Background job scheduling
- **pytz** - Timezone handling

## Documentation

- [User Guide](docs/user-guide.md) - How to use the bot

## License

MIT License
