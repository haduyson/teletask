"""
SQLAlchemy Models for TeleTask Bot
Database schema for task management system
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """
    Telegram user model.
    Stores user profile and notification preferences.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), index=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    display_name = Column(String(500))

    # Settings
    timezone = Column(String(50), default="Asia/Ho_Chi_Minh")
    language = Column(String(10), default="vi")

    # Notification preferences
    notify_reminder = Column(Boolean, default=True)
    notify_weekly_report = Column(Boolean, default=True)
    notify_monthly_report = Column(Boolean, default=True)

    # Google Calendar (Phase 09)
    google_calendar_token = Column(Text)
    google_calendar_refresh_token = Column(Text)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    group_memberships = relationship("GroupMember", back_populates="user")
    statistics = relationship("UserStatistics", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Group(Base):
    """
    Telegram group model.
    Stores group information for group task management.
    """
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    members = relationship("GroupMember", back_populates="group")
    tasks = relationship("Task", back_populates="group")
    statistics = relationship("UserStatistics", back_populates="group")

    def __repr__(self):
        return f"<Group(id={self.id}, telegram_id={self.telegram_id}, title={self.title})>"


class GroupMember(Base):
    """
    Group membership model.
    Links users to groups with role information.
    """
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="member")  # 'admin', 'member'
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
        Index("idx_gm_group", "group_id"),
        Index("idx_gm_user", "user_id"),
    )

    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, user_id={self.user_id}, role={self.role})>"


class Task(Base):
    """
    Main task model.
    Stores task information, status, and relationships.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(20), unique=True, nullable=False, index=True)  # P-1234 or G-500
    group_task_id = Column(String(20), index=True)  # Parent G-ID for group tasks

    content = Column(Text, nullable=False)
    description = Column(Text)

    status = Column(
        String(20),
        default="pending",
        nullable=False,
    )
    priority = Column(
        String(20),
        default="normal",
        nullable=False,
    )
    progress = Column(Integer, default=0)

    # Relationships - with proper cascade behavior
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))

    # Timestamps
    deadline = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Recurring (Phase 09)
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String(100))  # 'daily', 'weekly', 'monthly', 'custom'
    recurring_config = Column(JSONB)  # {'interval': 1, 'days': [1,3,5], ...}
    parent_recurring_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))

    # Google Calendar
    google_event_id = Column(String(255))

    # Flags
    is_personal = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    group = relationship("Group", back_populates="tasks")
    reminders = relationship("Reminder", back_populates="task", cascade="all, delete-orphan")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")
    parent_recurring = relationship("Task", remote_side=[id], foreign_keys=[parent_recurring_id])

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name="ck_task_status"),
        CheckConstraint("priority IN ('low', 'normal', 'high', 'urgent')", name="ck_task_priority"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_task_progress"),
        Index("idx_tasks_assignee_status", "assignee_id", "status", postgresql_where="is_deleted = false"),
        Index("idx_tasks_creator", "creator_id", postgresql_where="is_deleted = false"),
        Index("idx_tasks_deadline", "deadline", postgresql_where="is_deleted = false AND status != 'completed'"),
        Index("idx_tasks_group", "group_id", postgresql_where="is_deleted = false"),
    )

    def __repr__(self):
        return f"<Task(id={self.id}, public_id={self.public_id}, status={self.status})>"


class Reminder(Base):
    """
    Reminder model.
    Scheduled notifications for tasks.
    """
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    remind_at = Column(DateTime(timezone=True), nullable=False)
    reminder_type = Column(
        String(50),
        nullable=False,
    )
    reminder_offset = Column(String(20))  # '3d', '24h', '1h'

    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="reminders")
    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "reminder_type IN ('before_deadline', 'after_deadline', 'custom')",
            name="ck_reminder_type"
        ),
        Index("idx_reminders_pending", "remind_at", postgresql_where="is_sent = false"),
        Index("idx_reminders_task", "task_id"),
    )

    def __repr__(self):
        return f"<Reminder(id={self.id}, task_id={self.task_id}, remind_at={self.remind_at})>"


class TaskHistory(Base):
    """
    Task history model.
    Audit trail for task changes.
    """
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    action = Column(String(50), nullable=False)  # 'created', 'updated', 'completed', 'deleted'
    field_name = Column(String(100))  # 'status', 'deadline', 'assignee', etc.
    old_value = Column(Text)
    new_value = Column(Text)
    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="history")
    user = relationship("User")

    __table_args__ = (
        Index("idx_history_task", "task_id", "created_at"),
    )

    def __repr__(self):
        return f"<TaskHistory(id={self.id}, task_id={self.task_id}, action={self.action})>"


class UserStatistics(Base):
    """
    User statistics model.
    Aggregated task statistics per period.
    """
    __tablename__ = "user_statistics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))

    period_type = Column(String(20), nullable=False)  # 'weekly', 'monthly'
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Tasks assigned by user (giao viec)
    tasks_assigned_total = Column(Integer, default=0)
    tasks_assigned_completed = Column(Integer, default=0)
    tasks_assigned_overdue = Column(Integer, default=0)

    # Tasks received by user (nhan viec)
    tasks_received_total = Column(Integer, default=0)
    tasks_received_completed = Column(Integer, default=0)
    tasks_received_overdue = Column(Integer, default=0)

    # Personal tasks
    tasks_personal_total = Column(Integer, default=0)
    tasks_personal_completed = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="statistics")
    group = relationship("Group", back_populates="statistics")

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", "period_type", "period_start", name="uq_user_stats"),
        Index("idx_stats_user", "user_id", "period_type", "period_start"),
    )

    def __repr__(self):
        return f"<UserStatistics(user_id={self.user_id}, period={self.period_type})>"


class DeletedTaskUndo(Base):
    """
    Deleted tasks undo buffer.
    Stores deleted tasks for 30-second undo window.
    """
    __tablename__ = "deleted_tasks_undo"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)  # Original task ID
    task_data = Column(JSONB, nullable=False)  # Full task snapshot
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # Calculated: deleted_at + 30 seconds
    is_restored = Column(Boolean, default=False)

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_undo_expires", "expires_at", postgresql_where="is_restored = false"),
    )

    def __repr__(self):
        return f"<DeletedTaskUndo(task_id={self.task_id}, expires_at={self.expires_at})>"


class BotConfig(Base):
    """
    Bot configuration model.
    Key-value store for bot settings.
    """
    __tablename__ = "bot_config"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<BotConfig(key={self.key})>"
