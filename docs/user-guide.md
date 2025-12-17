# Hướng Dẫn Sử Dụng TeleTask Bot

Bot quản lý công việc qua Telegram cho nhóm và cá nhân.

## Bắt Đầu Nhanh

1. Khởi động bot: `/start`
2. Tạo việc: `/taoviec` (chế độ wizard)
3. Giao việc: `/giaoviec` (chế độ wizard)
4. Xem việc: `/xemviec`

---

## Tạo Việc (`/taoviec`)

Tạo việc từng bước với nút bấm hướng dẫn.

### Cách Sử Dụng

1. **Bắt đầu wizard**: Gõ `/taoviec` (không tham số)
2. **Bước 1 - Nội dung**: Nhập mô tả công việc
3. **Bước 2 - Deadline**: Chọn từ nút hoặc nhập thời gian
4. **Bước 3 - Người nhận**: Chọn "Cho mình" hoặc "Giao người khác"
5. **Bước 4 - Độ ưu tiên**: Chọn mức ưu tiên
6. **Bước 5 - Xác nhận**: Xem lại và tạo việc

### Chế Độ Nhanh

Bỏ qua wizard bằng cách nhập trực tiếp:
```
/taoviec Hoàn thành báo cáo 17h
```

### Tùy Chọn Deadline

| Nút | Ý nghĩa |
|-----|---------|
| Hôm nay | Cuối ngày hôm nay (23:59) |
| Ngày mai | Cuối ngày mai (23:59) |
| Tuần sau | 7 ngày từ bây giờ |
| Tháng sau | 30 ngày từ bây giờ |
| Nhập thời gian | Nhập thời gian tùy chỉnh |
| Bỏ qua | Không có deadline |

### Định Dạng Thời Gian

```
14h30          → Hôm nay 14:30
ngày mai 10h   → Ngày mai 10:00
thứ 6 15h      → Thứ 6 tuần này 15:00
20/12 9h       → Ngày 20/12 lúc 09:00
```

---

## Giao Việc (`/giaoviec`)

Giao việc cho một hoặc nhiều người.

### Cách Sử Dụng

1. **Bắt đầu wizard**: Gõ `/giaoviec` (không tham số)
2. **Bước 1 - Nội dung**: Nhập mô tả công việc
3. **Bước 2 - Người nhận**: Tag hoặc mention người dùng
4. **Bước 3 - Deadline**: Chọn deadline
5. **Bước 4 - Độ ưu tiên**: Chọn mức ưu tiên
6. **Bước 5 - Xác nhận**: Xem lại và giao việc

### Chế Độ Nhanh

```
/giaoviec @user Nội dung việc 14h
/giaoviec @user1 @user2 Việc nhóm 17h
```

### Cách Mention Người Dùng

**Hai cách mention:**

1. **@username** - Cho người có username Telegram
   ```
   @myduyenn2202 @xuanson319
   ```

2. **Text mention** - Cho người KHÔNG có username
   - Nhấn vào tên thành viên trong nhóm
   - Chọn "Mention" từ popup
   - Hoạt động ngay cả khi người dùng không có @username

### Lưu Ý Trong Nhóm

Trong nhóm chat, bạn phải **REPLY** tin nhắn của bot khi nhập text:
- Vuốt phải tin nhắn bot → Reply
- Do chế độ bảo mật của Telegram bot

---

## Loại Việc & Mã ID

| Định dạng | Loại | Mô tả |
|-----------|------|-------|
| T-xxx | Việc cá nhân | Việc một người nhận |
| G-xxx | Việc nhóm | Việc nhiều người (cha) |
| P-xxx | Việc con | Việc con của việc nhóm |

---

## Mức Độ Ưu Tiên

| Mức | Icon | Mô tả |
|-----|------|-------|
| Khẩn cấp | 🔴 | Cần xử lý ngay |
| Cao | 🟠 | Ưu tiên cao |
| Bình thường | 🟡 | Mặc định |
| Thấp | 🟢 | Ưu tiên thấp |

---

## Các Lệnh Khác

| Lệnh | Mô tả |
|------|-------|
| `/xemviec` | Xem việc với menu phân loại |
| `/xemviec T-123` | Xem chi tiết việc |
| `/xong T-123` | Đánh dấu hoàn thành |
| `/danglam T-123` | Đánh dấu đang làm |
| `/xoa T-123` | Xóa việc |
| `/viecdagiao` | Xem việc đã giao cho người khác |
| `/vieccanhan` | Tạo việc cá nhân |
| `/nhacviec T-123 14h` | Đặt nhắc nhở |
| `/thongtin` | Thông tin bot |

---

## Lệnh Thống Kê

| Lệnh | Mô tả |
|------|-------|
| `/thongke` | Thống kê tổng hợp (tất cả) |
| `/thongketuan` | Thống kê tuần này |
| `/thongkethang` | Thống kê tháng này |

