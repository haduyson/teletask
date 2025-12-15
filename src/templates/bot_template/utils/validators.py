"""
Input Validators
Validate user input for task management
"""

import re
from typing import List, Optional, Tuple


def extract_mentions(text: str) -> Tuple[List[str], str]:
    """
    Extract @mentions from text.

    Args:
        text: Input text

    Returns:
        Tuple of (list of usernames without @, remaining text)
    """
    mentions = re.findall(r"@(\w+)", text)
    remaining = re.sub(r"@\w+", "", text).strip()
    remaining = re.sub(r"\s+", " ", remaining)  # Normalize whitespace
    return mentions, remaining


def validate_task_content(content: str) -> Tuple[bool, str]:
    """
    Validate task content.

    Args:
        content: Task content text

    Returns:
        Tuple of (is_valid, error_message_or_cleaned_content)
    """
    if not content:
        return False, "Nội dung việc không được để trống."

    content = content.strip()

    if len(content) < 2:
        return False, "Nội dung việc quá ngắn (tối thiểu 2 ký tự)."

    if len(content) > 500:
        return False, "Nội dung việc quá dài (tối đa 500 ký tự)."

    return True, content


def validate_priority(priority: str) -> Tuple[bool, str]:
    """
    Validate and normalize priority.

    Args:
        priority: Priority string

    Returns:
        Tuple of (is_valid, normalized_priority)
    """
    priority = priority.lower().strip()

    # Vietnamese mappings
    priority_map = {
        "thap": "low",
        "binh thuong": "normal",
        "bt": "normal",
        "cao": "high",
        "khan cap": "urgent",
        "khancap": "urgent",
        "kc": "urgent",
        # English
        "low": "low",
        "normal": "normal",
        "high": "high",
        "urgent": "urgent",
    }

    if priority in priority_map:
        return True, priority_map[priority]

    return False, "normal"  # Default to normal


def validate_status(status: str) -> Tuple[bool, str]:
    """
    Validate and normalize status.

    Args:
        status: Status string

    Returns:
        Tuple of (is_valid, normalized_status)
    """
    status = status.lower().strip()

    status_map = {
        # Vietnamese
        "cho xu ly": "pending",
        "chua lam": "pending",
        "dang lam": "in_progress",
        "hoan thanh": "completed",
        "xong": "completed",
        "da huy": "cancelled",
        "huy": "cancelled",
        # English
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
        "cancelled": "cancelled",
    }

    if status in status_map:
        return True, status_map[status]

    return False, "pending"


def validate_progress(progress: str) -> Tuple[bool, int]:
    """
    Validate progress percentage.

    Args:
        progress: Progress string (e.g., "50", "50%")

    Returns:
        Tuple of (is_valid, progress_int)
    """
    # Remove % sign
    progress = progress.replace("%", "").strip()

    try:
        value = int(progress)
        if 0 <= value <= 100:
            return True, value
        return False, 0
    except ValueError:
        return False, 0


def parse_task_command(text: str) -> dict:
    """
    Parse task creation command.

    Format: [content] [time expression]

    Args:
        text: Command text after /taoviec

    Returns:
        Dict with parsed fields
    """
    result = {
        "content": "",
        "deadline_text": "",
        "mentions": [],
        "priority": "normal",
    }

    if not text:
        return result

    # Extract mentions first
    mentions, text = extract_mentions(text)
    result["mentions"] = mentions

    # Check for priority keywords
    priority_patterns = [
        (r"\b(khan\s*cap|kc)\b", "urgent"),
        (r"\b(uu\s*tien\s*cao|cao)\b", "high"),
        (r"\b(uu\s*tien\s*thap|thap)\b", "low"),
    ]

    for pattern, priority in priority_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            result["priority"] = priority
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            break

    result["content"] = text.strip()
    return result


def is_valid_public_id(public_id: str) -> bool:
    """
    Check if string is a valid task public ID.

    Format: P-XXXX or G-XXXX

    Args:
        public_id: Task ID string

    Returns:
        True if valid format
    """
    pattern = r"^[PG]-\d{4}$"
    return bool(re.match(pattern, public_id.upper()))


def sanitize_html(text: str) -> str:
    """
    Sanitize text for HTML message mode.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    replacements = [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text
