# Task Group Isolation & Notification Enhancements

## Overview
Enhance task visibility and notifications to properly isolate tasks by group context and improve notification delivery.

## Requirements Summary
1. `/xemviec` in group → show only tasks related to that group
2. `/xemviec` in private → show all tasks from all groups
3. `/giaoviec` → send private messages to both assigner and assignee
4. Statistics → group-specific in groups, all in private
5. Fix error handling when task created but reminder fails

## Phases

| Phase | Description | Status | Link |
|-------|-------------|--------|------|
| 1 | xemviec Group Isolation | pending | [phase-01](./phase-01-xemviec-isolation.md) |
| 2 | giaoviec Private Notifications | pending | [phase-02](./phase-02-giaoviec-notifications.md) |
| 3 | Statistics Group Isolation | pending | [phase-03](./phase-03-stats-isolation.md) |
| 4 | Error Handling Fix | pending | [phase-04](./phase-04-error-handling.md) |

## Key Files
- `handlers/task_view.py` - /xemviec command
- `handlers/task_assign.py` - /giaoviec command
- `handlers/statistics.py` - Statistics commands
- `services/task_service.py` - Task queries

## Architecture Decision
- Add `group_id` filter to task queries
- Store `source_group_id` on tasks for filtering
- Use try/except blocks for non-critical operations (reminders)
