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
/vieccanhan - Xem danh sách việc cá nhân
/thongtin - Xem thông tin tài khoản

Gõ /help để xem hướng dẫn chi tiết.
"""

MSG_START_GROUP = """
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
📖 HƯỚNG DẪN SỬ DỤNG TELETASK BOT

━━━━━ TẠO VIỆC ━━━━━
/taoviec - Tạo việc cá nhân (wizard)

Ví dụ:
  /taoviec Họp đội 14h30

━━━━━ VIỆC LẶP LẠI ━━━━━
/vieclaplai - Tạo việc lặp lại tự động
/danhsachvieclaplai - Xem danh sách việc lặp

Ví dụ:
  /vieclaplai Họp đội hàng tuần thứ 2 9h
  /vieclaplai Báo cáo hàng tháng ngày 1 10h

━━━━━ XEM VIỆC ━━━━━
/xemviec - Danh mục việc (menu)
/xemviec [mã] - Chi tiết việc
/viecdanhan - Việc được giao cho bạn
/timviec [từ khóa] - Tìm kiếm việc

━━━━━ CẬP NHẬT ━━━━━
/xong [mã] - Hoàn thành việc
/tiendo [mã] [%] - Cập nhật tiến độ
/xoa [mã] - Xóa việc (hoàn tác 10s)
/xoanhieu [mã1,mã2,...] - Xóa nhiều việc
/xoatatca - Xóa tất cả việc (hoàn tác 10s)

━━━━━ NHẮC VIỆC ━━━━━
/nhacviec [mã] [thời gian] - Đặt nhắc
/xemnhac - Xem nhắc đã đặt

━━━━━ THỐNG KÊ ━━━━━
/thongke - Thống kê tổng hợp
/thongketuan - Thống kê tuần này
/thongkethang - Thống kê tháng này
/viectrehan - Xem việc trễ hạn
/export - Xuất báo cáo (CSV/Excel/PDF)

━━━━━ TÍCH HỢP ━━━━━
/lichgoogle - Kết nối và cài đặt Google Calendar

━━━━━ TÀI KHOẢN ━━━━━
/menu - Menu tính năng (nút bấm)
/caidat - Cài đặt cá nhân (thông báo, múi giờ)
/thongtin - Thông tin tài khoản
/start - Bắt đầu sử dụng bot
/help - Xem hướng dẫn này

📖 Hướng dẫn chi tiết: https://teletask.haduyson.com
"""

MSG_HELP_GROUP = """
📖 HƯỚNG DẪN SỬ DỤNG TELETASK BOT

━━━━━ TẠO VIỆC ━━━━━
/taoviec - Tạo việc cá nhân (wizard)
/giaoviec - Giao việc cho người khác

Ví dụ:
  /taoviec Họp đội 14h30
  /giaoviec @nam Chuẩn bị slide ngày mai 10h

━━━━━ VIỆC LẶP LẠI ━━━━━
/vieclaplai - Tạo việc lặp lại tự động
/danhsachvieclaplai - Xem danh sách việc lặp

Ví dụ:
  /vieclaplai Họp đội hàng tuần thứ 2 9h
  /vieclaplai Báo cáo hàng tháng ngày 1 10h

━━━━━ XEM VIỆC ━━━━━
/xemviec - Danh mục việc (menu)
/xemviec [mã] - Chi tiết việc
/viecdagiao - Việc bạn đã giao
/viecdanhan - Việc được giao cho bạn
/timviec [từ khóa] - Tìm kiếm việc

━━━━━ CẬP NHẬT ━━━━━
/xong [mã] - Hoàn thành việc
/tiendo [mã] [%] - Cập nhật tiến độ
/xoa [mã] - Xóa việc (hoàn tác 10s)
/xoanhieu [mã1,mã2,...] - Xóa nhiều việc
/xoatatca - Xóa tất cả việc (hoàn tác 10s)

━━━━━ NHẮC VIỆC ━━━━━
/nhacviec [mã] [thời gian] - Đặt nhắc
/xemnhac - Xem nhắc đã đặt

━━━━━ THỐNG KÊ ━━━━━
/thongke - Thống kê tổng hợp
/thongketuan - Thống kê tuần này
/thongkethang - Thống kê tháng này
/viectrehan - Xem việc trễ hạn
/export - Xuất báo cáo (CSV/Excel/PDF)

━━━━━ TÍCH HỢP ━━━━━
/lichgoogle - Kết nối và cài đặt Google Calendar

━━━━━ TÀI KHOẢN ━━━━━
/menu - Menu tính năng (nút bấm)
/caidat - Cài đặt cá nhân (thông báo, múi giờ)
/thongtin - Thông tin tài khoản
/start - Bắt đầu sử dụng bot
/help - Xem hướng dẫn này

📖 Hướng dẫn chi tiết: https://teletask.haduyson.com
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
<b>{task_id}</b>: {content}

<b>Trạng thái:</b> {status}
<b>Tiến độ:</b> {progress}%
<b>Ưu tiên:</b> {priority}

<b>Người tạo:</b> {creator}
<b>Người nhận:</b> {assignee}
<b>Deadline:</b> {deadline}
{group_line}
<b>Tạo lúc:</b> {created_at}
<b>Cập nhật:</b> {updated_at}
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
⏰ <b>Nhắc nhở:</b> Việc sắp đến hạn!

<b>{task_id}</b>: {content}
<b>Deadline:</b> {deadline}

Còn 24 giờ để hoàn thành.
"""

MSG_REMINDER_1H = """
🚨 <b>KHẨN CẤP:</b> Việc sắp hết hạn!

<b>{task_id}</b>: {content}
<b>Deadline:</b> {deadline}

Chỉ còn 1 giờ!
"""

MSG_REMINDER_OVERDUE = """
⚠️ <b>CẢNH BÁO:</b> Việc đã quá hạn!

<b>{task_id}</b>: {content}
<b>Deadline:</b> {deadline}

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
