# TeleTask Bot - Code Standards & Guidelines

## 1. File & Directory Naming

### Python Files
- **Kebab-case for filenames**: `task_wizard.py`, `reminder_service.py`, `health_check.py`
- **Descriptive names**: Clearly indicate module purpose
- **No abbreviated names**: Use `task_service.py` not `ts.py`

### Module Organization
```
handlers/
  ├── task_create.py      # Single command/feature
  ├── task_wizard.py      # Multi-step flow for same command
  ├── callbacks.py        # All inline button handlers
  └── __init__.py         # Handler registration

services/
  ├── task_service.py     # One entity CRUD
  ├── notification.py     # Cross-cutting service
  └── __init__.py         # Service exports
```

### Database Files
- `models.py`: All SQLAlchemy models (not split by entity)
- `connection.py`: Pool, session factory, lifecycle management
- `migrations/versions/`: Timestamp + description (e.g., `20251218_0009_task_id_sequence.py`)

## 2. Code Style & Formatting

### Python Version
- **Target**: Python 3.11+
- **Type hints**: Required for all function signatures
- **Async/await**: Required for all I/O operations (no blocking calls)

### Code Structure
```python
"""Module docstring describing purpose."""

import asyncio  # Standard library first
import logging

from datetime import datetime  # Standard library grouped
from typing import Optional, List

from sqlalchemy import select  # Third-party imports
from telegram import Update

from database import get_db  # Local imports last
from services.task_service import TaskService
from utils.formatters import format_task
```

### Naming Conventions
```python
# Constants: UPPER_SNAKE_CASE
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
MAX_TASK_TITLE_LENGTH = 500
REMINDER_TYPES = ["before_deadline", "after_deadline", "custom"]

# Functions/Methods: snake_case
async def create_task(user_id: int, content: str) -> Task:
    pass

# Classes: PascalCase
class TaskService:
    pass

# Private: _leading_underscore
_internal_helper = ...

# Variables: snake_case
user_tasks = []
current_user_id = 123
```

### Async/Await Pattern
```python
# CORRECT: Mark all async operations
async def get_user_tasks(user_id: int) -> List[Task]:
    async with db.session() as session:
        result = await session.execute(select(...))
        return result.scalars().all()

# WRONG: No async without I/O
def get_user_tasks(user_id: int):  # Not async!
    pass

# WRONG: Blocking I/O in async function
async def process_task(task_id: int):
    time.sleep(1)  # Blocks event loop!
    pass
```

### Type Hints
```python
# REQUIRED for function signatures
async def update_task(
    task_id: int,
    status: str,
    progress: int = 0,
) -> Optional[Task]:
    """Update task status and progress.

    Args:
        task_id: ID of task to update
        status: New status (pending/in_progress/completed)
        progress: Progress percentage (0-100)

    Returns:
        Updated Task object or None if not found

    Raises:
        ValueError: If status not valid
    """
    pass

# Type hints for complex types
from typing import Dict, List, Optional, Union

tasks: List[Task] = []
task_map: Dict[int, Task] = {}
user_or_group: Union[User, Group] = ...
config: Optional[Dict[str, str]] = None
```

### Docstrings
- Use Google-style docstrings
- Always include: description, Args, Returns, Raises
- For classes: brief description at top, explain key methods

```python
class TaskService:
    """Service for task CRUD operations.

    Handles task creation, retrieval, updates with P-ID/G-ID system.
    All operations are async and require database session.
    """

    async def create_task(
        self,
        user_id: int,
        content: str,
        deadline: Optional[datetime] = None,
    ) -> Task:
        """Create a personal task.

        Args:
            user_id: ID of task creator
            content: Task title/description
            deadline: Optional deadline datetime

        Returns:
            Created Task with generated public_id (P-XXXX)

        Raises:
            ValueError: If content is empty
            DatabaseError: If database insert fails
        """
        pass
```

## 3. Handler Patterns

### Single Command Handler
```python
from telegram import Update
from telegram.ext import ContextTypes

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /xemviec command to list user's tasks."""
    user_id = update.effective_user.id

    try:
        tasks = await TaskService.get_user_tasks(user_id)
        message = format_task_list(tasks)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error viewing tasks for {user_id}: {e}")
        await update.message.reply_text("Lỗi khi lấy danh sách việc.")
```