### Phân Loại Thống Kê

- **Việc đã giao**: Việc bạn giao cho người khác
- **Việc được giao**: Việc người khác giao cho bạn
- **Việc cá nhân**: Việc tự tạo cho mình

---

## Việc Trễ Hạn (`/viectrehan`)

Xem việc trễ hạn, mặc định lọc theo tháng hiện tại.

### Cách Sử Dụng

```
/viectrehan
```

Hiển thị việc trễ hạn của **tháng hiện tại** với nút lọc:
- 📅 **Hôm nay** - Việc trễ hạn hôm nay
- 📆 **Tuần này** - Việc trễ hạn tuần này
- 📊 **Tất cả** - Tất cả việc trễ hạn

### Reset Hàng Tháng

Số việc trễ hạn tự động reset đầu mỗi tháng mới. Giúp theo dõi hiệu suất theo tháng.

---

## Thông Báo Riêng

Khi tạo việc trong **nhóm chat**, người được giao nhận thông báo riêng qua tin nhắn DM từ bot.

### Cách Hoạt Động

1. Người tạo giao việc trong nhóm: `/giaoviec @user1 @user2 Nội dung`
2. Bot trả lời trong nhóm với xác nhận
3. Mỗi người nhận được **tin nhắn riêng** với chi tiết việc

### Lợi Ích

- Người nhận không bỏ lỡ việc ngay cả khi tắt thông báo nhóm
- Chi tiết việc có sẵn trong chat riêng để xem lại
- Hoạt động với cả việc một và nhiều người

---

## Chỉnh Sửa Việc

Sau khi xem việc với `/xemviec T-123`, sử dụng các nút menu chỉnh sửa.

### Tùy Chọn Chỉnh Sửa

| Nút | Chức năng |
|-----|-----------|
| 📝 Sửa nội dung | Chỉnh sửa nội dung việc |
| 📅 Sửa deadline | Thay đổi deadline |
| 👤 Sửa người nhận | Thay đổi người nhận |
| 🔔 Sửa độ ưu tiên | Thay đổi mức ưu tiên |

### Sửa Người Nhận

**Hai cách thay đổi người nhận:**

1. **@username** - Gõ username trực tiếp
   ```
   @newuser
   ```

2. **Text mention** - Cho người KHÔNG có @username
   - Nhấn vào tên thành viên trong nhóm
   - Chọn "Mention" từ popup
   - Reply tin nhắn chỉnh sửa của bot

**Chuyển đổi loại việc:**
- 1 người nhận → Việc cá nhân (P-ID)
- Nhiều người nhận → Việc nhóm (G-ID với P-IDs)

**Lưu ý:**
- Reply (vuốt phải) tin nhắn bot khi nhập text
- Link mention có thể click trong tin nhắn xác nhận

---

## Xóa Hàng Loạt

Xóa nhiều việc cùng lúc. Chỉ người tạo việc mới có thể xóa.

| Lệnh | Mô tả |
|------|-------|
| `/xoahet` | Xóa tất cả việc bạn tạo |
| `/xoaviecdagiao` | Xóa việc đã giao cho người khác |

### Cách Hoạt Động

1. Chạy lệnh
2. Bot hiển thị danh sách việc sẽ bị xóa (tối đa 5)
3. Nhấn **"Xác nhận"** để xóa hoặc **"Hủy"** để hủy

⚠️ **Cảnh báo:** Xóa hàng loạt không thể hoàn tác!

### Ví Dụ

```
/xoahet
→ Hiển thị: "Bạn có 3 việc sẽ bị xóa"
→ • P-0001: Hoàn thành báo cáo...
→ • P-0002: Gửi email...
→ • T-0003: Review code...
→ [Xác nhận xóa 3 việc] [Hủy]
```

---

## Xuất Báo Cáo (`/export`)

Xuất thống kê việc dưới dạng CSV, Excel, hoặc PDF.

### Cách Sử Dụng

1. Chạy `/export`
2. Chọn khoảng thời gian (7 ngày, 30 ngày, tuần này, tháng này, tùy chỉnh)
3. Chọn bộ lọc việc (tất cả, đã tạo, đã giao, được giao)
4. Chọn định dạng (CSV, Excel, PDF)
5. Nhận link tải với mật khẩu

### Truy Cập Báo Cáo

- Báo cáo được bảo vệ bằng mật khẩu
- Link tải hết hạn sau **72 giờ**
- Giao diện web kiểu MacOS để nhập mật khẩu

---

## Tích Hợp Google Calendar (`/lichgoogle`)

Đồng bộ deadline việc với Google Calendar.

### Cách Kết Nối

1. Chạy `/lichgoogle`
2. Nhấn nút "🔗 Kết nối Google"
3. Đăng nhập tài khoản Google
4. Cấp quyền truy cập calendar
5. Quay lại Telegram - thấy thông báo thành công

