"""
Callback Query Handler
Routes inline button callbacks to appropriate handlers
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    update_task_status,
    update_task_progress,
    restore_task,
)
from utils import (
    MSG_TASK_RESTORED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_UNDO_EXPIRED,
    format_task_detail,
    task_detail_keyboard,
    progress_keyboard,
    undo_keyboard,
)
from handlers.task_delete import process_delete, process_restore

logger = logging.getLogger(__name__)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Route callback queries to appropriate handlers.

    Callback data format: action:param1:param2:...
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split(":")
    action = parts[0]

    try:
        db = get_db()
        user = update.effective_user
        db_user = await get_or_create_user(db, user)

        # Task complete
        if action == "task_complete":
            task_id = parts[1]
            await handle_complete(query, db, db_user, task_id, context.bot)

        # Task progress
        elif action == "task_progress":
            task_id = parts[1]
            await handle_progress_menu(query, task_id)

        # Progress update
        elif action == "progress":
            task_id = parts[1]
            value = int(parts[2])
            await handle_progress_update(query, db, db_user, task_id, value)

        # Task detail
        elif action == "task_detail":
            task_id = parts[1]
            await handle_detail(query, db, db_user, task_id)

        # Task delete
        elif action == "task_delete":
            task_id = parts[1]
            await handle_delete_confirm(query, task_id)

        # Confirm delete
        elif action == "confirm":
            if parts[1] == "delete":
                task_id = parts[2]
                await handle_delete(query, db, db_user, task_id, context.bot, context)

        # Cancel action
        elif action == "cancel":
            await query.edit_message_text("Đã huỷ.")

        # Undo delete
        elif action == "task_undo":
            undo_id = int(parts[1])
            await handle_undo(query, db, undo_id, context)

        # List navigation
        elif action == "list":
            list_type = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 1
            await handle_list_page(query, db, db_user, list_type, page)

        # No-op (for pagination display)
        elif action == "noop":
            pass

        # Statistics callbacks
        elif action in ("stats_weekly", "stats_monthly"):
            from handlers.statistics import handle_stats_callback
            await handle_stats_callback(update, context)

        else:
            logger.warning(f"Unknown callback action: {action}")

    except Exception as e:
        logger.error(f"Error in callback_router: {e}")
        await query.edit_message_text("Lỗi hệ thống. Vui lòng thử lại.")


async def handle_complete(query, db, db_user, task_id: str, bot) -> None:
    """Handle task completion callback."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    # Check permission
    if task["assignee_id"] != db_user["id"] and task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    # Update status
    await update_task_status(db, task["id"], "completed", db_user["id"])

    await query.edit_message_text(
        f"Đã hoàn thành việc {task_id}!\n\n"
        f"{task['content']}"
    )

    # Notify creator
    if task["creator_id"] != db_user["id"]:
        try:
            creator = await db.fetch_one(
                "SELECT telegram_id FROM users WHERE id = $1",
                task["creator_id"]
            )
            if creator:
                await bot.send_message(
                    chat_id=creator["telegram_id"],
                    text=f"Việc {task_id} đã được hoàn thành!\n\n"
                         f"Nội dung: {task['content']}\n"
                         f"Người thực hiện: {db_user.get('display_name', 'N/A')}",
                )
        except Exception as e:
            logger.warning(f"Could not notify creator: {e}")


async def handle_progress_menu(query, task_id: str) -> None:
    """Show progress selection menu."""
    await query.edit_message_text(
        f"Chọn tiến độ mới cho {task_id}:",
        reply_markup=progress_keyboard(task_id),
    )


async def handle_progress_update(query, db, db_user, task_id: str, value: int) -> None:
    """Handle progress update callback."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["assignee_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    await update_task_progress(db, task["id"], value, db_user["id"])

    # Progress bar
    filled = int(10 * value / 100)
    bar = "█" * filled + "░" * (10 - filled)

    status = "Hoàn thành!" if value == 100 else "Đang làm"

    await query.edit_message_text(
        f"Cập nhật tiến độ {task_id}!\n\n"
        f"{bar} {value}%\n"
        f"Trạng thái: {status}"
    )


async def handle_detail(query, db, db_user, task_id: str) -> None:
    """Show task detail."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    can_edit = task["creator_id"] == db_user["id"]
    can_complete = task["assignee_id"] == db_user["id"] and task["status"] != "completed"

    msg = format_task_detail(task)
    keyboard = task_detail_keyboard(task_id, can_edit=can_edit, can_complete=can_complete)

    await query.edit_message_text(msg, reply_markup=keyboard)


