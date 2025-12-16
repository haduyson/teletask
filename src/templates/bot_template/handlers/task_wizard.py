"""
Task Wizard Handler
Step-by-step task creation with ConversationHandler
"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import get_db
from services import (
    get_or_create_user,
    get_user_by_id,
    create_task,
    create_group_task,
    find_users_by_mention,
    parse_vietnamese_time,
)
from utils import (
    ERR_DATABASE,
    MSG_TASK_CREATED,
    validate_task_content,
    format_datetime,
    format_priority,
    task_actions_keyboard,
    wizard_deadline_keyboard,
    wizard_assignee_keyboard,
    wizard_priority_keyboard,
    wizard_confirm_keyboard,
    wizard_cancel_keyboard,
)

logger = logging.getLogger(__name__)

# Conversation states
CONTENT, DEADLINE, DEADLINE_CUSTOM, ASSIGNEE, ASSIGNEE_INPUT, PRIORITY, CONFIRM = range(7)

# Priority mapping
PRIORITY_MAP = {
    "urgent": "urgent",
    "high": "high",
    "normal": "normal",
    "low": "low",
}

PRIORITY_LABELS = {
    "urgent": "Khẩn cấp",
    "high": "Cao",
    "normal": "Bình thường",
    "low": "Thấp",
}


def get_wizard_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Get wizard data from user_data."""
    if "wizard" not in context.user_data:
        context.user_data["wizard"] = {}
    return context.user_data["wizard"]


def clear_wizard_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear wizard data from user_data."""
    if "wizard" in context.user_data:
        del context.user_data["wizard"]


def format_wizard_summary(data: dict) -> str:
    """Format wizard data summary for confirmation."""
    content = data.get("content", "N/A")
    deadline = data.get("deadline")
    deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
    assignee_name = data.get("assignee_name", "Bản thân")
    priority = data.get("priority", "normal")
    priority_str = format_priority(priority)

    return f"""
TẠO VIỆC MỚI

Nội dung: {content}

Deadline: {deadline_str}
Người nhận: {assignee_name}
Độ ưu tiên: {priority_str}

Xác nhận tạo việc?
""".strip()


# =============================================================================
# Entry Point
# =============================================================================


async def wizard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start task creation wizard or direct creation if args provided."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Check if args provided -> direct creation (legacy mode)
    if context.args:
        await direct_task_creation(update, context)
        return ConversationHandler.END

    # Initialize wizard data
    clear_wizard_data(context)
    data = get_wizard_data(context)
    data["creator_id"] = None  # Will be set when accessing DB

    await update.message.reply_text(
        "TẠO VIỆC TỪNG BƯỚC\n\n"
        "Bước 1/5: Nhập nội dung việc\n\n"
        "Nhập nội dung việc cần làm:",
        reply_markup=wizard_cancel_keyboard(),
    )

    return CONTENT


async def direct_task_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct task creation with args (legacy /taoviec flow)."""
    user = update.effective_user
    text = " ".join(context.args)

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Parse time from content
        deadline, remaining = parse_vietnamese_time(text)
        content = remaining.strip() if remaining else text

        # Validate content
        is_valid, result = validate_task_content(content)
        if not is_valid:
            await update.message.reply_text(result)
            return

        content = result

        # Create task
        task = await create_task(
            db=db,
            content=content,
            creator_id=user_id,
            assignee_id=user_id,
            deadline=deadline,
            priority="normal",
            is_personal=True,
        )

        deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
        priority_str = format_priority("normal")

        await update.message.reply_text(
            MSG_TASK_CREATED.format(
                task_id=task["public_id"],
                content=content,
                deadline=deadline_str,
                priority=priority_str,
            ),
            reply_markup=task_actions_keyboard(task["public_id"]),
        )

        logger.info(f"Direct: User {user.id} created task {task['public_id']}")

    except Exception as e:
        logger.error(f"Error in direct_task_creation: {e}")
        await update.message.reply_text(ERR_DATABASE)


# =============================================================================
# Step 1: Content
# =============================================================================


