"""
Callback Query Handler
Routes inline button callbacks to appropriate handlers
"""

import logging
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters


# =============================================================================
# Rate Limiting
# =============================================================================
_rate_limits: dict = defaultdict(list)
RATE_LIMIT = 30  # max requests per window
RATE_WINDOW = 60  # seconds


def rate_limit(func: Callable) -> Callable:
    """Rate limit decorator for callback handlers."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        now = time.time()

        # Clean old entries
        _rate_limits[user_id] = [
            t for t in _rate_limits[user_id]
            if now - t < RATE_WINDOW
        ]

        if len(_rate_limits[user_id]) >= RATE_LIMIT:
            await update.callback_query.answer(
                "⚠️ Quá nhiều yêu cầu. Vui lòng đợi.",
                show_alert=True
            )
            return

        _rate_limits[user_id].append(now)
        return await func(update, context)
    return wrapper

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    update_task_status,
    update_task_progress,
    update_task_content,
    update_task_deadline,
    update_task_priority,
    update_task_assignee,
    restore_task,
    parse_vietnamese_time,
    get_user_by_username,
    bulk_delete_tasks,
)
from utils import (
    MSG_TASK_RESTORED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_UNDO_EXPIRED,
    format_task_detail,
    format_datetime,
    format_priority,
    task_detail_keyboard,
    task_category_keyboard,
    progress_keyboard,
    undo_keyboard,
    edit_menu_keyboard,
    edit_priority_keyboard,
    mention_user,
)
from handlers.task_delete import process_delete, process_restore

logger = logging.getLogger(__name__)


# Callback validation constants
# Task ID pattern: P0001, G0001, etc.
TASK_ID_PATTERN = re.compile(r'^[PG]\d{4,8}$')

# Valid priorities
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}

# Valid list types
VALID_LIST_TYPES = {"all", "personal", "assigned", "received"}

# Valid filter types
VALID_FILTER_TYPES = {"all", "individual", "group"}

# Valid category types
VALID_CATEGORIES = {"menu", "personal", "assigned", "received", "all"}


def validate_task_id(task_id: str) -> Optional[str]:
    """
    Validate task ID format.

    Args:
        task_id: Task ID to validate

    Returns:
        Validated task ID or None if invalid
    """
    if not task_id:
        return None

    task_id = task_id.strip().upper()

    if not TASK_ID_PATTERN.match(task_id):
        return None

    return task_id


def validate_int(value: str, min_val: int = 0, max_val: int = 10000) -> Optional[int]:
    """
    Validate and convert string to integer with bounds.

    Args:
        value: String value to convert
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated integer or None if invalid
    """
    if not value:
        return None

    try:
        num = int(value)
        if min_val <= num <= max_val:
            return num
        return None
    except (ValueError, TypeError):
        return None


def validate_priority(priority: str) -> Optional[str]:
    """
    Validate priority value.

    Args:
        priority: Priority string

    Returns:
        Validated priority or None if invalid
    """
    if not priority:
        return None

    priority = priority.strip().lower()
    return priority if priority in VALID_PRIORITIES else None


def validate_list_type(list_type: str) -> str:
    """
    Validate list type, default to 'all'.

    Args:
        list_type: List type string

    Returns:
        Validated list type or 'all'
    """
    if not list_type:
        return "all"

    list_type = list_type.strip().lower()
    return list_type if list_type in VALID_LIST_TYPES else "all"


def parse_callback_data(data: str) -> Tuple[str, list]:
    """
    Parse callback data safely.

    Args:
        data: Raw callback data string

    Returns:
        Tuple of (action, params)
    """
    if not data:
        return ("", [])

    # Limit total length to prevent abuse
    if len(data) > 200:
        return ("", [])

    parts = data.split(":")
    action = parts[0].strip().lower() if parts else ""

    return (action, parts[1:])


async def safe_edit_message(query, text: str, reply_markup=None, parse_mode=None) -> bool:
    """
    Safely edit message, catching 'Message is not modified' errors.

    Args:
        query: CallbackQuery object
        text: New message text
        reply_markup: Optional keyboard markup
        parse_mode: Optional parse mode

    Returns:
        True if edit succeeded, False if skipped due to same content
    """
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg:
            # Content unchanged - this is not a real error
            logger.debug(f"Skipped edit: message unchanged")
            return False
        # Re-raise other errors
        raise


@rate_limit
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Route callback queries to appropriate handlers.

    Callback data format: action:param1:param2:...
    All parameters are validated before use.
    """
    query = update.callback_query
    await query.answer()

    data = query.data

    # Parse and validate callback data
    action, params = parse_callback_data(data)

    # Handle special prefixes first (before main routing)
    if data and data.startswith("overdue_"):
        from handlers.statistics import handle_overdue_callback
        await handle_overdue_callback(update, context)
        return

    if data and data.startswith("cal_"):
        # Calendar callbacks handled elsewhere
        return

    try:
        db = get_db()
        user = update.effective_user
        db_user = await get_or_create_user(db, user)

        # Task complete
        if action == "task_complete":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_complete(query, db, db_user, task_id, context.bot)

        # Task progress
        elif action == "task_progress":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_progress_menu(query, task_id)

        # Progress update
        elif action == "progress":
            task_id = validate_task_id(params[0] if params else "")
            value = validate_int(params[1] if len(params) > 1 else "", min_val=0, max_val=100)

            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            if value is None:
                await query.edit_message_text("Giá trị tiến độ phải từ 0-100.")
                return

            await handle_progress_update(query, db, db_user, task_id, value)

        # Task detail
        elif action == "task_detail":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_detail(query, db, db_user, task_id)

        # Task delete
        elif action == "task_delete":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_delete_confirm(query, task_id)

        # Confirm delete
        elif action == "confirm":
            if len(params) >= 2 and params[0] == "delete":
                task_id = validate_task_id(params[1])
                if not task_id:
                    await query.edit_message_text("Mã việc không hợp lệ.")
                    return
                await handle_delete(query, db, db_user, task_id, context.bot, context)

        # Cancel action
        elif action == "cancel":
            await query.edit_message_text("Đã huỷ.")

        # Undo delete
        elif action == "task_undo":
            undo_id = validate_int(params[0] if params else "", min_val=1)
            if undo_id is None:
                await query.edit_message_text("Dữ liệu không hợp lệ.")
                return
            await handle_undo(query, db, undo_id, context)

        # Bulk undo delete
        elif action == "bulk_undo":
            undo_id = validate_int(params[0] if params else "", min_val=1)
            if undo_id is None:
                await query.edit_message_text("Dữ liệu không hợp lệ.")
                return
            await handle_bulk_undo(query, db, undo_id, context)

        # List navigation
        elif action == "list":
            list_type = validate_list_type(params[0] if params else "all")
            page = validate_int(params[1] if len(params) > 1 else "1", min_val=1, max_val=1000) or 1
            # Parse group_id from callback data (format: list:type:page:gN)
            group_id = None
            if len(params) > 2 and params[2].startswith("g"):
                try:
                    gid = int(params[2][1:])
                    if gid > 0:
                        group_id = gid
                except ValueError:
                    pass
            await handle_list_page(query, db, db_user, list_type, page, group_id)

        # No-op (for pagination display)
        elif action == "noop":
            pass

        # Task edit menu
        elif action == "task_edit":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_edit_menu(query, db, db_user, task_id)

        # Edit content prompt
        elif action == "edit_content":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_edit_content_prompt(query, db, db_user, task_id, context)

        # Edit deadline prompt
        elif action == "edit_deadline":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_edit_deadline_prompt(query, db, db_user, task_id, context)

        # Edit priority menu
        elif action == "edit_priority":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_edit_priority_menu(query, db, db_user, task_id)

        # Set priority
        elif action == "set_priority":
            task_id = validate_task_id(params[0] if params else "")
            priority = validate_priority(params[1] if len(params) > 1 else "")

            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            if not priority:
                await query.edit_message_text("Độ ưu tiên không hợp lệ.")
                return

            await handle_set_priority(query, db, db_user, task_id, priority)

        # Edit assignee prompt
        elif action == "edit_assignee":
            task_id = validate_task_id(params[0] if params else "")
            if not task_id:
                await query.edit_message_text("Mã việc không hợp lệ.")
                return
            await handle_edit_assignee_prompt(query, db, db_user, task_id, context)

        # Task category menu
        elif action == "task_category":
            category = params[0].lower() if params else "menu"
            if category not in VALID_CATEGORIES:
                category = "menu"
            # Parse group_id from callback data (format: task_category:category:gN)
            group_id = None
            if len(params) > 1 and params[1].startswith("g"):
                try:
                    group_id = int(params[1][1:])  # Extract number after 'g'
                except ValueError:
                    pass
            await handle_task_category(query, db, db_user, category, group_id)

        # Task type filter (Individual/Group)
        elif action == "task_filter":
            filter_type = params[0].lower() if params else "all"
            if filter_type not in VALID_FILTER_TYPES:
                filter_type = "all"
            # Parse group_id from callback data
            group_id = None
            if len(params) > 1 and params[1].startswith("g"):
                try:
                    group_id = int(params[1][1:])
                except ValueError:
                    pass
            list_type = validate_list_type(params[2] if len(params) > 2 else "all")
            await handle_task_filter(query, db, db_user, filter_type, list_type, group_id)

        # Statistics callbacks
        elif action in ("stats_weekly", "stats_monthly"):
            from handlers.statistics import handle_stats_callback
            await handle_stats_callback(update, context)

        # Bulk delete callbacks
        elif action == "bulk_delete":
            if len(params) < 2:
                await query.edit_message_text("Dữ liệu không hợp lệ.")
                return

            delete_type = params[0].lower()
            confirm_action = params[1].lower()

            if delete_type not in {"all", "assigned"}:
                await query.edit_message_text("Loại xóa không hợp lệ.")
                return
            if confirm_action not in {"confirm", "cancel"}:
                await query.edit_message_text("Hành động không hợp lệ.")
                return

            await handle_bulk_delete(query, db, db_user, delete_type, confirm_action, context)

        else:
            if action:
                logger.warning(f"Unknown callback action: {action}")

    except IndexError:
        logger.warning(f"Callback data missing params: {data}")
        await query.edit_message_text("Dữ liệu không đầy đủ.")
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
    updated_task = await update_task_status(db, task["id"], "completed", db_user["id"])

    await query.edit_message_text(
        f"Đã hoàn thành việc {task_id}!\n\n"
        f"{task['content']}"
    )

    # Notify task creator/assigner
    from services.notification import send_task_completed_to_assigner
    await send_task_completed_to_assigner(bot, db, updated_task or task, db_user)


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
        f"Cập nhật tiến độ <b>{task_id}</b>!\n\n"
        f"{bar} {value}%\n"
        f"<b>Trạng thái:</b> {status}",
        parse_mode="HTML",
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

    await query.edit_message_text(msg, reply_markup=keyboard, parse_mode="HTML")


