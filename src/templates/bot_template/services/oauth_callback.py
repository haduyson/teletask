"""
OAuth Callback Handler
HTTP endpoint to receive Google OAuth callback
"""

import logging
import os
from aiohttp import web

from database import get_db
from services.calendar_service import (
    exchange_code_for_tokens,
    save_user_tokens,
)
from services.user_service import get_user_by_telegram_id

logger = logging.getLogger(__name__)

# OAuth callback port
OAUTH_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8081"))


def _macos_page(title: str, icon: str, heading: str, message: str, is_success: bool = False) -> str:
    """Generate MacOS-style HTML page."""
    icon_bg = "linear-gradient(180deg, #34c759 0%, #248a3d 100%)" if is_success else "linear-gradient(180deg, #ff3b30 0%, #d32f2f 100%)"
    icon_shadow = "rgba(52,199,89,0.3)" if is_success else "rgba(255,59,48,0.3)"

    return f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleTask - {title}</title>
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
            text-align: center;
        }}
        .status-icon {{
            width: 64px;
            height: 64px;
            background: {icon_bg};
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto 16px;
            box-shadow: 0 4px 12px {icon_shadow};
        }}
        h1 {{
            font-size: 18px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 12px;
        }}
        .message {{
            font-size: 13px;
            color: #86868b;
            line-height: 1.6;
        }}
        .message code {{
            background: #f5f5f7;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            color: #007aff;
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
            <div class="window-title">Google Calendar</div>
        </div>
        <div class="window-content">
            <div class="status-icon">{icon}</div>
            <h1>{heading}</h1>
            <p class="message">{message}</p>
        </div>
    </div>
</body>
</html>'''


async def oauth_callback_handler(request: web.Request) -> web.Response:
    """
    Handle OAuth callback from Google.

    Query params:
        code: Authorization code
        state: User's Telegram ID
    """
    try:
        code = request.query.get("code")
        state = request.query.get("state")  # Telegram user ID
        error = request.query.get("error")

        if error:
            return web.Response(
                text=_macos_page(
                    "Lỗi",
                    "❌",
                    "Kết nối thất bại",
                    f"Lỗi: {error}<br><br>Vui lòng thử lại trong Telegram."
                ),
                content_type="text/html"
            )

        if not code or not state:
            return web.Response(
                text=_macos_page(
                    "Lỗi",
                    "❌",
                    "Thiếu thông tin",
                    "Vui lòng thử lại từ đầu trong Telegram."
                ),
                content_type="text/html"
            )

        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(code)

        if not tokens:
            return web.Response(
                text=_macos_page(
                    "Lỗi",
                    "❌",
                    "Không thể lấy token",
                    "Vui lòng thử lại trong Telegram."
                ),
                content_type="text/html"
            )

        # Get user by Telegram ID
        db = get_db()
        telegram_id = int(state)
        db_user = await get_user_by_telegram_id(db, telegram_id)

        if not db_user:
            return web.Response(
                text=_macos_page(
                    "Lỗi",
                    "❌",
                    "Không tìm thấy người dùng",
                    "Vui lòng gửi <code>/start</code> trong bot trước khi kết nối."
                ),
                content_type="text/html"
            )

        # Save tokens
        success = await save_user_tokens(
            db,
            db_user["id"],
            tokens["access_token"],
            tokens["refresh_token"],
        )

        if success:
            return web.Response(
                text=_macos_page(
                    "Thành công",
                    "✅",
                    "Kết nối thành công!",
                    "Google Calendar đã được kết nối với tài khoản Telegram của bạn.<br><br>"
                    "Bạn có thể đóng trang này và quay lại Telegram.<br><br>"
                    "Sử dụng <code>/lichgoogle</code> để xem tùy chọn.",
                    is_success=True
                ),
                content_type="text/html"
            )
        else:
            return web.Response(
                text=_macos_page(
                    "Lỗi",
                    "❌",
                    "Lỗi lưu token",
                    "Vui lòng thử lại trong Telegram."
                ),
                content_type="text/html"
            )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return web.Response(
            text=_macos_page(
                "Lỗi",
                "❌",
                "Lỗi hệ thống",
                "Vui lòng thử lại trong Telegram."
            ),
            content_type="text/html"
        )


async def start_oauth_server(app_runner=None) -> web.AppRunner:
    """
    Start the OAuth callback HTTP server.

    Returns:
        AppRunner instance
    """
    app = web.Application()
    app.router.add_get("/oauth/callback", oauth_callback_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", OAUTH_PORT)
    await site.start()

    logger.info(f"OAuth callback server started on port {OAUTH_PORT}")
    return runner


async def stop_oauth_server(runner: web.AppRunner) -> None:
    """Stop the OAuth callback server."""
    if runner:
        await runner.cleanup()
        logger.info("OAuth callback server stopped")
