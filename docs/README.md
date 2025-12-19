# TeleTask Bot Documentation Index

Welcome to TeleTask Bot documentation. This directory contains comprehensive guides for understanding, developing, and maintaining the bot.

## Quick Navigation

**Getting Started?** Start here:
1. Read the main [`../README.md`](../README.md) (10 min - project overview & setup)
2. Review [`system-architecture.md`](./system-architecture.md) (20 min - understand the system)
3. Skim [`codebase-summary.md`](./codebase-summary.md) (15 min - know the code structure)
4. Bookmark [`code-standards.md`](./code-standards.md) (reference while coding)

**Looking for something specific?** Use the index below.

---

## Documentation Files

### 1. [`project-overview-pdr.md`](./project-overview-pdr.md)
**Purpose**: Business requirements, features, goals

**Contains**:
- Project summary & vision
- Target users & use cases
- Feature overview (15+ commands)
- Technical requirements & stack
- Database models (10 entities)
- Success metrics & KPIs
- Non-functional requirements
- 3-phase roadmap

**Read if**: You need to understand *why* the project exists and *what* it does.

**Time**: 15-20 minutes

---

### 2. [`codebase-summary.md`](./codebase-summary.md)
**Purpose**: Code organization, modules, dependencies

**Contains**:
- Project overview (68 files, 21K lines)
- Complete directory structure
- 15 handler modules with purposes
- 11 service modules with responsibilities
- 10 database models with relationships
- Async/await architecture patterns
- Dependency list with versions
- Performance characteristics
- Security considerations

**Read if**: You're new to the codebase and need to understand the structure.

**Time**: 20-30 minutes

**Key Sections**:
- `## Directory Structure` - See the full file layout
- `## Key Modules & Responsibilities` - Understand what each module does
- `## Database Schema Overview` - See the data model
- `## Dependencies` - Know what libraries are used

---

### 3. [`code-standards.md`](./code-standards.md)
**Purpose**: Code style, patterns, best practices

**Contains**:
- File & naming conventions (kebab-case, descriptive names)
- Python style guide (3.11+, type hints required, async mandatory)
- Async/await patterns with examples
- Type hints requirements
- Docstring standards (Google-style)
- Handler patterns (ConversationHandler, CommandHandler, Callback)
- Service layer patterns
- Database access patterns
- Error handling guidelines
- Security considerations
- Testing patterns
- Vietnamese language conventions

**Read if**: You're writing code and need to know the standards.

**Time**: 30-40 minutes (reference while coding)

**Key Sections**:
- `## 3. Handler Patterns` - How to write handlers
- `## 4. Service Layer Patterns` - How to write services
- `## 5. Database Access Patterns` - How to query data
- `## 6. Error Handling Guidelines` - What exceptions to throw
- `## 10. Code Review Checklist` - Before committing

---

### 4. [`system-architecture.md`](./system-architecture.md)
**Purpose**: System design, data flow, integrations

**Contains**:
- High-level architecture diagram
- 5 component layers (handlers, services, database, scheduler, monitoring)
- Handler lifecycle & patterns
- Service responsibilities & patterns
- Database connection management
- Database schema with indexes & constraints
- External integrations (Telegram, Google Calendar, PostgreSQL)
- Data flow examples:
  - Creating a task (personal)
  - Setting a reminder
  - Soft delete with undo
  - Generating reports
- Failure scenarios & error recovery
- Performance characteristics
- Reliability & scaling limits

**Read if**: You need to understand how components interact and how data flows.

**Time**: 25-35 minutes

**Key Sections**:
- `## 1. High-Level Architecture Overview` - See the system diagram
- `## 2. Component Architecture` - Understand layers
- `## 3. Data Flow Examples` - See how features work
- `## 4. Database Schema Overview` - See data model
- `## 5. External Integrations` - Understand dependencies

---

### 5. Main Project [`../README.md`](../README.md)
**Purpose**: Quick start, setup, deployment

