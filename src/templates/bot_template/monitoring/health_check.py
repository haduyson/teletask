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
        """Generate MacOS-style password entry HTML page."""
        error_html = f'<div class="error-banner"><span class="error-icon">⚠️</span>{error}</div>' if error else ''
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
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif;
            background: linear-gradient(180deg, #f5f5f7 0%, #e8e8ed 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }}
        .macos-window {{
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 12px;
            max-width: 380px;
            width: 100%;
            box-shadow: 0 22px 70px 4px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
            overflow: hidden;
        }}
        .window-header {{
            background: linear-gradient(180deg, #e8e8e8 0%, #d6d6d6 100%);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        .traffic-lights {{
            display: flex;
            gap: 8px;
        }}
        .traffic-light {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.1);
        }}
        .light-close {{ background: #ff5f57; }}
        .light-minimize {{ background: #febc2e; }}
        .light-maximize {{ background: #28c840; }}
        .window-title {{
            flex: 1;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            color: #4d4d4d;
            margin-right: 52px;
        }}
        .window-content {{
            padding: 30px;
        }}
        .app-icon {{
            text-align: center;
            margin-bottom: 16px;
        }}
        .app-icon-img {{
            width: 64px;
            height: 64px;
            background: linear-gradient(180deg, #007aff 0%, #0055d4 100%);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto;
            box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        }}
        .app-title {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .app-title h1 {{
            font-size: 18px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 4px;
        }}
        .app-title p {{
            font-size: 13px;
            color: #86868b;
        }}
        .file-badge {{
            background: #f5f5f7;
            border-radius: 8px;
            padding: 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            border: 1px solid rgba(0,0,0,0.04);
        }}
        .file-badge-icon {{
            font-size: 28px;
        }}
        .file-badge-info {{
            flex: 1;
        }}
        .file-badge-type {{
            font-size: 13px;
            font-weight: 600;
            color: #1d1d1f;
        }}
        .file-badge-desc {{
            font-size: 11px;
            color: #86868b;
        }}
        .error-banner {{
            background: #fff2f2;
            border: 1px solid #ffcdd2;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: #c62828;
        }}
        .error-icon {{
            font-size: 14px;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        .form-label {{
            display: block;
            font-size: 13px;
            font-weight: 500;
            color: #1d1d1f;
            margin-bottom: 6px;
        }}
        .form-input {{
            width: 100%;
            padding: 10px 12px;
            font-size: 15px;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            background: #fff;
            transition: all 0.2s;
            font-family: inherit;
        }}
        .form-input:focus {{
            outline: none;
            border-color: #007aff;
            box-shadow: 0 0 0 3px rgba(0,122,255,0.2);
        }}
        .btn-primary {{
            width: 100%;
            padding: 10px 20px;
            font-size: 15px;
            font-weight: 500;
            color: #fff;
            background: linear-gradient(180deg, #007aff 0%, #0055d4 100%);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}
        .btn-primary:hover {{
            background: linear-gradient(180deg, #0077ed 0%, #004fc4 100%);
            transform: scale(1.01);
        }}
        .btn-primary:active {{
            transform: scale(0.99);
        }}
        .footer-note {{
            text-align: center;
            margin-top: 16px;
            font-size: 11px;
            color: #86868b;
        }}
    </style>
</head>
<body>
    <div class="macos-window">
        <div class="window-header">
            <div class="traffic-lights">
                <div class="traffic-light light-close"></div>
                <div class="traffic-light light-minimize"></div>
                <div class="traffic-light light-maximize"></div>
            </div>
            <div class="window-title">TeleTask Report</div>
        </div>
        <div class="window-content">
            <div class="app-icon">
                <div class="app-icon-img">📋</div>
            </div>
            <div class="app-title">
                <h1>Tải báo cáo</h1>
                <p>Nhập mật khẩu để tải xuống file</p>
            </div>
            <div class="file-badge">
                <div class="file-badge-icon">{format_icons.get(file_format, '📄')}</div>
                <div class="file-badge-info">
                    <div class="file-badge-type">Báo cáo {format_names.get(file_format, file_format.upper())}</div>
                    <div class="file-badge-desc">Thống kê công việc TeleTask</div>
                </div>
            </div>
            {error_html}
            <form method="post">
                <div class="form-group">
                    <label class="form-label" for="password">Mật khẩu</label>
                    <input type="password" id="password" name="password" class="form-input" placeholder="Nhập mật khẩu..." required autofocus>
                </div>
                <button type="submit" class="btn-primary">Tải xuống</button>
            </form>
            <p class="footer-note">Link hết hạn sau 72 giờ</p>
        </div>
    </div>
</body>
</html>'''

    def _error_page(self, title: str, message: str) -> str:
        """Generate MacOS-style error HTML page."""
        return f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleTask - Lỗi</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif;
            background: linear-gradient(180deg, #f5f5f7 0%, #e8e8ed 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            -webkit-font-smoothing: antialiased;
        }}
        .macos-window {{
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 12px;
            max-width: 340px;
            width: 100%;
            box-shadow: 0 22px 70px 4px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
            overflow: hidden;
        }}
        .window-header {{
            background: linear-gradient(180deg, #e8e8e8 0%, #d6d6d6 100%);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        .traffic-lights {{
            display: flex;
            gap: 8px;
        }}
        .traffic-light {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.1);
        }}
        .light-close {{ background: #ff5f57; }}
        .light-minimize {{ background: #febc2e; }}
        .light-maximize {{ background: #28c840; }}
        .window-title {{
            flex: 1;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            color: #4d4d4d;
            margin-right: 52px;
        }}
        .window-content {{
            padding: 30px;
            text-align: center;
        }}
        .error-icon {{
            width: 64px;
            height: 64px;
            background: linear-gradient(180deg, #ff3b30 0%, #d32f2f 100%);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto 16px;
            box-shadow: 0 4px 12px rgba(255,59,48,0.3);
        }}
        h1 {{
            font-size: 18px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
        }}
        .message {{
            font-size: 13px;
            color: #86868b;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="macos-window">
        <div class="window-header">
            <div class="traffic-lights">
                <div class="traffic-light light-close"></div>
                <div class="traffic-light light-minimize"></div>
                <div class="traffic-light light-maximize"></div>
            </div>
            <div class="window-title">TeleTask</div>
        </div>
        <div class="window-content">
            <div class="error-icon">❌</div>
            <h1>{title}</h1>
            <p class="message">{message}</p>
        </div>
    </div>
</body>
</html>'''
