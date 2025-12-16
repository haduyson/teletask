"""
Task Delete Handler
Commands for deleting tasks with undo support
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    soft_delete_task,
    restore_task,
    get_tasks_created_by_user,
    get_tasks_assigned_to_others,
    bulk_delete_tasks,
)
from utils import (
    MSG_TASK_DELETED,
    MSG_TASK_RESTORED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_DATABASE,
    undo_keyboard,
    confirm_keyboard,
    bulk_delete_confirm_keyboard,
    format_datetime,
    format_status,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Delete Menu Keyboards
# =============================================================================

def delete_menu_keyboard() -> InlineKeyboardMarkup:
    """Main delete menu - choose category."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Việc đã giao cho người khác", callback_data="delete_menu:assigned")],
        [InlineKeyboardButton("📋 Việc tự tạo cho bản thân", callback_data="delete_menu:personal")],
        [InlineKeyboardButton("❌ Đóng", callback_data="delete_menu:close")],
    ])


def delete_task_list_keyboard(tasks: list, category: str) -> InlineKeyboardMarkup:
    """Task list for deletion - each task on separate row."""
    buttons = []

    for task in tasks[:10]:  # Max 10 tasks
        content = task["content"][:25] + "..." if len(task["content"]) > 25 else task["content"]
        public_id = task["public_id"]
        buttons.append([
            InlineKeyboardButton(
                f"🗑️ {public_id}: {content}",
                callback_data=f"delete_task:{public_id}"
            )
        ])

    if len(tasks) > 10:
        buttons.append([
            InlineKeyboardButton(f"... còn {len(tasks) - 10} việc khác", callback_data="noop")
        ])

    # Add bulk delete and back buttons
    if tasks:
        buttons.append([
            InlineKeyboardButton(f"🗑️ XÓA TẤT CẢ ({len(tasks)} việc)", callback_data=f"delete_all:{category}")
        ])

    buttons.append([InlineKeyboardButton("« Quay lại", callback_data="delete_menu:back")])

    return InlineKeyboardMarkup(buttons)


def delete_confirm_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Confirm deletion of single task."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Xác nhận xóa", callback_data=f"delete_confirm:{task_id}")],
        [InlineKeyboardButton("❌ Hủy", callback_data="delete_menu:back_to_list")],
    ])


def delete_all_confirm_keyboard(category: str, count: int) -> InlineKeyboardMarkup:
    """Confirm bulk deletion."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Xác nhận xóa {count} việc", callback_data=f"delete_all_confirm:{category}")],
        [InlineKeyboardButton("❌ Hủy", callback_data=f"delete_menu:{category}")],
    ])


# =============================================================================
# Command Handlers
# =============================================================================

async def xoa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xoa or /xoaviec command.
    Without args: show delete menu
    With task_id: delete specific task
    """
    user = update.effective_user
    if not user:
        return

    # If task ID provided, delete directly
    if context.args:
        task_id = context.args[0].upper()
        await delete_specific_task(update, context, task_id)
        return

    # Show delete menu
    await update.message.reply_text(
        "🗑️ <b>XÓA VIỆC</b>\n\n"
        "Chọn loại việc muốn xóa:",
        reply_markup=delete_menu_keyboard(),
        parse_mode="HTML",
    )