async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive task content."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy tạo việc.")
        return ConversationHandler.END

    # Validate content
    is_valid, result = validate_task_content(text)
    if not is_valid:
        await update.message.reply_text(
            f"{result}\n\nVui lòng nhập lại nội dung:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return CONTENT

    # Save content
    data = get_wizard_data(context)
    data["content"] = result

    await update.message.reply_text(
        "Bước 2/5: Chọn deadline\n\n"
        "Chọn thời hạn hoàn thành hoặc nhập thời gian:",
        reply_markup=wizard_deadline_keyboard(),
    )

    return DEADLINE


# =============================================================================
# Step 2: Deadline
# =============================================================================


async def deadline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle deadline button selection."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    now = datetime.now()

    if action == "today":
        # End of today (23:59)
        data["deadline"] = now.replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "tomorrow":
        # End of tomorrow (23:59)
        data["deadline"] = (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "nextweek":
        # 7 days from now
        data["deadline"] = (now + timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "nextmonth":
        # 30 days from now
        data["deadline"] = (now + timedelta(days=30)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "skip":
        data["deadline"] = None
    elif action == "custom":
        await query.edit_message_text(
            "Nhập thời gian deadline:\n\n"
            "Ví dụ:\n"
            "• `14h30` - hôm nay 14:30\n"
            "• `ngày mai 10h` - ngày mai 10:00\n"
            "• `thứ 6 15h` - thứ 6 tuần này 15:00\n"
            "• `20/12 9h` - ngày 20/12\n\n"
            "Hoặc /huy để hủy",
            parse_mode="Markdown",
        )
        return DEADLINE_CUSTOM

    # Move to assignee step
    deadline_str = format_datetime(data.get("deadline"), relative=True) if data.get("deadline") else "Không có"

    # Get recent users for suggestions
    try:
        db = get_db()
        user = update.effective_user
        db_user = await get_or_create_user(db, user)
        data["creator_id"] = db_user["id"]

        # Get recent task assignees
        recent = await db.fetch_all(
            """
            SELECT DISTINCT u.id, u.display_name, u.username
            FROM users u
            JOIN tasks t ON t.assignee_id = u.id
            WHERE t.creator_id = $1 AND u.id != $1
            ORDER BY t.created_at DESC
            LIMIT 3
            """,
            db_user["id"],
        )
        recent_users = [dict(r) for r in recent] if recent else None
    except Exception:
        recent_users = None

    await query.edit_message_text(
        f"Deadline: {deadline_str}\n\n"
        "Bước 3/5: Chọn người nhận\n\n"
        "Giao việc cho ai?",
        reply_markup=wizard_assignee_keyboard(recent_users),
    )

    return ASSIGNEE


async def receive_deadline_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive custom deadline input."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy tạo việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)

    # Parse time
    deadline, _ = parse_vietnamese_time(text)

    if not deadline:
        await update.message.reply_text(
            "Không nhận dạng được thời gian.\n\n"
            "Ví dụ: `14h30`, `ngày mai 10h`, `20/12 9h`\n\n"
            "Nhập lại hoặc /huy để hủy:",
            parse_mode="Markdown",
        )
        return DEADLINE_CUSTOM

    data["deadline"] = deadline

    # Get recent users
    try:
        db = get_db()
        user = update.effective_user
        db_user = await get_or_create_user(db, user)
        data["creator_id"] = db_user["id"]

        recent = await db.fetch_all(
            """
            SELECT DISTINCT u.id, u.display_name, u.username
            FROM users u
            JOIN tasks t ON t.assignee_id = u.id
            WHERE t.creator_id = $1 AND u.id != $1
            ORDER BY t.created_at DESC
            LIMIT 3
            """,
            db_user["id"],
        )
        recent_users = [dict(r) for r in recent] if recent else None
    except Exception:
        recent_users = None

    deadline_str = format_datetime(deadline, relative=True)

    await update.message.reply_text(
        f"Deadline: {deadline_str}\n\n"
        "Bước 3/5: Chọn người nhận\n\n"
        "Giao việc cho ai?",
        reply_markup=wizard_assignee_keyboard(recent_users),
    )

    return ASSIGNEE


# =============================================================================
# Step 3: Assignee
# =============================================================================


async def assignee_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle assignee button selection."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "self":
        # Assign to self
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)
            data["assignee_ids"] = [db_user["id"]]
            data["assignee_name"] = "Bản thân"
            data["creator_id"] = db_user["id"]
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            await query.edit_message_text(ERR_DATABASE)
            return ConversationHandler.END

    elif action == "others":
        # Ask for @mention input
        await query.edit_message_text(
            "Nhập @username hoặc tag người nhận:\n\n"
            "Ví dụ:\n"
            "• `@username` - một người\n"
            "• `@user1 @user2` - nhiều người (tạo việc nhóm)\n\n"
            "Hoặc /huy để hủy",
            parse_mode="Markdown",
        )
        return ASSIGNEE_INPUT

    elif action.startswith("user:"):
        # Select recent user
        user_id = int(parts[2]) if len(parts) > 2 else None
        if user_id:
            try:
                db = get_db()
                assignee = await get_user_by_id(db, user_id)
                if assignee:
                    data["assignee_ids"] = [user_id]
                    data["assignee_name"] = assignee.get("display_name", "?")
            except Exception as e:
                logger.error(f"Error getting assignee: {e}")

    # Move to priority step
    assignee_name = data.get("assignee_name", "?")

    await query.edit_message_text(
        f"Người nhận: {assignee_name}\n\n"
        "Bước 4/5: Chọn độ ưu tiên",
        reply_markup=wizard_priority_keyboard(),
    )

    return PRIORITY


async def receive_assignee_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive assignee @mention input."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy tạo việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)

    try:
        db = get_db()

        # Find users by mention
        users = await find_users_by_mention(db, text)

        if not users:
            await update.message.reply_text(
                "Không tìm thấy người dùng.\n\n"
                "Vui lòng nhập @username chính xác hoặc /huy để hủy:",
            )
            return ASSIGNEE_INPUT

        data["assignee_ids"] = [u["id"] for u in users]

        if len(users) == 1:
            data["assignee_name"] = users[0].get("display_name", users[0].get("username", "?"))
        else:
            names = [u.get("display_name", u.get("username", "?"))[:10] for u in users[:3]]
            data["assignee_name"] = ", ".join(names)
            if len(users) > 3:
                data["assignee_name"] += f" +{len(users) - 3}"

    except Exception as e:
        logger.error(f"Error finding users: {e}")
        await update.message.reply_text(ERR_DATABASE)
        return ConversationHandler.END

    assignee_name = data.get("assignee_name", "?")

    await update.message.reply_text(
        f"Người nhận: {assignee_name}\n\n"
        "Bước 4/5: Chọn độ ưu tiên",
        reply_markup=wizard_priority_keyboard(),
    )

    return PRIORITY


# =============================================================================
# Step 4: Priority
# =============================================================================


async def priority_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle priority button selection."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else "normal"

    data["priority"] = PRIORITY_MAP.get(action, "normal")

    # Show confirmation
    summary = format_wizard_summary(data)

    await query.edit_message_text(
        f"Bước 5/5: Xác nhận\n\n{summary}",
        reply_markup=wizard_confirm_keyboard(),
    )

    return CONFIRM


# =============================================================================
# Step 5: Confirm
# =============================================================================


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation buttons."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    parts = query.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "cancel":
        clear_wizard_data(context)
        await query.edit_message_text("Đã hủy tạo việc.")
        return ConversationHandler.END

    if action == "create":
        # Create the task
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            assignee_ids = data.get("assignee_ids", [db_user["id"]])
            content = data.get("content", "")
            deadline = data.get("deadline")
            priority = data.get("priority", "normal")

            if len(assignee_ids) == 1:
                # Single assignee - create regular task
                task = await create_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignee_id=assignee_ids[0],
                    deadline=deadline,
                    priority=priority,
                    is_personal=(assignee_ids[0] == db_user["id"]),
                )

                deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
                priority_str = format_priority(priority)

                await query.edit_message_text(
                    MSG_TASK_CREATED.format(
                        task_id=task["public_id"],
                        content=content,
                        deadline=deadline_str,
                        priority=priority_str,
                    ),
                    reply_markup=task_actions_keyboard(task["public_id"]),
                )

                logger.info(f"Wizard: User {user.id} created task {task['public_id']}")

            else:
                # Multiple assignees - create group task
                group_task = await create_group_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignee_ids=assignee_ids,
                    deadline=deadline,
                    priority=priority,
                )

                deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
                priority_str = format_priority(priority)

                await query.edit_message_text(
                    f"VIỆC NHÓM ĐÃ TẠO\n\n"
                    f"ID: {group_task['public_id']}\n"
                    f"Nội dung: {content}\n"
                    f"Deadline: {deadline_str}\n"
                    f"Ưu tiên: {priority_str}\n"
                    f"Số người nhận: {len(assignee_ids)}\n\n"
                    f"Xem chi tiết: /xemviec {group_task['public_id']}",
                )

                logger.info(f"Wizard: User {user.id} created group task {group_task['public_id']}")

            clear_wizard_data(context)
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error creating task in wizard: {e}")
            await query.edit_message_text(ERR_DATABASE)
            clear_wizard_data(context)
            return ConversationHandler.END

    return CONFIRM


async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle edit buttons in confirmation step."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    field = parts[1] if len(parts) > 1 else ""

    if field == "content":
        await query.edit_message_text(
            "Sửa nội dung việc:\n\n"
            "Nhập nội dung mới:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return CONTENT

    elif field == "deadline":
        await query.edit_message_text(
            "Sửa deadline:\n\n"
            "Chọn thời hạn mới:",
            reply_markup=wizard_deadline_keyboard(),
        )
        return DEADLINE

    elif field == "assignee":
        # Get recent users
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            recent = await db.fetch_all(
                """
                SELECT DISTINCT u.id, u.display_name, u.username
                FROM users u
                JOIN tasks t ON t.assignee_id = u.id
                WHERE t.creator_id = $1 AND u.id != $1
                ORDER BY t.created_at DESC
                LIMIT 3
                """,
                db_user["id"],
            )
            recent_users = [dict(r) for r in recent] if recent else None
        except Exception:
            recent_users = None

        await query.edit_message_text(
            "Sửa người nhận:\n\n"
            "Chọn người nhận mới:",
            reply_markup=wizard_assignee_keyboard(recent_users),
        )
        return ASSIGNEE

    elif field == "priority":
        await query.edit_message_text(
            "Sửa độ ưu tiên:\n\n"
            "Chọn độ ưu tiên mới:",
            reply_markup=wizard_priority_keyboard(),
        )
        return PRIORITY

    return CONFIRM


# =============================================================================
# Back & Cancel Handlers
# =============================================================================


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back button."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    target = parts[1] if len(parts) > 1 else ""

    data = get_wizard_data(context)

    if target == "content":
        await query.edit_message_text(
            "Bước 1/5: Nhập nội dung việc\n\n"
            f"Nội dung hiện tại: {data.get('content', 'Chưa có')}\n\n"
            "Nhập nội dung mới hoặc /huy để hủy:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return CONTENT

    elif target == "deadline":
        await query.edit_message_text(
            "Bước 2/5: Chọn deadline\n\n"
            "Chọn thời hạn hoàn thành:",
            reply_markup=wizard_deadline_keyboard(),
        )
        return DEADLINE

    elif target == "assignee":
        # Get recent users
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            recent = await db.fetch_all(
                """
                SELECT DISTINCT u.id, u.display_name, u.username
                FROM users u
                JOIN tasks t ON t.assignee_id = u.id
                WHERE t.creator_id = $1 AND u.id != $1
                ORDER BY t.created_at DESC
                LIMIT 3
                """,
                db_user["id"],
            )
            recent_users = [dict(r) for r in recent] if recent else None
        except Exception:
            recent_users = None

        await query.edit_message_text(
            "Bước 3/5: Chọn người nhận\n\n"
            "Giao việc cho ai?",
            reply_markup=wizard_assignee_keyboard(recent_users),
        )
        return ASSIGNEE

    return CONTENT


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel button."""
    query = update.callback_query
    await query.answer()

    clear_wizard_data(context)
    await query.edit_message_text("Đã hủy tạo việc.")
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /huy command."""
    clear_wizard_data(context)
    await update.message.reply_text("Đã hủy tạo việc.")
    return ConversationHandler.END


# =============================================================================
# Handler Registration
# =============================================================================


def get_wizard_conversation_handler() -> ConversationHandler:
    """Get the wizard ConversationHandler for /taoviec."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("taoviec", wizard_start),
        ],
        states={
            CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content),
                CommandHandler("huy", cancel_command),
            ],
            DEADLINE: [
                CallbackQueryHandler(deadline_callback, pattern=r"^wizard_deadline:"),
                CallbackQueryHandler(back_callback, pattern=r"^wizard_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^wizard_cancel$"),
            ],
            DEADLINE_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deadline_custom),
                CommandHandler("huy", cancel_command),
            ],
            ASSIGNEE: [
                CallbackQueryHandler(assignee_callback, pattern=r"^wizard_assignee:"),
                CallbackQueryHandler(back_callback, pattern=r"^wizard_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^wizard_cancel$"),
            ],
            ASSIGNEE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_assignee_input),
                CommandHandler("huy", cancel_command),
            ],
            PRIORITY: [
                CallbackQueryHandler(priority_callback, pattern=r"^wizard_priority:"),
                CallbackQueryHandler(back_callback, pattern=r"^wizard_back:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^wizard_cancel$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(confirm_callback, pattern=r"^wizard_confirm:"),
                CallbackQueryHandler(edit_callback, pattern=r"^wizard_edit:"),
                CallbackQueryHandler(cancel_callback, pattern=r"^wizard_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("huy", cancel_command),
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_callback, pattern=r"^wizard_cancel$"),
        ],
        per_user=True,
        per_chat=True,
    )


# =============================================================================
# Assignment Wizard States (for /giaoviec)
# =============================================================================

ASSIGN_CONTENT, ASSIGN_RECIPIENT, ASSIGN_DEADLINE, ASSIGN_DEADLINE_CUSTOM, ASSIGN_PRIORITY, ASSIGN_CONFIRM = range(100, 106)


def format_assign_summary(data: dict) -> str:
    """Format assignment wizard data summary."""
    content = data.get("content", "N/A")
    deadline = data.get("deadline")
    deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
    assignee_name = data.get("assignee_name", "Chưa chọn")
    priority = data.get("priority", "normal")
    priority_str = format_priority(priority)

    return f"""
GIAO VIỆC MỚI

Nội dung: {content}

Người nhận: {assignee_name}
Deadline: {deadline_str}
Độ ưu tiên: {priority_str}

Xác nhận giao việc?
""".strip()


async def assign_wizard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start assignment wizard or direct creation if args provided."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Check if args provided -> use direct creation
    if context.args:
        # Import and call original giaoviec logic
        from handlers.task_assign import giaoviec_command
        await giaoviec_command(update, context)
        return ConversationHandler.END

    # Initialize wizard data
    clear_wizard_data(context)
    data = get_wizard_data(context)
    data["wizard_type"] = "assign"

    await update.message.reply_text(
        "GIAO VIỆC TỪNG BƯỚC\n\n"
        "Bước 1/5: Nhập nội dung việc\n\n"
        "Nhập nội dung việc cần giao:",
        reply_markup=wizard_cancel_keyboard(),
    )

    return ASSIGN_CONTENT


async def assign_receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive task content for assignment."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy giao việc.")
        return ConversationHandler.END

    # Validate content
    is_valid, result = validate_task_content(text)
    if not is_valid:
        await update.message.reply_text(
            f"{result}\n\nVui lòng nhập lại nội dung:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return ASSIGN_CONTENT

    data = get_wizard_data(context)
    data["content"] = result

    # Get recent assignees for suggestions
    try:
        db = get_db()
        user = update.effective_user
        db_user = await get_or_create_user(db, user)
        data["creator_id"] = db_user["id"]

        recent = await db.fetch_all(
            """
            SELECT DISTINCT u.id, u.display_name, u.username
            FROM users u
            JOIN tasks t ON t.assignee_id = u.id
            WHERE t.creator_id = $1 AND u.id != $1
            ORDER BY t.created_at DESC
            LIMIT 3
            """,
            db_user["id"],
        )
        recent_users = [dict(r) for r in recent] if recent else None
    except Exception:
        recent_users = None

    # Custom keyboard for assignment (no "self" option)
    buttons = []
    if recent_users:
        recent_row = []
        for user_rec in recent_users[:3]:
            name = user_rec.get("display_name", "?")[:10]
            user_id = user_rec.get("id")
            recent_row.append(
                InlineKeyboardButton(f"@{name}", callback_data=f"assign_user:{user_id}")
            )
        buttons.append(recent_row)

    buttons.extend([
        [InlineKeyboardButton("📝 Nhập @username", callback_data="assign_input")],
        [
            InlineKeyboardButton("« Quay lại", callback_data="assign_back:content"),
            InlineKeyboardButton("❌ Hủy", callback_data="assign_cancel"),
        ],
    ])

    await update.message.reply_text(
        "Bước 2/5: Chọn người nhận\n\n"
        "Chọn người nhận hoặc nhập @username:\n"
        "(Có thể nhập nhiều người: @user1 @user2)",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return ASSIGN_RECIPIENT


async def assign_recipient_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle recipient selection callback."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    action = query.data

    if action == "assign_input":
        await query.edit_message_text(
            "Nhập @username người nhận:\n\n"
            "Ví dụ:\n"
            "• `@username` - một người\n"
            "• `@user1 @user2` - nhiều người (tạo việc nhóm)\n\n"
            "Hoặc /huy để hủy",
            parse_mode="Markdown",
        )
        return ASSIGN_RECIPIENT  # Stay in same state but wait for text

    elif action.startswith("assign_user:"):
        user_id = int(action.split(":")[1])
        try:
            db = get_db()
            assignee = await get_user_by_id(db, user_id)
            if assignee:
                data["assignee_ids"] = [user_id]
                data["assignee_name"] = assignee.get("display_name", "?")
        except Exception as e:
            logger.error(f"Error getting assignee: {e}")

    elif action == "assign_cancel":
        clear_wizard_data(context)
        await query.edit_message_text("Đã hủy giao việc.")
        return ConversationHandler.END

    elif action == "assign_back:content":
        await query.edit_message_text(
            "Bước 1/5: Nhập nội dung việc\n\n"
            f"Nội dung hiện tại: {data.get('content', 'Chưa có')}\n\n"
            "Nhập nội dung mới hoặc /huy để hủy:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return ASSIGN_CONTENT

    # Move to deadline step
    await query.edit_message_text(
        f"Người nhận: {data.get('assignee_name', '?')}\n\n"
        "Bước 3/5: Chọn deadline",
        reply_markup=assign_deadline_keyboard(),
    )

    return ASSIGN_DEADLINE


async def assign_receive_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive recipient @mention input."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy giao việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)

    try:
        db = get_db()
        users = await find_users_by_mention(db, text)

        if not users:
            await update.message.reply_text(
                "Không tìm thấy người dùng.\n\n"
                "Vui lòng nhập @username chính xác.\n"
                "Người nhận cần /start bot trước.\n\n"
                "Hoặc /huy để hủy:",
            )
            return ASSIGN_RECIPIENT

        data["assignee_ids"] = [u["id"] for u in users]

        if len(users) == 1:
            data["assignee_name"] = users[0].get("display_name", users[0].get("username", "?"))
        else:
            names = [u.get("display_name", u.get("username", "?"))[:10] for u in users[:3]]
            data["assignee_name"] = ", ".join(names)
            if len(users) > 3:
                data["assignee_name"] += f" +{len(users) - 3}"

    except Exception as e:
        logger.error(f"Error finding users: {e}")
        await update.message.reply_text(ERR_DATABASE)
        return ConversationHandler.END

    await update.message.reply_text(
        f"Người nhận: {data.get('assignee_name', '?')}\n\n"
        "Bước 3/5: Chọn deadline",
        reply_markup=assign_deadline_keyboard(),
    )

    return ASSIGN_DEADLINE


def assign_deadline_keyboard() -> InlineKeyboardMarkup:
    """Deadline keyboard for assignment wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Hôm nay", callback_data="assign_deadline:today"),
            InlineKeyboardButton("📅 Ngày mai", callback_data="assign_deadline:tomorrow"),
        ],
        [
            InlineKeyboardButton("📅 Tuần sau", callback_data="assign_deadline:nextweek"),
            InlineKeyboardButton("⏰ Nhập khác", callback_data="assign_deadline:custom"),
        ],
        [
            InlineKeyboardButton("⏭️ Bỏ qua", callback_data="assign_deadline:skip"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="assign_back:recipient"),
            InlineKeyboardButton("❌ Hủy", callback_data="assign_cancel"),
        ],
    ])