async def handle_delete_confirm(query, task_id: str) -> None:
    """Show delete confirmation."""
    from utils import confirm_keyboard

    await query.edit_message_text(
        f"Xác nhận xóa việc {task_id}?",
        reply_markup=confirm_keyboard("delete", task_id),
    )


async def handle_delete(query, db, db_user, task_id: str, bot, context=None) -> None:
    """Process task deletion with countdown timer (10 seconds)."""
    success, result = await process_delete(db, task_id, db_user["id"], bot)

    if success:
        undo_id = result
        message = await query.edit_message_text(
            f"🗑️ Đã xóa việc {task_id}!\n\n"
            f"Bấm nút bên dưới để hoàn tác.",
            reply_markup=undo_keyboard(undo_id, 10),
        )

        # Schedule countdown updates if context is available
        if context and context.job_queue:
            chat_id = query.message.chat_id
            message_id = query.message.message_id

            # Schedule countdown updates every second (10s -> 1s)
            for seconds in range(9, 0, -1):
                context.job_queue.run_once(
                    countdown_update_job,
                    when=10 - seconds,
                    data={
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "task_id": task_id,
                        "undo_id": undo_id,
                        "seconds": seconds,
                    },
                    name=f"undo_countdown_{undo_id}_{seconds}",
                )

            # Schedule final expiry message at 10 seconds
            context.job_queue.run_once(
                countdown_expired_job,
                when=10,
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
        # Check if undo was already performed
        db = get_db()
        undo_record = await db.fetch_one(
            "SELECT is_restored FROM deleted_tasks_undo WHERE id = $1",
            undo_id
        )
        if not undo_record or undo_record["is_restored"]:
            return  # Undo already performed, skip update

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
        # Check if undo was already performed
        db = get_db()
        undo_record = await db.fetch_one(
            "SELECT is_restored FROM deleted_tasks_undo WHERE id = $1",
            undo_id
        )
        if not undo_record or undo_record["is_restored"]:
            return  # Undo already performed, skip expiry message

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
    # Cancel any pending countdown jobs (9s -> 1s)
    if context and context.job_queue:
        for seconds in range(9, 0, -1):
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


async def handle_bulk_undo(query, db, undo_id: int, context=None) -> None:
    """Handle bulk undo deletion."""
    from services import bulk_restore_tasks

    # Cancel any pending countdown jobs
    if context:
        job_queue = context.application.job_queue if hasattr(context, 'application') else context.job_queue
        if job_queue:
            current_jobs = job_queue.jobs()
            for job in current_jobs:
                if job.name and f"bulk_undo_{undo_id}" in job.name:
                    job.schedule_removal()

    restored_count = await bulk_restore_tasks(db, undo_id)

    if restored_count > 0:
        await query.edit_message_text(
            f"↩️ Đã hoàn tác xóa <b>{restored_count}</b> việc!",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            "❌ Không thể hoàn tác. Đã hết thời gian (10 giây).",
        )


async def handle_list_page(query, db, db_user, list_type: str, page: int, group_id: int = None) -> None:
    """Handle list pagination.

    Args:
        group_id: If provided, filter tasks to this group only.
    """
    from services import (
        get_user_personal_tasks,
        get_user_created_tasks,
        get_user_received_tasks,
        get_all_user_related_tasks,
    )
    from utils import task_list_with_pagination

    page_size = 10
    offset = (page - 1) * page_size
    g_suffix = f":g{group_id}" if group_id else ":g0"

    if list_type == "personal":
        tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size, offset=offset, group_id=group_id)
        title = "📋 VIỆC CÁ NHÂN"
    elif list_type == "assigned":
        tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size, offset=offset, group_id=group_id)
        title = "📤 VIỆC ĐÃ GIAO"
    elif list_type == "received":
        tasks = await get_user_received_tasks(db, db_user["id"], limit=page_size, offset=offset, group_id=group_id)
        title = "📥 VIỆC ĐÃ NHẬN"
    else:  # all
        tasks = await get_all_user_related_tasks(db, db_user["id"], limit=page_size, offset=offset, group_id=group_id)
        title = "📊 TẤT CẢ VIỆC"

    if not tasks:
        await safe_edit_message(
            query,
            f"{title}\n\n📭 Không có việc nào.",
            reply_markup=task_category_keyboard(group_id),
        )
        return

    # Estimate total pages (simplified)
    total_pages = page + (1 if len(tasks) == page_size else 0)
    total_count = len(tasks) + offset

    # Show only title with count - task list is in buttons
    group_note = " (trong nhóm)" if group_id else ""
    msg = f"{title}{group_note}\n\nTổng: {total_count} việc | Trang {page}/{total_pages}\n\nChọn việc để xem chi tiết:"

    await safe_edit_message(
        query,
        msg,
        reply_markup=task_list_with_pagination(tasks, page, total_pages, list_type, group_id),
    )


