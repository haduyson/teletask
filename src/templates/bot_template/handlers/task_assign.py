"""
Task Assign Handler
Handles /giaoviec command for assigning tasks to others
Supports multi-assignee with G-ID/P-ID system
"""

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
)

logger = logging.getLogger(__name__)

# Group task messages
MSG_GROUP_TASK_CREATED = """
Đã tạo việc nhóm thành công!

{task_id}: {content}
Người nhận: {assignees}
Deadline: {deadline}

Theo dõi tiến độ: /xemviec {task_id}
"""

MSG_GROUP_TASK_RECEIVED = """
Bạn có việc mới!

{task_id}: {content}
Từ: {creator}
Deadline: {deadline}
Thành viên: {total_members} người

Đây là việc của bạn: {personal_id}
Trả lời /xong {personal_id} khi hoàn thành.
"""


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
        if message.reply_to_message and message.reply_to_message.from_user:
            assignee_tg_user = message.reply_to_message.from_user
            assignee = await get_or_create_user(db, assignee_tg_user)
            if is_group:
                await add_group_member(db, group_id, assignee["id"], "member")
            assignees.append(assignee)

        # Method 2: @mentions in text (supports multiple)
        if not assignees and text:
            mentions, remaining_text = extract_mentions(text)
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

            # Send confirmation to creator
            await message.reply_text(
                MSG_TASK_ASSIGNED.format(
                    task_id=task["public_id"],
                    content=content,
                    assignee=assignee.get("display_name", "N/A"),
                    deadline=deadline_str,
                )
            )

            # Notify assignee
            try:
                if assignee.get("telegram_id") != user.id:
                    await context.bot.send_message(
                        chat_id=assignee["telegram_id"],
                        text=MSG_TASK_RECEIVED.format(
                            task_id=task["public_id"],
                            content=content,
                            creator=db_user.get("display_name", "N/A"),
                            deadline=deadline_str,
                        ),
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

            # Format assignee names
            assignee_names = ", ".join(a.get("display_name", "N/A") for a in assignees)

            # Send confirmation to creator
            await message.reply_text(
                MSG_GROUP_TASK_CREATED.format(
                    task_id=group_task["public_id"],
                    content=content,
                    assignees=assignee_names,
                    deadline=deadline_str,
                )
            )

            # Notify each assignee with their personal P-ID
            for i, assignee in enumerate(assignees):
                try:
                    if assignee.get("telegram_id") != user.id:
                        # child_tasks[i] is tuple of (task_dict, assignee_dict)
                        child_task, _ = child_tasks[i]
                        await context.bot.send_message(
                            chat_id=assignee["telegram_id"],
                            text=MSG_GROUP_TASK_RECEIVED.format(
                                task_id=group_task["public_id"],
                                content=content,
                                creator=db_user.get("display_name", "N/A"),
                                deadline=deadline_str,
                                total_members=len(assignees),
                                personal_id=child_task["public_id"],
                            ),
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
    return [
        CommandHandler("giaoviec", giaoviec_command),
        CommandHandler("viecdagiao", viecdagiao_command),
    ]
