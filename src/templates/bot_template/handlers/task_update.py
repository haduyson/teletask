"""
Task Update Handler
Commands for updating task status and progress
Supports G-ID/P-ID group task auto-completion
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database import get_db
from services import (
    get_or_create_user,
    get_task_by_public_id,
    update_task_status,
    update_task_progress,
    check_and_complete_group_task,
    get_group_task_progress,
)
from utils import (
    MSG_TASK_COMPLETED,
    ERR_TASK_NOT_FOUND,
    ERR_NO_PERMISSION,
    ERR_ALREADY_COMPLETED,
    ERR_DATABASE,
    format_datetime,
    progress_keyboard,
)

logger = logging.getLogger(__name__)


async def xong_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /xong [task_id] or /hoanthanh [task_id] command.
    Mark task as completed.
    Auto-completes parent G-ID when all P-ID children are done.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc.\n\nVí dụ: /xong P-0001"
        )
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        # Support multiple task IDs: /xong P-0001, P-0002
        task_ids = [t.strip().upper() for t in " ".join(context.args).split(",")]
        results = []
        group_completions = []

        for task_id in task_ids:
            task = await get_task_by_public_id(db, task_id)

            if not task:
                results.append(f"{task_id}: Không tồn tại")
                continue

            # Check permission (assignee or creator can mark complete)
            if task["assignee_id"] != db_user["id"] and task["creator_id"] != db_user["id"]:
                results.append(f"{task_id}: Không có quyền")
                continue

            if task["status"] == "completed":
                results.append(f"{task_id}: Đã hoàn thành rồi")
                continue

            # Update status
            updated = await update_task_status(
                db, task["id"], "completed", db_user["id"]
            )

            results.append(f"{task_id}: Hoàn thành!")

            # Notify creator if different from person completing
            if task["creator_id"] != db_user["id"]:
                try:
                    creator = await db.fetch_one(
                        "SELECT telegram_id FROM users WHERE id = $1",
                        task["creator_id"]
                    )
                    if creator:
                        await context.bot.send_message(
                            chat_id=creator["telegram_id"],
                            text=f"Việc {task_id} đã được hoàn thành!\n\n"
                                 f"Nội dung: {task['content']}\n"
                                 f"Người thực hiện: {db_user.get('display_name', 'N/A')}",
                        )
                except Exception as e:
                    logger.warning(f"Could not notify creator: {e}")

            # Check if this is a P-ID and auto-complete parent G-ID
            if task_id.startswith("P-"):
                group_result = await check_and_complete_group_task(
                    db, task["id"], db_user["id"]
                )
                if group_result:
                    group_completions.append(group_result)
                    # Notify creator about group completion
                    try:
                        if group_result["creator_id"] != db_user["id"]:
                            creator = await db.fetch_one(
                                "SELECT telegram_id FROM users WHERE id = $1",
                                group_result["creator_id"]
                            )
                            if creator:
                                await context.bot.send_message(
                                    chat_id=creator["telegram_id"],
                                    text=f"VIỆC NHÓM ĐÃ HOÀN THÀNH!\n\n"
                                         f"{group_result['public_id']}: {group_result['content']}\n\n"
                                         f"Tất cả {group_result.get('total_members', 'N/A')} thành viên đã hoàn thành!",
                                )
                    except Exception as e:
                        logger.warning(f"Could not notify group completion: {e}")

        # Response
        if len(task_ids) == 1 and results[0].endswith("Hoàn thành!"):
            msg = MSG_TASK_COMPLETED.format(
                task_id=task_ids[0],
                content=task["content"],
                completed_at=format_datetime(updated.get("completed_at")),
            )

            # Add group completion info
            if group_completions:
                g = group_completions[0]
                msg += f"\n\nViệc nhóm {g['public_id']} đã hoàn thành!"

            await update.message.reply_text(msg)
        else:
            response = "\n".join(results)
            if group_completions:
                response += "\n\nViệc nhóm hoàn thành:\n"
                for g in group_completions:
                    response += f"  {g['public_id']}: {g['content'][:30]}..."
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error in xong_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def danglam_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /danglam [task_id] command.
    Mark task as in progress.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc.\n\nVí dụ: /danglam P-0001"
        )
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task_ids = [t.strip().upper() for t in " ".join(context.args).split(",")]
        updated_count = 0

        for task_id in task_ids:
            task = await get_task_by_public_id(db, task_id)

            if not task:
                continue

            # Only assignee can update status
            if task["assignee_id"] != db_user["id"]:
                continue

            await update_task_status(db, task["id"], "in_progress", db_user["id"])
            updated_count += 1

        if updated_count > 0:
            await update.message.reply_text(
                f"Đã cập nhật {updated_count} việc sang 'Đang làm'"
            )
        else:
            await update.message.reply_text("Không cập nhật được việc nào.")

    except Exception as e:
        logger.error(f"Error in danglam_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def tiendo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tiendo [task_id] [%] command.
    Update task progress percentage.
    """
    user = update.effective_user
    if not user:
        return

    if len(context.args) < 1:
        await update.message.reply_text(
            "Cú pháp: /tiendo [mã việc] [%]\n\n"
            "Ví dụ:\n"
            "  /tiendo P-0001 50\n"
            "  /tiendo P-0001 75%"
        )
        return

    task_id = context.args[0].upper()

    # Parse progress if provided
    progress = None
    if len(context.args) >= 2:
        try:
            progress = int(context.args[1].replace("%", ""))
            progress = max(0, min(100, progress))
        except ValueError:
            await update.message.reply_text("Phần trăm phải là số (0-100)")
            return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task = await get_task_by_public_id(db, task_id)

        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Only assignee can update progress
        if task["assignee_id"] != db_user["id"]:
            await update.message.reply_text(ERR_NO_PERMISSION)
            return

        if progress is not None:
            # Update progress
            updated = await update_task_progress(
                db, task["id"], progress, db_user["id"]
            )

            # Format response with progress bar
            bar = progress_bar(progress)
            status_text = "Hoàn thành!" if progress == 100 else "Đang làm"

            msg = f"Cập nhật tiến độ {task_id}!\n\n{bar} {progress}%\nTrạng thái: {status_text}"

            # Check for group task auto-completion
            group_completed = None
            if progress == 100 and task_id.startswith("P-"):
                group_completed = await check_and_complete_group_task(
                    db, task["id"], db_user["id"]
                )
                if group_completed:
                    msg += f"\n\nViệc nhóm {group_completed['public_id']} đã hoàn thành!"

            await update.message.reply_text(msg)

            # Notify group completion
            if group_completed and group_completed["creator_id"] != db_user["id"]:
                try:
                    creator = await db.fetch_one(
                        "SELECT telegram_id FROM users WHERE id = $1",
                        group_completed["creator_id"]
                    )
                    if creator:
                        await context.bot.send_message(
                            chat_id=creator["telegram_id"],
                            text=f"VIỆC NHÓM ĐÃ HOÀN THÀNH!\n\n"
                                 f"{group_completed['public_id']}: {group_completed['content']}",
                        )
                except Exception as e:
                    logger.warning(f"Could not notify group completion: {e}")
        else:
            # Show progress selection keyboard
            current = task.get("progress", 0)
            await update.message.reply_text(
                f"Chọn tiến độ mới cho {task_id}:\n\n"
                f"Hiện tại: {progress_bar(current)} {current}%",
                reply_markup=progress_keyboard(task_id),
            )

    except Exception as e:
        logger.error(f"Error in tiendo_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


async def tiendogrouptask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /tiendoviecnhom [G-ID] command.
    View aggregated progress for a group task.
    """
    user = update.effective_user
    if not user:
        return

    if not context.args:
        await update.message.reply_text(
            "Vui lòng nhập mã việc nhóm.\n\nVí dụ: /tiendoviecnhom G-0001"
        )
        return

    task_id = context.args[0].upper()

    if not task_id.startswith("G-"):
        await update.message.reply_text("Mã việc nhóm phải bắt đầu bằng G-")
        return

    try:
        db = get_db()
        db_user = await get_or_create_user(db, user)

        task = await get_task_by_public_id(db, task_id)
        if not task:
            await update.message.reply_text(ERR_TASK_NOT_FOUND.format(task_id=task_id))
            return

        # Get aggregated progress
        progress_info = await get_group_task_progress(db, task_id)

        pct = progress_info.get("progress", 0)
        bar = progress_bar(pct)

        # Build member list
        member_lines = []
        for member in progress_info.get("members", []):
            icon = "✅" if member["status"] == "completed" else "⏳"
            member_lines.append(f"  {icon} {member['name']}: {member['progress']}%")

        members_text = "\n".join(member_lines) if member_lines else "  Không có thành viên"

        msg = f"""
TIẾN ĐỘ VIỆC NHÓM: {task_id}

📋 {task['content']}

📊 TỔNG QUAN:
{bar} {pct}%
Hoàn thành: {progress_info['completed']}/{progress_info['total']}

👥 CHI TIẾT:
{members_text}
""".strip()

        await update.message.reply_text(msg)

    except Exception as e:
        logger.error(f"Error in tiendogrouptask_command: {e}")
        await update.message.reply_text(ERR_DATABASE)


def progress_bar(percent: int, width: int = 10) -> str:
    """Generate visual progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    return "█" * filled + "░" * empty


def get_handlers() -> list:
    """Return list of handlers for this module."""
    return [
        CommandHandler(["xong", "hoanthanh", "done"], xong_command),
        CommandHandler("danglam", danglam_command),
        CommandHandler("tiendo", tiendo_command),
        CommandHandler("tiendoviecnhom", tiendogrouptask_command),
    ]
