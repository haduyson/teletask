"""
Inline Keyboards
Telegram inline keyboards for task management
"""

from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def task_actions_keyboard(
    task_id: str,
    show_complete: bool = True,
    show_progress: bool = True,
    show_delete: bool = True,
) -> InlineKeyboardMarkup:
    """Create task action buttons."""
    buttons = []

    row1 = []
    if show_complete:
        row1.append(
            InlineKeyboardButton("✅ Xong", callback_data=f"task_complete:{task_id}")
        )
    if show_progress:
        row1.append(
            InlineKeyboardButton("📊 Tiến độ", callback_data=f"task_progress:{task_id}")
        )
    if row1:
        buttons.append(row1)

    row2 = []
    row2.append(
        InlineKeyboardButton("📝 Chi tiết", callback_data=f"task_detail:{task_id}")
    )
    if show_delete:
        row2.append(
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"task_delete:{task_id}")
        )
    buttons.append(row2)

    return InlineKeyboardMarkup(buttons)


def task_detail_keyboard(
    task_id: str,
    can_edit: bool = True,
    can_complete: bool = True,
) -> InlineKeyboardMarkup:
    """Create task detail action buttons."""
    buttons = []

    row1 = []
    if can_complete:
        row1.append(
            InlineKeyboardButton("✅ Xong", callback_data=f"task_complete:{task_id}")
        )
    row1.append(
        InlineKeyboardButton("📊 Cập nhật", callback_data=f"task_progress:{task_id}")
    )
    buttons.append(row1)

    if can_edit:
        buttons.append([
            InlineKeyboardButton("✏️ Sửa", callback_data=f"task_edit:{task_id}"),
            InlineKeyboardButton("🗑️ Xóa", callback_data=f"task_delete:{task_id}"),
        ])

    buttons.append([
        InlineKeyboardButton("« Quay lại", callback_data="task_category:menu")
    ])

    return InlineKeyboardMarkup(buttons)


def task_category_keyboard() -> InlineKeyboardMarkup:
    """Create task category selection menu."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Việc cá nhân", callback_data="task_category:personal"),
        ],
        [
            InlineKeyboardButton("📤 Việc đã giao", callback_data="task_category:assigned"),
        ],
        [
            InlineKeyboardButton("📥 Việc đã nhận", callback_data="task_category:received"),
        ],
        [
            InlineKeyboardButton("📊 Tất cả việc", callback_data="task_category:all"),
        ],
    ])


def progress_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create progress update buttons."""
    buttons = [
        [
            InlineKeyboardButton("25%", callback_data=f"progress:{task_id}:25"),
            InlineKeyboardButton("50%", callback_data=f"progress:{task_id}:50"),
            InlineKeyboardButton("75%", callback_data=f"progress:{task_id}:75"),
        ],
        [
            InlineKeyboardButton("✅ 100% (Xong)", callback_data=f"progress:{task_id}:100"),
        ],
        [
            InlineKeyboardButton("« Huỷ", callback_data=f"task_detail:{task_id}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def undo_keyboard(undo_id: int, seconds_remaining: int = 30) -> InlineKeyboardMarkup:
    """Create undo button for deleted tasks with countdown."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"↩️ Hoàn tác ({seconds_remaining}s)", callback_data=f"task_undo:{undo_id}")]
    ])


def pagination_keyboard(
    prefix: str,
    page: int,
    total_pages: int,
    extra_data: str = "",
) -> InlineKeyboardMarkup:
    """Create pagination buttons."""
    buttons = []

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                "« Trước",
                callback_data=f"{prefix}:page:{page - 1}:{extra_data}"
            )
        )

    nav_row.append(
        InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
    )

    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                "Sau »",
                callback_data=f"{prefix}:page:{page + 1}:{extra_data}"
            )
        )

    buttons.append(nav_row)

    return InlineKeyboardMarkup(buttons)


def task_list_with_pagination(
    tasks: list,
    page: int,
    total_pages: int,
    list_type: str = "personal",
) -> InlineKeyboardMarkup:
    """Create task list with pagination."""
    buttons = []

    # Task buttons
    for task in tasks:
        task_id = task.get("public_id", "")
        content = task.get("content", "")[:30]
        if len(task.get("content", "")) > 30:
            content += "..."

        buttons.append([
            InlineKeyboardButton(
                f"{task_id}: {content}",
                callback_data=f"task_detail:{task_id}"
            )
        ])

    # Pagination
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton("« Trước", callback_data=f"list:{list_type}:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton("Sau »", callback_data=f"list:{list_type}:{page + 1}")
        )
    buttons.append(nav_row)

    # Back to category menu
    buttons.append([
        InlineKeyboardButton("« Quay lại danh mục", callback_data="task_category:menu")
    ])

    return InlineKeyboardMarkup(buttons)


def priority_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create priority selection buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Thấp", callback_data=f"priority:{task_id}:low"),
            InlineKeyboardButton("Bình thường", callback_data=f"priority:{task_id}:normal"),
        ],
        [
            InlineKeyboardButton("Cao", callback_data=f"priority:{task_id}:high"),
            InlineKeyboardButton("🚨 Khẩn cấp", callback_data=f"priority:{task_id}:urgent"),
        ],
        [
            InlineKeyboardButton("« Huỷ", callback_data=f"task_detail:{task_id}"),
        ],
    ])


def confirm_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """Create confirmation buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm:{action}:{item_id}"),
            InlineKeyboardButton("❌ Huỷ", callback_data=f"cancel:{action}:{item_id}"),
        ]
    ])


