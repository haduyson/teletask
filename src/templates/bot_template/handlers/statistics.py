"""
Statistics Handler
Commands for viewing user statistics
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import get_or_create_user
from services.statistics_service import (
    calculate_user_stats,
    calculate_all_time_stats,
    get_week_range,
    get_previous_week_range,
    get_month_range,
    get_previous_month_range,
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
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Get all-time stats
        stats = await calculate_all_time_stats(db, db_user["id"])

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Tuần này", callback_data="stats_weekly"),
                    InlineKeyboardButton("Tháng này", callback_data="stats_monthly"),
                ],
            ]
        )

        text = format_stats_overview(stats, db_user.get("display_name") or user.full_name)
        await update.message.reply_text(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in thongke_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def thongketuan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongketuan command.
    Show this week's statistics.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        week_start, week_end = get_week_range()
        stats = await calculate_user_stats(db, db_user["id"], "weekly", week_start, week_end)

        prev_start, prev_end = get_previous_week_range()
        prev_stats = await calculate_user_stats(db, db_user["id"], "weekly", prev_start, prev_end)

        text = format_weekly_report(
            db_user.get("display_name") or user.full_name,
            stats,
            week_start,
            week_end,
            prev_stats=prev_stats,
        )
        await update.message.reply_text(text)

    except Exception as e:
        logger.error(f"Error in thongketuan_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def thongkethang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /thongkethang command.
    Show this month's statistics.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        month_start, month_end = get_month_range()
        stats = await calculate_user_stats(db, db_user["id"], "monthly", month_start, month_end)

        prev_start, prev_end = get_previous_month_range()
        prev_stats = await calculate_user_stats(db, db_user["id"], "monthly", prev_start, prev_end)

        text = format_monthly_report(
            db_user.get("display_name") or user.full_name,
            stats,
            prev_stats,
            month_start,
            month_end,
        )
        await update.message.reply_text(text)

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

        if data == "stats_weekly":
            week_start, week_end = get_week_range()
            stats = await calculate_user_stats(db, db_user["id"], "weekly", week_start, week_end)

            prev_start, prev_end = get_previous_week_range()
            prev_stats = await calculate_user_stats(db, db_user["id"], "weekly", prev_start, prev_end)

            text = format_weekly_report(
                db_user.get("display_name") or user.full_name,
                stats,
                week_start,
                week_end,
                prev_stats=prev_stats,
            )
            await query.edit_message_text(text)

        elif data == "stats_monthly":
            month_start, month_end = get_month_range()
            stats = await calculate_user_stats(db, db_user["id"], "monthly", month_start, month_end)

            prev_start, prev_end = get_previous_month_range()
            prev_stats = await calculate_user_stats(db, db_user["id"], "monthly", prev_start, prev_end)

            text = format_monthly_report(
                db_user.get("display_name") or user.full_name,
                stats,
                prev_stats,
                month_start,
                month_end,
            )
            await query.edit_message_text(text)

    except Exception as e:
        logger.error(f"Error in stats callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler("thongke", thongke_command),
        CommandHandler("thongketuan", thongketuan_command),
        CommandHandler("thongkethang", thongkethang_command),
    ]