async def handle_task_category(query, db, db_user, category: str, group_id: int = None) -> None:
    """Handle task category selection.

    Args:
        group_id: If provided, filter tasks to this group only (0 = no filter)
    """
    from services import (
        get_user_personal_tasks,
        get_user_created_tasks,
        get_user_received_tasks,
        get_all_user_related_tasks,
    )
    from utils import task_list_with_pagination

    page_size = 10

    # Parse group_id (0 means no filter)
    gid = group_id if group_id and group_id > 0 else None
    g_suffix = f":g{group_id}" if group_id else ":g0"

    if category == "menu":
        # Show category menu with filter options
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Việc cá nhân", callback_data=f"task_category:personal{g_suffix}")],
            [InlineKeyboardButton("📤 Việc đã giao", callback_data=f"task_category:assigned{g_suffix}")],
            [InlineKeyboardButton("📥 Việc đã nhận", callback_data=f"task_category:received{g_suffix}")],
            [InlineKeyboardButton("📊 Tất cả việc", callback_data=f"task_category:all{g_suffix}")],
            [
                InlineKeyboardButton("👤 Lọc: Cá nhân", callback_data=f"task_filter:individual{g_suffix}"),
                InlineKeyboardButton("👥 Lọc: Nhóm", callback_data=f"task_filter:group{g_suffix}"),
            ],
        ])

        group_note = "\n\n👥 _Chỉ hiển thị việc trong nhóm này_" if gid else ""
        await safe_edit_message(
            query,
            "📋 CHỌN DANH MỤC VIỆC\n\n"
            "📋 Việc cá nhân - Việc bạn tự tạo cho mình\n"
            "📤 Việc đã giao - Việc bạn giao cho người khác\n"
            "📥 Việc đã nhận - Việc người khác giao cho bạn\n"
            "📊 Tất cả việc - Toàn bộ việc liên quan\n\n"
            "🔍 Lọc theo loại: Cá nhân (P-ID) | Nhóm (G-ID)" + group_note,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    if category == "personal":
        title = "📋 VIỆC CÁ NHÂN"
        list_type = "personal"

        # Privacy feature: In group context, send personal tasks via private DM
        if gid is not None:
            from utils import mention_user
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            # Fetch ALL personal tasks (not filtered by group) for private DM
            tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size, group_id=None)

            user_telegram_id = db_user.get("telegram_id")
            user_mention = mention_user(db_user)

            if not tasks:
                # No personal tasks - notify in group and send empty message privately
                try:
                    await query.message.get_bot().send_message(
                        chat_id=user_telegram_id,
                        text="📋 *VIỆC CÁ NHÂN*\n\n"
                             "📭 Bạn chưa có việc cá nhân nào.\n\n"
                             "Tạo việc mới: /taoviec",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.warning(f"Could not send private message to {user_telegram_id}: {e}")
                    await safe_edit_message(
                        query,
                        f"⚠️ Không thể gửi tin nhắn riêng.\n\n"
                        f"Vui lòng nhắn /start cho bot trước để nhận tin nhắn riêng.",
                    )
                    return

                await safe_edit_message(
                    query,
                    f"📬 Đã gửi tin nhắn riêng về việc cá nhân cho {user_mention}.\n\n"
                    f"_Kiểm tra tin nhắn riêng từ bot._",
                    parse_mode="Markdown",
                )
                return

            # Has personal tasks - send list via private DM
            total = len(tasks)
            total_pages = max(1, (total + page_size - 1) // page_size)

            # Build task list message for private DM
            task_lines = []
            for task in tasks[:10]:
                task_id = task.get("public_id", "")
                content = task.get("content", "")[:40]
                if len(task.get("content", "")) > 40:
                    content += "..."
                status_icon = "✅" if task.get("status") == "completed" else "📋"
                task_lines.append(f"{status_icon} `{task_id}`: {content}")

            task_list_text = "\n".join(task_lines)

            try:
                # Send private DM with task list and action buttons
                await query.message.get_bot().send_message(
                    chat_id=user_telegram_id,
                    text=f"📋 *VIỆC CÁ NHÂN CỦA BẠN*\n\n"
                         f"Tổng: {total} việc\n\n"
                         f"{task_list_text}\n\n"
                         f"_Sử dụng /xemviec [mã việc] để xem chi tiết_",
                    parse_mode="Markdown",
                    reply_markup=task_list_with_pagination(tasks, 1, total_pages, list_type, None),
                )
            except Exception as e:
                logger.warning(f"Could not send private message to {user_telegram_id}: {e}")
                await safe_edit_message(
                    query,
                    f"⚠️ Không thể gửi tin nhắn riêng.\n\n"
                    f"Vui lòng nhắn /start cho bot trước để nhận tin nhắn riêng.",
                )
                return

            # Update group message with notification
            await safe_edit_message(
                query,
                f"📬 Đã gửi tin nhắn riêng về việc cá nhân cho {user_mention}.\n\n"
                f"_Kiểm tra tin nhắn riêng từ bot._",
                parse_mode="Markdown",
            )
            return
        else:
            # Private chat context - show all personal tasks inline
            tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size, group_id=None)

    elif category == "assigned":
        tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size, group_id=gid)
        title = "📤 VIỆC ĐÃ GIAO"
        list_type = "assigned"
    elif category == "received":
        tasks = await get_user_received_tasks(db, db_user["id"], limit=page_size, group_id=gid)
        title = "📥 VIỆC ĐÃ NHẬN"
        list_type = "received"
    else:  # all
        tasks = await get_all_user_related_tasks(db, db_user["id"], limit=page_size, group_id=gid)
        title = "📊 TẤT CẢ VIỆC"
        list_type = "all"

    if not tasks:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        # Use simple back button instead of full menu to avoid duplicate content
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("« Quay lại danh mục", callback_data=f"task_category:menu{g_suffix}")]
        ])
        group_note = " (trong nhóm)" if gid else ""
        await safe_edit_message(
            query,
            f"{title}{group_note}\n\n📭 Không có việc nào trong danh mục này.\n\nTạo việc mới: /taoviec hoặc /giaoviec",
            reply_markup=back_kb,
        )
        return

    total = len(tasks)
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Show only title with count - task list is in buttons
    group_note = " (trong nhóm)" if gid else ""
    msg = f"{title}{group_note}\n\nTổng: {total} việc | Trang 1/{total_pages}\n\nChọn việc để xem chi tiết:"

    await safe_edit_message(
        query,
        msg,
        reply_markup=task_list_with_pagination(tasks, 1, total_pages, list_type, gid),
    )


