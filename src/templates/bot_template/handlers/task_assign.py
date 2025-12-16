"""
Task Assign Handler
Handles /giaoviec command for assigning tasks to others
Supports multi-assignee with G-ID/P-ID system
"""

import re
import logging
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_or_create_group,
    add_group_member,
    get_user_by_username,
    find_users_by_mention,
    create_task,
    create_group_task,
    get_user_created_tasks,
    parse_vietnamese_time,
)
from utils import (
    MSG_TASK_ASSIGNED,
    MSG_TASK_RECEIVED,
    ERR_NO_CONTENT,
    ERR_NO_ASSIGNEE,
    ERR_USER_NOT_FOUND,
    ERR_GROUP_ONLY,
    ERR_DATABASE,
    extract_mentions,
    validate_task_content,
    parse_task_command,
    format_datetime,
    format_priority,
    task_actions_keyboard,
    mention_user,
)

logger = logging.getLogger(__name__)

# Messages with mention support (Markdown format)
MSG_TASK_ASSIGNED_MD = """✅ *Đã giao việc thành công!*

📋 *{task_id}*: {content}
👤 Giao cho: {assignee}
📅 Deadline: {deadline}

Xem chi tiết: /xemviec {task_id}"""

MSG_TASK_RECEIVED_MD = """📬 *Bạn có việc mới!*

📋 *{task_id}*: {content}
👤 Từ: {creator}
📅 Deadline: {deadline}

Trả lời /xong {task_id} khi hoàn thành."""

MSG_GROUP_TASK_CREATED_MD = """✅ *Đã tạo việc nhóm thành công!*

📋 *{task_id}*: {content}
👥 Người nhận: {assignees}
📅 Deadline: {deadline}

Theo dõi tiến độ: /xemviec {task_id}"""

MSG_GROUP_TASK_RECEIVED_MD = """📬 *Bạn có việc nhóm mới!*

📋 *{task_id}*: {content}
👤 Từ: {creator}
📅 Deadline: {deadline}
👥 Thành viên: {total_members} người

🔖 Việc của bạn: *{personal_id}*
Trả lời /xong {personal_id} khi hoàn thành."""