async def assign_deadline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle deadline selection for assignment."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    now = datetime.now()

    if action == "today":
        data["deadline"] = now.replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "tomorrow":
        data["deadline"] = (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "nextweek":
        data["deadline"] = (now + timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "skip":
        data["deadline"] = None
    elif action == "custom":
        await query.edit_message_text(
            "Nhập thời gian deadline:\n\n"
            "Ví dụ: `14h30`, `ngày mai 10h`, `20/12 9h`\n\n"
            "Hoặc /huy để hủy",
            parse_mode="Markdown",
        )
        return ASSIGN_DEADLINE_CUSTOM

    # Move to priority
    await query.edit_message_text(
        "Bước 4/5: Chọn độ ưu tiên",
        reply_markup=assign_priority_keyboard(),
    )

    return ASSIGN_PRIORITY


async def assign_receive_deadline_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive custom deadline for assignment."""
    text = update.message.text.strip()

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy giao việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)
    deadline, _ = parse_vietnamese_time(text)

    if not deadline:
        await update.message.reply_text(
            "Không nhận dạng được thời gian.\n\n"
            "Ví dụ: `14h30`, `ngày mai 10h`, `20/12 9h`\n\n"
            "Nhập lại hoặc /huy để hủy:",
            parse_mode="Markdown",
        )
        return ASSIGN_DEADLINE_CUSTOM

    data["deadline"] = deadline

    await update.message.reply_text(
        "Bước 4/5: Chọn độ ưu tiên",
        reply_markup=assign_priority_keyboard(),
    )

    return ASSIGN_PRIORITY


def assign_priority_keyboard() -> InlineKeyboardMarkup:
    """Priority keyboard for assignment wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Khẩn cấp", callback_data="assign_priority:urgent"),
            InlineKeyboardButton("🟠 Cao", callback_data="assign_priority:high"),
        ],
        [
            InlineKeyboardButton("🟡 Bình thường", callback_data="assign_priority:normal"),
            InlineKeyboardButton("🟢 Thấp", callback_data="assign_priority:low"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="assign_back:deadline"),
            InlineKeyboardButton("❌ Hủy", callback_data="assign_cancel"),
        ],
    ])