### Multi-Step Conversation Handler (Task Wizard)
```python
from telegram.ext import ConversationHandler

# Define conversation states
class TaskWizardState:
    TITLE = 1
    DESCRIPTION = 2
    DEADLINE = 3
    CONFIRM = 4

async def task_wizard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start task creation wizard."""
    await update.message.reply_text("Nhập tiêu đề việc:")
    return TaskWizardState.TITLE

async def task_wizard_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle title input."""
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Nhập mô tả (hoặc 'bỏ qua'):")
    return TaskWizardState.DESCRIPTION

# ... more state handlers ...

# Register in handlers/__init__.py
ConversationHandler(
    entry_points=[CommandHandler("taoviec", task_wizard_start)],
    states={
        TaskWizardState.TITLE: [MessageHandler(filters.TEXT, task_wizard_title)],
        TaskWizardState.DESCRIPTION: [MessageHandler(filters.TEXT, task_wizard_desc)],
        # ...
    },
    fallbacks=[CommandHandler("cancel", task_wizard_cancel)],
)
```

### Inline Button Callbacks
```python
async def button_callback_update_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle status update button click."""
    query = update.callback_query
    data = query.data  # e.g., "update_task_123_completed"

    parts = data.split("_")
    task_id = int(parts[2])
    new_status = parts[3]

    try:
        await TaskService.update_task(task_id, status=new_status)
        await query.answer("Cập nhật thành công")
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {e}")
        await query.answer("Lỗi cập nhật", show_alert=True)
```

### Permission Checking Pattern
```python
async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a task (must be creator)."""
    user_id = update.effective_user.id
    task_id = context.args[0] if context.args else None

    if not task_id:
        await update.message.reply_text("Vui lòng cung cấp ID việc")
        return

    try:
        task = await TaskService.get_task(task_id)

        # Permission check
        if task.creator_id != user_id:
            await update.message.reply_text("Bạn không có quyền xóa việc này")
            return

        await TaskService.soft_delete_task(task_id)
        await update.message.reply_text(f"Đã xóa việc {task.public_id}")
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        await update.message.reply_text("Lỗi khi xóa việc")
```

## 4. Service Layer Patterns

### Database CRUD Pattern
```python
from database import get_db
from database.models import Task

class TaskService:
    """Task business logic."""

    @staticmethod
    async def create_task(
        user_id: int,
        content: str,
        deadline: Optional[datetime] = None,
        group_id: Optional[int] = None,
    ) -> Task:
        """Create task with proper ID generation."""
        db = get_db()
        async with db.session() as session:
            task = Task(
                creator_id=user_id,
                content=content,
                deadline=deadline,
                group_id=group_id,
                is_personal=group_id is None,
            )
            session.add(task)
            await session.flush()  # Get auto-increment ID

            # Generate public ID based on task type
            if group_id:
                task.public_id = f"G-{task.id:04d}"
            else:
                task.public_id = f"P-{task.id:04d}"

            await session.commit()
            return task

    @staticmethod
    async def get_task(task_id: int) -> Optional[Task]:
        """Fetch task by ID."""
        db = get_db()
        async with db.session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_task(
        task_id: int,
        **kwargs
    ) -> Optional[Task]:
        """Update task fields (only provided kwargs)."""
        db = get_db()
        async with db.session() as session:
            stmt = select(Task).where(Task.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                await session.commit()

            return task
```

### Notification Service Pattern
```python
class NotificationService:
    """Format and send messages to users."""

    @staticmethod
    def format_task_summary(task: Task) -> str:
        """Format task for display."""
        deadline_str = ""
        if task.deadline:
            deadline_str = f"\nHạn: {format_datetime(task.deadline)}"

        return f"""
📋 {task.public_id}: {task.content}
Trạng thái: {format_status(task.status)}
Ưu tiên: {format_priority(task.priority)}
Tiến độ: {task.progress}%{deadline_str}
        """.strip()

    @staticmethod
    async def send_notification(
        bot,
        user_id: int,
        message: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send message to user safely."""
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to notify user {user_id}: {e}")
            return False
```