async def delete_specific_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: str) -> None:
    """Delete a specific task by ID."""
    user = update.effective_user

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        task = await get_task_by_public_id(db, task_id)

        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Only creator can delete
        if task["creator_id"] != db_user["id"]:
            await update.message.reply_text(ERR_NO_PERMISSION)
            return

        # Show task details for review
        status = format_status(task["status"])
        deadline_str = format_datetime(task.get("deadline"), relative=True) if task.get("deadline") else "Không có"
        assignee_name = task.get("assignee_name", "Chưa giao")

        await update.message.reply_text(
            f"⚠️ <b>XÁC NHẬN XÓA VIỆC?</b>\n\n"
            f"📋 <b>{task_id}</b>: {task['content']}\n"
            f"📊 Trạng thái: {status}\n"
            f"👤 Người nhận: {assignee_name}\n"
            f"📅 Deadline: {deadline_str}",
            reply_markup=delete_confirm_keyboard(task_id),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in delete_specific_task: {e}")
        await update.message.reply_text(ERR_DATABASE)


# =============================================================================
# Callback Handlers
# =============================================================================

async def delete_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle delete menu callbacks."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data
    action = data.split(":")[1] if ":" in data else ""

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        if action == "close":
            await query.edit_message_text("Đã đóng menu xóa việc.")
            return

        if action == "back":
            await query.edit_message_text(
                "🗑️ <b>XÓA VIỆC</b>\n\n"
                "Chọn loại việc muốn xóa:",
                reply_markup=delete_menu_keyboard(),
                parse_mode="HTML",
            )
            return

        if action == "assigned":
            # Show tasks assigned to others
            tasks = await get_tasks_assigned_to_others(db, db_user["id"])
            context.user_data["delete_category"] = "assigned"
            context.user_data["delete_tasks"] = tasks

            if not tasks:
                await query.edit_message_text(
                    "📤 <b>Việc đã giao cho người khác</b>\n\n"
                    "Bạn chưa giao việc cho ai.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("« Quay lại", callback_data="delete_menu:back")]
                    ]),
                    parse_mode="HTML",
                )
                return

            await query.edit_message_text(
                f"📤 <b>Việc đã giao cho người khác</b>\n\n"
                f"Bạn có {len(tasks)} việc đã giao.\n"
                f"Chọn việc để xóa:",
                reply_markup=delete_task_list_keyboard(tasks, "assigned"),
                parse_mode="HTML",
            )
            return

        if action == "personal":
            # Show personal tasks (created for self)
            all_tasks = await get_tasks_created_by_user(db, db_user["id"], include_assigned_to_others=False)
            # Filter only tasks where creator == assignee
            tasks = [t for t in all_tasks if t.get("assignee_id") == db_user["id"]]
            context.user_data["delete_category"] = "personal"
            context.user_data["delete_tasks"] = tasks

            if not tasks:
                await query.edit_message_text(
                    "📋 <b>Việc tự tạo cho bản thân</b>\n\n"
                    "Bạn chưa có việc cá nhân nào.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("« Quay lại", callback_data="delete_menu:back")]
                    ]),
                    parse_mode="HTML",
                )
                return

            await query.edit_message_text(
                f"📋 <b>Việc tự tạo cho bản thân</b>\n\n"
                f"Bạn có {len(tasks)} việc cá nhân.\n"
                f"Chọn việc để xóa:",
                reply_markup=delete_task_list_keyboard(tasks, "personal"),
                parse_mode="HTML",
            )
            return

        if action == "back_to_list":
            # Return to task list
            category = context.user_data.get("delete_category", "personal")
            tasks = context.user_data.get("delete_tasks", [])

            category_name = "Việc đã giao cho người khác" if category == "assigned" else "Việc tự tạo cho bản thân"
            icon = "📤" if category == "assigned" else "📋"

            await query.edit_message_text(
                f"{icon} <b>{category_name}</b>\n\n"
                f"Bạn có {len(tasks)} việc.\n"
                f"Chọn việc để xóa:",
                reply_markup=delete_task_list_keyboard(tasks, category),
                parse_mode="HTML",
            )
            return

    except Exception as e:
        logger.error(f"Error in delete_menu_callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


async def delete_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle individual task deletion callback."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    task_id = query.data.split(":")[1] if ":" in query.data else ""

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        task = await get_task_by_public_id(db, task_id)

        if not task:
            await query.edit_message_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Store for later
        context.user_data["delete_task_id"] = task_id

        # Show confirmation
        status = format_status(task["status"])
        deadline_str = format_datetime(task.get("deadline"), relative=True) if task.get("deadline") else "Không có"
        assignee_name = task.get("assignee_name", "Chưa giao")

        await query.edit_message_text(
            f"⚠️ <b>XÁC NHẬN XÓA VIỆC?</b>\n\n"
            f"📋 <b>{task_id}</b>: {task['content']}\n"
            f"📊 Trạng thái: {status}\n"
            f"👤 Người nhận: {assignee_name}\n"
            f"📅 Deadline: {deadline_str}",
            reply_markup=delete_confirm_keyboard(task_id),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in delete_task_callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


async def delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deletion confirmation with 10s countdown."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    task_id = query.data.split(":")[1] if ":" in query.data else ""

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        success, result = await process_delete(db, task_id, db_user["id"], context.bot)

        if success:
            undo_id = result
            await query.edit_message_text(
                f"✅ Đã xóa việc {task_id}.\n\n"
                f"Bấm nút bên dưới để hoàn tác:",
                reply_markup=undo_keyboard(undo_id, 10),
            )

            # Schedule countdown updates
            chat_id = query.message.chat_id
            message_id = query.message.message_id

            # Get job_queue from application
            job_queue = context.application.job_queue

            if job_queue:

                # Schedule countdown updates every second (9s -> 1s)
                for seconds in range(9, 0, -1):
                    job_queue.run_once(
                        _countdown_update_job,
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

                # Schedule final expiry at 10 seconds
                job_queue.run_once(
                    _countdown_expired_job,
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
            await query.edit_message_text(f"❌ {result}")

    except Exception as e:
        logger.error(f"Error in delete_confirm_callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


async def _countdown_update_job(context) -> None:
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
            text=f"✅ Đã xóa việc {task_id}.\n\n"
                 f"Bấm nút bên dưới để hoàn tác:",
            reply_markup=undo_keyboard(undo_id, seconds),
        )
    except Exception as e:
        logger.debug(f"Could not update countdown: {e}")


async def _countdown_expired_job(context) -> None:
    """Job to handle undo expiry."""
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]
    task_id = job_data["task_id"]

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🗑️ Đã xóa việc {task_id}!\n\n"
                 f"⏰ Đã hết thời gian hoàn tác.",
        )
    except Exception as e:
        logger.debug(f"Could not update expired message: {e}")


async def delete_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bulk delete request."""
    query = update.callback_query
    await query.answer()

    category = query.data.split(":")[1] if ":" in query.data else ""
    tasks = context.user_data.get("delete_tasks", [])

    if not tasks:
        await query.edit_message_text("Không có việc nào để xóa.")
        return

    # Build preview
    preview_lines = []
    for t in tasks[:5]:
        content_short = t["content"][:25] + "..." if len(t["content"]) > 25 else t["content"]
        preview_lines.append(f"• {t['public_id']}: {content_short}")

    if len(tasks) > 5:
        preview_lines.append(f"... và {len(tasks) - 5} việc khác")

    preview = "\n".join(preview_lines)

    category_name = "việc đã giao" if category == "assigned" else "việc cá nhân"

    await query.edit_message_text(
        f"⚠️ <b>XÁC NHẬN XÓA TẤT CẢ?</b>\n\n"
        f"Bạn sắp xóa <b>{len(tasks)}</b> {category_name}:\n\n"
        f"{preview}\n\n"
        f"⚠️ <b>Hành động này không thể hoàn tác!</b>",
        reply_markup=delete_all_confirm_keyboard(category, len(tasks)),
        parse_mode="HTML",
    )


async def delete_all_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bulk delete confirmation."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    tasks = context.user_data.get("delete_tasks", [])

    if not tasks:
        await query.edit_message_text("Không có việc nào để xóa.")
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task_ids = [t["id"] for t in tasks]
        count = await bulk_delete_tasks(db, task_ids, db_user["id"])

        # Clear stored data
        context.user_data.pop("delete_tasks", None)
        context.user_data.pop("delete_category", None)

        await query.edit_message_text(
            f"✅ Đã xóa <b>{count}</b> việc thành công.",
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Error in delete_all_confirm_callback: {e}")
        await query.edit_message_text(ERR_DATABASE)


# =============================================================================
# Legacy Functions (kept for compatibility)
# =============================================================================

async def process_delete(
    db,
    task_id: str,
    user_id: int,
    bot,
) -> tuple:
    """
    Process task deletion.
    Returns (success, undo_id or error_message).
    """
    task = await get_task_by_public_id(db, task_id)

    if not task:
        return False, ERR_TASK_NOT_FOUND.format(task_id=task_id)

    # Soft delete
    undo = await soft_delete_task(db, task["id"], user_id)

    if not undo:
        return False, "Lỗi khi xóa việc."

    # Notify assignee if different from creator
    if task["assignee_id"] != task["creator_id"]:
        try:
            assignee = await db.fetch_one(
                "SELECT telegram_id FROM users WHERE id = $1",
                task["assignee_id"]
            )
            if assignee:
                await bot.send_message(
                    chat_id=assignee["telegram_id"],
                    text=f"Việc {task_id} đã bị xóa bởi người tạo.\n\n"
                         f"Nội dung: {task['content'][:50]}...",
                )
        except Exception as e:
            logger.warning(f"Could not notify assignee: {e}")

    return True, undo["id"]


async def process_restore(db, undo_id: int) -> tuple:
    """
    Process task restoration.
    Returns (success, task or error_message).
    """
    task = await restore_task(db, undo_id)

    if not task:
        return False, "Không thể hoàn tác. Đã hết thời gian (10 giây)."

    return True, task


# Legacy bulk delete commands (kept for backwards compatibility)
async def xoahet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /xoahet - redirects to delete menu."""
    await xoa_command(update, context)


async def xoaviecdagiao_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /xoaviecdagiao - redirects to delete menu."""
    await xoa_command(update, context)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler(["xoa", "xoaviec"], xoa_command),
        CommandHandler("xoahet", xoahet_command),
        CommandHandler("xoaviecdagiao", xoaviecdagiao_command),
        CallbackQueryHandler(delete_menu_callback, pattern=r"^delete_menu:"),
        CallbackQueryHandler(delete_task_callback, pattern=r"^delete_task:"),
        CallbackQueryHandler(delete_confirm_callback, pattern=r"^delete_confirm:"),
        CallbackQueryHandler(delete_all_callback, pattern=r"^delete_all:(?!confirm)"),
        CallbackQueryHandler(delete_all_confirm_callback, pattern=r"^delete_all_confirm:"),
    ]
