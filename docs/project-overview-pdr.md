# TeleTask Bot - Project Overview & Product Development Requirements

## 1. Project Summary

**TeleTask Bot** is a Vietnamese-language task management Telegram bot designed for individuals and groups to collaborate on task tracking, reminders, and progress reporting. The bot enables users to create, assign, track, and analyze tasks with advanced features like recurring tasks, calendar integration, and automated reports.

**GitHub Repository**: [TeleTask Bot](https://github.com/your-org/teletask-bot)

**Deployment**: Python 3.11 + PostgreSQL + Telegram Bot API

## 2. Target Users & Use Cases

### Primary Users
- **Individual Task Managers**: Vietnamese-speaking users who need personal task tracking
- **Team Leads**: Groups using Telegram for communication who need shared task management
- **Project Teams**: Collaborative groups managing project deliverables

### Key Use Cases
1. **Personal Task Management**: Create, track, and complete individual tasks
2. **Group Collaboration**: Assign tasks to team members with deadline tracking
3. **Progress Reporting**: Auto-generated weekly/monthly statistics (CSV/XLSX/PDF)
4. **Calendar Sync**: Sync completed tasks to Google Calendar
5. **Smart Reminders**: Automatic notifications before/after deadlines
6. **Recurring Tasks**: Create repeating tasks (daily, weekly, monthly patterns)

## 3. Product Goals

- Enable efficient task management directly within Telegram (no context-switching)
- Support both individual and group task workflows
- Provide intelligent reminders and deadline alerts
- Generate actionable statistics and reports
- Integrate with Google Calendar for calendar-aware task management
- Maintain data integrity with audit trails and undo functionality
- Support Vietnamese language and timezone preferences

## 4. Feature Overview

### Core Features
- **Task Creation** (`/taoviec`): Multi-step wizard for task details
- **Task Viewing** (`/xemviec`): List personal/group tasks with filters
- **Task Assignment** (`/giaoviec`): Assign group tasks to team members
- **Status Updates** (`/xong`, `/danglam`, `/tiendo`): Update task progress
- **Task Deletion** (`/xoa`): Soft delete with 30-second undo window

### Advanced Features
- **Reminders** (`/nhacviec`): Set custom, before-deadline, after-deadline alerts
- **Recurring Tasks** (`/vieclaplai`): Automated task generation patterns
- **Statistics** (`/thongke`): Weekly/monthly metrics with export
- **Google Calendar** (`/lichgoogle`): OAuth 2.0 sync of completed tasks
- **Settings** (`/caidat`): Timezone, language, notification preferences

### Administrative Features
- **Health Monitoring**: HTTP health check endpoint (port 8080)
- **Resource Monitoring**: CPU, memory, database connection tracking
- **Error Alerts**: Admin notifications for bot crashes
- **Metrics Collection**: Optional Prometheus metrics export

## 5. Technical Requirements

### Technology Stack
- **Language**: Python 3.11+
- **Telegram Framework**: python-telegram-bot 21.0+
- **Database**: PostgreSQL with async driver (asyncpg)
- **ORM**: SQLAlchemy 2.0
- **Scheduling**: APScheduler 3.10+
- **Process Manager**: PM2
- **Optional**:
  - Google Calendar API for calendar integration
  - Prometheus for metrics
  - Redis for caching

### Database Models (10 core entities)
1. **User**: Telegram users with timezone/notification prefs
2. **Group**: Telegram groups for shared task management
3. **GroupMember**: Group membership with roles (admin/member)
4. **Task**: Main entity (status: pending/in_progress/completed)
5. **Reminder**: Task notifications (before/after deadline/custom)
6. **TaskHistory**: Audit trail of all task changes
7. **RecurringTemplate**: Templates for recurring tasks
8. **UserStatistics**: Weekly/monthly task metrics
9. **DeletedTaskUndo**: Soft delete recovery (30s window)
10. **BotConfig**: Runtime configuration

### Public ID System
- **P-XXXX**: Personal task IDs (P-0001, P-0042, etc.)
- **G-XXXX**: Group task IDs (G-0001, G-0500, etc.)

## 6. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Telegram Users/Groups                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           TeleTask Bot (bot.py - Entry Point)            │
│  ┌──────────────┬──────────────┬──────────────────────┐ │
│  │  Config/     │  Handlers    │  Services            │ │
│  │  Settings    │  (15 modules)│  (11 modules)        │ │
│  └──────────────┴──────────────┴──────────────────────┘ │
│  ┌──────────────┬──────────────┬──────────────────────┐ │
│  │  Database    │  Scheduler   │  Monitoring          │ │
│  │  (Models,    │  (APScheduler)  (Health/Alert)    │ │
│  │  Connection) │              │                      │ │
│  └──────────────┴──────────────┴──────────────────────┘ │
└────────────┬─────────────────────────────────────────────┘
             │
   ┌─────────┼──────────┬──────────────┐
   ▼         ▼          ▼              ▼
┌────────┐┌──────────┐┌────────┐┌──────────────┐
│PostSQL ││Google    ││Health  ││Prometheus   │
│Database││Calendar  ││Check   ││Metrics      │
│        ││API       ││Server  ││(optional)   │
└────────┘└──────────┘└────────┘└──────────────┘
```

## 7. Key Design Patterns

### Handler Pattern
- ConversationHandler for multi-step wizards (task creation, assignment)
- CommandHandler for single-command operations
- CallbackQueryHandler for inline button interactions
- Context-based state management for wizard flows

### Service Layer
- Business logic separation from handlers
- Database abstraction (TaskService, ReminderService, etc.)
- Reusable notification logic (NotificationService)

### Database Access
- SQLAlchemy ORM with async queries (SQLAlchemy 2.0)
- Indexed queries for performance (status, deadline, assignee)
- Connection pooling (min: 2, max: 10 by default)
- Migration management (Alembic with 9+ versions)

### Soft Delete Pattern
- Tasks marked deleted with 30-second undo window
- DeletedTaskUndo table tracks deletion metadata
- Deleted tasks excluded from normal queries

## 8. Data Flow Examples

### Creating a Task (Personal)
```
User: /taoviec
 └─> TaskWizard (ConversationHandler)
      ├─> task_create.py (handler registration)
      ├─> TaskService.create_task() (database insert)
      ├─> Public ID generation (P-XXXX)
      └─> User notification
```

### Reminder Trigger
```
APScheduler (reminder_scheduler.py)
 └─> ReminderService.process_pending_reminders()
      ├─> Query overdue reminders
      ├─> NotificationService.send_reminder()
      ├─> Mark reminder as sent
      └─> Log to TaskHistory
```

### Report Generation
```
User: /export or APScheduler (weekly/monthly)
 └─> StatisticsService.calculate_stats()
      ├─> ReportService.generate_report()
      │    ├─> CSV export
      │    ├─> XLSX with charts (matplotlib)
      │    └─> PDF with reportlab
      └─> Telegram file upload
```

## 9. Success Metrics

### Functional Metrics
- All commands execute without errors (target: 99.9% uptime)
- Task creation < 2 seconds (UX critical)
- Reminders deliver within 1 minute of scheduled time
- Reports generate within 5 seconds
- Database queries < 500ms (p95)

### User Adoption Metrics
- Active users per week (target: 50+ in pilot)
- Task creation rate (target: 5+ tasks/user/week)
- Feature usage (reminder adoption, recurring task usage)
- User retention (target: 80% weekly retention)

### System Metrics
- Error rate < 0.1% of all updates
- Bot CPU usage < 30% (sustained)
- Memory usage < 200MB
- Database connections < 8 (of 10 max)

## 10. Non-Functional Requirements

### Performance
- Response time to user input: < 3 seconds
- Batch operations (reports, reminders): < 10 seconds
- Database query optimization with proper indexing
- Connection pooling for concurrent requests

### Reliability
- Automatic reconnection on database loss
- Error handling for Telegram API failures
- Graceful degradation (monitoring optional)
- Logging at DEBUG/INFO/WARNING/ERROR levels

### Security
- No sensitive data in logs (API keys, tokens)
- OAuth 2.0 for Google Calendar integration
- User data isolation (no cross-user data leaks)
- Admin command access control

### Scalability
- Support for 100+ concurrent users
- Async/await throughout for non-blocking I/O
- Connection pooling (2-10 connections)
- Optional Redis caching for frequently accessed data

### Maintainability
- Modular code structure (handlers, services, utils)
- Comprehensive database migrations (9 versions tracked)
- Clear error messages for debugging
- Vietnamese language support throughout

## 11. Constraints & Dependencies

### External Dependencies
- Telegram Bot API (https://core.telegram.org/bots)
- Google Calendar API (if calendar enabled)
- PostgreSQL 12+ (tested with async driver)

### Environmental Constraints
- Python 3.11 runtime required
- 512MB minimum RAM
- 1GB disk space minimum
- Network connectivity required

### Operational Constraints
- Single bot instance per token
- PM2 process management required for production
- Database backups required (daily recommended)

## 12. Roadmap & Future Phases

### Phase 1 (Current)
- Core task management (create, view, update, delete)
- Personal + group task support
- Basic reminder system
- Statistics & export

### Phase 2 (Planned)
- Calendar sync (Google Calendar)
- Recurring task templates
- Advanced filtering & search
- Webhook callbacks for task changes

### Phase 3 (Future)
- Mobile app (native iOS/Android)
- Team workspace management
- Integration with other tools (Jira, Asana)
- AI-powered task suggestions

## 13. Document Version History

| Version | Date       | Author      | Changes                           |
|---------|------------|-------------|-----------------------------------|
| 1.0     | 2024-12-18 | Docs-Manager| Initial project overview & PDR     |

---

**Last Updated**: 2024-12-18
**Status**: ACTIVE
**Owner**: Development Team
