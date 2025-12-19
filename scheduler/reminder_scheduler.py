"""
Reminder Scheduler
APScheduler-based reminder system for task deadlines
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


class ReminderScheduler:
    """Manages scheduled reminders for tasks."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.bot = None
        self.db = None

    def start(self, bot, db) -> None:
        """
        Initialize and start the scheduler.

        Args:
            bot: Telegram bot instance
            db: Database connection
        """
        self.bot = bot
        self.db = db

        self.scheduler = AsyncIOScheduler(timezone=TZ)

        # Process pending reminders every minute
        self.scheduler.add_job(
            self._process_pending_reminders,
            CronTrigger(minute="*"),
            id="process_reminders",
            replace_existing=True,
        )

        # Cleanup expired undo records every 5 minutes
        self.scheduler.add_job(
            self._cleanup_expired_undo,
            CronTrigger(minute="*/5"),
            id="cleanup_undo",
            replace_existing=True,
        )

        # Process recurring task templates every 5 minutes
        self.scheduler.add_job(
            self._process_recurring_templates,
            CronTrigger(minute="*/5"),
            id="process_recurring",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Reminder scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("Reminder scheduler stopped")

    async def _process_pending_reminders(self) -> None:
        """Process all pending reminders due now."""
        from services.reminder_service import get_pending_reminders, mark_reminder_sent
        from services.notification import send_reminder_notification

        try:
            reminders = await get_pending_reminders(self.db)

            for reminder in reminders:
                try:
                    await send_reminder_notification(self.bot, reminder)
                    await mark_reminder_sent(self.db, reminder["id"])
                    logger.info(f"Sent reminder {reminder['id']} for task {reminder.get('public_id')}")
                except Exception as e:
                    logger.error(f"Failed to send reminder {reminder['id']}: {e}")
                    await mark_reminder_sent(self.db, reminder["id"], error=str(e))

        except Exception as e:
            logger.error(f"Error processing reminders: {e}")

    async def _cleanup_expired_undo(self) -> None:
        """Clean up expired undo records."""
        try:
            await self.db.execute(
                """
                DELETE FROM deleted_tasks_undo
                WHERE expires_at < CURRENT_TIMESTAMP AND is_restored = false
                """
            )
        except Exception as e:
            logger.error(f"Error cleaning up undo records: {e}")

    async def _process_recurring_templates(self) -> None:
        """Process recurring templates and generate tasks."""
        from services.recurring_service import get_due_templates, generate_task_from_template

        try:
            templates = await get_due_templates(self.db)

            for template in templates:
                try:
                    task = await generate_task_from_template(self.db, template)
                    if task:
                        # Notify creator about new task
                        try:
                            await self.bot.send_message(
                                chat_id=template["creator_telegram_id"],
                                text=(
                                    f"🔄 *VIỆC LẶP LẠI TỰ ĐỘNG*\n\n"
                                    f"Đã tạo việc mới từ mẫu `{template['public_id']}`:\n\n"
                                    f"🆔 `{task['public_id']}`\n"
                                    f"📝 {task['content'][:100]}\n"
                                    f"⏰ Deadline: {task['deadline'].strftime('%H:%M %d/%m') if task.get('deadline') else 'N/A'}"
                                ),
                                parse_mode="Markdown",
                            )
                        except Exception as notify_err:
                            logger.warning(f"Failed to notify recurring task creation: {notify_err}")

                        logger.info(f"Generated task {task['public_id']} from template {template['public_id']}")
                except Exception as e:
                    logger.error(f"Failed to generate task from template {template.get('public_id')}: {e}")

        except Exception as e:
            logger.error(f"Error processing recurring templates: {e}")

    def add_custom_reminder(
        self,
        task_id: int,
        user_id: int,
        remind_at: datetime,
    ) -> str:
        """
        Add a custom reminder job.

        Args:
            task_id: Task internal ID
            user_id: User internal ID
            remind_at: When to send reminder

        Returns:
            Job ID
        """
        job_id = f"custom_{task_id}_{user_id}_{int(remind_at.timestamp())}"

        self.scheduler.add_job(
            self._send_single_reminder,
            DateTrigger(run_date=remind_at, timezone=TZ),
            args=[task_id, user_id],
            id=job_id,
            replace_existing=True,
        )

        logger.info(f"Scheduled custom reminder {job_id} at {remind_at}")
        return job_id

    async def _send_single_reminder(self, task_id: int, user_id: int) -> None:
        """Send a single custom reminder."""
        from services.notification import send_reminder_by_task

        try:
            await send_reminder_by_task(self.bot, self.db, task_id, user_id)
        except Exception as e:
            logger.error(f"Failed to send custom reminder for task {task_id}: {e}")

    def cancel_reminder(self, job_id: str) -> bool:
        """
        Cancel a scheduled reminder.

        Args:
            job_id: The job ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled reminder job {job_id}")
            return True
        except Exception:
            return False


# Global scheduler instance
reminder_scheduler = ReminderScheduler()


def init_scheduler(bot, db) -> None:
    """Initialize the global reminder scheduler."""
    reminder_scheduler.start(bot, db)


def stop_scheduler() -> None:
    """Stop the global reminder scheduler."""
    reminder_scheduler.stop()
