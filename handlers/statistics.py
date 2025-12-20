"""
Statistics Handler
Commands for viewing user statistics
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import get_or_create_user, get_or_create_group
from services.statistics_service import (
    calculate_user_stats,
    calculate_all_time_stats,
    get_week_range,
    get_previous_week_range,
    get_month_range,
    get_previous_month_range,
    get_overdue_tasks,
    get_overdue_stats,
)
from utils.formatters import (
    format_stats_overview,
    format_weekly_report,
    format_monthly_report,
)
from utils import ERR_DATABASE

logger = logging.getLogger(__name__)


async def thongke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongke command.
    Show overview statistics.
    In group chat: Only stats for that group
    In private chat: All stats
    """
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Detect group context for filtering
        is_group = chat.type in ["group", "supergroup"]
        group_id = None
        group_note = ""
        if is_group:
            group = await get_or_create_group(db, chat.id, chat.title or "Unknown")
            group_id = group["id"]
            group_note = f"\n\n_Chỉ thống kê trong nhóm {chat.title}_"

        # Get all-time stats (pass group_id for filtering)
        stats = await calculate_all_time_stats(db, db_user["id"], group_id)

        # Encode group_id in callback data
        g = f":{group_id}" if group_id else ":0"
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Tuần này", callback_data=f"stats_weekly{g}"),
                    InlineKeyboardButton("Tháng này", callback_data=f"stats_monthly{g}"),
                ],
            ]
        )

        text = format_stats_overview(stats, db_user.get("display_name") or user.full_name) + group_note
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in thongke_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def thongketuan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongketuan command.
    Show this week's statistics.
    In group chat: Only stats for that group
    In private chat: All stats
    """
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Detect group context for filtering
        is_group = chat.type in ["group", "supergroup"]
        group_id = None
        group_note = ""
        if is_group:
            group = await get_or_create_group(db, chat.id, chat.title or "Unknown")
            group_id = group["id"]
            group_note = f"\n\n_Chỉ thống kê trong nhóm {chat.title}_"

        week_start, week_end = get_week_range()
        stats = await calculate_user_stats(db, db_user["id"], "weekly", week_start, week_end, group_id)

        prev_start, prev_end = get_previous_week_range()
        prev_stats = await calculate_user_stats(db, db_user["id"], "weekly", prev_start, prev_end, group_id)

        text = format_weekly_report(
            db_user.get("display_name") or user.full_name,
            stats,
            week_start,
            week_end,
            prev_stats=prev_stats,
        ) + group_note
        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in thongketuan_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def thongkethang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongkethang command.
    Show this month's statistics.
    In group chat: Only stats for that group
    In private chat: All stats
    """
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Detect group context for filtering
        is_group = chat.type in ["group", "supergroup"]
        group_id = None
        group_note = ""
        if is_group:
            group = await get_or_create_group(db, chat.id, chat.title or "Unknown")
            group_id = group["id"]
            group_note = f"\n\n_Chỉ thống kê trong nhóm {chat.title}_"

        month_start, month_end = get_month_range()
        stats = await calculate_user_stats(db, db_user["id"], "monthly", month_start, month_end, group_id)

        prev_start, prev_end = get_previous_month_range()
        prev_stats = await calculate_user_stats(db, db_user["id"], "monthly", prev_start, prev_end, group_id)

        text = format_monthly_report(
            db_user.get("display_name") or user.full_name,
            stats,
            prev_stats,
            month_start,
            month_end,
        ) + group_note
        await update.message.reply_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in thongkethang_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle statistics callback queries."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Parse group_id from callback data (format: stats_weekly:123 or stats_weekly:0)
        group_id = None
        group_note = ""
        if ":" in data:
            parts = data.split(":")
            data = parts[0]
            try:
                gid = int(parts[1])
                if gid > 0:
                    group_id = gid
                    # Get group name for display
                    group_row = await db.fetch_one("SELECT title FROM groups WHERE id = $1", group_id)
                    if group_row:
                        group_note = f"\n\n_Chỉ thống kê trong nhóm {group_row['title']}_"
            except (ValueError, IndexError):
                pass

        if data == "stats_weekly":
            week_start, week_end = get_week_range()
            stats = await calculate_user_stats(db, db_user["id"], "weekly", week_start, week_end, group_id)

            prev_start, prev_end = get_previous_week_range()
            prev_stats = await calculate_user_stats(db, db_user["id"], "weekly", prev_start, prev_end, group_id)

            text = format_weekly_report(
                db_user.get("display_name") or user.full_name,
                stats,
                week_start,
                week_end,
                prev_stats=prev_stats,
            ) + group_note
            await query.edit_message_text(text, parse_mode="Markdown")

        elif data == "stats_monthly":
            month_start, month_end = get_month_range()
            stats = await calculate_user_stats(db, db_user["id"], "monthly", month_start, month_end, group_id)

            prev_start, prev_end = get_previous_month_range()
            prev_stats = await calculate_user_stats(db, db_user["id"], "monthly", prev_start, prev_end, group_id)

            text = format_monthly_report(
                db_user.get("display_name") or user.full_name,
                stats,
                prev_stats,
                month_start,
                month_end,
            ) + group_note
            await query.edit_message_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in stats callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


