"""
Task Permissions Service
Authorization checks for task operations
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PermissionError(Exception):
    """Exception raised for permission errors."""

    def __init__(self, message: str, user_id: int = None, task_id: str = None):
        self.message = message
        self.user_id = user_id
        self.task_id = task_id
        super().__init__(self.message)


def can_view_task(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can view a task.

    Users can view tasks they created or are assigned to.

    Args:
        task: Task dict with creator_id and assignee_id
        user_id: User requesting access

    Returns:
        True if user can view the task
    """
    if not task:
        return False

    return (
        task.get("creator_id") == user_id or
        task.get("assignee_id") == user_id
    )


def can_modify_task(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can modify a task.

    Users can modify tasks they created or are assigned to.

    Args:
        task: Task dict with creator_id and assignee_id
        user_id: User requesting modification

    Returns:
        True if user can modify the task
    """
    if not task:
        return False

    return (
        task.get("creator_id") == user_id or
        task.get("assignee_id") == user_id
    )


def can_delete_task(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can delete a task.

    Only task creators can delete tasks.

    Args:
        task: Task dict with creator_id
        user_id: User requesting deletion

    Returns:
        True if user can delete the task
    """
    if not task:
        return False

    return task.get("creator_id") == user_id


def can_assign_task(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can assign/reassign a task.

    Only task creators can assign tasks.

    Args:
        task: Task dict with creator_id
        user_id: User requesting assignment

    Returns:
        True if user can assign the task
    """
    if not task:
        return False

    return task.get("creator_id") == user_id


def can_complete_task(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can mark a task as complete.

    Task creators and assignees can complete tasks.

    Args:
        task: Task dict with creator_id and assignee_id
        user_id: User requesting completion

    Returns:
        True if user can complete the task
    """
    if not task:
        return False

    return (
        task.get("creator_id") == user_id or
        task.get("assignee_id") == user_id
    )


def can_update_progress(task: Dict[str, Any], user_id: int) -> bool:
    """
    Check if user can update task progress.

    Task assignees and creators can update progress.

    Args:
        task: Task dict with creator_id and assignee_id
        user_id: User requesting update

    Returns:
        True if user can update progress
    """
    if not task:
        return False

    return (
        task.get("creator_id") == user_id or
        task.get("assignee_id") == user_id
    )


def check_view_permission(task: Dict[str, Any], user_id: int) -> None:
    """
    Check view permission, raise error if denied.

    Args:
        task: Task dict
        user_id: User requesting access

    Raises:
        PermissionError: If user cannot view the task
    """
    if not can_view_task(task, user_id):
        raise PermissionError(
            "Bạn không có quyền xem việc này.",
            user_id=user_id,
            task_id=task.get("public_id")
        )


def check_modify_permission(task: Dict[str, Any], user_id: int) -> None:
    """
    Check modify permission, raise error if denied.

    Args:
        task: Task dict
        user_id: User requesting modification

    Raises:
        PermissionError: If user cannot modify the task
    """
    if not can_modify_task(task, user_id):
        raise PermissionError(
            "Bạn không có quyền chỉnh sửa việc này.",
            user_id=user_id,
            task_id=task.get("public_id")
        )


def check_delete_permission(task: Dict[str, Any], user_id: int) -> None:
    """
    Check delete permission, raise error if denied.

    Args:
        task: Task dict
        user_id: User requesting deletion

    Raises:
        PermissionError: If user cannot delete the task
    """
    if not can_delete_task(task, user_id):
        raise PermissionError(
            "Chỉ người tạo mới có quyền xóa việc này.",
            user_id=user_id,
            task_id=task.get("public_id")
        )


def check_assign_permission(task: Dict[str, Any], user_id: int) -> None:
    """
    Check assign permission, raise error if denied.

    Args:
        task: Task dict
        user_id: User requesting assignment

    Raises:
        PermissionError: If user cannot assign the task
    """
    if not can_assign_task(task, user_id):
        raise PermissionError(
            "Chỉ người tạo mới có quyền giao việc này.",
            user_id=user_id,
            task_id=task.get("public_id")
        )


def check_complete_permission(task: Dict[str, Any], user_id: int) -> None:
    """
    Check complete permission, raise error if denied.

    Args:
        task: Task dict
        user_id: User requesting completion

    Raises:
        PermissionError: If user cannot complete the task
    """
    if not can_complete_task(task, user_id):
        raise PermissionError(
            "Bạn không có quyền hoàn thành việc này.",
            user_id=user_id,
            task_id=task.get("public_id")
        )
