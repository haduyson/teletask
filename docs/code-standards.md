# TeleTask Code Standards & Guidelines

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Target Audience:** Developers contributing to TeleTask

---

## 1. Coding Standards Overview

TeleTask follows Python PEP 8 standards with some project-specific conventions. All new code must adhere to these standards before merging to main branch.

---

## 2. Naming Conventions

### 2.1 Files & Directories

```
snake_case.py           # Good: task_service.py
snakecase.py            # Bad:  taskservice.py
TaskService.py          # Bad:  PascalCase for files
```

**Rules:**
- All Python files: lowercase with underscores
- Max 30 characters for filename
- Descriptive names reflecting module purpose

**Examples:**
```
✓ task_service.py
✓ google_calendar_integration.py
✓ notification_handlers.py
✗ ts.py (too abbreviated)
✗ TaskService.py (should be snake_case)
```

### 2.2 Classes

```python
class TaskService:           # Good
class UserProfile:           # Good
class PdfReportGenerator:    # Good
class task_service:          # Bad - should be PascalCase
class TASKSERVICE:           # Bad - should be PascalCase
```

**Rules:**
- PascalCase (CapWords)
- Nouns describing what they represent
- Avoid abbreviations
- Abstract base classes prefix with `Base`

**Examples:**
```python
✓ class TaskService:
✓ class GoogleCalendarIntegration:
✓ class BaseNotificationHandler:
✗ class task_service:
✗ class TS:
```

### 2.3 Functions & Methods

```python
def create_task(user_id, content):      # Good
def get_user_tasks(user_id):            # Good
def send_notification(user_id, msg):    # Good
def CreateTask(user_id, content):       # Bad - should be snake_case
def create_task_content_for_user():     # Bad - too generic
```

**Rules:**
- snake_case with lowercase
- Verb-noun pattern preferred
- First word describes action (create, get, send, update, delete)
- Max 40 characters
- Avoid generic names (do_something, process_data)

**Common Patterns:**
```python
# Fetch/Read operations
get_user_by_id()
fetch_all_tasks()
query_overdue_tasks()
list_group_members()

# Create/Write operations
create_task()
save_user_settings()
insert_reminder()

# Update operations
update_task_status()
modify_user_timezone()

# Delete/Remove operations
delete_task()
remove_user_from_group()

# Check/Validate operations
is_valid_email()
has_permission()
can_delete_task()
validate_input()

# Boolean returns use is_, has_, can_
is_task_overdue()
has_reminder()
can_edit()
```

### 2.4 Constants

```python
MAX_RETRY_COUNT = 3
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
TASK_ID_PREFIX = "P-"
EMAIL_REGEX_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# Bad - should be UPPER_CASE
max_retry_count = 3
MaxRetryCount = 3
```

**Rules:**
- ALL_CAPS with underscores
- Define at module level
- Group related constants together
- Add comments for complex values

**Exceptions:**
- Database configuration constants (OK to be lowercase)
- URL patterns (lowercase with hyphens OK)

### 2.5 Variables

```python
user_id = 12345                # Good
task_content = "Buy milk"      # Good
reminder_time = datetime.now() # Good
userId = 12345                 # Bad - should be snake_case
user_i_d = 12345              # Bad - should be user_id
tmp = 123                      # Bad - too abbreviated
```

**Rules:**
- snake_case with lowercase
- Descriptive names (3-30 characters usually)
- Avoid single letter variables (except loop indices: i, j, k)
- Avoid abbreviations unless very common (id, url, etc)

**Loop Variables (Exception):**
```python
for i in range(10):          # OK for simple loops
for item in items:           # Better if meaningful
for user in users:           # Better than 'u'
```

### 2.6 Private/Protected Members

```python
class TaskService:
    _database = None          # Protected (single underscore)
    __private_key = None      # Private (double underscore)

    def _validate_input(self):    # Protected method
        pass

    def __process_internal(self):  # Private method
        pass
```

**Rules:**
- Protected: single underscore prefix `_`
- Private: double underscore prefix `__` (name mangling)
- Document why members are private

---

## 3. File Structure & Organization

### 3.1 Module Header

Every Python file should start with:

```python
"""
Brief module description explaining purpose.

This module handles task creation and management through Telegram bot commands.
It provides the wizard-based interface for creating tasks with various options.

Author: Developer Name
Created: YYYY-MM-DD
Modified: YYYY-MM-DD
"""

# Standard library imports
from datetime import datetime
from typing import Optional, List, Dict
import logging

# Third-party imports
from sqlalchemy import Column, String
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Local imports
from database.models import Task, User
from services.task_service import TaskService
from utils.validators import validate_task_content

# Constants
MAX_TASK_CONTENT_LENGTH = 500
DEFAULT_TASK_PRIORITY = "NORMAL"

# Logger setup
logger = logging.getLogger(__name__)
```

### 3.2 Import Order

1. Python standard library (alphabetical)
2. Third-party packages (alphabetical)
3. Local imports (alphabetical)
4. Blank line between groups

```python
# Standard library
import asyncio
import logging
from datetime import datetime
from typing import Optional, List

# Third-party
from sqlalchemy import Column, String
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Local
from database.models import Task, User
from services.task_service import TaskService
```

### 3.3 Class Organization

```python
class TaskService:
    """
    Service for managing task operations.

    Handles CRUD operations for tasks, recurring tasks, and task-related
    notifications.
    """

    def __init__(self, db_session):
        """Initialize service with database session."""
        self.db = db_session
        self._cache = {}

    # Public methods (alphabetical by function)
    async def create_task(self, ...): pass
    async def delete_task(self, ...): pass
    async def get_task_by_id(self, ...): pass
    async def list_user_tasks(self, ...): pass
    async def update_task(self, ...): pass

    # Protected methods (with underscore prefix)
    async def _validate_task_content(self, ...): pass
    async def _calculate_deadline(self, ...): pass

    # Private methods (with double underscore)
    async def __process_recurring(self, ...): pass
```

---

## 4. Code Style & Formatting

### 4.1 Indentation

- **Use 4 spaces** (not tabs)
- No trailing whitespace
- Max line length: 100 characters

```python
# Good - 4 spaces
def create_task(user_id, content, deadline):
    if user_id and content:
        task = Task(
            user_id=user_id,
            content=content,
            deadline=deadline
        )
        return task
    return None

# Bad - 2 spaces
def create_task(user_id, content, deadline):
  if user_id and content:
    task = Task(...)
    return task

# Bad - tabs
def create_task(user_id, content, deadline):
→if user_id and content:  # Tab character
→→task = Task(...)
```

### 4.2 Line Length

Target: < 100 characters

```python
# Good - under 100 chars
notification_text = "Task completed: " + task.content

# OK - exactly at limit or using line continuation
notification_text = (
    "Task completed: " + task.content +
    "\nDeadline: " + str(task.deadline)
)

# Bad - over 100 chars
notification_text = "Task " + str(task.id) + " completed: " + task.content + " with deadline " + str(task.deadline) + " was successfully finished"
```

### 4.3 Blank Lines

```python
# 2 blank lines between top-level definitions
def function_one():
    pass


def function_two():
    pass


# 1 blank line between methods
class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
```

### 4.4 String Formatting

```python
# Good - f-strings (Python 3.6+)
name = "Alice"
message = f"Hello {name}"

# Good - for longer strings
message = (
    f"Task: {task.content}\n"
    f"Deadline: {task.deadline}\n"
    f"Status: {task.status}"
)

# OK - .format()
message = "Hello {}".format(name)

# Avoid - % formatting
message = "Hello %s" % name

# Avoid - string concatenation in loops
result = ""
for item in items:
    result += str(item)  # Creates new string each iteration
```

**Multi-line Strings:**
```python
# Good - triple quotes for docstrings
"""
This is a module docstring.
It can span multiple lines.
"""

# Good - for long messages
message = (
    "Line 1\n"
    "Line 2\n"
    "Line 3"
)
```

---

## 5. Comments & Documentation

### 5.1 Docstrings

Use Google-style docstrings:

```python
def create_task(user_id: int, content: str, deadline: datetime) -> Task:
    """
    Create a new task for the user.

    Args:
        user_id (int): The Telegram user ID.
        content (str): Task description (max 500 chars).
        deadline (datetime): Task deadline in user's timezone.

    Returns:
        Task: The created Task object.

    Raises:
        ValueError: If content exceeds 500 characters.
        DatabaseError: If database operation fails.

    Example:
        >>> task = create_task(123, "Buy milk", datetime.now())
        >>> print(task.id)
        "P-001"
    """
    if len(content) > 500:
        raise ValueError("Content exceeds 500 characters")
    # Implementation...
    return task
```

### 5.2 Function Comments