async def giaoviec_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /giaoviec command.
    Assign task to one or multiple users.

    Format: /giaoviec @user1 [@user2 ...] [content] [time]
    Examples:
        /giaoviec @nam Chuan bi slide 10h ngay mai
        /giaoviec @nam @linh @hoa Review code truoc 17h

    Can also reply to a message to assign to that user.
    """
    user = update.effective_user
    chat = update.effective_chat
    message = update.message

    if not user or not chat or not message:
        return

    # Get text after command
    text = " ".join(context.args) if context.args else ""

    # Check if this is a group or private chat
    is_group = chat.type in ["group", "supergroup"]

    try:
        db = get_db()

        # Register/get creator
        db_user = await get_or_create_user(db, user)
        creator_id = db_user["id"]

        # Handle group context
        group_id = None
        if is_group:
            group = await get_or_create_group(db, chat.id, chat.title or "Unknown")
            group_id = group["id"]
            await add_group_member(db, group_id, creator_id, "member")

        # Find assignees
        assignees: List[Dict[str, Any]] = []
        remaining_text = text

        # Method 1: Reply to message (single assignee)
        # Skip if replying to own message (creator should not auto-assign to self)
        if message.reply_to_message and message.reply_to_message.from_user:
            assignee_tg_user = message.reply_to_message.from_user
            # Only add if NOT the creator (avoid auto-assigning to self)
            if assignee_tg_user.id != user.id:
                assignee = await get_or_create_user(db, assignee_tg_user)
                if is_group:
                    await add_group_member(db, group_id, assignee["id"], "member")
                assignees.append(assignee)

        # Method 2: Process message entities for mentions
        # - text_mention: for users without username (has user_id in entity)
        # - mention: for @username mentions (username is in message text)
        mention_ranges = []
        if message.entities:
            full_text = message.text or ""
            for entity in message.entities:
                # Text mention - user clicked on name (most reliable, has user_id)
                if entity.type == "text_mention" and entity.user:
                    mentioned_user = await get_or_create_user(db, entity.user)
                    if not any(a["id"] == mentioned_user["id"] for a in assignees):
                        assignees.append(mentioned_user)
                        if is_group:
                            await add_group_member(db, group_id, mentioned_user["id"], "member")
                    mention_ranges.append((entity.offset, entity.offset + entity.length))
                    logger.info(f"Found text_mention: {entity.user.first_name} (id={entity.user.id})")

                # @mention - username mention
                elif entity.type == "mention":
                    # Extract username from message text (includes @)
                    username_with_at = full_text[entity.offset:entity.offset + entity.length]
                    username = username_with_at.lstrip("@")
                    found_user = await get_user_by_username(db, username)
                    if found_user:
                        if not any(a["id"] == found_user["id"] for a in assignees):
                            assignees.append(found_user)
                            if is_group:
                                await add_group_member(db, group_id, found_user["id"], "member")
                        mention_ranges.append((entity.offset, entity.offset + entity.length))
                        logger.info(f"Found @mention entity: @{username} (id={found_user['id']})")
                    else:
                        logger.warning(f"User @{username} not found in database")

        # Remove mentions from remaining text
        if mention_ranges:
            # Work with full message text, then extract content
            full_text = message.text or ""
            # Sort by offset descending to remove from end first
            for start, end in sorted(mention_ranges, reverse=True):
                full_text = full_text[:start] + full_text[end:]
            # Remove command and clean up
            remaining_text = re.sub(r"^/\w+\s*", "", full_text).strip()
            remaining_text = re.sub(r"\s+", " ", remaining_text)

        # Method 3: @mentions in text (supports multiple)
        # Also process @mentions even if text_mentions were found
        if remaining_text:
            mentions, remaining_text = extract_mentions(remaining_text)
            if mentions:
                not_found = []
                for username in mentions:
                    found_user = await get_user_by_username(db, username)
                    if found_user:
                        # Avoid duplicates
                        if not any(a["id"] == found_user["id"] for a in assignees):
                            assignees.append(found_user)
                            if is_group:
                                await add_group_member(db, group_id, found_user["id"], "member")
                            logger.info(f"Found @mention: @{username} (id={found_user['id']})")
                    else:
                        not_found.append(username)

                # Report users not found
                if not_found and not assignees:
                    await message.reply_text(
                        ERR_USER_NOT_FOUND.format(user=f"@{not_found[0]}")
                        + "\n\nNgười này chưa dùng bot. Họ cần /start bot trước."
                    )
                    return
                elif not_found:
                    logger.warning(f"Some users not found: {not_found}")

        if not assignees:
            await message.reply_text(
                ERR_NO_ASSIGNEE + "\n\nVí dụ:\n/giaoviec @user Nội dung việc\n/giaoviec @user1 @user2 Việc nhóm"
            )
            return

        # Parse remaining text
        if not remaining_text.strip():
            await message.reply_text(
                ERR_NO_CONTENT + "\n\nVí dụ: /giaoviec @username Nội dung việc 14h"
            )
            return

        parsed = parse_task_command(remaining_text.strip())

        # Extract time
        deadline, remaining = parse_vietnamese_time(parsed["content"])
        content = remaining.strip() if remaining else parsed["content"]

        # Validate content
        is_valid, result = validate_task_content(content)
        if not is_valid:
            await message.reply_text(result)
            return
        content = result

        # Format deadline for messages
        deadline_str = format_datetime(deadline, relative=True) if deadline else "Không có"

        # Single assignee: regular task (T-ID)
        if len(assignees) == 1:
            assignee = assignees[0]
            task = await create_task(
                db=db,
                content=content,
                creator_id=creator_id,
                assignee_id=assignee["id"],
                deadline=deadline,
                priority=parsed["priority"],
                is_personal=False,
                group_id=group_id,
            )

            # Send confirmation to creator with mention
            assignee_mention = mention_user(assignee)
            await message.reply_text(
                MSG_TASK_ASSIGNED_MD.format(
                    task_id=task["public_id"],
                    content=content,
                    assignee=assignee_mention,
                    deadline=deadline_str,
                ),
                parse_mode="Markdown",
            )

            # Notify assignee with mention
            try:
                if assignee.get("telegram_id") != user.id:
                    creator_mention = mention_user(db_user)
                    await context.bot.send_message(
                        chat_id=assignee["telegram_id"],
                        text=MSG_TASK_RECEIVED_MD.format(
                            task_id=task["public_id"],
                            content=content,
                            creator=creator_mention,
                            deadline=deadline_str,
                        ),
                        parse_mode="Markdown",
                        reply_markup=task_actions_keyboard(task["public_id"]),
                    )
            except Exception as e:
                logger.warning(f"Could not notify assignee {assignee['telegram_id']}: {e}")

            logger.info(
                f"User {user.id} assigned task {task['public_id']} to {assignee['telegram_id']}"
            )

        # Multiple assignees: group task (G-ID + P-IDs)
        else:
            group_task, child_tasks = await create_group_task(
                db=db,
                content=content,
                creator_id=creator_id,
                assignees=assignees,
                deadline=deadline,
                priority=parsed["priority"],
                group_id=group_id,
            )

            # Format assignee mentions
            assignee_mentions = ", ".join(mention_user(a) for a in assignees)

            # Send confirmation to creator with mentions
            await message.reply_text(
                MSG_GROUP_TASK_CREATED_MD.format(
                    task_id=group_task["public_id"],
                    content=content,
                    assignees=assignee_mentions,
                    deadline=deadline_str,
                ),
                parse_mode="Markdown",
            )

            # Notify each assignee with their personal P-ID
            creator_mention = mention_user(db_user)
            for i, assignee in enumerate(assignees):
                try:
                    if assignee.get("telegram_id") != user.id:
                        # child_tasks[i] is tuple of (task_dict, assignee_dict)
                        child_task, _ = child_tasks[i]
                        await context.bot.send_message(
                            chat_id=assignee["telegram_id"],
                            text=MSG_GROUP_TASK_RECEIVED_MD.format(
                                task_id=group_task["public_id"],
                                content=content,
                                creator=creator_mention,
                                deadline=deadline_str,
                                total_members=len(assignees),
                                personal_id=child_task["public_id"],
                            ),
                            parse_mode="Markdown",
                            reply_markup=task_actions_keyboard(child_task["public_id"]),
                        )
                except Exception as e:
                    logger.warning(f"Could not notify assignee {assignee['telegram_id']}: {e}")

            logger.info(
                f"User {user.id} created group task {group_task['public_id']} for {len(assignees)} assignees"
            )

    except Exception as e:
        logger.error(f"Error in giaoviec_command: {e}")
        await message.reply_text(ERR_DATABASE)


async def viecdagiao_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /viecdagiao command.
    List tasks created by user and assigned to others.
    """
    user = update.effective_user
    if not user:
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)
        user_id = db_user["id"]

        # Get tasks assigned to others
        tasks = await get_user_created_tasks(db, user_id, limit=10)

        if not tasks:
            await update.message.reply_text(
                "Bạn chưa giao việc cho ai.\n\nGiao việc:\n/giaoviec @user Nội dung\n/giaoviec @user1 @user2 Việc nhóm"
            )
            return

        # Format task list
        from utils import format_task_list, task_list_with_pagination

        total = len(tasks)
        total_pages = (total + 9) // 10

        msg = format_task_list(
            tasks=tasks,
            title="VIỆC BẠN ĐÃ GIAO",
            page=1,
            total=total,
        )

        await update.message.reply_text(
            msg,
            reply_markup=task_list_with_pagination(tasks, 1, total_pages, "assigned"),
        )

    except Exception as e:
        logger.error(f"Error in viecdagiao_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def get_handlers() -> list:
    """Return list of handlers for this module."""
    # Note: /giaoviec is now handled by task_wizard.py (wizard mode)
    # The wizard calls giaoviec_command when args are provided
    return [
        # /viecdagiao and /viectoigiao - Tasks you assigned to others
        CommandHandler(["viecdagiao", "viectoigiao"], viecdagiao_command),
    ]