**Contains**:
- Project description
- Quick start guide (5 steps)
- Environment variables (with example)
- Core commands table (13 Vietnamese commands)
- Project structure
- Database models (summary)
- Key features list
- Development guidelines
- Deployment instructions
- Monitoring & troubleshooting
- Contributing guidelines

**Read if**: You need to get the bot running or understand features quickly.

**Time**: 10-15 minutes

---

## Common Tasks

### "I just started and need to understand the project"
1. Read [`../README.md`](../README.md) (10 min)
2. Read [`system-architecture.md`](./system-architecture.md) (30 min)
3. Skim [`codebase-summary.md`](./codebase-summary.md) directory structure (10 min)
4. Bookmark [`code-standards.md`](./code-standards.md) for reference

**Total time**: 50 minutes

---

### "I need to write a new command handler"
1. Review [`code-standards.md`](./code-standards.md) § 3 (Handler Patterns)
2. Check [`codebase-summary.md`](./codebase-summary.md) § Key Modules (see similar handlers)
3. Look at existing handler in `handlers/` directory
4. Follow the pattern: ConversationHandler or CommandHandler
5. Write docstrings, add type hints, handle errors

**Reference**:
- Single command: [`code-standards.md`](./code-standards.md) § Single Command Handler
- Multi-step: [`code-standards.md`](./code-standards.md) § Multi-Step Conversation Handler

---

### "I need to add a database model"
1. Edit `database/models.py` - add SQLAlchemy model
2. Create Alembic migration: `alembic revision --autogenerate -m "Add field"`
3. Review migration in `database/migrations/versions/`
4. Apply migration: `alembic upgrade head`
5. Update services to use new model
6. Document in [`codebase-summary.md`](./codebase-summary.md) § Database Schema

**Reference**: [`code-standards.md`](./code-standards.md) § Database Access Patterns

---

### "I need to fix a bug or add a feature"
1. Understand the feature in [`project-overview-pdr.md`](./project-overview-pdr.md)
2. Find the code in [`codebase-summary.md`](./codebase-summary.md) directory structure
3. Review data flow in [`system-architecture.md`](./system-architecture.md) § Data Flow Examples
4. Follow code standards in [`code-standards.md`](./code-standards.md)
5. Update database schema if needed (migration)
6. Update documentation if behavior changes

---

### "I need to deploy the bot"
1. Read [`../README.md`](../README.md) § Deployment
2. Read [`../README.md`](../README.md) § Production Checklist
3. Configure `.env` file
4. Set up PostgreSQL database
5. Run migrations: `alembic upgrade head`
6. Start with PM2: `pm2 start ecosystem.config.js`

---

### "The bot is slow or crashing"
1. Check [`../README.md`](../README.md) § Troubleshooting
2. Review logs: `pm2 logs teletask-bot`
3. Check health: `curl http://localhost:8080/health`
4. Review [`system-architecture.md`](./system-architecture.md) § Reliability & Failure Scenarios
5. Check performance metrics in [`system-architecture.md`](./system-architecture.md) § Performance Characteristics

---

### "I'm adding a new feature"
1. Document in [`project-overview-pdr.md`](./project-overview-pdr.md) § Feature Overview
2. Update commands table in [`../README.md`](../README.md)
3. Create handlers following [`code-standards.md`](./code-standards.md)
4. Add services if needed
5. Update [`codebase-summary.md`](./codebase-summary.md) with new modules
6. Document architecture changes in [`system-architecture.md`](./system-architecture.md)
7. Add tests

---

## Architecture at a Glance

```
Telegram Update
    ↓
Handler (15 modules)
    ├─ Permission check
    ├─ Input validation
    └─ Call service
        ↓
Service (11 modules)
    ├─ Business logic
    └─ Database access
        ↓
Database (PostgreSQL)
    ├─ 10 models
    ├─ Async pool
    └─ Migrations
        ↓
Response to Telegram
```

