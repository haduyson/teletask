"""
Alert Service
Send Telegram notifications to admins for critical events
"""

import os
import logging
import traceback
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


class AlertService:
    """Send alerts to admin Telegram accounts."""

    def __init__(self, bot, admin_ids: List[int]):
        self.bot = bot
        self.admin_ids = admin_ids
        self.alert_cooldown = {}  # Prevent spam
        self.bot_name = os.getenv('BOT_NAME', 'TeleTask')

    async def send_alert(
        self,
        level: str,
        title: str,
        message: str,
        cooldown_key: str = None,
        cooldown_seconds: int = 300
    ):
        """Send alert to all admins."""
        # Check cooldown
        if cooldown_key:
            last_sent = self.alert_cooldown.get(cooldown_key)
            if last_sent and (datetime.now() - last_sent).seconds < cooldown_seconds:
                return

        # Format alert
        level_icons = {
            'critical': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️',
            'success': '✅'
        }
        icon = level_icons.get(level, '📢')

        text = f"""{icon} {level.upper()} - {title}

🤖 Bot: {self.bot_name}
📅 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}

{message}"""

        # Send to all admins
        sent_count = 0
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(chat_id=admin_id, text=text)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send alert to admin {admin_id}: {e}")

        if sent_count > 0:
            logger.info(f"Alert sent to {sent_count} admins: {title}")

        # Update cooldown
        if cooldown_key:
            self.alert_cooldown[cooldown_key] = datetime.now()

    async def alert_bot_start(self):
        """Alert on bot startup."""
        await self.send_alert(
            'success',
            'BOT STARTED',
            "🚀 Bot đã khởi động thành công!",
            cooldown_key='bot_start',
            cooldown_seconds=60
        )

    async def alert_bot_crash(self, error: Exception):
        """Alert on bot crash/critical error."""
        error_tb = traceback.format_exc()[:800]
        await self.send_alert(
            'critical',
            'BOT ERROR',
            f"""❌ Lỗi: {str(error)[:300]}

📝 Chi tiết:
```
{error_tb}
```""",
            cooldown_key='bot_crash',
            cooldown_seconds=60
        )

    async def alert_db_error(self, error: Exception):
        """Alert on database error."""
        await self.send_alert(
            'critical',
            'DATABASE ERROR',
            f"""🐘 Database không kết nối được

❌ Lỗi: {str(error)[:300]}

🔄 Đang thử kết nối lại...""",
            cooldown_key='db_error',
            cooldown_seconds=120
        )

    async def alert_high_memory(self, current_mb: float, threshold_mb: float):
        """Alert on high memory usage."""
        percent = (current_mb / threshold_mb) * 100 if threshold_mb > 0 else 0
        await self.send_alert(
            'warning',
            'HIGH MEMORY',
            f"""💾 Memory: {current_mb:.0f}MB ({percent:.0f}%)

💡 Khuyến nghị:
• Kiểm tra memory leak
• Restart bot nếu cần""",
            cooldown_key='high_memory',
            cooldown_seconds=600
        )

    async def alert_high_cpu(self, current_percent: float):
        """Alert on high CPU usage."""
        await self.send_alert(
            'warning',
            'HIGH CPU',
            f"""🖥️ CPU: {current_percent:.0f}%

💡 Khuyến nghị:
• Kiểm tra process đang chạy
• Kiểm tra scheduled jobs""",
            cooldown_key='high_cpu',
            cooldown_seconds=600
        )

    async def alert_disk_low(self, free_gb: float, total_gb: float):
        """Alert on low disk space."""
        percent = (free_gb / total_gb) * 100 if total_gb > 0 else 0
        await self.send_alert(
            'critical',
            'LOW DISK SPACE',
            f"""💿 Disk: {free_gb:.1f}GB free / {total_gb:.1f}GB total ({percent:.0f}% free)

💡 Khuyến nghị:
• Xóa log cũ
• Xóa backup cũ""",
            cooldown_key='disk_low',
            cooldown_seconds=3600
        )

    async def alert_backup_status(self, success: bool, message: str = ""):
        """Alert on backup status."""
        if success:
            await self.send_alert(
                'success',
                'BACKUP SUCCESS',
                f"💾 Backup hoàn tất!\n\n{message}",
                cooldown_key='backup_success',
                cooldown_seconds=86400  # Once per day
            )
        else:
            await self.send_alert(
                'warning',
                'BACKUP FAILED',
                f"""💾 Backup thất bại!

❌ Lỗi: {message}""",
                cooldown_key='backup_failed',
                cooldown_seconds=3600
            )

    async def alert_overdue_tasks(self, count: int):
        """Alert on overdue tasks for current month (daily summary)."""
        if count > 0:
            await self.send_alert(
                'info',
                'OVERDUE TASKS',
                f"""📋 Có {count} việc quá hạn trong tháng này

Xem chi tiết: /viectrehan""",
                cooldown_key='overdue_tasks',
                cooldown_seconds=86400  # Once per day
            )
