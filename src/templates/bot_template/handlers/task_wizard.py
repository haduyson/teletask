"""
Task Wizard Handler
Step-by-step task creation with ConversationHandler
"""

import warnings
warnings.filterwarnings("ignore", message=".*per_message.*", category=UserWarning)

import logging
from datetime import datetime, timedelta
import pytz
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
    get_user_by_username,
    create_task,
    create_group_task,
    parse_vietnamese_time,
)
from handlers.calendar import sync_task_to_calendar
from utils import (
    ERR_DATABASE,
    MSG_TASK_CREATED,
    validate_task_content,
    extract_mentions,
    format_datetime,
    format_priority,
    mention_user,
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


async def send_private_notification(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
    message: str,
    parse_mode: str = "Markdown",
    reply_markup=None,
) -> bool:
    """
    Send private DM notification to a user.

    Args:
        context: Telegram context
        telegram_id: User's Telegram ID
        message: Message text
        parse_mode: Message parse mode
        reply_markup: Optional inline keyboard

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return True
    except Exception as e:
        logger.warning(f"Could not send private notification to {telegram_id}: {e}")
        return False


def format_wizard_summary(data: dict) -> str:
    """Format wizard data summary for confirmation."""
    content = data.get("content", "N/A")
    deadline = data.get("deadline")
    deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
    assignee_name = data.get("assignee_name", "Bản thân")
    priority = data.get("priority", "normal")
    priority_str = format_priority(priority)

    return f"""
<b>TẠO VIỆC MỚI</b>

<b>Nội dung:</b> {content}

<b>Deadline:</b> {deadline_str}
<b>Người nhận:</b> {assignee_name}
<b>Độ ưu tiên:</b> {priority_str}

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

    # Check if group chat - need REPLY instruction
    chat = update.effective_chat
    is_group = chat and chat.type in ["group", "supergroup"]

    reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập (vuốt phải)" if is_group else ""

    await update.message.reply_text(
        f"TẠO VIỆC TỪNG BƯỚC\n\n"
        f"Bước 1/5: Nhập nội dung việc\n\n"
        f"Nhập nội dung việc cần làm:{reply_hint}",
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
            reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
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

    # Use timezone-aware datetime
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)

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
        # Check if group chat
        chat = update.effective_chat
        is_group = chat and chat.type in ["group", "supergroup"]
        reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập" if is_group else ""

        await query.edit_message_text(
            f"Nhập thời gian deadline:\n\n"
            f"Ví dụ:\n"
            f"• `14h30` - hôm nay 14:30\n"
            f"• `ngày mai 10h` - ngày mai 10:00\n"
            f"• `thứ 6 15h` - thứ 6 tuần này 15:00\n"
            f"• `20/12 9h` - ngày 20/12{reply_hint}\n\n"
            f"Hoặc /huy để hủy",
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

    # Check if private chat
    is_private = update.effective_chat.type == "private"

    await query.edit_message_text(
        f"Deadline: {deadline_str}\n\n"
        "Bước 3/5: Chọn người nhận\n\n"
        "Giao việc cho ai?",
        reply_markup=wizard_assignee_keyboard(recent_users, is_private_chat=is_private),
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

    # Check if private chat
    is_private = update.effective_chat.type == "private"

    await update.message.reply_text(
        f"Deadline: {deadline_str}\n\n"
        "Bước 3/5: Chọn người nhận\n\n"
        "Giao việc cho ai?",
        reply_markup=wizard_assignee_keyboard(recent_users, is_private_chat=is_private),
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
        # Check if group chat
        chat = update.effective_chat
        is_group = chat and chat.type in ["group", "supergroup"]
        reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập" if is_group else ""

        # Ask for @mention input
        await query.edit_message_text(
            f"Nhập @username hoặc tag người nhận:\n\n"
            f"Ví dụ:\n"
            f"• `@username` - một người\n"
            f"• `@user1 @user2` - nhiều người (tạo việc nhóm){reply_hint}\n\n"
            f"Hoặc /huy để hủy",
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
    """Receive assignee mention input (supports both @username and text_mention)."""
    text = update.message.text.strip()
    message = update.message

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy tạo việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)

    try:
        db = get_db()
        users = []

        # Method 1: Check message entities for text_mention (users without username)
        if message.entities:
            for entity in message.entities:
                if entity.type == "text_mention" and entity.user:
                    # User without username - register/get from entity.user
                    mentioned_user = await get_or_create_user(db, entity.user)
                    if not any(u["id"] == mentioned_user["id"] for u in users):
                        users.append(mentioned_user)
                        logger.info(f"Found text_mention: {entity.user.first_name} (id={entity.user.id})")

                elif entity.type == "mention":
                    # @username mention - extract from text
                    full_text = message.text or ""
                    username_with_at = full_text[entity.offset:entity.offset + entity.length]
                    username = username_with_at.lstrip("@")
                    found_user = await get_user_by_username(db, username)
                    if found_user and not any(u["id"] == found_user["id"] for u in users):
                        users.append(found_user)
                        logger.info(f"Found @mention: @{username} (id={found_user['id']})")

        # Method 2: Fallback to extract_mentions for @username in plain text
        if not users:
            usernames, _ = extract_mentions(text)
            not_found = []
            for username in usernames:
                user = await get_user_by_username(db, username)
                if user and not any(u["id"] == user["id"] for u in users):
                    users.append(user)
                else:
                    not_found.append(username)

            if not users and not_found:
                await update.message.reply_text(
                    f"Không tìm thấy: @{', @'.join(not_found)}\n\n"
                    "Người nhận cần /start bot trước.\n"
                    "Vui lòng tag tên hoặc nhập @username:",
                )
                return ASSIGNEE_INPUT

        if not users:
            await update.message.reply_text(
                "Vui lòng tag tên người nhận hoặc nhập @username.\n\n"
                "💡 Tip: Tag tên (vuốt phải reply) hoặc gõ @username\n"
                "Hoặc /huy để hủy:",
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
        f"<b>Bước 5/5:</b> Xác nhận\n\n{summary}",
        reply_markup=wizard_confirm_keyboard(),
        parse_mode="HTML",
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
            chat = update.effective_chat
            db_user = await get_or_create_user(db, user)
            is_group_chat = chat.type in ["group", "supergroup"]

            assignee_ids = data.get("assignee_ids", [db_user["id"]])
            content = data.get("content", "")
            deadline = data.get("deadline")
            priority = data.get("priority", "normal")

            if len(assignee_ids) == 1:
                # Single assignee - create regular task
                is_personal = (assignee_ids[0] == db_user["id"])
                task = await create_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignee_id=assignee_ids[0],
                    deadline=deadline,
                    priority=priority,
                    is_personal=is_personal,
                )

                deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
                priority_str = format_priority(priority)

                if is_personal:
                    # Personal task - no mention needed
                    await query.edit_message_text(
                        MSG_TASK_CREATED.format(
                            task_id=task["public_id"],
                            content=content,
                            deadline=deadline_str,
                            priority=priority_str,
                        ),
                        reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
                    )

                    # Sync to Google Calendar if connected
                    calendar_synced = False
                    if deadline:
                        calendar_synced = await sync_task_to_calendar(db, task, db_user["id"])

                    # Send private notification if created in group
                    if is_group_chat:
                        calendar_note = "\n📅 *Đã thêm vào Google Calendar*" if calendar_synced else ""
                        await send_private_notification(
                            context,
                            user.id,
                            f"📋 *Việc cá nhân đã tạo*\n\n"
                            f"*{task['public_id']}*: {content}\n"
                            f"📅 Deadline: {deadline_str}\n"
                            f"⚡ Ưu tiên: {priority_str}{calendar_note}\n\n"
                            f"Xem chi tiết: /xemviec {task['public_id']}",
                            reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
                        )
                else:
                    # Task assigned to someone else - show mention
                    assignee = await get_user_by_id(db, assignee_ids[0])
                    assignee_mention = mention_user(assignee) if assignee else data.get("assignee_name", "?")
                    await query.edit_message_text(
                        f"✅ ĐÃ TẠO VIỆC\n\n"
                        f"📋 *{task['public_id']}*: {content}\n"
                        f"👤 Người nhận: {assignee_mention}\n"
                        f"📅 Deadline: {deadline_str}\n"
                        f"⚡ Ưu tiên: {priority_str}\n\n"
                        f"Xem chi tiết: /xemviec {task['public_id']}",
                        parse_mode="Markdown",
                        reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
                    )

                    # Send private notification to creator if in group
                    if is_group_chat:
                        await send_private_notification(
                            context,
                            user.id,
                            f"✅ *Đã giao việc*\n\n"
                            f"📋 *{task['public_id']}*: {content}\n"
                            f"👤 Giao cho: {assignee_mention}\n"
                            f"📅 Deadline: {deadline_str}\n\n"
                            f"Xem chi tiết: /xemviec {task['public_id']}",
                            reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
                        )

                    # Send private notification to assignee and sync calendar
                    if assignee and assignee.get("telegram_id") != user.id:
                        creator_mention = mention_user(db_user)

                        # Sync to assignee's Google Calendar if connected
                        calendar_synced = False
                        if deadline:
                            calendar_synced = await sync_task_to_calendar(db, task, assignee_ids[0])
                        calendar_note = "\n📅 *Đã thêm vào Google Calendar*" if calendar_synced else ""

                        await send_private_notification(
                            context,
                            assignee["telegram_id"],
                            f"📬 *Bạn có việc mới!*\n\n"
                            f"📋 *{task['public_id']}*: {content}\n"
                            f"👤 Từ: {creator_mention}\n"
                            f"📅 Deadline: {deadline_str}{calendar_note}\n\n"
                            f"Trả lời /xong {task['public_id']} khi hoàn thành.",
                            reply_markup=task_actions_keyboard(task["public_id"], show_complete=False),
                        )

                logger.info(f"Wizard: User {user.id} created task {task['public_id']}")

            else:
                # Multiple assignees - fetch user objects and create group task
                assignees = []
                for aid in assignee_ids:
                    assignee = await get_user_by_id(db, aid)
                    if assignee:
                        assignees.append(assignee)

                if not assignees:
                    await query.edit_message_text("Không tìm thấy người nhận.")
                    clear_wizard_data(context)
                    return ConversationHandler.END

                group_task, child_tasks = await create_group_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignees=assignees,
                    deadline=deadline,
                    priority=priority,
                )

                deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"
                priority_str = format_priority(priority)

                # Create mention tags for assignees
                assignee_mentions = ", ".join(mention_user(a) for a in assignees)

                await query.edit_message_text(
                    f"✅ VIỆC NHÓM ĐÃ TẠO\n\n"
                    f"📋 *{group_task['public_id']}*: {content}\n"
                    f"👥 Người nhận: {assignee_mentions}\n"
                    f"📅 Deadline: {deadline_str}\n"
                    f"⚡ Ưu tiên: {priority_str}\n\n"
                    f"Xem chi tiết: /xemviec {group_task['public_id']}",
                    parse_mode="Markdown",
                )

                # Send private notification to creator if in group
                if is_group_chat:
                    await send_private_notification(
                        context,
                        user.id,
                        f"✅ *Đã tạo việc nhóm*\n\n"
                        f"📋 *{group_task['public_id']}*: {content}\n"
                        f"👥 Người nhận: {assignee_mentions}\n"
                        f"📅 Deadline: {deadline_str}\n\n"
                        f"Xem chi tiết: /xemviec {group_task['public_id']}",
                    )

                # Send private notification to each assignee with their P-ID
                creator_mention = mention_user(db_user)
                for child_task, assignee in child_tasks:
                    if assignee.get("telegram_id") != user.id:
                        await send_private_notification(
                            context,
                            assignee["telegram_id"],
                            f"📬 *Bạn có việc nhóm mới!*\n\n"
                            f"📋 *{group_task['public_id']}*: {content}\n"
                            f"👤 Từ: {creator_mention}\n"
                            f"📅 Deadline: {deadline_str}\n"
                            f"👥 Thành viên: {len(assignees)} người\n\n"
                            f"🔖 Việc của bạn: *{child_task['public_id']}*\n"
                            f"Trả lời /xong {child_task['public_id']} khi hoàn thành.",
                            reply_markup=task_actions_keyboard(child_task['public_id'], show_complete=False),
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

    # Show edit menu
    if field == "menu":
        from utils.keyboards import wizard_edit_menu_keyboard
        await query.edit_message_text(
            "✏️ <b>Sửa thông tin việc</b>\n\n"
            "Chọn mục cần sửa:",
            reply_markup=wizard_edit_menu_keyboard(),
            parse_mode="HTML",
        )
        return CONFIRM

    # Back to confirm screen
    if field == "back":
        data = get_wizard_data(context)
        summary = format_wizard_summary(data)
        from utils.keyboards import wizard_confirm_keyboard
        await query.edit_message_text(
            f"<b>Bước 5/5:</b> Xác nhận\n\n{summary}",
            reply_markup=wizard_confirm_keyboard(),
            parse_mode="HTML",
        )
        return CONFIRM

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

        is_private = update.effective_chat.type == "private"
        await query.edit_message_text(
            "Sửa người nhận:\n\n"
            "Chọn người nhận mới:",
            reply_markup=wizard_assignee_keyboard(recent_users, is_private_chat=is_private),
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

        is_private = update.effective_chat.type == "private"
        await query.edit_message_text(
            "Bước 3/5: Chọn người nhận\n\n"
            "Giao việc cho ai?",
            reply_markup=wizard_assignee_keyboard(recent_users, is_private_chat=is_private),
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
        per_message=False,
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
<b>GIAO VIỆC MỚI</b>

<b>Nội dung:</b> {content}

<b>Người nhận:</b> {assignee_name}
<b>Deadline:</b> {deadline_str}
<b>Độ ưu tiên:</b> {priority_str}

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

    # Check if group chat - need REPLY instruction
    chat = update.effective_chat
    is_group = chat and chat.type in ["group", "supergroup"]
    reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập (vuốt phải)" if is_group else ""

    await update.message.reply_text(
        f"GIAO VIỆC TỪNG BƯỚC\n\n"
        f"Bước 1/5: Nhập nội dung việc\n\n"
        f"Nhập nội dung việc cần giao:{reply_hint}",
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
        # Check if group chat
        chat = update.effective_chat
        is_group = chat and chat.type in ["group", "supergroup"]
        reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập" if is_group else ""

        await query.edit_message_text(
            f"Nhập @username người nhận:\n\n"
            f"Ví dụ:\n"
            f"• `@username` - một người\n"
            f"• `@user1 @user2` - nhiều người (tạo việc nhóm){reply_hint}\n\n"
            f"Hoặc /huy để hủy",
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
    """Receive recipient mention input (supports both @username and text_mention)."""
    text = update.message.text.strip()
    message = update.message

    if text.lower() in ["/huy", "/cancel"]:
        clear_wizard_data(context)
        await update.message.reply_text("Đã hủy giao việc.")
        return ConversationHandler.END

    data = get_wizard_data(context)

    try:
        db = get_db()
        users = []

        # Method 1: Check message entities for text_mention (users without username)
        if message.entities:
            for entity in message.entities:
                if entity.type == "text_mention" and entity.user:
                    # User without username - register/get from entity.user
                    mentioned_user = await get_or_create_user(db, entity.user)
                    if not any(u["id"] == mentioned_user["id"] for u in users):
                        users.append(mentioned_user)
                        logger.info(f"Found text_mention: {entity.user.first_name} (id={entity.user.id})")

                elif entity.type == "mention":
                    # @username mention - extract from text
                    full_text = message.text or ""
                    username_with_at = full_text[entity.offset:entity.offset + entity.length]
                    username = username_with_at.lstrip("@")
                    found_user = await get_user_by_username(db, username)
                    if found_user and not any(u["id"] == found_user["id"] for u in users):
                        users.append(found_user)
                        logger.info(f"Found @mention: @{username} (id={found_user['id']})")

        # Method 2: Fallback to extract_mentions for @username in plain text
        if not users:
            usernames, _ = extract_mentions(text)
            not_found = []
            for username in usernames:
                user = await get_user_by_username(db, username)
                if user and not any(u["id"] == user["id"] for u in users):
                    users.append(user)
                else:
                    not_found.append(username)

            if not users and not_found:
                await update.message.reply_text(
                    f"Không tìm thấy: @{', @'.join(not_found)}\n\n"
                    "Người nhận cần /start bot trước.\n"
                    "Vui lòng tag tên hoặc nhập @username:",
                )
                return ASSIGN_RECIPIENT

        if not users:
            await update.message.reply_text(
                "Vui lòng tag tên người nhận hoặc nhập @username.\n\n"
                "💡 Tip: Tag tên (vuốt phải reply) hoặc gõ @username\n"
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

    # Use timezone-aware datetime
    tz = pytz.timezone("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)

    if action == "today":
        data["deadline"] = now.replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "tomorrow":
        data["deadline"] = (now + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "nextweek":
        data["deadline"] = (now + timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)
    elif action == "skip":
        data["deadline"] = None
    elif action == "custom":
        # Check if group chat
        chat = update.effective_chat
        is_group = chat and chat.type in ["group", "supergroup"]
        reply_hint = "\n\n⚠️ REPLY tin nhắn này khi nhập" if is_group else ""

        await query.edit_message_text(
            f"Nhập thời gian deadline:\n\n"
            f"Ví dụ: `14h30`, `ngày mai 10h`, `20/12 9h`{reply_hint}\n\n"
            f"Hoặc /huy để hủy",
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
        f"<b>Bước 5/5:</b> Xác nhận\n\n{summary}",
        reply_markup=assign_confirm_keyboard(),
        parse_mode="HTML",
    )

    return ASSIGN_CONFIRM


def assign_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for assignment wizard - each on separate row."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ SỬA THÔNG TIN", callback_data="assign_edit:menu")],
        [InlineKeyboardButton("❌ Hủy giao việc", callback_data="assign_confirm:cancel")],
        [InlineKeyboardButton("✅ XÁC NHẬN GIAO VIỆC", callback_data="assign_confirm:create")],
    ])


def assign_edit_menu_keyboard() -> InlineKeyboardMarkup:
    """Edit submenu for task assignment wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Sửa nội dung", callback_data="assign_edit:content"),
        ],
        [
            InlineKeyboardButton("👤 Sửa người nhận", callback_data="assign_edit:recipient"),
        ],
        [
            InlineKeyboardButton("📅 Sửa deadline", callback_data="assign_edit:deadline"),
        ],
        [
            InlineKeyboardButton("🔔 Sửa độ ưu tiên", callback_data="assign_edit:priority"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="assign_edit:back"),
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
            chat = update.effective_chat
            db_user = await get_or_create_user(db, user)
            is_group_chat = chat.type in ["group", "supergroup"]

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

                # Get assignee for mention
                assignee = await get_user_by_id(db, assignee_ids[0])
                assignee_mention = mention_user(assignee) if assignee else data.get("assignee_name", "?")

                await query.edit_message_text(
                    f"✅ ĐÃ GIAO VIỆC\n\n"
                    f"📋 *{task['public_id']}*: {content}\n"
                    f"👤 Người nhận: {assignee_mention}\n"
                    f"📅 Deadline: {deadline_str}\n\n"
                    f"Xem chi tiết: /xemviec {task['public_id']}",
                    parse_mode="Markdown",
                )

                # Send private notification to creator if in group
                if is_group_chat:
                    await send_private_notification(
                        context,
                        user.id,
                        f"✅ *Đã giao việc*\n\n"
                        f"📋 *{task['public_id']}*: {content}\n"
                        f"👤 Giao cho: {assignee_mention}\n"
                        f"📅 Deadline: {deadline_str}\n\n"
                        f"Xem chi tiết: /xemviec {task['public_id']}",
                        reply_markup=task_actions_keyboard(task['public_id'], show_complete=False),
                    )

                # Send private notification to assignee and sync calendar
                if assignee and assignee.get("telegram_id") != user.id:
                    creator_mention = mention_user(db_user)

                    # Sync to assignee's Google Calendar if connected
                    calendar_synced = False
                    if deadline:
                        calendar_synced = await sync_task_to_calendar(db, task, assignee_ids[0])
                    calendar_note = "\n📅 *Đã thêm vào Google Calendar*" if calendar_synced else ""

                    await send_private_notification(
                        context,
                        assignee["telegram_id"],
                        f"📬 *Bạn có việc mới!*\n\n"
                        f"📋 *{task['public_id']}*: {content}\n"
                        f"👤 Từ: {creator_mention}\n"
                        f"📅 Deadline: {deadline_str}{calendar_note}\n\n"
                        f"Trả lời /xong {task['public_id']} khi hoàn thành.",
                        reply_markup=task_actions_keyboard(task['public_id'], show_complete=False),
                    )

                logger.info(f"Assign wizard: User {user.id} assigned task {task['public_id']}")

            else:
                # Multiple assignees - fetch user objects and create group task
                assignees = []
                for aid in assignee_ids:
                    assignee = await get_user_by_id(db, aid)
                    if assignee:
                        assignees.append(assignee)

                if not assignees:
                    await query.edit_message_text("Không tìm thấy người nhận.")
                    clear_wizard_data(context)
                    return ConversationHandler.END

                group_task, child_tasks = await create_group_task(
                    db=db,
                    content=content,
                    creator_id=db_user["id"],
                    assignees=assignees,
                    deadline=deadline,
                    priority=priority,
                )

                # Create mention tags for assignees
                assignee_mentions = ", ".join(mention_user(a) for a in assignees)

                await query.edit_message_text(
                    f"✅ ĐÃ TẠO VIỆC NHÓM\n\n"
                    f"📋 *{group_task['public_id']}*: {content}\n"
                    f"👥 Người nhận: {assignee_mentions}\n"
                    f"📅 Deadline: {deadline_str}\n\n"
                    f"Xem chi tiết: /xemviec {group_task['public_id']}",
                    parse_mode="Markdown",
                )

                # Send private notification to creator if in group
                if is_group_chat:
                    await send_private_notification(
                        context,
                        user.id,
                        f"✅ *Đã tạo việc nhóm*\n\n"
                        f"📋 *{group_task['public_id']}*: {content}\n"
                        f"👥 Người nhận: {assignee_mentions}\n"
                        f"📅 Deadline: {deadline_str}\n\n"
                        f"Xem chi tiết: /xemviec {group_task['public_id']}",
                    )

                # Send private notification to each assignee with their P-ID and sync calendar
                creator_mention = mention_user(db_user)
                for child_task, assignee in child_tasks:
                    if assignee.get("telegram_id") != user.id:
                        # Sync to assignee's Google Calendar if connected
                        calendar_synced = False
                        if deadline:
                            calendar_synced = await sync_task_to_calendar(db, child_task, assignee["id"])
                        calendar_note = "\n📅 *Đã thêm vào Google Calendar*" if calendar_synced else ""

                        await send_private_notification(
                            context,
                            assignee["telegram_id"],
                            f"📬 *Bạn có việc nhóm mới!*\n\n"
                            f"📋 *{group_task['public_id']}*: {content}\n"
                            f"👤 Từ: {creator_mention}\n"
                            f"📅 Deadline: {deadline_str}\n"
                            f"👥 Thành viên: {len(assignees)} người{calendar_note}\n\n"
                            f"🔖 Việc của bạn: *{child_task['public_id']}*\n"
                            f"Trả lời /xong {child_task['public_id']} khi hoàn thành.",
                            reply_markup=task_actions_keyboard(child_task['public_id'], show_complete=False),
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

    # Show edit menu
    if field == "menu":
        await query.edit_message_text(
            "✏️ <b>Sửa thông tin giao việc</b>\n\n"
            "Chọn mục cần sửa:",
            reply_markup=assign_edit_menu_keyboard(),
            parse_mode="HTML",
        )
        return ASSIGN_CONFIRM

    # Back to confirm screen
    if field == "back":
        summary = format_assign_summary(data)
        await query.edit_message_text(
            f"<b>Bước 5/5:</b> Xác nhận\n\n{summary}",
            reply_markup=assign_confirm_keyboard(),
            parse_mode="HTML",
        )
        return ASSIGN_CONFIRM

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
        per_message=False,
    )


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        get_wizard_conversation_handler(),
        get_assign_wizard_conversation_handler(),
    ]