**Async throughout** - no blocking calls.

See [`system-architecture.md`](./system-architecture.md) § High-Level Architecture for full diagram.

---

## Key Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Telegram | python-telegram-bot | 21.0+ |
| Database | PostgreSQL | 12+ |
| ORM | SQLAlchemy | 2.0+ |
| Async Driver | asyncpg | 0.29+ |
| Scheduler | APScheduler | 3.10+ |
| Process Manager | PM2 | Latest |
| Migrations | Alembic | 1.13+ |
| Reports | openpyxl, reportlab | Latest |

---

## Code Quality Checklist

Before committing code, verify:
- [ ] Type hints on all function signatures
- [ ] Docstrings with Args, Returns, Raises
- [ ] All I/O operations are async
- [ ] Error handling with specific exceptions
- [ ] No hardcoded values (use constants)
- [ ] Input validation with user-friendly messages
- [ ] Permission checks for sensitive ops
- [ ] No blocking calls in handlers
- [ ] Tests for new functionality
- [ ] Database migrations for schema changes

See [`code-standards.md`](./code-standards.md) § Code Review Checklist for details.

---

## Common Patterns

### Creating a Task
Handler → TaskService.create_task() → Insert + generate P-ID → Return

### Setting a Reminder
Handler → ReminderService.create_reminder() → Insert → Scheduler polls every 30s → Send notification

### Soft Delete
Handler → TaskService.soft_delete_task() → Mark is_deleted=true → User can undo for 30s

### Multi-Step Wizard
ConversationHandler with states → STATE_1 → STATE_2 → STATE_3 → Confirm → Save

### Inline Buttons
Handler creates keyboard → User clicks button → CallbackQueryHandler processes → Update message

See [`code-standards.md`](./code-standards.md) § Handler Patterns for implementation details.

---

## Database Models

10 Core Entities:
1. **User** - Telegram user profile & preferences
2. **Group** - Telegram group for shared tasks
3. **GroupMember** - Group membership with roles
4. **Task** - Core task entity (status, deadline, progress)
5. **Reminder** - Task notifications
6. **TaskHistory** - Audit trail
7. **RecurringTemplate** - Recurring task patterns
8. **UserStatistics** - Weekly/monthly metrics
9. **DeletedTaskUndo** - Soft delete recovery
10. **BotConfig** - Runtime configuration

See [`codebase-summary.md`](./codebase-summary.md) § Database Schema Overview for relationships.

---

## Performance Targets

- **Response time**: 100-500ms
- **Task creation**: <2s
- **Database query**: <500ms (p95)
- **Report generation**: <5s
- **Memory usage**: <200MB
- **CPU usage**: <30% sustained
- **Concurrent users**: ~100
- **Uptime target**: 99.9%

See [`system-architecture.md`](./system-architecture.md) § Performance Characteristics.

---

## Getting Help

1. **Understanding code**: Check [`codebase-summary.md`](./codebase-summary.md)
2. **Writing code**: Check [`code-standards.md`](./code-standards.md)
3. **How features work**: Check [`system-architecture.md`](./system-architecture.md) § Data Flow Examples
4. **Feature requirements**: Check [`project-overview-pdr.md`](./project-overview-pdr.md)
5. **Quick setup**: Check [`../README.md`](../README.md)
6. **Troubleshooting**: Check [`../README.md`](../README.md) § Troubleshooting

---

## Document Maintenance

Documentation should be updated when:
- New commands added
- New database models created
- Architecture changes
- Code standards evolve
- Deployment procedure changes

**Who**: Any team member
**When**: Same time as code changes
**How**: Edit relevant `.md` files and commit with code

---

## Version History

| Date | Changes |
|------|---------|
| 2024-12-18 | Initial documentation created (4 docs + README) |

---

**Status**: Production Ready
**Last Updated**: 2024-12-18
**Total Lines**: 2400+ across 5 files
**Audience**: Developers, Maintainers, New Team Members