### Menu Cài Đặt

Sau khi kết nối, `/lichgoogle` hiển thị menu cài đặt:

| Nút | Chức năng |
|-----|-----------|
| 🔄 Chế độ đồng bộ | Chuyển chế độ (Tự động/Thủ công) |
| ⚡ Đồng bộ ngay | Đồng bộ tất cả việc vào lịch ngay |
| ❌ Ngắt kết nối | Ngắt kết nối tài khoản Google |

### Chế Độ Đồng Bộ

| Chế độ | Mô tả |
|--------|-------|
| **Tự động** | Đồng bộ ngay khi việc thay đổi |
| **Thủ công** | Chỉ đồng bộ khi nhấn "Đồng bộ ngay" |

### Những Gì Được Đồng Bộ

- ✅ Tạo việc → Tạo sự kiện calendar
- ✅ Cập nhật việc → Cập nhật sự kiện calendar
- ✅ Xóa việc → Xóa sự kiện calendar
- ✅ Khôi phục việc → Khôi phục sự kiện calendar
- ✅ Hoàn thành việc → Sự kiện hiển thị ✅ ở tiêu đề

### Tính Năng

- Deadline việc trở thành sự kiện calendar
- Việc hoàn thành hiển thị ✅ trong tiêu đề calendar
- Việc đã xóa được xóa khỏi calendar
- Hoạt động với thông báo Google Calendar

---

## Cài Đặt (`/caidat`)

Cấu hình thông báo và múi giờ.

### Tùy Chọn Menu

| Nút | Chức năng |
|-----|-----------|
| 🔔 Thông báo | Cài đặt thông báo |
| 🌏 Múi giờ | Cài đặt múi giờ |

### Cài Đặt Thông Báo

Kiểm soát thông báo nào bạn nhận:

| Cài đặt | Mô tả |
|---------|-------|
| 📥 Giao việc | Khi ai đó giao việc cho bạn |
| 📊 Trạng thái | Khi trạng thái việc thay đổi |
| ⏰ Nhắc việc | Nhắc nhở trước deadline |
| 📈 Báo cáo | Báo cáo tổng hợp hàng ngày/tuần |

### Cài Đặt Nhắc Nhở

Đặt thời điểm nhận nhắc nhở:

| Tùy chọn | Thời điểm |
|----------|-----------|
| 24 giờ trước | 24 giờ trước deadline |
| 1 giờ trước | 1 giờ trước deadline |
| 30 phút trước | 30 phút trước deadline |
| 5 phút trước | 5 phút trước deadline |
| Khi trễ hạn | Khi việc trễ hạn |

### Nguồn Nhắc Nhở

Chọn nơi nhận nhắc nhở:

| Nguồn | Mô tả |
|-------|-------|
| Telegram | Bot gửi nhắc nhở trong chat |
| Google Calendar | Thông báo từ ứng dụng Calendar |
| Cả hai | Cả Telegram và Calendar |

### Múi Giờ

Chọn múi giờ để hiển thị deadline chính xác:
- Asia/Ho_Chi_Minh (UTC+7) - Mặc định
- Các múi giờ chính khác có sẵn

---

## Giao Diện Web

TeleTask cung cấp giao diện web kiểu MacOS.

### Các Trang

| Trang | Mục đích | URL |
|-------|----------|-----|
| Hướng dẫn | Tài liệu bot | `/` |
| Tải báo cáo | Truy cập báo cáo có mật khẩu | `/report/{id}` |
| OAuth Callback | Xác thực Google Calendar | Nội bộ |

### Thiết Kế Responsive

Trang hướng dẫn tự động điều chỉnh theo kích thước màn hình:

| Thiết bị | Bố cục |
|----------|--------|
| Desktop (>1024px) | 4 cột + sidebar |
| Tablet (768-1024px) | 4 cột compact |
| Mobile (520-768px) | 4 cột nhỏ |
| Mobile nhỏ (<520px) | Lưới 2x2 |

---

## Mẹo Sử Dụng

1. **Dùng wizard** cho việc phức tạp với nhiều tùy chọn
2. **Dùng chế độ nhanh** cho việc đơn giản
3. **Text mention** hoạt động với người không có @username
4. **Reply tin nhắn bot** trong nhóm chat khi nhập text
5. **Link mention** trong xác nhận để thông báo người nhận
6. **Báo cáo xuất** được bảo vệ bằng mật khẩu
7. **Hướng dẫn** có sẵn tại trang web để xem nhanh
8. **Kết nối Google Calendar** (`/lichgoogle`) để nhận thông báo calendar
9. **Tùy chỉnh thông báo** (`/caidat`) để kiểm soát cảnh báo nhận được
10. **Dùng "Cả hai" nguồn nhắc** để nhận thông báo qua cả Telegram và Calendar
