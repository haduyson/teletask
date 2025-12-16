"""
Health Check Server
HTTP endpoint for monitoring bot health status and report downloads
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from aiohttp import web
import psutil
import pytz

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Ho_Chi_Minh")


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
        web_app.router.add_get('/report/{report_id}', self.report_page_handler)
        web_app.router.add_post('/report/{report_id}', self.report_download_handler)

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

    async def report_page_handler(self, request):
        """Serve password entry page for report download."""
        report_id = request.match_info.get('report_id', '')

        # Check if report exists and not expired
        try:
            from services.report_service import get_report_by_id
            report = await get_report_by_id(self.db, report_id)

            if not report:
                return web.Response(
                    text=self._error_page("Báo cáo không tồn tại", "Report not found"),
                    content_type='text/html',
                    status=404
                )

            now = datetime.now(TZ)
            if report['expires_at'].replace(tzinfo=TZ) < now:
                return web.Response(
                    text=self._error_page("Báo cáo đã hết hạn", "Report expired"),
                    content_type='text/html',
                    status=410
                )

            # Return password entry page
            return web.Response(
                text=self._password_page(report_id, report['file_format']),
                content_type='text/html'
            )

        except Exception as e:
            logger.error(f"Error in report_page_handler: {e}")
            return web.Response(
                text=self._error_page("Lỗi hệ thống", str(e)),
                content_type='text/html',
                status=500
            )

    async def report_download_handler(self, request):
        """Handle password verification and file download."""
        report_id = request.match_info.get('report_id', '')

        try:
            data = await request.post()
            password = data.get('password', '')

            from services.report_service import get_report_by_id, verify_password, increment_download_count
            report = await get_report_by_id(self.db, report_id)

            if not report:
                return web.Response(
                    text=self._error_page("Báo cáo không tồn tại", "Report not found"),
                    content_type='text/html',
                    status=404
                )

            now = datetime.now(TZ)
            if report['expires_at'].replace(tzinfo=TZ) < now:
                return web.Response(
                    text=self._error_page("Báo cáo đã hết hạn", "Report expired"),
                    content_type='text/html',
                    status=410
                )

            # Verify password
            if not verify_password(password, report['password_hash']):
                return web.Response(
                    text=self._password_page(report_id, report['file_format'], error="Mật khẩu không đúng"),
                    content_type='text/html',
                    status=401
                )

            # Serve the file
            file_path = Path(report['file_path'])
            if not file_path.exists():
                return web.Response(
                    text=self._error_page("File không tồn tại", "File not found"),
                    content_type='text/html',
                    status=404
                )

            # Increment download count
            await increment_download_count(self.db, report_id)

            # Determine content type
            content_types = {
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'pdf': 'application/pdf',
            }
            content_type = content_types.get(report['file_format'], 'application/octet-stream')

            # Create filename
            timestamp = datetime.now(TZ).strftime('%Y%m%d_%H%M')
            filename = f"teletask_report_{timestamp}.{report['file_format']}"

            # Read and return file
            with open(file_path, 'rb') as f:
                file_content = f.read()

            return web.Response(
                body=file_content,
                content_type=content_type,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )

        except Exception as e:
            logger.error(f"Error in report_download_handler: {e}")
            return web.Response(
                text=self._error_page("Lỗi tải file", str(e)),
                content_type='text/html',
                status=500
            )

    def _password_page(self, report_id: str, file_format: str, error: str = None) -> str:
        """Generate password entry HTML page."""
        error_html = f'<p class="error">{error}</p>' if error else ''
        format_icons = {'csv': '📄', 'xlsx': '📊', 'pdf': '📑'}
        format_names = {'csv': 'CSV', 'xlsx': 'Excel', 'pdf': 'PDF'}

        return f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleTask - Tải báo cáo</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .logo {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo h1 {{
            font-size: 28px;
            color: #333;
            margin-bottom: 5px;
        }}
        .logo p {{
            color: #666;
            font-size: 14px;
        }}
        .file-info {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .file-icon {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        .file-type {{
            font-weight: 600;
            color: #333;
        }}
        form {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        label {{
            font-weight: 500;
            color: #333;
            font-size: 14px;
        }}
        input[type="password"] {{
            padding: 15px;
            border: 2px solid #e1e5eb;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        input[type="password"]:focus {{
            outline: none;
            border-color: #667eea;
        }}
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        .error {{
            background: #fee2e2;
            color: #dc2626;
            padding: 12px;
            border-radius: 8px;
            font-size: 14px;
            text-align: center;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>📋 TeleTask</h1>
            <p>Báo cáo thống kê công việc</p>
        </div>
        <div class="file-info">
            <div class="file-icon">{format_icons.get(file_format, '📄')}</div>
            <div class="file-type">File {format_names.get(file_format, file_format.upper())}</div>
        </div>
        {error_html}
        <form method="post">
            <label for="password">Nhập mật khẩu để tải file:</label>
            <input type="password" id="password" name="password" placeholder="Mật khẩu" required autofocus>
            <button type="submit">⬇️ Tải xuống</button>
        </form>
        <p class="footer">Báo cáo sẽ hết hạn sau 72 giờ</p>
    </div>
</body>
</html>'''

    def _error_page(self, title: str, message: str) -> str:
        """Generate error HTML page."""
        return f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleTask - Lỗi</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #dc2626;
            font-size: 24px;
            margin-bottom: 10px;
        }}
        p {{
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">❌</div>
        <h1>{title}</h1>
        <p>{message}</p>
    </div>
</body>
</html>'''