async def handle_delete_confirm(query, task_id: str) -> None:
    """Show delete confirmation."""
    from utils import confirm_keyboard

    await query.edit_message_text(
        f"Xác nhận xóa việc {task_id}?",
        reply_markup=confirm_keyboard("delete", task_id),
    )


async def handle_delete(query, db, db_user, task_id: str, bot, context=None) -> None:
    """Process task deletion with countdown timer."""
    success, result = await process_delete(db, task_id, db_user["id"], bot)

    if success:
        undo_id = result
        message = await query.edit_message_text(
            f"🗑️ Đã xóa việc {task_id}!\n\n"
            f"Bấm nút bên dưới để hoàn tác.",
            reply_markup=undo_keyboard(undo_id, 30),
        )

        # Schedule countdown updates if context is available
        if context and context.job_queue:
            chat_id = query.message.chat_id
            message_id = query.message.message_id

            # Schedule countdown updates every 5 seconds
            for seconds in [25, 20, 15, 10, 5]:
                context.job_queue.run_once(
                    countdown_update_job,
                    when=30 - seconds,
                    data={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "task_id": task_id,
                        "undo_id": undo_id,
                        "seconds": seconds,
                    },
                    name=f"undo_countdown_{undo_id}_{seconds}",
                )

            # Schedule final expiry message
            context.job_queue.run_once(
                countdown_expired_job,
                when=30,
                data={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "task_id": task_id,
                    "undo_id": undo_id,
                },
                name=f"undo_expired_{undo_id}",
            )
    else:
        await query.edit_message_text(result)


async def countdown_update_job(context) -> None:
    """Job to update undo button countdown."""
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]
    task_id = job_data["task_id"]
    undo_id = job_data["undo_id"]
    seconds = job_data["seconds"]

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🗑️ Đã xóa việc {task_id}!\n\n"
                 f"Bấm nút bên dưới để hoàn tác.",
            reply_markup=undo_keyboard(undo_id, seconds),
        )
    except Exception as e:
        # Message may have been modified by user clicking undo
        logger.debug(f"Could not update countdown: {e}")


async def countdown_expired_job(context) -> None:
    """Job to handle undo expiry."""
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]
    task_id = job_data["task_id"]
    undo_id = job_data["undo_id"]

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🗑️ Đã xóa việc {task_id}!\n\n"
                 f"⏰ Đã hết thời gian hoàn tác.",
        )
    except Exception as e:
        logger.debug(f"Could not update expired message: {e}")


async def handle_undo(query, db, undo_id: int, context=None) -> None:
    """Handle undo deletion."""
    # Cancel any pending countdown jobs
    if context and context.job_queue:
        for seconds in [25, 20, 15, 10, 5]:
            jobs = context.job_queue.get_jobs_by_name(f"undo_countdown_{undo_id}_{seconds}")
            for job in jobs:
                job.schedule_removal()
        # Cancel expired job
        expired_jobs = context.job_queue.get_jobs_by_name(f"undo_expired_{undo_id}")
        for job in expired_jobs:
            job.schedule_removal()

    success, result = await process_restore(db, undo_id)

    if success:
        task = result
        await query.edit_message_text(
            MSG_TASK_RESTORED.format(task_id=task["public_id"])
        )
    else:
        await query.edit_message_text(result)


async def handle_list_page(query, db, db_user, list_type: str, page: int) -> None:
    """Handle list pagination."""
    from services import get_user_tasks, get_user_created_tasks, get_group_tasks
    from utils import format_task_list, task_list_with_pagination

    page_size = 10
    offset = (page - 1) * page_size

    if list_type == "personal":
        tasks = await get_user_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "VIỆC CÁ NHÂN CỦA BẠN"
    elif list_type == "assigned":
        tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "VIỆC BẠN ĐÃ GIAO"
    else:
        tasks = await get_user_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "DANH SÁCH VIỆC"

    if not tasks:
        await query.edit_message_text("Không có việc nào.")
        return

    # Estimate total pages (simplified)
    total_pages = page + (1 if len(tasks) == page_size else 0)

    msg = format_task_list(
        tasks=tasks,
        title=title,
        page=page,
        total=len(tasks) + offset,
    )

    await query.edit_message_text(
        msg,
        reply_markup=task_list_with_pagination(tasks, page, total_pages, list_type),
    )


def get_handlers() -> list:
    """Return callback query handler."""
    return [
        CallbackQueryHandler(callback_router),
    ]
