"""
Callback Query Handler
Routes inline button callbacks to appropriate handlers
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

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

        # Task edit menu
        elif action == "task_edit":
            task_id = parts[1]
            await handle_edit_menu(query, db, db_user, task_id)

        # Edit content prompt
        elif action == "edit_content":
            task_id = parts[1]
            await handle_edit_content_prompt(query, db, db_user, task_id, context)

        # Edit deadline prompt
        elif action == "edit_deadline":
            task_id = parts[1]
            await handle_edit_deadline_prompt(query, db, db_user, task_id, context)

        # Edit priority menu
        elif action == "edit_priority":
            task_id = parts[1]
            await handle_edit_priority_menu(query, db, db_user, task_id)

        # Set priority
        elif action == "set_priority":
            task_id = parts[1]
            priority = parts[2]
            await handle_set_priority(query, db, db_user, task_id, priority)

        # Edit assignee prompt
        elif action == "edit_assignee":
            task_id = parts[1]
            await handle_edit_assignee_prompt(query, db, db_user, task_id, context)

        # Task category menu
        elif action == "task_category":
            category = parts[1]
            await handle_task_category(query, db, db_user, category)

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


async def handle_list_page(query, db, db_user, list_type: str, page: int) -> None:
    """Handle list pagination."""
    from services import (
        get_user_personal_tasks,
        get_user_created_tasks,
        get_user_received_tasks,
        get_all_user_related_tasks,
    )
    from utils import format_task_list, task_list_with_pagination

    page_size = 10
    offset = (page - 1) * page_size

    if list_type == "personal":
        tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "📋 VIỆC CÁ NHÂN"
    elif list_type == "assigned":
        tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "📤 VIỆC ĐÃ GIAO"
    elif list_type == "received":
        tasks = await get_user_received_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "📥 VIỆC ĐÃ NHẬN"
    else:  # all
        tasks = await get_all_user_related_tasks(db, db_user["id"], limit=page_size, offset=offset)
        title = "📊 TẤT CẢ VIỆC"

    if not tasks:
        await query.edit_message_text(
            f"{title}\n\nKhông có việc nào.",
            reply_markup=task_category_keyboard(),
        )
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


async def handle_task_category(query, db, db_user, category: str) -> None:
    """Handle task category selection."""
    from services import (
        get_user_personal_tasks,
        get_user_created_tasks,
        get_user_received_tasks,
        get_all_user_related_tasks,
    )
    from utils import format_task_list, task_list_with_pagination

    page_size = 10

    if category == "menu":
        # Show category menu
        await query.edit_message_text(
            "📋 CHỌN DANH MỤC VIỆC\n\n"
            "📋 Việc cá nhân - Việc bạn tự tạo cho mình\n"
            "📤 Việc đã giao - Việc bạn giao cho người khác\n"
            "📥 Việc đã nhận - Việc người khác giao cho bạn\n"
            "📊 Tất cả việc - Toàn bộ việc liên quan",
            reply_markup=task_category_keyboard(),
        )
        return

    if category == "personal":
        tasks = await get_user_personal_tasks(db, db_user["id"], limit=page_size)
        title = "📋 VIỆC CÁ NHÂN"
        list_type = "personal"
    elif category == "assigned":
        tasks = await get_user_created_tasks(db, db_user["id"], limit=page_size)
        title = "📤 VIỆC ĐÃ GIAO"
        list_type = "assigned"
    elif category == "received":
        tasks = await get_user_received_tasks(db, db_user["id"], limit=page_size)
        title = "📥 VIỆC ĐÃ NHẬN"
        list_type = "received"
    else:  # all
        tasks = await get_all_user_related_tasks(db, db_user["id"], limit=page_size)
        title = "📊 TẤT CẢ VIỆC"
        list_type = "all"

    if not tasks:
        await query.edit_message_text(
            f"{title}\n\nKhông có việc nào trong danh mục này.",
            reply_markup=task_category_keyboard(),
        )
        return

    total = len(tasks)
    total_pages = max(1, (total + page_size - 1) // page_size)

    msg = format_task_list(
        tasks=tasks,
        title=title,
        page=1,
        total=total,
    )

    await query.edit_message_text(
        msg,
        reply_markup=task_list_with_pagination(tasks, 1, total_pages, list_type),
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
        f"✏️ SỬA VIỆC {task_id}\n\n"
        f"📝 Nội dung: {task['content'][:100]}{'...' if len(task['content']) > 100 else ''}\n"
        f"📅 Deadline: {current_deadline}\n"
        f"🔔 Độ ưu tiên: {current_priority}\n\n"
        f"Chọn mục cần sửa:",
        reply_markup=edit_menu_keyboard(task_id),
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

    if is_group:
        # Get current assignees for group task
        children = await get_child_tasks(db, task_id)
        current_assignees = ", ".join([c.get("assignee_name", "?") for c in children])
        await query.edit_message_text(
            f"👥 SỬA NGƯỜI NHẬN VIỆC NHÓM {task_id}\n\n"
            f"Người nhận hiện tại:\n{current_assignees}\n\n"
            f"📝 Nhập danh sách người nhận mới (cách nhau bằng dấu phẩy):\n"
            f"Ví dụ: @user1, @user2, @user3\n\n"
            f"💡 Nhập 1 người để chuyển thành việc cá nhân\n"
            f"(Gửi /huy để hủy)"
        )
    else:
        current_assignee = task.get("assignee_name", "Không rõ")
        await query.edit_message_text(
            f"👤 SỬA NGƯỜI NHẬN {task_id}\n\n"
            f"Người nhận hiện tại: {current_assignee}\n\n"
            f"📝 Nhập người nhận mới:\n"
            f"• 1 người: @username → việc cá nhân\n"
            f"• Nhiều người: @user1, @user2 → việc nhóm\n\n"
            f"(Gửi /huy để hủy)"
        )


async def handle_pending_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages for pending edits (content/deadline)."""
    pending = context.user_data.get("pending_edit")
    if not pending:
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

            # Parse multiple assignees (comma or space separated)
            raw_inputs = [x.strip().lstrip("@") for x in text.replace(",", " ").split()]
            raw_inputs = [x for x in raw_inputs if x]  # Remove empty

            if not raw_inputs:
                await update.message.reply_text("Vui lòng nhập ít nhất 1 người nhận.")
                return

            # Find all users
            assignees = []
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
                    f"Vui lòng thử lại."
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
                    await update.message.reply_text(
                        f"✅ Đã chuyển việc nhóm {task_id} → việc cá nhân {new_task['public_id']}!\n\n"
                        f"👤 Người nhận: {new_assignee.get('display_name', '?')}"
                    )
                else:
                    # Simple update
                    await update_task_assignee(db, task_db_id, new_assignee["id"], db_user["id"])
                    context.user_data.pop("pending_edit", None)
                    await update.message.reply_text(
                        f"✅ Đã cập nhật người nhận {task_id}!\n\n"
                        f"👤 Người nhận mới: {new_assignee.get('display_name', '?')}"
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
                if is_group:
                    # Update existing group
                    new_children = await update_group_assignees(db, task_id, assignees, db_user["id"])
                    context.user_data.pop("pending_edit", None)

                    assignee_names = ", ".join([a.get("display_name", "?") for a in assignees])
                    await update.message.reply_text(
                        f"✅ Đã cập nhật việc nhóm {task_id}!\n\n"
                        f"👥 Người nhận: {assignee_names}"
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
                        f"👥 Việc con: {child_ids}"
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


def get_handlers() -> list:
    """Return callback query handler and pending edit message handler."""
    return [
        CallbackQueryHandler(callback_router),
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_pending_edit
        ),
    ]
