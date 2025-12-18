# TeleTask Project Roadmap

## Current Version: v1.2.0

### Completed Features (v1.0 - v1.2)
- [x] Task creation wizard with Vietnamese NLP time parsing
- [x] Group task assignment (G-ID/P-ID system)
- [x] Bulk delete with undo functionality
- [x] Recurring tasks (daily, weekly, monthly)
- [x] Google Calendar integration with OAuth 2.0
- [x] Notification preferences (task assigned, status, reminders)
- [x] Reminder settings (24h, 1h, 30m, 5m, overdue)
- [x] Export reports (PDF, Excel, CSV)
- [x] Statistics dashboard (weekly, monthly)
- [x] BotPanel CLI for bot management
- [x] Automated installation script
- [x] Dynamic website bot name

### Security Fixes (v1.2.0)
- [x] Fixed password exposure in logs
- [x] Changed OAuth binding from 0.0.0.0 to 127.0.0.1 (localhost only)
- [x] Added PBKDF2-SHA256 with salt for report PDF passwords (100,000 iterations)
- [x] Implemented input validation for callback data
- [x] Fixed race condition in countdown timers
- [x] Improved error logging without exposing sensitive data

---

## Phase 1: Core Improvements (v1.3)

### Task Management
- [ ] Task priority levels with visual indicators
- [ ] Task categories/tags for organization
- [ ] Task dependencies (blocked by/blocks)
- [ ] Subtasks support

### User Experience
- [ ] Inline keyboard for quick task updates
- [ ] Task search with filters (date range, status, priority)
- [ ] Customizable reminder intervals per task
- [ ] Task history/activity log

---

## Phase 2: Team Features (v1.4)

### Collaboration
- [ ] Team/workspace creation
- [ ] Role-based permissions (admin, member, viewer)
- [ ] Team task dashboard
- [ ] @mention notifications in groups

### Communication
- [ ] Task comments/notes
- [ ] Task attachments (files, images)
- [ ] Daily/weekly digest notifications

---

## Phase 3: Admin & Monitoring (v1.5)

### Admin Dashboard
- [ ] Web-based admin panel
- [ ] Multi-bot management interface
- [ ] User analytics and engagement metrics
- [ ] Bot health monitoring

### Infrastructure
- [ ] Prometheus metrics integration
- [ ] Grafana dashboards
- [ ] Automated backup verification
- [ ] Log aggregation and alerting

---

## Phase 4: Integrations (v1.6)

### External Services
- [ ] Webhook support for external triggers
- [ ] REST API for third-party integrations
- [ ] Slack/Discord integration
- [ ] Trello/Jira sync

### Automation
- [ ] Zapier/Make integration
- [ ] Custom automation rules (if-this-then-that)
- [ ] Scheduled reports via email

---

## Phase 5: Enterprise Features (v2.0)

### Multi-tenancy
- [ ] Organization-level bot instances
- [ ] Custom branding per organization
- [ ] SSO integration (Google Workspace, Microsoft)

### Advanced Analytics
- [ ] Productivity reports
- [ ] Team performance metrics
- [ ] Goal tracking and OKRs

### Security
- [ ] Audit logging
- [ ] Data encryption at rest
- [ ] GDPR compliance tools

---

## Technical Debt & Improvements

### Performance
- [ ] Redis caching for frequent queries
- [ ] Database query optimization
- [ ] Connection pooling improvements

### Code Quality
- [ ] Unit test coverage (target: 80%)
- [ ] Integration tests for handlers
- [ ] API documentation (OpenAPI/Swagger)

### DevOps
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests

---

## Contributing

Feature requests and bug reports: [GitHub Issues](https://github.com/haduyson/teletask/issues)

---

*Last updated: December 17, 2025*
