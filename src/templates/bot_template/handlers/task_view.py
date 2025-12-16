"""
Task View Handler
Commands for viewing and searching tasks
Supports G-ID group task viewing with aggregated progress
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    get_user_tasks,
    get_group_tasks,
    get_tasks_with_deadline,
    is_group_task,
    get_group_task_progress,
    get_child_tasks,
    get_user_received_tasks,
    get_all_user_related_tasks,
)
from utils import (
    ERR_TASK_NOT_FOUND,
    ERR_GROUP_ONLY,
    ERR_DATABASE,
    format_task_detail,
    format_task_list,
    task_detail_keyboard,
    task_category_keyboard,
    task_list_with_pagination,
    format_datetime,
    format_status,
    get_status_icon,
    mention_user,
)

logger = logging.getLogger(__name__)


def format_group_task_detail(task: dict, progress_info: dict, child_tasks: list) -> str:
    """Format group task (G-ID) detail with aggregated progress (Markdown format)."""
    status_icon = get_status_icon(task)  # Pass full dict, not just status string

    # Build member progress list with mention tags
    member_lines = []
    for child in child_tasks:
        child_icon = get_status_icon(child)  # Pass full dict
        # Create mention link for assignee
        assignee_mention = mention_user({
            "display_name": child.get("assignee_name", "N/A"),
            "telegram_id": child.get("telegram_id"),
        })
        member_lines.append(f"  {child_icon} {child['public_id']}: {assignee_mention}")

    members_text = "\n".join(member_lines) if member_lines else "  Không có thành viên"

    # Progress bar
    pct = progress_info.get("progress", 0)
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)

    deadline_str = format_datetime(task.get("deadline"), relative=True) if task.get("deadline") else "Không có"
    created_str = format_datetime(task.get("created_at"), relative=True) if task.get("created_at") else "N/A"

    return f"""
{status_icon} VIỆC NHÓM: {task['public_id']}

📋 {task['content']}

📊 TIẾN ĐỘ NHÓM:
[{bar}] {pct}%
Hoàn thành: {progress_info['completed']}/{progress_info['total']}

👥 THÀNH VIÊN:
{members_text}

📅 Deadline: {deadline_str}
🕐 Tạo: {created_str}

