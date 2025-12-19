"""
Report Scheduler
Weekly and monthly report jobs
"""

import os
import logging
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger
import pytz

from services.statistics_service import (
    calculate_user_stats,
    store_user_stats,
    get_week_range,
    get_previous_week_range,
    get_month_range,
    get_previous_month_range,
    get_group_rankings,
    get_active_users_for_report,
    get_user_groups,
)
from utils.formatters import format_weekly_report, format_monthly_report

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


class ReportScheduler:
    """Report scheduler for weekly and monthly reports."""

    def __init__(self):
        self.scheduler = None
        self.bot = None
        self.db = None
        self.admin_ids = []

    def start(self, scheduler, bot, db) -> None:
        """Register report jobs with the scheduler."""
        self.scheduler = scheduler
        self.bot = bot
        self.db = db

        # Parse admin IDs (support both personal and group IDs)
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        for x in admin_ids_str.split(','):
            x = x.strip()
            if x.lstrip('-').isdigit() and x:
                self.admin_ids.append(int(x))

        # Weekly report: Saturday 17:00
        self.scheduler.add_job(
            self._send_weekly_reports,
            CronTrigger(day_of_week="sat", hour=17, minute=0, timezone=TZ),
            id="weekly_reports",
            replace_existing=True,
        )

        # Monthly report: Last day of month 17:00
        self.scheduler.add_job(
            self._send_monthly_reports,
            CronTrigger(day="last", hour=17, minute=0, timezone=TZ),
            id="monthly_reports",
            replace_existing=True,
        )

        # Admin daily summary: Every day at 08:00
        if self.admin_ids:
            self.scheduler.add_job(
                self._send_admin_summary,
                CronTrigger(hour=8, minute=0, timezone=TZ),
                id="admin_daily_summary",
                replace_existing=True,
            )
            logger.info(f"Admin summary scheduled for {len(self.admin_ids)} recipients")

        logger.info("Report scheduler jobs registered")

    async def _send_weekly_reports(self) -> None:
        """Send weekly reports to all active users."""
        logger.info("Starting weekly report generation")

        week_start, week_end = get_week_range()
        prev_start, prev_end = get_previous_week_range()

        users = await get_active_users_for_report(self.db, "weekly")
        logger.info(f"Sending weekly reports to {len(users)} users")

        success_count = 0
        for user in users:
            try:
                # Calculate stats
                stats = await calculate_user_stats(
                    self.db, user["id"], "weekly", week_start, week_end
                )

                # Previous week for comparison
                prev_stats = await calculate_user_stats(
                    self.db, user["id"], "weekly", prev_start, prev_end
                )

                # Get groups user belongs to
                groups = await get_user_groups(self.db, user["id"])

                # Get ranking in each group
                group_rankings = {}
                for group in groups:
                    rankings = await get_group_rankings(
                        self.db, group["id"], "weekly", week_start
                    )
                    for i, r in enumerate(rankings):
                        if r["user_id"] == user["id"]:
                            group_rankings[group["title"]] = (i + 1, len(rankings))
                            break

                # Format and send report
                text = format_weekly_report(
                    user["display_name"] or user["username"] or "Ban",
                    stats,
                    week_start,
                    week_end,
                    group_rankings=group_rankings,
                    prev_stats=prev_stats,
                )

                await self.bot.send_message(chat_id=user["telegram_id"], text=text)

                # Store stats
                await store_user_stats(
                    self.db, user["id"], None, "weekly", stats, week_start, week_end
                )

                success_count += 1

            except Exception as e:
                logger.error(f"Error sending weekly report to user {user['id']}: {e}")

        logger.info(f"Weekly reports sent: {success_count}/{len(users)}")

    async def _send_monthly_reports(self) -> None:
        """Send monthly reports to all active users."""
        logger.info("Starting monthly report generation")

        month_start, month_end = get_month_range()
        prev_start, prev_end = get_previous_month_range()

        users = await get_active_users_for_report(self.db, "monthly")
        logger.info(f"Sending monthly reports to {len(users)} users")

        success_count = 0
        for user in users:
            try:
                stats = await calculate_user_stats(
                    self.db, user["id"], "monthly", month_start, month_end
                )

                prev_stats = await calculate_user_stats(
                    self.db, user["id"], "monthly", prev_start, prev_end
                )

                text = format_monthly_report(
                    user["display_name"] or user["username"] or "Ban",
                    stats,
                    prev_stats,
                    month_start,
                    month_end,
                )

                await self.bot.send_message(chat_id=user["telegram_id"], text=text)

                await store_user_stats(
                    self.db, user["id"], None, "monthly", stats, month_start, month_end
                )

                success_count += 1

            except Exception as e:
                logger.error(f"Error sending monthly report to user {user['id']}: {e}")

        logger.info(f"Monthly reports sent: {success_count}/{len(users)}")

    async def _send_admin_summary(self) -> None:
        """Send daily summary report to admins (personal or group)."""
        if not self.admin_ids:
            return

        logger.info("Starting admin daily summary generation")

        try:
            now = datetime.now(TZ)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Get overall statistics
            total_stats = await self.db.fetch_one("""
                SELECT
                    COUNT(*) as total_tasks,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_tasks,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_tasks,
                    COUNT(*) FILTER (WHERE status != 'completed' AND deadline < NOW()) as overdue_tasks,
                    COUNT(*) FILTER (WHERE created_at >= $1) as today_tasks,
                    COUNT(*) FILTER (WHERE completed_at >= $1) as today_completed
                FROM tasks
                WHERE is_deleted = false
            """, today_start)

            total_users = await self.db.fetch_one(
                "SELECT COUNT(*) as count FROM users"
            )

            # Calculate completion rate
            total = total_stats['total_tasks'] or 0
            completed = total_stats['completed_tasks'] or 0
            completion_rate = (completed / total * 100) if total > 0 else 0

            # Format message
            bot_name = os.getenv('BOT_NAME', 'TeleTask')
            message = f"""📊 BÁO CÁO TỔNG HỢP - {bot_name}
📅 Ngày: {now.strftime('%d/%m/%Y')}

👥 Tổng người dùng: {total_users['count']}
📋 Tổng số việc: {total}

📅 Hôm nay:
• Việc mới: {total_stats['today_tasks'] or 0}
• Đã hoàn thành: {total_stats['today_completed'] or 0}

📊 Trạng thái tổng:
• Đang chờ: {total_stats['pending_tasks'] or 0}
• Đã hoàn thành: {completed}
• Quá hạn: {total_stats['overdue_tasks'] or 0}
• Tỷ lệ hoàn thành: {completion_rate:.1f}%"""

            # Send to all admin IDs (personal or group)
            sent_count = 0
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(chat_id=admin_id, text=message)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to send admin summary to {admin_id}: {e}")

            logger.info(f"Admin summary sent to {sent_count}/{len(self.admin_ids)} recipients")

        except Exception as e:
            logger.error(f"Error generating admin summary: {e}")


# Global instance
report_scheduler = ReportScheduler()


def init_report_scheduler(scheduler, bot, db) -> None:
    """Initialize report scheduler."""
    report_scheduler.start(scheduler, bot, db)
