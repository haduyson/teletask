"""
Health Check Server
HTTP endpoint for monitoring bot health status
"""

import os
import logging
from datetime import datetime
from aiohttp import web
import psutil

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """HTTP server for health check and metrics endpoints."""

    def __init__(self, app, db, port: int = 8080):
        self.telegram_app = app
        self.db = db
        self.port = port
        self.start_time = datetime.now()
        self.runner = None

    async def start(self):
        """Start health check HTTP server."""
        web_app = web.Application()
        web_app.router.add_get('/health', self.health_handler)
        web_app.router.add_get('/metrics', self.metrics_handler)

        self.runner = web.AppRunner(web_app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Health check server started on port {self.port}")

    async def stop(self):
        """Stop server."""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Health check server stopped")

    async def health_handler(self, request):
        """Handle /health requests."""
        # Check database
        db_status = 'connected'
        try:
            await self.db.fetch_one("SELECT 1")
        except Exception as e:
            db_status = 'disconnected'
            logger.warning(f"Database health check failed: {e}")

        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

        # Get process memory and CPU
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        # Get today's stats
        today_stats = await self._get_today_stats()

        return web.json_response({
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'bot_name': os.getenv('BOT_NAME', 'TeleTask'),
            'uptime': uptime_str,
            'uptime_seconds': int(uptime.total_seconds()),
            'memory_mb': round(memory_mb, 2),
            'cpu_percent': round(cpu_percent, 2),
            'database': db_status,
            'last_activity': datetime.now().isoformat(),
            'tasks_today': today_stats.get('tasks_created', 0),
            'completed_today': today_stats.get('completed', 0),
        })

    async def metrics_handler(self, request):
        """Handle /metrics requests (Prometheus format)."""
        try:
            from monitoring.metrics import get_metrics_text
            return web.Response(text=get_metrics_text(), content_type='text/plain')
        except ImportError:
            return web.Response(text="# Metrics not available", content_type='text/plain')

    async def _get_today_stats(self):
        """Get today's statistics."""
        try:
            result = await self.db.fetch_one("""
                SELECT
                    COUNT(*) FILTER (WHERE DATE(created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = CURRENT_DATE) as tasks_created,
                    COUNT(*) FILTER (WHERE status = 'completed' AND DATE(updated_at AT TIME ZONE 'Asia/Ho_Chi_Minh') = CURRENT_DATE) as completed
                FROM tasks WHERE is_deleted = false
            """)
            return dict(result) if result else {'tasks_created': 0, 'completed': 0}
        except Exception as e:
            logger.warning(f"Failed to get today stats: {e}")
            return {'tasks_created': 0, 'completed': 0}