async def viectrehan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /viectrehan command.
    Show overdue tasks for current month by default.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Get overdue statistics
        stats = await get_overdue_stats(db, db_user["id"])

        # Get current month name in Vietnamese
        import datetime
        now = datetime.datetime.now()
        month_names = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
                       "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]
        current_month = month_names[now.month]

        # Default: show current month overdue
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"📅 Hôm nay ({stats['today']})", callback_data="overdue_day"),
                InlineKeyboardButton(f"📆 Tuần này ({stats['this_week']})", callback_data="overdue_week"),
            ],
            [
                InlineKeyboardButton(f"📊 Tất cả ({stats['total']})", callback_data="overdue_all"),
            ],
        ])

        text = f"""🔴 VIỆC TRỄ HẠN - {current_month.upper()}

📊 Trễ hạn tháng này: {stats['this_month']} việc

Thống kê chi tiết:
• Hôm nay: {stats['today']} việc
• Tuần này: {stats['this_week']} việc
• Tổng tất cả: {stats['total']} việc

Xem theo khoảng thời gian khác:"""

        # If there are overdue tasks this month, show them directly
        if stats['this_month'] > 0:
            tasks = await get_overdue_tasks(db, db_user["id"], "month")
            from utils.formatters import format_datetime, get_status_icon

            lines = []
            for task in tasks[:10]:  # Show first 10
                icon = get_status_icon(task)
                deadline_str = format_datetime(task.get("deadline"), relative=True)
                content = task.get("content", "")[:35]
                if len(task.get("content", "")) > 35:
                    content += "..."
                lines.append(f"{icon} {task['public_id']}: {content}\n   📅 {deadline_str}")

            task_list = "\n\n".join(lines)
            shown = min(10, stats['this_month'])

            text = f"""🔴 VIỆC TRỄ HẠN - {current_month.upper()}

Tổng: {stats['this_month']} việc trễ hạn{f' (hiện {shown} đầu tiên)' if stats["this_month"] > 10 else ''}

{task_list}

Xem chi tiết: /xemviec [mã việc]
Hoàn thành: /xong [mã việc]

📊 Xem thêm:"""

        await update.message.reply_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in viectrehan_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def handle_overdue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle overdue task list callback queries."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    # Get current month name
    import datetime
    now = datetime.datetime.now()
    month_names = ["", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
                   "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"]

    period_map = {
        "overdue_day": ("day", "HÔM NAY"),
        "overdue_week": ("week", "TUẦN NÀY"),
        "overdue_month": ("month", month_names[now.month].upper()),
        "overdue_all": ("all", "TẤT CẢ THỜI GIAN"),
    }

    if data not in period_map:
        return

    period, period_label = period_map[data]

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        tasks = await get_overdue_tasks(db, db_user["id"], period)

        if not tasks:
            await query.edit_message_text(
                f"🔴 VIỆC TRỄ HẠN - {period_label}\n\n"
                "✅ Không có việc trễ hạn trong khoảng thời gian này!"
            )
            return

        # Format task list
        from utils.formatters import format_datetime, get_status_icon

        lines = []
        for task in tasks[:20]:  # Limit to 20 tasks
            icon = get_status_icon(task)
            deadline_str = format_datetime(task.get("deadline"), relative=True)
            content = task.get("content", "")[:40]
            if len(task.get("content", "")) > 40:
                content += "..."
            lines.append(f"{icon} {task['public_id']}: {content}\n   📅 {deadline_str}")

        task_list = "\n\n".join(lines)
        total = len(tasks)
        shown = min(20, total)

        text = f"""🔴 VIỆC TRỄ HẠN - {period_label}

Tổng: {total} việc{f' (hiện {shown} đầu tiên)' if total > 20 else ''}

{task_list}

Xem chi tiết: /xemviec [mã việc]
Hoàn thành: /xong [mã việc]"""

        await query.edit_message_text(text)

    except Exception as e:
        logger.error(f"Error in overdue callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("thongke", thongke_command),
        CommandHandler("thongketuan", thongketuan_command),
        CommandHandler("thongkethang", thongkethang_command),
        CommandHandler(["viectrehan", "trehan"], viectrehan_command),
    ]