## 5. Database Access Patterns

### Session Management
```python
from database import get_db

async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Use session from db singleton."""
    db = get_db()

    # CORRECT: Use context manager
    async with db.session() as session:
        result = await session.execute(select(User).where(...))
        users = result.scalars().all()
        # Session auto-closed here

    # WRONG: Session not properly closed
    session = db.session()
    result = await session.execute(...)
    # Connection leaked!
```

### Query Patterns
```python
from sqlalchemy import select, and_, or_

# Get single item
async with db.session() as session:
    result = await session.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

# Get multiple items
async with db.session() as session:
    result = await session.execute(
        select(Task)
        .where(
            and_(
                Task.creator_id == user_id,
                Task.is_deleted == False,
                Task.status != "completed",
            )
        )
        .order_by(Task.deadline.asc())
        .limit(10)
    )
    tasks = result.scalars().all()

# Aggregate queries
async with db.session() as session:
    result = await session.execute(
        select(func.count(Task.id))
        .where(Task.status == "completed")
    )
    completed_count = result.scalar()
```

### Transaction Pattern
```python
async def complex_operation(task_id: int):
    """Operation with rollback on error."""
    db = get_db()

    try:
        async with db.session() as session:
            task = await session.get(Task, task_id)
            task.status = "completed"

            # Log change
            history = TaskHistory(
                task_id=task_id,
                action="completed",
                user_id=user_id,
            )
            session.add(history)

            await session.commit()
    except Exception as e:
        logger.error(f"Complex operation failed: {e}")
        # Transaction auto-rolled back
        raise
```

## 6. Error Handling Guidelines

### Handler-Level Error Handling
```python
async def safe_task_operation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handler with proper error handling."""
    try:
        user_id = update.effective_user.id
        task_id = int(context.args[0]) if context.args else None

        if not task_id:
            await update.message.reply_text(
                "❌ Vui lòng cung cấp ID việc\nCú pháp: /cmd <task_id>"
            )
            return

        task = await TaskService.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Không tìm thấy việc {task_id}")
            return

        # Permission check
        if task.creator_id != user_id and task.assignee_id != user_id:
            await update.message.reply_text("❌ Bạn không có quyền truy cập việc này")
            return

        # Main logic
        result = await TaskService.update_task(task_id, status="completed")
        await update.message.reply_text(f"✅ Cập nhật thành công: {result.public_id}")

    except ValueError as e:
        logger.warning(f"Invalid input from {update.effective_user.id}: {e}")
        await update.message.reply_text(f"❌ Dữ liệu không hợp lệ: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in task operation: {e}", exc_info=True)
        await update.message.reply_text("❌ Lỗi hệ thống, vui lòng thử lại sau")
```

### Service-Level Error Handling
```python
class TaskService:
    """Services raise specific exceptions."""

    @staticmethod
    async def update_task_status(task_id: int, status: str) -> Task:
        """Update task status with validation."""
        valid_statuses = ["pending", "in_progress", "completed"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")

        db = get_db()
        async with db.session() as session:
            task = await session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = status
            if status == "completed":
                task.completed_at = datetime.now(timezone.utc)

            await session.commit()
            return task
```

## 7. Security Considerations

### Input Validation
```python
from utils.validators import validate_task_title, validate_deadline

async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate all inputs before processing."""
    title = update.message.text.strip()

    # Validate length
    if not title or len(title) > 500:
        await update.message.reply_text("❌ Tiêu đề phải từ 1-500 ký tự")
        return

    # Sanitize for display
    safe_title = html.escape(title)  # Prevent XSS-like issues

    # Create task
    task = await TaskService.create_task(
        user_id=update.effective_user.id,
        content=safe_title,
    )
```

### Permission Checking
```python
async def delete_group_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Only group admins can delete group tasks."""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    task_id = int(context.args[0])

    # Check if user is group admin
    is_admin = await GroupService.is_admin(group_id, user_id)
    if not is_admin:
        await update.message.reply_text("❌ Chỉ admin nhóm mới có quyền xóa")
        return

    task = await TaskService.get_task(task_id)
    if task.group_id != group_id:
        await update.message.reply_text("❌ Việc này không thuộc nhóm")
        return

    # Safe to delete
    await TaskService.soft_delete_task(task_id, user_id)
```