def edit_menu_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create edit options menu."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Sửa nội dung", callback_data=f"edit_content:{task_id}"),
        ],
        [
            InlineKeyboardButton("📅 Sửa deadline", callback_data=f"edit_deadline:{task_id}"),
        ],
        [
            InlineKeyboardButton("🔔 Sửa độ ưu tiên", callback_data=f"edit_priority:{task_id}"),
        ],
        [
            InlineKeyboardButton("👤 Sửa người nhận", callback_data=f"edit_assignee:{task_id}"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data=f"task_detail:{task_id}"),
        ],
    ])


def edit_priority_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Create priority edit buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬇️ Thấp", callback_data=f"set_priority:{task_id}:low"),
            InlineKeyboardButton("➡️ Bình thường", callback_data=f"set_priority:{task_id}:normal"),
        ],
        [
            InlineKeyboardButton("⬆️ Cao", callback_data=f"set_priority:{task_id}:high"),
            InlineKeyboardButton("🚨 Khẩn cấp", callback_data=f"set_priority:{task_id}:urgent"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data=f"task_edit:{task_id}"),
        ],
    ])


# =============================================================================
# Wizard Keyboards for Step-by-Step Task Creation
# =============================================================================


def wizard_deadline_keyboard() -> InlineKeyboardMarkup:
    """Deadline selection buttons for wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Hôm nay", callback_data="wizard_deadline:today"),
            InlineKeyboardButton("📅 Ngày mai", callback_data="wizard_deadline:tomorrow"),
        ],
        [
            InlineKeyboardButton("📅 Tuần sau", callback_data="wizard_deadline:nextweek"),
            InlineKeyboardButton("📅 Tháng sau", callback_data="wizard_deadline:nextmonth"),
        ],
        [
            InlineKeyboardButton("⏰ Nhập thời gian", callback_data="wizard_deadline:custom"),
            InlineKeyboardButton("⏭️ Bỏ qua", callback_data="wizard_deadline:skip"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="wizard_back:content"),
            InlineKeyboardButton("❌ Hủy", callback_data="wizard_cancel"),
        ],
    ])


def wizard_assignee_keyboard(recent_users: Optional[List[dict]] = None) -> InlineKeyboardMarkup:
    """Assignee selection buttons for wizard."""
    buttons = [
        [
            InlineKeyboardButton("👤 Cho mình", callback_data="wizard_assignee:self"),
            InlineKeyboardButton("👥 Giao người khác", callback_data="wizard_assignee:others"),
        ],
    ]

    # Add recent users if available
    if recent_users:
        recent_row = []
        for user in recent_users[:3]:  # Max 3 recent users
            name = user.get("display_name", "?")[:10]
            user_id = user.get("id")
            recent_row.append(
                InlineKeyboardButton(f"@{name}", callback_data=f"wizard_assignee:user:{user_id}")
            )
        if recent_row:
            buttons.append(recent_row)

    buttons.extend([
        [
            InlineKeyboardButton("« Quay lại", callback_data="wizard_back:deadline"),
            InlineKeyboardButton("❌ Hủy", callback_data="wizard_cancel"),
        ],
    ])

    return InlineKeyboardMarkup(buttons)


def wizard_priority_keyboard() -> InlineKeyboardMarkup:
    """Priority selection buttons for wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Khẩn cấp", callback_data="wizard_priority:urgent"),
            InlineKeyboardButton("🟠 Cao", callback_data="wizard_priority:high"),
        ],
        [
            InlineKeyboardButton("🟡 Bình thường", callback_data="wizard_priority:normal"),
            InlineKeyboardButton("🟢 Thấp", callback_data="wizard_priority:low"),
        ],
        [
            InlineKeyboardButton("« Quay lại", callback_data="wizard_back:assignee"),
            InlineKeyboardButton("❌ Hủy", callback_data="wizard_cancel"),
        ],
    ])


def wizard_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation buttons for wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tạo việc", callback_data="wizard_confirm:create"),
            InlineKeyboardButton("❌ Hủy bỏ", callback_data="wizard_confirm:cancel"),
        ],
        [
            InlineKeyboardButton("✏️ Sửa nội dung", callback_data="wizard_edit:content"),
            InlineKeyboardButton("📅 Sửa deadline", callback_data="wizard_edit:deadline"),
        ],
        [
            InlineKeyboardButton("👤 Sửa người nhận", callback_data="wizard_edit:assignee"),
            InlineKeyboardButton("🔔 Sửa độ ưu tiên", callback_data="wizard_edit:priority"),
        ],
    ])


def wizard_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel wizard button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Hủy", callback_data="wizard_cancel")],
    ])


def task_type_filter_keyboard(current_filter: str = "all") -> InlineKeyboardMarkup:
    """Task type filter buttons (Individual/Group)."""
    # Mark current filter with checkmark
    ind_label = "✓ 👤 Cá nhân" if current_filter == "individual" else "👤 Cá nhân"
    grp_label = "✓ 👥 Nhóm" if current_filter == "group" else "👥 Nhóm"
    all_label = "✓ 📋 Tất cả" if current_filter == "all" else "📋 Tất cả"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(all_label, callback_data="task_filter:all"),
            InlineKeyboardButton(ind_label, callback_data="task_filter:individual"),
            InlineKeyboardButton(grp_label, callback_data="task_filter:group"),
        ],
    ])