```python
# Good - explains why, not what
async def send_reminder(user_id: int, task_id: str):
    """Send task reminder notification."""
    # Add exponential backoff for retries to avoid rate limiting
    for attempt in range(3):
        try:
            await notify_user(user_id, f"Reminder: {task_id}")
            break
        except RateLimitError:
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)

# Bad - explains obvious code
async def send_reminder(user_id: int, task_id: str):
    """Send reminder."""
    # Get user
    user = get_user(user_id)
    # Get task
    task = get_task(task_id)
    # Create message
    msg = f"Reminder: {task.content}"
    # Send message
    send_message(user, msg)
```

### 5.3 Inline Comments

```python
# Good - explains unusual logic
deadline = datetime.now() + timedelta(days=7)
# Set deadline to end of day (23:59:59) to allow full day for completion
deadline = deadline.replace(hour=23, minute=59, second=59)

# Bad - states obvious
x = x + 1  # Increment x

# Bad - commented code (use version control instead)
# task = get_task_from_db(task_id)
# old_status = task.status
```

---

## 6. Type Hints

All functions should use type hints (Python 3.11+ requirement):

```python
# Good - with type hints
async def create_task(
    user_id: int,
    content: str,
    deadline: Optional[datetime] = None
) -> Task:
    """Create task."""
    pass

# Good - with complex types
from typing import Dict, List, Optional, Tuple

async def batch_update_tasks(
    tasks: List[Dict[str, Any]]
) -> Tuple[int, int]:
    """Update tasks. Returns (success_count, error_count)."""
    pass

# Bad - no type hints
def create_task(user_id, content, deadline=None):
    pass

# Bad - incomplete type hints
def create_task(user_id: int, content: str, deadline) -> Task:
    pass
```

**Common Type Patterns:**

```python
from typing import Optional, List, Dict, Tuple, Any, Union

# Optional (can be None)
async def get_user(user_id: int) -> Optional[User]:
    pass

# List
async def get_all_tasks(user_id: int) -> List[Task]:
    pass

# Dict
settings: Dict[str, Any] = {"timezone": "UTC", "notify": True}

# Union (multiple possible types)
value: Union[int, str] = get_setting("timeout")

# Tuple (fixed types and count)
def parse_deadline(text: str) -> Tuple[datetime, bool]:
    """Returns (datetime, is_recurring)"""
    pass

# Callable
from typing import Callable
callback: Callable[[str], None] = notify_user
```

---

## 7. Error Handling Patterns

### 7.1 Exception Hierarchy

Define custom exceptions:

```python
# In exceptions.py
class TeleTaskError(Exception):
    """Base exception for TeleTask."""
    pass

class ValidationError(TeleTaskError):
    """Raised when input validation fails."""
    pass

class DatabaseError(TeleTaskError):
    """Raised on database operation failures."""
    pass

class GoogleCalendarError(TeleTaskError):
    """Raised on Google Calendar API errors."""
    pass
```

### 7.2 Exception Handling

```python
# Good - specific exceptions
async def create_task(user_id: int, content: str):
    try:
        if not content or len(content) > 500:
            raise ValidationError("Invalid content length")

        task = Task(user_id=user_id, content=content)
        await db.add(task)
        await db.commit()
        return task

    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        await update.message.reply_text(f"Invalid input: {e}")

    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        await db.rollback()
        raise DatabaseError("Failed to create task")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise

# Bad - too broad
try:
    create_task(user_id, content)
except:  # Catches everything including SystemExit
    print("Error occurred")
```

### 7.3 Cleanup with Context Managers

```python
# Good - automatic cleanup
async with db.begin():
    task = Task(content="Example")
    await db.add(task)
    # Automatically commits or rolls back

# Good - for file operations
with open("report.pdf", "wb") as f:
    f.write(pdf_content)
    # File automatically closed
```

---

## 8. Async/Await Patterns

All database and network operations must be async:

```python
# Good - async/await
async def get_user_tasks(user_id: int) -> List[Task]:
    """Fetch user tasks from database."""
    query = select(Task).where(Task.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()

# Good - async in handlers
async def handle_task_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /taoviec command."""
    user_id = update.effective_user.id
    tasks = await get_user_tasks(user_id)
    await update.message.reply_text(f"You have {len(tasks)} tasks")

# Bad - blocking operation in async context
async def get_user_tasks(user_id: int):
    tasks = db.query(Task).filter(Task.user_id == user_id).all()  # Blocking!
    return tasks

# Bad - missing await
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_user_tasks(user_id)  # Missing await!
```