async def handle_task_filter(query, db, db_user, filter_type: str, list_type: str, group_id: int = None) -> None:
    """Handle task type filter (Individual/Group)."""
    from services import get_all_user_related_tasks
    from utils import task_type_filter_keyboard
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    # Parse group_id (0 means no filter)
    gid = group_id if group_id and group_id > 0 else None
    g_suffix = f":g{group_id}" if group_id else ":g0"

    # Map filter_type to task_type for SQL filtering
    task_type_map = {
        "individual": "individual",
        "group": "group",
    }
    task_type = task_type_map.get(filter_type)

    # Get tasks with SQL filter (no in-memory filtering needed)
    tasks = await get_all_user_related_tasks(
        db, db_user["id"], limit=50, task_type=task_type, group_id=gid
    )

    # Set title based on filter
    if filter_type == "individual":
        title = "👤 VIỆC CÁ NHÂN"
    elif filter_type == "group":
        title = "👥 VIỆC NHÓM"
    else:
        title = "📊 TẤT CẢ VIỆC"

    if gid:
        title += " (trong nhóm)"

    # Build filter buttons row
    filter_kb = task_type_filter_keyboard(filter_type)

    if not tasks:
        buttons = list(filter_kb.inline_keyboard) + [
            [InlineKeyboardButton("« Quay lại danh mục", callback_data=f"task_category:menu{g_suffix}")]
        ]
        await safe_edit_message(
            query,
            f"{title}\n\n📭 Không có việc nào trong danh mục này.\n\nTạo việc mới: /taoviec hoặc /giaoviec",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    total = len(tasks)
    total_pages = max(1, (total + 9) // 10)
    tasks = tasks[:10]  # First page

    # Show only title with count - task list is in buttons
    msg = f"{title}\n\nTổng: {total} việc | Trang 1/{total_pages}\n\nChọn việc để xem chi tiết:"

    # Build task buttons with longer content display
    task_buttons = []
    for task in tasks:
        task_id = task.get("public_id", "")
        content = task.get("content", "")[:40]
        if len(task.get("content", "")) > 40:
            content += "..."
        task_buttons.append([
            InlineKeyboardButton(f"{task_id}: {content}", callback_data=f"task_detail:{task_id}")
        ])

    # Pagination buttons
    nav_row = []
    nav_row.append(InlineKeyboardButton("1/{}".format(total_pages), callback_data="noop"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton("Sau »", callback_data=f"task_filter:{filter_type}:2{g_suffix}"))
    task_buttons.append(nav_row)

    # Combine: filter row + task buttons + back button
    all_buttons = list(filter_kb.inline_keyboard) + task_buttons + [
        [InlineKeyboardButton("« Quay lại danh mục", callback_data=f"task_category:menu{g_suffix}")]
    ]

    await safe_edit_message(
        query,
        msg,
        reply_markup=InlineKeyboardMarkup(all_buttons),
    )


async def handle_edit_menu(query, db, db_user, task_id: str) -> None:
    """Show edit options menu."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    # Only creator can edit
    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    current_deadline = format_datetime(task.get("deadline")) if task.get("deadline") else "Không có"
    current_priority = format_priority(task.get("priority", "normal"))

    await query.edit_message_text(
        f"✏️ <b>SỬA VIỆC {task_id}</b>\n\n"
        f"📝 <b>Nội dung:</b> {task['content'][:100]}{'...' if len(task['content']) > 100 else ''}\n"
        f"📅 <b>Deadline:</b> {current_deadline}\n"
        f"🔔 <b>Độ ưu tiên:</b> {current_priority}\n\n"
        f"Chọn mục cần sửa:",
        reply_markup=edit_menu_keyboard(task_id),
        parse_mode="HTML",
    )


async def handle_edit_content_prompt(query, db, db_user, task_id: str, context) -> None:
    """Prompt user to enter new content."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    # Store pending edit in user_data
    context.user_data["pending_edit"] = {
        "type": "content",
        "task_id": task_id,
        "task_db_id": task["id"],
    }

    await query.edit_message_text(
        f"📝 SỬA NỘI DUNG {task_id}\n\n"
        f"Nội dung hiện tại:\n{task['content']}\n\n"
        f"Hãy gửi nội dung mới cho việc này.\n"
        f"⚠️ REPLY tin nhắn này khi nhập (vuốt phải)\n"
        f"(Gửi /huy để hủy)"
    )


async def handle_edit_deadline_prompt(query, db, db_user, task_id: str, context) -> None:
    """Prompt user to enter new deadline."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    # Store pending edit in user_data
    context.user_data["pending_edit"] = {
        "type": "deadline",
        "task_id": task_id,
        "task_db_id": task["id"],
    }

    current_deadline = format_datetime(task.get("deadline")) if task.get("deadline") else "Không có"

    await query.edit_message_text(
        f"📅 SỬA DEADLINE {task_id}\n\n"
        f"Deadline hiện tại: {current_deadline}\n\n"
        f"Hãy gửi deadline mới.\n"
        f"Ví dụ: ngày mai 9h, thứ 6, 25/12, cuối tuần\n\n"
        f"⚠️ REPLY tin nhắn này khi nhập (vuốt phải)\n"
        f"(Gửi /huy để hủy, gửi 'xóa' để xóa deadline)"
    )


async def handle_edit_priority_menu(query, db, db_user, task_id: str) -> None:
    """Show priority selection menu."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    current_priority = format_priority(task.get("priority", "normal"))

    await query.edit_message_text(
        f"🔔 SỬA ĐỘ ƯU TIÊN {task_id}\n\n"
        f"Độ ưu tiên hiện tại: {current_priority}\n\n"
        f"Chọn độ ưu tiên mới:",
        reply_markup=edit_priority_keyboard(task_id),
    )


async def handle_set_priority(query, db, db_user, task_id: str, priority: str) -> None:
    """Set task priority."""
    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    await update_task_priority(db, task["id"], priority, db_user["id"])

    priority_text = format_priority(priority)

    await query.edit_message_text(
        f"✅ Đã cập nhật độ ưu tiên {task_id}!\n\n"
        f"🔔 Độ ưu tiên mới: {priority_text}"
    )


async def handle_edit_assignee_prompt(query, db, db_user, task_id: str, context) -> None:
    """Prompt user to enter new assignee(s)."""
    from services import is_group_task, get_child_tasks

    task = await get_task_by_public_id(db, task_id)

    if not task:
        await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
        return

    if task["creator_id"] != db_user["id"]:
        await query.edit_message_text(ERR_NO_PERMISSION)
        return

    is_group = await is_group_task(db, task_id)

    # Store pending edit in user_data
    context.user_data["pending_edit"] = {
        "type": "assignee",
        "task_id": task_id,
        "task_db_id": task["id"],
        "is_group": is_group,
    }
    logger.info(f"Set pending_edit for assignee: task_id={task_id}, user_id={db_user['id']}")

    if is_group:
        # Get current assignees for group task with @username mentions
        children = await get_child_tasks(db, task_id)
        assignee_mentions = []
        for c in children:
            username = c.get("assignee_username")
            name = c.get("assignee_name", "?")
            if username:
                assignee_mentions.append(f"@{username} ({name})")
            else:
                assignee_mentions.append(name)
        current_assignees = ", ".join(assignee_mentions)
        await query.edit_message_text(
            f"👥 SỬA NGƯỜI NHẬN VIỆC NHÓM {task_id}\n\n"
            f"Người nhận hiện tại:\n{current_assignees}\n\n"
            f"📝 Nhập danh sách người nhận mới (cách nhau bằng dấu phẩy):\n"
            f"Ví dụ: @user1, @user2, @user3\n\n"
            f"💡 Nhập 1 người để chuyển thành việc cá nhân\n"
            f"⚠️ REPLY tin nhắn này khi nhập (vuốt phải)\n"
            f"(Gửi /huy để hủy)"
        )
    else:
        # Get username for individual task
        assignee_info = await db.fetch_one(
            "SELECT display_name, username FROM users WHERE id = $1",
            task.get("assignee_id")
        )
        if assignee_info:
            username = assignee_info.get("username")
            name = assignee_info.get("display_name", "?")
            current_assignee = f"@{username} ({name})" if username else name
        else:
            current_assignee = "Không rõ"
        await query.edit_message_text(
            f"👤 SỬA NGƯỜI NHẬN {task_id}\n\n"
            f"Người nhận hiện tại: {current_assignee}\n\n"
            f"📝 Nhập người nhận mới:\n"
            f"• 1 người: @username → việc cá nhân\n"
            f"• Nhiều người: @user1, @user2 → việc nhóm\n\n"
            f"⚠️ REPLY tin nhắn này khi nhập (vuốt phải)\n"
            f"(Gửi /huy để hủy)"
        )


async def handle_pending_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages for pending edits (content/deadline)."""
    logger.info(f"handle_pending_edit called with text: {update.message.text[:50] if update.message and update.message.text else 'None'}")
    logger.info(f"user_data keys: {list(context.user_data.keys())}")

    pending = context.user_data.get("pending_edit")
    logger.info(f"pending_edit value: {pending}")

    if not pending:
        logger.info("No pending edit, returning")
        return  # No pending edit, let other handlers process

    user = update.effective_user
    text = update.message.text.strip()

    # Handle cancel
    if text.lower() in ("/huy", "/cancel", "hủy"):
        context.user_data.pop("pending_edit", None)
        await update.message.reply_text("Đã hủy chỉnh sửa.")
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        task_id = pending["task_id"]
        task_db_id = pending["task_db_id"]
        edit_type = pending["type"]

        if edit_type == "content":
            # Update content
            if len(text) < 3:
                await update.message.reply_text("Nội dung quá ngắn. Vui lòng nhập ít nhất 3 ký tự.")
                return

            await update_task_content(db, task_db_id, text, db_user["id"])
            context.user_data.pop("pending_edit", None)

            await update.message.reply_text(
                f"✅ Đã cập nhật nội dung {task_id}!\n\n"
                f"📝 Nội dung mới: {text[:200]}{'...' if len(text) > 200 else ''}"
            )

        elif edit_type == "deadline":
            # Handle remove deadline
            if text.lower() in ("xóa", "xoa", "remove", "clear"):
                await update_task_deadline(db, task_db_id, None, db_user["id"])
                context.user_data.pop("pending_edit", None)
                await update.message.reply_text(f"✅ Đã xóa deadline của {task_id}!")
                return

            # Parse deadline - returns (datetime, remaining_text) tuple
            deadline, _ = parse_vietnamese_time(text)
            if not deadline:
                await update.message.reply_text(
                    "Không hiểu được thời gian. Vui lòng thử lại.\n\n"
                    "Ví dụ: ngày mai 9h, thứ 6, 25/12, cuối tuần"
                )
                return

            await update_task_deadline(db, task_db_id, deadline, db_user["id"])
            context.user_data.pop("pending_edit", None)

            deadline_str = format_datetime(deadline)
            await update.message.reply_text(
                f"✅ Đã cập nhật deadline {task_id}!\n\n"
                f"📅 Deadline mới: {deadline_str}"
            )

        elif edit_type == "assignee":
            from services import convert_individual_to_group, update_group_assignees

            message = update.message
            assignees = []

            # Method 1: Check message entities for text_mention (users without @username)
            if message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention" and entity.user:
                        # User without @username - get or create from entity.user
                        mentioned_user = await get_or_create_user(db, entity.user)
                        if not any(u["id"] == mentioned_user["id"] for u in assignees):
                            assignees.append(mentioned_user)
                            logger.info(f"Edit assignee - Found text_mention: {entity.user.first_name} (id={entity.user.id})")
                    elif entity.type == "mention":
                        # @username mention
                        full_text = message.text or ""
                        username_with_at = full_text[entity.offset:entity.offset + entity.length]
                        username = username_with_at.lstrip("@")
                        found_user = await get_user_by_username(db, username)
                        if found_user and not any(u["id"] == found_user["id"] for u in assignees):
                            assignees.append(found_user)
                            logger.info(f"Edit assignee - Found @mention: @{username} (id={found_user['id']})")

            # Method 2: Parse @username from text if no entities found
            if not assignees:
                raw_inputs = [x.strip().lstrip("@") for x in text.replace(",", " ").split()]
                raw_inputs = [x for x in raw_inputs if x]  # Remove empty
                not_found = []

                for inp in raw_inputs:
                    found = None
                    if inp.isdigit():
                        found = await db.fetch_one(
                            "SELECT id, display_name, telegram_id, username FROM users WHERE telegram_id = $1",
                            int(inp)
                        )
                    if not found:
                        found = await db.fetch_one(
                            "SELECT id, display_name, telegram_id, username FROM users WHERE LOWER(username) = LOWER($1)",
                            inp
                        )
                    if found:
                        assignees.append(dict(found))
                    else:
                        not_found.append(inp)

                if not_found:
                    await update.message.reply_text(
                        f"Không tìm thấy: {', '.join(not_found)}\n\n"
                        f"Người này cần đã từng tương tác với bot.\n"
                        f"💡 Hoặc dùng text mention (chạm tên trong nhóm)"
                    )
                    return

            if not assignees:
                await update.message.reply_text(
                    "Vui lòng nhập ít nhất 1 người nhận.\n\n"
                    "💡 Dùng @username hoặc text mention (chạm tên trong nhóm)"
                )
                return

            # Remove duplicates
            seen_ids = set()
            unique_assignees = []
            for a in assignees:
                if a["id"] not in seen_ids:
                    seen_ids.add(a["id"])
                    unique_assignees.append(a)
            assignees = unique_assignees

            is_group = pending.get("is_group", False)
            task = await get_task_by_public_id(db, task_id)

            if len(assignees) == 1:
                # Single assignee - update or convert to individual
                new_assignee = assignees[0]

                if is_group:
                    # Convert group to individual - soft delete group and children, create new P-ID
                    from services import get_child_tasks, soft_delete_task

                    children = await get_child_tasks(db, task_id)
                    # Delete all children
                    for child in children:
                        await soft_delete_task(db, child["id"], db_user["id"])
                    # Delete parent
                    await soft_delete_task(db, task_db_id, db_user["id"])

                    # Create new individual task
                    from services import create_task
                    new_task = await create_task(
                        db=db,
                        content=task["content"],
                        creator_id=task["creator_id"],
                        assignee_id=new_assignee["id"],
                        deadline=task.get("deadline"),
                        priority=task.get("priority", "normal"),
                    )

                    context.user_data.pop("pending_edit", None)
                    assignee_mention = mention_user(new_assignee)
                    await update.message.reply_text(
                        f"✅ Đã chuyển việc nhóm {task_id} → việc cá nhân {new_task['public_id']}!\n\n"
                        f"👤 Người nhận: {assignee_mention}",
                        parse_mode="Markdown"
                    )
                else:
                    # Simple update
                    await update_task_assignee(db, task_db_id, new_assignee["id"], db_user["id"])
                    context.user_data.pop("pending_edit", None)
                    assignee_mention = mention_user(new_assignee)
                    await update.message.reply_text(
                        f"✅ Đã cập nhật người nhận {task_id}!\n\n"
                        f"👤 Người nhận mới: {assignee_mention}",
                        parse_mode="Markdown"
                    )

                # Notify new assignee
                if new_assignee["telegram_id"] != user.id:
                    try:
                        await context.bot.send_message(
                            chat_id=new_assignee["telegram_id"],
                            text=f"📋 Bạn được giao việc!\n\n"
                                 f"Nội dung: {task['content']}\n"
                                 f"Từ: {db_user.get('display_name', 'N/A')}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not notify assignee: {e}")

            else:
                # Multiple assignees - convert to group or update group
                assignee_mentions = ", ".join([mention_user(a) for a in assignees])

                if is_group:
                    # Update existing group
                    new_children = await update_group_assignees(db, task_id, assignees, db_user["id"])
                    context.user_data.pop("pending_edit", None)

                    await update.message.reply_text(
                        f"✅ Đã cập nhật việc nhóm {task_id}!\n\n"
                        f"👥 Người nhận: {assignee_mentions}",
                        parse_mode="Markdown"
                    )
                else:
                    # Convert individual to group
                    parent, children = await convert_individual_to_group(
                        db, task_db_id, assignees, db_user["id"]
                    )
                    context.user_data.pop("pending_edit", None)

                    child_ids = ", ".join([c[0]["public_id"] for c in children])
                    await update.message.reply_text(
                        f"✅ Đã chuyển việc cá nhân {task_id} → việc nhóm {parent['public_id']}!\n\n"
                        f"👥 Người nhận: {assignee_mentions}\n"
                        f"📋 Việc con: {child_ids}",
                        parse_mode="Markdown"
                    )

                # Notify all assignees
                for assignee in assignees:
                    if assignee["telegram_id"] != user.id:
                        try:
                            await context.bot.send_message(
                                chat_id=assignee["telegram_id"],
                                text=f"📋 Bạn được giao việc!\n\n"
                                     f"Nội dung: {task['content']}\n"
                                     f"Từ: {db_user.get('display_name', 'N/A')}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not notify assignee: {e}")

    except Exception as e:
        logger.error(f"Error handling pending edit: {e}")
        await update.message.reply_text("Lỗi hệ thống. Vui lòng thử lại.")


async def handle_bulk_delete(query, db, db_user, delete_type: str, action: str, context) -> None:
    """Handle bulk delete confirmation/cancellation."""
    if action == "cancel":
        await query.edit_message_text("Đã hủy xóa hàng loạt.")
        return

    if action == "confirm":
        # Get task IDs from context
        task_ids = context.user_data.get("bulk_delete_ids", [])
        stored_type = context.user_data.get("bulk_delete_type", "")

        if not task_ids:
            await query.edit_message_text("Không tìm thấy danh sách việc cần xóa.")
            return

        if stored_type != delete_type:
            await query.edit_message_text("Lỗi xác thực. Vui lòng thử lại.")
            return

        # Process bulk deletion
        count = await bulk_delete_tasks(db, task_ids, db_user["id"])

        # Clear context data
        context.user_data.pop("bulk_delete_ids", None)
        context.user_data.pop("bulk_delete_type", None)

        if delete_type == "all":
            msg = f"✅ Đã xóa *{count}* việc thành công."
        else:
            msg = f"✅ Đã xóa *{count}* việc đã giao thành công."

        await query.edit_message_text(msg, parse_mode="Markdown")
        logger.info(f"Bulk deleted {count} tasks for user {db_user['id']} (type: {delete_type})")


def get_handlers() -> list:
    """Return callback query handler and pending edit message handler."""
    return [
        CallbackQueryHandler(callback_router),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_pending_edit
        ),
    ]
