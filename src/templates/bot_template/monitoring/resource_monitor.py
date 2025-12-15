"""
Resource Monitor
Monitor system resources and trigger alerts
"""

import os
import asyncio
import logging
from datetime import datetime

import psutil

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources and send alerts."""

    def __init__(self, db, alert_service, start_time: datetime):
        self.db = db
        self.alert_service = alert_service
        self.start_time = start_time
        self.running = False
        self.task = None

        # Thresholds (configurable via env)
        self.memory_threshold_mb = float(os.getenv('MEMORY_THRESHOLD_MB', 500))
        self.cpu_threshold = float(os.getenv('CPU_THRESHOLD', 90))
        self.disk_threshold_percent = float(os.getenv('DISK_THRESHOLD_PERCENT', 10))
        self.check_interval = int(os.getenv('MONITOR_INTERVAL', 60))

    async def start(self):
        """Start monitoring loop."""
        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("Resource monitor started")

    async def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Resource monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self.check_resources()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def check_resources(self):
        """Check system resources and alert if needed."""
        try:
            # Get current process
            process = psutil.Process(os.getpid())

            # Memory check
            memory_mb = process.memory_info().rss / 1024 / 1024
            if memory_mb > self.memory_threshold_mb:
                await self.alert_service.alert_high_memory(memory_mb, self.memory_threshold_mb)

            # CPU check (system-wide)
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.cpu_threshold:
                await self.alert_service.alert_high_cpu(cpu_percent)

            # Disk check
            disk = psutil.disk_usage('/')
            free_percent = (disk.free / disk.total) * 100
            if free_percent < self.disk_threshold_percent:
                await self.alert_service.alert_disk_low(
                    disk.free / 1024 / 1024 / 1024,
                    disk.total / 1024 / 1024 / 1024
                )

            # Update Prometheus metrics
            from monitoring.metrics import update_system_metrics
            uptime = (datetime.now() - self.start_time).total_seconds()
            update_system_metrics(
                uptime,
                process.memory_info().rss,
                process.cpu_percent()
            )

            # Check overdue tasks
            await self._check_overdue_tasks()

        except Exception as e:
            logger.error(f"Error checking resources: {e}")

    async def _check_overdue_tasks(self):
        """Check and alert for overdue tasks."""
        try:
            result = await self.db.fetch_one("""
                SELECT COUNT(*) as count
                FROM tasks
                WHERE is_deleted = false
                AND status != 'completed'
                AND deadline < NOW()
            """)
            overdue_count = result['count'] if result else 0

            # Update metric
            from monitoring.metrics import update_overdue_tasks
            update_overdue_tasks(overdue_count)

            # Alert if there are overdue tasks (once per day)
            if overdue_count > 0:
                await self.alert_service.alert_overdue_tasks(overdue_count)

        except Exception as e:
            logger.warning(f"Error checking overdue tasks: {e}")

    def get_status(self) -> dict:
        """Get current resource status."""
        process = psutil.Process(os.getpid())
        disk = psutil.disk_usage('/')

        return {
            'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
            'cpu_percent': round(process.cpu_percent(), 2),
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
        }
