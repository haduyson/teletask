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
                text=f"""
                <html>
                <head><meta charset="UTF-8"><title>Lỗi</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Kết nối thất bại</h2>
                    <p>Lỗi: {error}</p>
                    <p>Vui lòng thử lại trong Telegram.</p>
                </body>
                </html>
                """,
                content_type="text/html"
            )

        if not code or not state:
            return web.Response(
                text="""
                <html>
                <head><meta charset="UTF-8"><title>Lỗi</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Thiếu thông tin</h2>
                    <p>Vui lòng thử lại từ đầu trong Telegram.</p>
                </body>
                </html>
                """,
                content_type="text/html"
            )

        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(code)

        if not tokens:
            return web.Response(
                text="""
                <html>
                <head><meta charset="UTF-8"><title>Lỗi</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Không thể lấy token</h2>
                    <p>Vui lòng thử lại trong Telegram.</p>
                </body>
                </html>
                """,
                content_type="text/html"
            )

        # Get user by Telegram ID
        db = get_db()
        telegram_id = int(state)
        db_user = await get_user_by_telegram_id(db, telegram_id)

        if not db_user:
            return web.Response(
                text="""
                <html>
                <head><meta charset="UTF-8"><title>Lỗi</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Không tìm thấy người dùng</h2>
                    <p>Vui lòng gửi /start trong bot trước khi kết nối.</p>
                </body>
                </html>
                """,
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
                text="""
                <html>
                <head><meta charset="UTF-8"><title>Thành công</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>✅ Kết nối thành công!</h2>
                    <p>Google Calendar đã được kết nối với tài khoản Telegram của bạn.</p>
                    <p>Bạn có thể đóng trang này và quay lại Telegram.</p>
                    <p>Sử dụng <code>/lichgoogle</code> để xem tùy chọn.</p>
                </body>
                </html>
                """,
                content_type="text/html"
            )
        else:
            return web.Response(
                text="""
                <html>
                <head><meta charset="UTF-8"><title>Lỗi</title></head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h2>❌ Lỗi lưu token</h2>
                    <p>Vui lòng thử lại trong Telegram.</p>
                </body>
                </html>
                """,
                content_type="text/html"
            )

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return web.Response(
            text=f"""
            <html>
            <head><meta charset="UTF-8"><title>Lỗi</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h2>❌ Lỗi hệ thống</h2>
                <p>Vui lòng thử lại trong Telegram.</p>
            </body>
            </html>
            """,
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
