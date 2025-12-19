"""
Task Validation Service
Input validation for task operations
"""

import logging
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Valid status values
VALID_STATUSES = {"pending", "in_progress", "completed"}

# Valid priority values
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}

# Content limits
MIN_CONTENT_LENGTH = 2
MAX_CONTENT_LENGTH = 500


class ValidationError(Exception):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_content(content: str) -> Tuple[bool, str]:
    """
    Validate task content.

    Args:
        content: Task content string

    Returns:
        Tuple of (is_valid, error_message or cleaned content)
    """
    if content is None:
        return False, "Nội dung việc không được để trống."

    content = str(content).strip()

    if len(content) < MIN_CONTENT_LENGTH:
        return False, f"Nội dung việc quá ngắn (tối thiểu {MIN_CONTENT_LENGTH} ký tự)."

    if len(content) > MAX_CONTENT_LENGTH:
        return False, f"Nội dung việc quá dài (tối đa {MAX_CONTENT_LENGTH} ký tự)."

    return True, content


def validate_priority(priority: str) -> Tuple[bool, str]:
    """
    Validate and normalize priority.

    Args:
        priority: Priority string

    Returns:
        Tuple of (is_valid, normalized priority or error message)
    """
    if priority is None:
        return True, "normal"  # Default to normal

    priority = str(priority).lower().strip()

    # Vietnamese mappings
    priority_map = {
        "thap": "low",
        "binh thuong": "normal",
        "bt": "normal",
        "cao": "high",
        "khan cap": "urgent",
        "khancap": "urgent",
        "kc": "urgent",
        "low": "low",
        "normal": "normal",
        "high": "high",
        "urgent": "urgent",
    }

    if priority in priority_map:
        return True, priority_map[priority]

    if priority in VALID_PRIORITIES:
        return True, priority

    return False, f"Độ ưu tiên không hợp lệ. Chọn: {', '.join(VALID_PRIORITIES)}"


def validate_status(status: str) -> Tuple[bool, str]:
    """
    Validate and normalize status.

    Args:
        status: Status string

    Returns:
        Tuple of (is_valid, normalized status or error message)
    """
    if status is None:
        return True, "pending"  # Default to pending

    status = str(status).lower().strip()

    # Vietnamese mappings
    status_map = {
        "cho xu ly": "pending",
        "chua lam": "pending",
        "dang lam": "in_progress",
        "hoan thanh": "completed",
        "xong": "completed",
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
    }

    if status in status_map:
        return True, status_map[status]

    if status in VALID_STATUSES:
        return True, status

    return False, f"Trạng thái không hợp lệ. Chọn: {', '.join(VALID_STATUSES)}"


def validate_progress(progress: Any) -> Tuple[bool, int]:
    """
    Validate progress percentage.

    Args:
        progress: Progress value (int, str, or None)

    Returns:
        Tuple of (is_valid, validated progress value)
    """
    if progress is None:
        return True, 0

    try:
        # Handle string with % sign
        if isinstance(progress, str):
            progress = progress.replace("%", "").strip()
        value = int(progress)
        if 0 <= value <= 100:
            return True, value
        return False, 0
    except (ValueError, TypeError):
        return False, 0


def validate_deadline(deadline: Any) -> Tuple[bool, Optional[datetime]]:
    """
    Validate deadline datetime.

    Args:
        deadline: Deadline value (datetime, str, or None)

    Returns:
        Tuple of (is_valid, validated deadline)
    """
    if deadline is None:
        return True, None

    if isinstance(deadline, datetime):
        return True, deadline

    # String parsing not implemented here - handled by time_parser service
    return False, None


def validate_task_input(
    content: str = None,
    priority: str = None,
    status: str = None,
    progress: Any = None,
) -> Dict[str, Any]:
    """
    Validate multiple task inputs at once.

    Args:
        content: Task content
        priority: Task priority
        status: Task status
        progress: Task progress

    Returns:
        Dict with validated values

    Raises:
        ValidationError: If any validation fails
    """
    validated = {}
    errors = []

    if content is not None:
        valid, result = validate_content(content)
        if valid:
            validated["content"] = result
        else:
            errors.append(("content", result))

    if priority is not None:
        valid, result = validate_priority(priority)
        if valid:
            validated["priority"] = result
        else:
            errors.append(("priority", result))

    if status is not None:
        valid, result = validate_status(status)
        if valid:
            validated["status"] = result
        else:
            errors.append(("status", result))

    if progress is not None:
        valid, result = validate_progress(progress)
        if valid:
            validated["progress"] = result
        else:
            errors.append(("progress", "Tiến độ phải từ 0 đến 100."))

    if errors:
        error_messages = "; ".join([f"{field}: {msg}" for field, msg in errors])
        raise ValidationError(error_messages)

    return validated


def with_validation(func: Callable) -> Callable:
    """
    Decorator to add input validation to service functions.

    Validates common task fields if present in kwargs.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract fields to validate
        validation_fields = {}

        if "content" in kwargs and kwargs["content"] is not None:
            validation_fields["content"] = kwargs["content"]

        if "priority" in kwargs and kwargs["priority"] is not None:
            validation_fields["priority"] = kwargs["priority"]

        if "status" in kwargs and kwargs["status"] is not None:
            validation_fields["status"] = kwargs["status"]

        if "progress" in kwargs and kwargs["progress"] is not None:
            validation_fields["progress"] = kwargs["progress"]

        # Validate and update kwargs with validated values
        if validation_fields:
            validated = validate_task_input(**validation_fields)
            kwargs.update(validated)

        return await func(*args, **kwargs)

    return wrapper