---

## 9. Database Access Patterns

### 9.1 Query Patterns

```python
# Good - using SQLAlchemy ORM
from sqlalchemy import select

async def get_task_by_id(task_id: str) -> Optional[Task]:
    """Get task by ID."""
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    return result.scalars().first()

# Good - with multiple conditions
async def get_user_overdue_tasks(user_id: int) -> List[Task]:
    """Get tasks past deadline."""
    query = (
        select(Task)
        .where(Task.user_id == user_id)
        .where(Task.deadline < datetime.now())
        .where(Task.status != "completed")
        .order_by(Task.deadline.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()

# Bad - SQL injection risk
tasks = await db.execute(f"SELECT * FROM tasks WHERE user_id = {user_id}")
```

### 9.2 CRUD Operations

```python
# CREATE
async def create_task(user_id: int, content: str) -> Task:
    """Create new task."""
    task = Task(user_id=user_id, content=content)
    db.add(task)
    await db.commit()
    await db.refresh(task)  # Refresh to get ID
    return task

# READ
async def get_task(task_id: str) -> Optional[Task]:
    """Get task by ID."""
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    return result.scalars().first()

# UPDATE
async def update_task(task: Task, status: str) -> Task:
    """Update task status."""
    task.status = status
    task.updated_at = datetime.now()
    await db.commit()
    await db.refresh(task)
    return task

# DELETE
async def delete_task(task_id: str) -> bool:
    """Soft delete task."""
    task = await get_task(task_id)
    if not task:
        return False
    task.is_deleted = True
    await db.commit()
    return True
```

---

## 10. Testing Standards

### 10.1 Test File Structure

```
tests/
├── unit/
│   ├── test_task_service.py
│   ├── test_user_service.py
│   └── test_time_parser.py
├── integration/
│   ├── test_task_creation_flow.py
│   └── test_calendar_sync.py
└── fixtures.py
```

### 10.2 Test Naming

```python
# Good - test_<function>_<scenario>
def test_create_task_with_valid_content():
    pass

def test_create_task_raises_on_empty_content():
    pass

def test_create_task_exceeding_max_length():
    pass

# Bad - vague names
def test_task():
    pass

def test_works():
    pass
```

### 10.3 Test Structure (Arrange-Act-Assert)

```python
async def test_create_task_with_deadline():
    # Arrange
    user_id = 123
    content = "Buy milk"
    deadline = datetime.now() + timedelta(days=1)

    # Act
    task = await create_task(user_id, content, deadline)

    # Assert
    assert task.id is not None
    assert task.user_id == user_id
    assert task.content == content
    assert task.deadline == deadline
```

---

## 11. Security Patterns

### 11.1 Input Validation

```python
# Good - validate all inputs
def validate_task_content(content: str) -> bool:
    """Validate task content."""
    if not content:
        raise ValueError("Content cannot be empty")
    if len(content) > 500:
        raise ValueError("Content exceeds 500 characters")
    if "<script>" in content.lower():
        raise ValueError("Invalid characters detected")
    return True

# Good - in handlers
async def handle_task_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        content = update.message.text
        validate_task_content(content)
        task = await create_task(update.effective_user.id, content)
    except ValueError as e:
        await update.message.reply_text(f"Invalid: {e}")
```

### 11.2 OAuth Security

```python
# Good - OAuth callback to localhost only
WEBHOOK_HOST = "127.0.0.1"
WEBHOOK_PORT = 8080

# Validate state token
def validate_oauth_state(provided_state: str, session_state: str) -> bool:
    """Prevent CSRF attacks."""
    return provided_state == session_state and session_state is not None

# Store tokens securely
async def store_oauth_token(user_id: int, token: str):
    """Store encrypted token."""
    encrypted = encrypt_token(token)  # Use PBKDF2 or similar
    user.google_calendar_token = encrypted
    await db.commit()
```

### 11.3 Logging Security

```python
# Good - never log sensitive data
async def authenticate_user(username: str, password: str) -> User:
    """Authenticate user."""
    logger.info(f"Login attempt for user: {username}")  # OK
    # Don't log password, tokens, etc.

# Bad - logs passwords
logger.info(f"User {username} logged in with password: {password}")

# Bad - logs tokens
logger.debug(f"Google token: {google_token}")
```

