"""
Vietnamese Messages
All user-facing messages in Vietnamese with proper diacritics
"""

# Command responses
MSG_START = """
Xin chào {name}!

Tôi là TeleTask Bot - hệ thống quản lý công việc qua Telegram.

Sử dụng các lệnh:
/taoviec - Tạo việc mới cho bản thân
/giaoviec - Giao việc cho người khác
/vieccanhan - Xem danh sách việc cá nhân
/thongtin - Xem thông tin tài khoản

Gõ /help để xem hướng dẫn chi tiết.
"""

MSG_HELP = """
Hướng dẫn sử dụng TeleTask Bot

TẠO VIỆC CÁ NHÂN:
/taoviec [nội dung] [thời gian]
Ví dụ:
  /taoviec Họp đội 14h30
  /taoviec Nộp báo cáo ngày mai 10h
  /taoviec Mua quà sinh nhật 15/12

GIAO VIỆC CHO NGƯỜI KHÁC:
/giaoviec @username [nội dung] [thời gian]
Ví dụ:
  /giaoviec @nam Chuẩn bị slide 10h ngày mai
  /giaoviec @linh Review code trước 17h

VIỆC LẶP LẠI:
/vieclaplai [nội dung] [lịch lặp]
Ví dụ:
  /vieclaplai Họp đội hàng tuần thứ 2 9h
  /vieclaplai Báo cáo hàng tháng ngày 1 10h
  /vieclaplai Kiểm tra email hàng ngày 8h
/danhsachvieclaplai - Xem việc lặp lại

QUẢN LÝ VIỆC:
/vieccanhan - Danh sách việc của bạn
/viecdagiao - Việc bạn giao cho người khác
/xemviec [mã việc] - Xem chi tiết việc

CẬP NHẬT TRẠNG THÁI:
/xong [mã việc] - Đánh dấu hoàn thành
/tiendo [mã việc] [%] - Cập nhật tiến độ
/xoa [mã việc] - Xóa việc (có thể hoàn tác)

NHÓM:
/viecduan - Việc trong nhóm
/thongke - Thống kê nhóm

CÀI ĐẶT:
/thongtin - Thông tin tài khoản
/caidat - Cài đặt thông báo, ngôn ngữ
"""

MSG_INFO = """
Thông tin tài khoản

Tên: {name}
Username: @{username}
Telegram ID: {telegram_id}

THỐNG KÊ:
Tổng việc: {total_tasks}
Đang xử lý: {in_progress}
Hoàn thành: {completed}
Trễ hạn: {overdue}

Múi giờ: {timezone}
"""

# Task messages
MSG_TASK_CREATED = """
Đã tạo việc thành công!

{task_id}: {content}
Deadline: {deadline}
Ưu tiên: {priority}
"""

MSG_TASK_ASSIGNED = """
Đã giao việc thành công!

{task_id}: {content}
Người nhận: {assignee}
Deadline: {deadline}
"""

MSG_TASK_RECEIVED = """
Bạn có việc mới!

{task_id}: {content}
Từ: {creator}
Deadline: {deadline}

Trả lời /xong {task_id} khi hoàn thành.
"""

MSG_TASK_COMPLETED = """
Đã hoàn thành việc {task_id}!

{content}
Thời gian: {completed_at}
"""

MSG_TASK_DELETED = """
Đã xóa việc {task_id}.

Bấm nút bên dưới để hoàn tác (trong 30 giây).
"""

MSG_TASK_RESTORED = "Đã khôi phục việc {task_id}."

MSG_TASK_DETAIL = """
{task_id}: {content}

Trạng thái: {status}
Tiến độ: {progress}%
Ưu tiên: {priority}

Người tạo: {creator}
Người nhận: {assignee}
Deadline: {deadline}

Tạo lúc: {created_at}
Cập nhật: {updated_at}
"""

MSG_TASK_LIST = """
{title}

{tasks}

Trang {page}/{total_pages} | Tổng: {total}
"""

MSG_TASK_LIST_EMPTY = "Không có việc nào."

MSG_TASK_LIST_ITEM = "{icon} {task_id}: {content} - {deadline}"

# Reminder messages
MSG_REMINDER_24H = """
Nhắc nhở: Việc sắp đến hạn!

{task_id}: {content}
Deadline: {deadline}

Còn 24 giờ để hoàn thành.
"""

MSG_REMINDER_1H = """
KHẨN CẤP: Việc sắp hết hạn!

{task_id}: {content}
Deadline: {deadline}

Chỉ còn 1 giờ!
"""

MSG_REMINDER_OVERDUE = """
CẢNH BÁO: Việc đã quá hạn!

{task_id}: {content}
Deadline: {deadline}

Vui lòng cập nhật trạng thái.
"""

# Error messages
ERR_NO_PERMISSION = "Bạn không có quyền thực hiện thao tác này."
ERR_NOT_FOUND = "Không tìm thấy mục được yêu cầu."
ERR_TASK_NOT_FOUND = "Không tìm thấy việc {task_id}."
ERR_USER_NOT_FOUND = "Không tìm thấy người dùng {user}."
ERR_INVALID_TIME = "Không thể hiểu thời gian '{time}'. Vui lòng dùng định dạng: 10h30, ngày mai 14h, 15/12 9h..."
ERR_NO_CONTENT = "Vui lòng nhập nội dung việc."
ERR_NO_ASSIGNEE = "Vui lòng chỉ định người nhận việc (@username hoặc reply tin nhắn)."
ERR_GROUP_ONLY = "Lệnh này chỉ hoạt động trong nhóm."
ERR_PRIVATE_ONLY = "Lệnh này chỉ hoạt động trong chat riêng."
ERR_UNDO_EXPIRED = "Hết thời gian hoàn tác."
ERR_ALREADY_COMPLETED = "Việc {task_id} đã hoàn thành rồi."
ERR_DATABASE = "Lỗi hệ thống. Vui lòng thử lại sau."

# Status labels
STATUS_PENDING = "Chờ xử lý"
STATUS_IN_PROGRESS = "Đang làm"
STATUS_COMPLETED = "Hoàn thành"
STATUS_CANCELLED = "Đã huỷ"

# Priority labels
PRIORITY_LOW = "Thấp"
PRIORITY_NORMAL = "Bình thường"
PRIORITY_HIGH = "Cao"
PRIORITY_URGENT = "Khẩn cấp"

# Status icons
ICON_PENDING = "⏳"
ICON_IN_PROGRESS = "🔄"
ICON_COMPLETED = "✅"
ICON_OVERDUE = "🔴"
ICON_URGENT = "🚨"
ICON_HIGH = "🔶"