Xem chi tiết từng việc: /xemviec [P-ID]
""".strip()


def group_task_keyboard(task_id: str, can_edit: bool = False) -> InlineKeyboardMarkup:
    """Keyboard for group task detail."""
    buttons = []

    if can_edit:
        buttons.append([
            InlineKeyboardButton("✏️ Sửa", callback_data=f"task_edit:{task_id}"),
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"task_delete:{task_id}"),
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Làm mới", callback_data=f"task_detail:{task_id}"),
        InlineKeyboardButton("« Quay lại", callback_data="task_category:menu"),
    ])

    return InlineKeyboardMarkup(buttons)


async def xemviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xemviec or /vic [task_id] command.
    View task detail by ID or list all tasks.
    Supports G-ID group tasks with aggregated progress.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Check if task ID provided
        if context.args:
            task_id = context.args[0].upper()
            task = await get_task_by_public_id(db, task_id)

            if not task:
                await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
                return

            # Check if this is a group task (G-ID)
            if await is_group_task(db, task_id):
                # Get aggregated progress
                progress_info = await get_group_task_progress(db, task_id)
                child_tasks = await get_child_tasks(db, task_id)

                can_edit = task["creator_id"] == db_user["id"]

                msg = format_group_task_detail(task, progress_info, child_tasks)
                keyboard = group_task_keyboard(task_id, can_edit=can_edit)

                await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")
            else:
                # Regular task (T-ID or P-ID)
                can_edit = task["creator_id"] == db_user["id"]
                can_complete = task["assignee_id"] == db_user["id"]

                msg = format_task_detail(task)

                # Add parent task reference for P-ID tasks
                if task_id.startswith("P-") and task.get("parent_task_id"):
                    parent = await db.fetch_one(
                        "SELECT public_id FROM tasks WHERE id = $1",
                        task["parent_task_id"]
                    )
                    if parent:
                        msg += f"\n\n👥 Thuộc việc nhóm: {parent['public_id']}"

                keyboard = task_detail_keyboard(
                    task_id,
                    can_edit=can_edit,
                    can_complete=can_complete and task["status"] != "completed",
                )

                await update.message.reply_text(msg, reply_markup=keyboard)
        else:
            # Show task category menu
            await update.message.reply_text(
                "📋 CHỌN DANH MỤC VIỆC\n\n"
                "📋 Việc cá nhân - Việc bạn tự tạo cho mình\n"
                "📤 Việc đã giao - Việc bạn giao cho người khác\n"
                "📥 Việc đã nhận - Việc người khác giao cho bạn\n"
                "📊 Tất cả việc - Toàn bộ việc liên quan",
                reply_markup=task_category_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error in xemviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def viecnhom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /viecnhom command.
    View all tasks in current group.
    """
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    # Check if in group
    if chat.type == "private":
        await update.message.reply_text(ERR_GROUP_ONLY)
        return

    try:
        db = get_db()

        # Get group
        group = await db.fetch_one(
            "SELECT id FROM groups WHERE telegram_id = $1",
            chat.id
        )

        if not group:
            await update.message.reply_text("Nhóm chưa có việc nào.")
            return

        tasks = await get_group_tasks(db, group["id"], limit=20)

        if not tasks:
            await update.message.reply_text(
                f"Nhóm {chat.title} chưa có việc nào.\n\nGiao việc: /giaoviec @username [nội dung]"
            )
            return

        total = len(tasks)
        total_pages = (total + 9) // 10

        msg = format_task_list(
            tasks=tasks,
            title=f"VIỆC TRONG NHÓM {chat.title}",
            page=1,
            total=total,
        )

        await update.message.reply_text(
            msg,
            reply_markup=task_list_with_pagination(tasks, 1, total_pages, "group"),
        )

    except Exception as e:
        logger.error(f"Error in viecnhom_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def timviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /timviec [keyword] command.
    Search tasks by keyword.
    """
    user = update.effective_user
    if not user:
        return

    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text("Nhập từ khoá: /timviec [từ khoá]")
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Search in user's tasks
        tasks = await db.fetch_all(
            """
            SELECT t.*, u.display_name as assignee_name, c.display_name as creator_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            LEFT JOIN users c ON t.creator_id = c.id
            WHERE (t.assignee_id = $1 OR t.creator_id = $1)
            AND t.is_deleted = false
            AND (
                LOWER(t.content) LIKE LOWER($2)
                OR LOWER(t.description) LIKE LOWER($2)
                OR t.public_id ILIKE $2
            )
            ORDER BY t.created_at DESC
            LIMIT 20
            """,
            db_user["id"],
            f"%{query}%",
        )

        if not tasks:
            await update.message.reply_text(f"Không tìm thấy việc với từ khoá: {query}")
            return

        tasks = [dict(t) for t in tasks]
        msg = format_task_list(
            tasks=tasks,
            title=f"KẾT QUẢ TÌM KIẾM: {query}",
            page=1,
            total=len(tasks),
        )

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in timviec_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def viecdanhan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /viecdanhan or /viectoinhan command.
    List tasks assigned TO the user BY others.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Get tasks assigned to user by others
        tasks = await get_user_received_tasks(db, user_id, limit=20)

        if not tasks:
            await update.message.reply_text(
                "Bạn chưa được giao việc nào.\n\nXem tất cả việc: /xemviec"
            )
            return

        total = len(tasks)
        total_pages = (total + 9) // 10

        msg = format_task_list(
            tasks=tasks,
            title="VIỆC ĐƯỢC GIAO CHO BẠN",
            page=1,
            total=total,
        )

        await update.message.reply_text(
            msg,
            reply_markup=task_list_with_pagination(tasks, 1, total_pages, "received"),
        )

    except Exception as e:
        logger.error(f"Error in viecdanhan_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def deadline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /deadline [hours] command.
    Show tasks with deadline within specified hours.
    """
    user = update.effective_user
    if not user:
        return

    # Parse hours (default 24)
    hours = 24
    if context.args:
        try:
            arg = context.args[0].lower().replace("h", "")
            hours = int(arg)
        except ValueError:
            pass

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        tasks = await get_tasks_with_deadline(db, hours, db_user["id"])

        if not tasks:
            await update.message.reply_text(f"Không có việc nào trong {hours} giờ tới.")
            return

        msg = format_task_list(
            tasks=tasks,
            title=f"VIỆC TRONG {hours} GIỜ TỚI",
            page=1,
            total=len(tasks),
        )

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in deadline_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        # /xemviec - View ALL related tasks (created, received, assigned)
        CommandHandler(["xemviec", "vic"], xemviec_command),
        # /viecdanhan, /viectoinhan - Tasks assigned TO you BY others
        CommandHandler(["viecdanhan", "viectoinhan"], viecdanhan_command),
        CommandHandler(["viecnhom", "viecduan"], viecnhom_command),
        CommandHandler("timviec", timviec_command),
        CommandHandler("deadline", deadline_command),
    ]