---

## 12. Performance Guidelines

### 12.1 Database Queries

```python
# Good - single query with join
query = (
    select(Task, User)
    .join(User, Task.user_id == User.id)
    .where(Task.status == "pending")
)
result = await db.execute(query)

# Bad - N+1 queries
tasks = await get_all_tasks()
for task in tasks:
    user = await get_user(task.user_id)  # Query for each task!
    print(f"{user.name}: {task.content}")
```

### 12.2 Pagination

```python
# Good - paginate large result sets
async def get_user_tasks(
    user_id: int,
    page: int = 1,
    page_size: int = 20
) -> List[Task]:
    """Get paginated user tasks."""
    offset = (page - 1) * page_size
    query = (
        select(Task)
        .where(Task.user_id == user_id)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all()
```

### 12.3 Caching

```python
# Good - cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def get_timezone_offset(timezone: str) -> timedelta:
    """Cache timezone offsets."""
    tz = pytz.timezone(timezone)
    return tz.utcoffset(datetime.now())

# Good - manual caching for database queries
_user_cache = {}

async def get_user_cached(user_id: int) -> Optional[User]:
    """Get user with caching."""
    if user_id not in _user_cache:
        _user_cache[user_id] = await get_user(user_id)
    return _user_cache[user_id]
```

---

## 13. Linting & Formatting

### 13.1 Recommended Tools

```bash
# Install tools
pip install black pylint mypy pytest

# Format code with Black
black src/

# Check for linting issues
pylint src/

# Type checking
mypy src/

# Run tests
pytest tests/
```

### 13.2 Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Format and check code before commit

black src/ || exit 1
pylint src/ || exit 1
mypy src/ || exit 1

exit 0
```

---

## 14. Git Commit Standards

### 14.1 Commit Messages

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring
- `docs:` - Documentation
- `test:` - Test additions/fixes
- `chore:` - Build, CI/CD, dependencies

**Example:**
```
feat: add task priority levels

- Add priority field to Task model
- Add priority selection in task_wizard
- Update task view to display priority
- Migration: 20251218_0008_task_priorities

Closes #123
```

### 14.2 Branch Naming

```
feature/task-priorities      # New feature
fix/calendar-sync-bug        # Bug fix
refactor/handler-cleanup     # Refactoring
docs/update-readme           # Documentation
```

---

## 15. Documentation Standards

### 15.1 README in Each Module

```python
"""
task_service.py - Task Service Module

Provides core business logic for task management operations.

Key Classes:
    TaskService - Main service class

Key Functions:
    create_task() - Create new task
    get_task_by_id() - Fetch task by ID
    delete_task() - Delete task

Dependencies:
    - database.models.Task
    - database.connection

Example:
    >>> service = TaskService(db_session)
    >>> task = await service.create_task(user_id, "Buy milk")
"""
```

### 15.2 Complex Logic Documentation

```python
async def calculate_recurring_deadline(
    base_deadline: datetime,
    recurrence_pattern: str
) -> datetime:
    """
    Calculate next occurrence deadline for recurring tasks.

    Algorithm:
        1. Parse recurrence pattern (DAILY, WEEKLY, MONTHLY)
        2. Calculate base interval
        3. Add interval to base_deadline
        4. Adjust for timezone and end-of-month edge cases
        5. Return adjusted deadline

    Args:
        base_deadline: Original task deadline
        recurrence_pattern: One of DAILY, WEEKLY, MONTHLY

    Returns:
        Next occurrence deadline

    Raises:
        ValueError: If pattern is invalid
    """
    pass
```

---

## 16. Code Review Checklist

Before requesting review, ensure:

- [ ] Code follows naming conventions
- [ ] File structure is organized
- [ ] Type hints are complete
- [ ] Docstrings are present
- [ ] Error handling is appropriate
- [ ] No hardcoded values (use constants)
- [ ] Async/await used correctly
- [ ] SQL injection prevention (use ORM)
- [ ] Sensitive data not logged
- [ ] Tests are included
- [ ] No commented-out code
- [ ] Line length < 100 chars
- [ ] Imports are organized

---

## 17. Useful Resources

- **PEP 8:** https://pep8.org/
- **Google Python Style Guide:** https://google.github.io/styleguide/pyguide.html
- **Real Python Best Practices:** https://realpython.com/python-pep8/
- **Python Type Hints:** https://docs.python.org/3/library/typing.html

---

**End of Document**