### Logging & Sensitive Data
```python
logger = logging.getLogger(__name__)

# GOOD: Log important events without sensitive data
logger.info(f"Task created: {task.public_id} by user {user_id}")

# WRONG: Logging token/password
logger.debug(f"API token: {bot_token}")  # NEVER!

# GOOD: Log API response without credentials
logger.debug(f"Google Calendar sync response: status={status_code}")

# WRONG: Logging full response with auth header
logger.debug(f"Response: {response}")  # May contain token!
```

## 8. Testing Standards

### Unit Test Pattern
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_create_task_success():
    """Test task creation with valid input."""
    user_id = 123
    content = "Test task"

    task = await TaskService.create_task(user_id, content)

    assert task.creator_id == user_id
    assert task.content == content
    assert task.public_id.startswith("P-")
    assert task.status == "pending"

@pytest.mark.asyncio
async def test_create_task_empty_content():
    """Test task creation with empty content."""
    with pytest.raises(ValueError):
        await TaskService.create_task(123, "")
```

### Integration Test Pattern
```python
@pytest.mark.asyncio
async def test_view_tasks_handler(update_mock):
    """Test /xemviec command with database."""
    # Setup
    user = await create_test_user(123)
    task = await TaskService.create_task(123, "Test")

    # Execute
    await view_tasks(update_mock, context_mock)

    # Assert
    sent_message = update_mock.message.reply_text.call_args[0][0]
    assert task.public_id in sent_message
```

## 9. Comment Guidelines

### When to Comment
```python
# GOOD: Explain WHY, not WHAT
# We use soft delete to allow 30-second undo window
task.is_deleted = True
task.deleted_at = datetime.now()

# WRONG: Obvious comments
# Set is_deleted to True
task.is_deleted = True

# GOOD: Explain non-obvious algorithm
# Sort by deadline, then by priority (high=1, low=4)
# This ensures overdue tasks with high priority appear first
sorted_tasks = sorted(tasks, key=lambda t: (t.deadline, -PRIORITY_RANK[t.priority]))

# GOOD: Explain business rules
# If deadline is within 24 hours, set reminder to 1 hour before
# Otherwise, set to 24 hours before
reminder_offset = "1h" if hours_until_deadline <= 24 else "24h"
```

## 10. Code Review Checklist

- [ ] Type hints on all function signatures
- [ ] Docstrings with Args, Returns, Raises
- [ ] All I/O operations are async
- [ ] Error handling with specific exceptions
- [ ] No blocking operations in handlers
- [ ] Permission checks for sensitive operations
- [ ] Input validation with user-friendly messages
- [ ] No hardcoded values (use settings/constants)
- [ ] Proper resource cleanup (sessions, connections)
- [ ] Logging at appropriate levels
- [ ] Tests for new functionality
- [ ] Database migrations for schema changes

## 11. Vietnamese Language Standards

### Message Format
```python
# GOOD: Vietnamese with proper formatting
message = """
✅ Cập nhật thành công

📋 Việc: {task.public_id}
Tiêu đề: {task.content}
Trạng thái: {format_status(task.status)}
Hạn: {format_datetime(task.deadline)}
"""

# Emoji conventions:
# ✅ Success, ❌ Error, ℹ️ Info, ⚠️ Warning
# 📋 Task, 👤 User, 👥 Group, 📅 Calendar
# ⏰ Reminder, 📊 Statistics, 🔔 Notification
```

### Error Messages
```python
# GOOD: Clear, actionable Vietnamese
await update.message.reply_text(
    "❌ Hạn phải là ngày trong tương lai\nVí dụ: ngày mai, 25/12, 14:00"
)

# WRONG: Vague, English technical terms
await update.message.reply_text("Invalid deadline format")
```

---

**Last Updated**: 2024-12-18
**Status**: ACTIVE
**Enforced**: Code Review & CI/CD