async def assign_priority_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle priority selection for assignment."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    action = query.data.split(":")[1] if ":" in query.data else "normal"

    data["priority"] = PRIORITY_MAP.get(action, "normal")

    summary = format_assign_summary(data)

    await query.edit_message_text(
        f"Bước 5/5: Xác nhận\n\n{summary}",
        reply_markup=assign_confirm_keyboard(),
    )

    return ASSIGN_CONFIRM


def assign_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for assignment wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Giao việc", callback_data="assign_confirm:create"),
            InlineKeyboardButton("❌ Hủy bỏ", callback_data="assign_confirm:cancel"),
        ],
        [
            InlineKeyboardButton("✏️ Sửa nội dung", callback_data="assign_edit:content"),
            InlineKeyboardButton("👤 Sửa người nhận", callback_data="assign_edit:recipient"),
        ],
    ])


async def assign_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for assignment wizard."""
    query = update.callback_query
    await query.answer()

    data = get_wizard_data(context)
    action = query.data.split(":")[1] if ":" in query.data else ""

    if action == "cancel":
        clear_wizard_data(context)
        await query.edit_message_text("Đã hủy giao việc.")
        return ConversationHandler.END

    if action == "create":
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            assignee_ids = data.get("assignee_ids", [])
            content = data.get("content", "")
            deadline = data.get("deadline")
            priority = data.get("priority", "normal")

            if not assignee_ids:
                await query.edit_message_text("Lỗi: Chưa chọn người nhận.")
                clear_wizard_data(context)
                return ConversationHandler.END

            deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"

            if len(assignee_ids) == 1:
                # Single assignee
                task = await create_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignee_id=assignee_ids[0],
                    deadline=deadline,
                    priority=priority,
                    is_personal=False,
                )

                await query.edit_message_text(
                    f"✅ ĐÃ GIAO VIỆC\n\n"
                    f"ID: {task['public_id']}\n"
                    f"Nội dung: {content}\n"
                    f"Người nhận: {data.get('assignee_name', '?')}\n"
                    f"Deadline: {deadline_str}\n\n"
                    f"Xem chi tiết: /xemviec {task['public_id']}",
                )

                logger.info(f"Assign wizard: User {user.id} assigned task {task['public_id']}")

            else:
                # Multiple assignees - group task
                group_task = await create_group_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignee_ids=assignee_ids,
                    deadline=deadline,
                    priority=priority,
                )

                await query.edit_message_text(
                    f"✅ ĐÃ TẠO VIỆC NHÓM\n\n"
                    f"ID: {group_task['public_id']}\n"
                    f"Nội dung: {content}\n"
                    f"Số người nhận: {len(assignee_ids)}\n"
                    f"Deadline: {deadline_str}\n\n"
                    f"Xem chi tiết: /xemviec {group_task['public_id']}",
                )

                logger.info(f"Assign wizard: User {user.id} created group task {group_task['public_id']}")

            clear_wizard_data(context)
            return ConversationHandler.END

        except Exception as e:
            logger.error(f"Error in assign wizard confirm: {e}")
            await query.edit_message_text(ERR_DATABASE)
            clear_wizard_data(context)
            return ConversationHandler.END

    return ASSIGN_CONFIRM


async def assign_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle edit buttons in assignment confirmation."""
    query = update.callback_query
    await query.answer()

    field = query.data.split(":")[1] if ":" in query.data else ""
    data = get_wizard_data(context)

    if field == "content":
        await query.edit_message_text(
            "Sửa nội dung việc:\n\n"
            f"Nội dung hiện tại: {data.get('content', 'N/A')}\n\n"
            "Nhập nội dung mới:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return ASSIGN_CONTENT

    elif field == "recipient":
        # Get recent users
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            recent = await db.fetch_all(
                """
                SELECT DISTINCT u.id, u.display_name, u.username
                FROM users u
                JOIN tasks t ON t.assignee_id = u.id
                WHERE t.creator_id = $1 AND u.id != $1
                ORDER BY t.created_at DESC
                LIMIT 3
                """,
                db_user["id"],
            )
            recent_users = [dict(r) for r in recent] if recent else None
        except Exception:
            recent_users = None

        buttons = []
        if recent_users:
            recent_row = []
            for user_rec in recent_users[:3]:
                name = user_rec.get("display_name", "?")[:10]
                user_id = user_rec.get("id")
                recent_row.append(
                    InlineKeyboardButton(f"@{name}", callback_data=f"assign_user:{user_id}")
                )
            buttons.append(recent_row)

        buttons.extend([
            [InlineKeyboardButton("📝 Nhập @username", callback_data="assign_input")],
            [
                InlineKeyboardButton("« Quay lại", callback_data="assign_back:content"),
                InlineKeyboardButton("❌ Hủy", callback_data="assign_cancel"),
            ],
        ])

        await query.edit_message_text(
            "Sửa người nhận:\n\n"
            "Chọn người nhận hoặc nhập @username:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return ASSIGN_RECIPIENT

    return ASSIGN_CONFIRM


async def assign_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back button in assignment wizard."""
    query = update.callback_query
    await query.answer()

    target = query.data.split(":")[1] if ":" in query.data else ""
    data = get_wizard_data(context)

    if target == "content":
        await query.edit_message_text(
            "Bước 1/5: Nhập nội dung việc\n\n"
            f"Nội dung hiện tại: {data.get('content', 'Chưa có')}\n\n"
            "Nhập nội dung mới hoặc /huy để hủy:",
            reply_markup=wizard_cancel_keyboard(),
        )
        return ASSIGN_CONTENT

    elif target == "recipient":
        # Get recent users
        try:
            db = get_db()
            user = update.effective_user
            db_user = await get_or_create_user(db, user)

            recent = await db.fetch_all(
                """
                SELECT DISTINCT u.id, u.display_name, u.username
                FROM users u
                JOIN tasks t ON t.assignee_id = u.id
                WHERE t.creator_id = $1 AND u.id != $1
                ORDER BY t.created_at DESC
                LIMIT 3
                """,
                db_user["id"],
            )
            recent_users = [dict(r) for r in recent] if recent else None
        except Exception:
            recent_users = None

        buttons = []
        if recent_users:
            recent_row = []
            for user_rec in recent_users[:3]:
                name = user_rec.get("display_name", "?")[:10]
                user_id = user_rec.get("id")
                recent_row.append(
                    InlineKeyboardButton(f"@{name}", callback_data=f"assign_user:{user_id}")
                )
            buttons.append(recent_row)

        buttons.extend([
            [InlineKeyboardButton("📝 Nhập @username", callback_data="assign_input")],
            [
                InlineKeyboardButton("« Quay lại", callback_data="assign_back:content"),
                InlineKeyboardButton("❌ Hủy", callback_data="assign_cancel"),
            ],
        ])

        await query.edit_message_text(
            "Bước 2/5: Chọn người nhận\n\n"
            "Chọn người nhận hoặc nhập @username:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return ASSIGN_RECIPIENT

    elif target == "deadline":
        await query.edit_message_text(
            "Bước 3/5: Chọn deadline",
            reply_markup=assign_deadline_keyboard(),
        )
        return ASSIGN_DEADLINE

    return ASSIGN_CONTENT


async def assign_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel in assignment wizard."""
    query = update.callback_query
    await query.answer()

    clear_wizard_data(context)
    await query.edit_message_text("Đã hủy giao việc.")
    return ConversationHandler.END


def get_assign_wizard_conversation_handler() -> ConversationHandler:
    """Get the assignment wizard ConversationHandler for /giaoviec."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("giaoviec", assign_wizard_start),
        ],
        states={
            ASSIGN_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, assign_receive_content),
                CommandHandler("huy", cancel_command),
            ],
            ASSIGN_RECIPIENT: [
                CallbackQueryHandler(assign_recipient_callback, pattern=r"^assign_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, assign_receive_recipient),
                CommandHandler("huy", cancel_command),
            ],
            ASSIGN_DEADLINE: [
                CallbackQueryHandler(assign_deadline_callback, pattern=r"^assign_deadline:"),
                CallbackQueryHandler(assign_back_callback, pattern=r"^assign_back:"),
                CallbackQueryHandler(assign_cancel_callback, pattern=r"^assign_cancel$"),
            ],
            ASSIGN_DEADLINE_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, assign_receive_deadline_custom),
                CommandHandler("huy", cancel_command),
            ],
            ASSIGN_PRIORITY: [
                CallbackQueryHandler(assign_priority_callback, pattern=r"^assign_priority:"),
                CallbackQueryHandler(assign_back_callback, pattern=r"^assign_back:"),
                CallbackQueryHandler(assign_cancel_callback, pattern=r"^assign_cancel$"),
            ],
            ASSIGN_CONFIRM: [
                CallbackQueryHandler(assign_confirm_callback, pattern=r"^assign_confirm:"),
                CallbackQueryHandler(assign_edit_callback, pattern=r"^assign_edit:"),
                CallbackQueryHandler(assign_cancel_callback, pattern=r"^assign_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("huy", cancel_command),
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(assign_cancel_callback, pattern=r"^assign_cancel$"),
        ],
        per_user=True,
        per_chat=True,
    )


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        get_wizard_conversation_handler(),
        get_assign_wizard_conversation_handler(),
    ]
