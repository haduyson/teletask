# TeleTask Bot - Chi Tiết Các Lệnh

**Cập nhật lần cuối:** 2025-12-20
**Phiên bản:** 1.0
**Ngôn ngữ:** Tiếng Việt

---

## Tổng Quan

Hướng dẫn chi tiết tất cả các lệnh Telegram có sẵn trong TeleTask Bot, kèm theo cách sử dụng và ví dụ.

---

## Mục Lục

1. [Lệnh Cơ Bản](#lệnh-cơ-bản)
2. [Quản Lý Việc](#quản-lý-việc)
3. [Công Việc Nhóm](#công-việc-nhóm)
4. [Thống Kê & Báo Cáo](#thống-kê--báo-cáo)
5. [Cài Đặt & Tích Hợp](#cài-đặt--tích-hợp)
6. [Lệnh Phụ Trợ](#lệnh-phụ-trợ)

---

## Lệnh Cơ Bản

### `/start`
**Mô tả:** Khởi động bot, hiển thị menu chính
**Cách dùng:** Gửi `/start` bất kỳ lúc nào
**Kết quả:**
- Đăng ký người dùng (nếu lần đầu)
- Hiển thị menu với các nút lệnh
- Giới thiệu bot

**Ví dụ:**
```
Bạn: /start
Bot: ✅ Chào mừng bạn đến TeleTask Bot!

Dưới đây là những lệnh bạn có thể sử dụng:
📋 /taoviec - Tạo việc mới
👁️ /xemviec - Xem danh sách việc
📊 /thongke - Xem thống kê
⚙️ /caidat - Cài đặt tùy chọn
```

### `/help`
**Mô tả:** Xem trợ giúp chi tiết
**Cách dùng:** `/help` hoặc `/help [tên_lệnh]`
**Ví dụ:**
```
Bạn: /help taoviec
Bot: 📋 Lệnh /taoviec - Tạo Việc Mới

Cách dùng: /taoviec
Mô tả: Bắt đầu wizard tạo việc với các bước:
1. Nhập tiêu đề
2. Nhập mô tả (tùy chọn)
3. Chọn hạn chót (tùy chọn)
4. Chọn ưu tiên
5. Giao cho ai (tùy chọn)
6. Xác nhận

Ví dụ: /taoviec
```

---

## Quản Lý Việc

### `/taoviec` - Tạo Việc Mới

**Mô tả:** Tạo một công việc mới qua wizard (5-6 bước)

**Các bước:**

**Bước 1: Nhập Tiêu Đề**
```
Bot: 📝 Hãy nhập tiêu đề của việc:
Bạn: Fix lỗi đăng nhập
```

**Bước 2: Mô Tả (Tùy Chọn)**
```
Bot: Hãy nhập mô tả chi tiết (gõ "bỏ qua" để bỏ)
Bạn: Người dùng không thể đăng nhập bằng tài khoản Google
```

**Bước 3: Chọn Hạn Chót (Tùy Chọn)**
```
Bot: Hạn chót? (Nhập ngày hoặc "bỏ qua")
   Ví dụ: "ngày mai", "25/12", "25/12 14:30"
Bạn: ngày mai 18h
```

**Bước 4: Ưu Tiên (Tùy Chọn)**
```
Bot: Chọn mức ưu tiên:
[🔴 Khẩn Cấp] [🟡 Cao] [🟢 Thường] [⚪ Thấp]
Bạn: (Nhấn nút 🔴 Khẩn Cấp)
```

**Bước 5: Giao Cho Ai (Tùy Chọn)**
```
Bot: Giao cho ai? (hoặc "bỏ qua" để giữ cho mình)
Bạn: @nam
```

**Bước 6: Xác Nhận**
```
Bot: ✅ Xác nhận tạo việc này?
    📋 Fix lỗi đăng nhập
    🔴 Khẩn Cấp
    ⏰ Ngày mai 18:00
    👤 @nam
[✅ Tạo] [❌ Hủy]
Bạn: (Nhấn ✅ Tạo)
```

**Kết Quả:**
```
Bot: ✅ Tạo thành công!
    Việc: P-0042
    Tiêu đề: Fix lỗi đăng nhập
    Ưu tiên: 🔴 Khẩn Cấp
    Hạn: Ngày mai 18:00
```

---

### `/xemviec` - Xem Công Việc

**Mô tả:** Xem danh sách hoặc chi tiết một công việc

**Cách sử dụng:**
- `/xemviec` - Hiển thị menu lọc
- `/xemviec P-0042` - Xem chi tiết việc P-0042
- `/xemviec G-0001` - Xem chi tiết việc nhóm G-0001

**Menu Lọc:**
```
Bạn: /xemviec
Bot: Chọn danh sách cần xem:
[📋 Cá Nhân] [📤 Đã Giao] [📥 Nhận Được] [🔍 Tất Cả]
```

**Danh Sách Công Việc:**
```
📋 Công Việc Của Bạn (5)
━━━━━━━━━━━━━━━━━━━
🔴 P-0042 Fix lỗi đăng nhập (18:00 ngày mai)
🟡 P-0038 Code review PR#123 (Thứ 5)
🟢 P-0035 Update documentation
⚪ P-0020 Refactor database queries
✅ P-0001 Hoàn thành (5 ngày trước)

[◀️ Trước] [Trang 1/2] [Tiếp ▶️]
```

**Chi Tiết Công Việc:**
```
Bạn: /xemviec P-0042
Bot: 📋 P-0042: Fix lỗi đăng nhập
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trạng thái: Đang làm
Ưu tiên: 🔴 Khẩn Cấp
Tiến độ: 50% [████░░░░░]
Mô tả: Người dùng không thể đăng nhập bằng tài khoản Google
Hạn: Thứ Năm, 25/12/2025 18:00 (3 ngày nữa)
Giao cho: @nam
Người tạo: @admin

[👁️ Xem] [✏️ Sửa] [✅ Xong] [❌ Xóa]
```

**Lệnh Liên Quan:**
- `/viecdanhan` - Xem công việc được giao cho bạn
- `/viecnhom` - Xem tất cả công việc nhóm (chỉ trong nhóm)
- `/timviec [từ_khóa]` - Tìm kiếm công việc
- `/deadline [số_giờ]` - Xem công việc sắp đến hạn

---

### `/xong` - Đánh Dấu Hoàn Thành

**Mô tả:** Đánh dấu công việc là hoàn thành

**Cách dùng:** `/xong P-0042` hoặc `/xong` (nếu trả lời tin nhắn của việc)

**Ví dụ:**
```
Bạn: /xong P-0042
Bot: ✅ Hoàn thành công việc P-0042!

    Thông báo được gửi cho người tạo (@admin)
```

**Lệnh Liên Quan:**
- `/danglam [ID]` - Đánh dấu đang làm
- `/tiendo [ID] [%]` - Cập nhật tiến độ

---

### `/danglam` - Đánh Dấu Đang Làm

**Mô tả:** Đánh dấu công việc là đang được xử lý

**Cách dùng:** `/danglam P-0042`

**Ví dụ:**
```
Bạn: /danglam P-0042
Bot: ⏳ Đánh dấu P-0042 đang làm
    Người tạo sẽ được thông báo
```

---

### `/tiendo` - Cập Nhật Tiến Độ

**Mô tả:** Cập nhật phần trăm tiến độ của công việc

**Cách dùng:** `/tiendo [ID] [%]`

**Ví dụ:**
```
Bạn: /tiendo P-0042 75
Bot: 📊 Cập nhật tiến độ P-0042
    Tiến độ: 75% [███████░░]
```

---

### `/xoa` - Xóa Công Việc

**Mô tả:** Xóa công việc (có thể hoàn tác trong 30 giây)

**Cách dùng:** `/xoa P-0042`

**Ví dụ:**
```
Bạn: /xoa P-0042
Bot: ❌ Đã xóa P-0042

    ⚠️ Bạn còn 30 giây để hoàn tác
    [↩️ Hoàn Tác] [✓ Xác Nhận]
```

**Lưu ý:**
- Nếu không hoàn tác trong 30 giây, công việc sẽ bị xóa vĩnh viễn
- Nhấn "Hoàn Tác" để khôi phục
- Nhấn "Xác Nhận" để xóa ngay

---

## Công Việc Nhóm

### `/giaoviec` - Giao Công Việc

**Mô tả:** Giao công việc cho một hoặc nhiều người

**Các Cách Dùng:**

**1. Giao cho một người:**
```
Bạn: /giaoviec @nam Fix bug
Bot: ✅ Đã giao việc P-0042 cho @nam
    @nam sẽ nhận thông báo
```

**2. Giao cho nhiều người (tạo việc nhóm):**
```
Bạn: /giaoviec @nam @linh @hoa Code review
Bot: ✅ Tạo công việc nhóm G-0001

    Giao cho:
    • @nam (P-0043)
    • @linh (P-0044)
    • @hoa (P-0045)

    Cả ba sẽ nhận thông báo
```

**3. Giao với thời gian:**
```
Bạn: /giaoviec @nam Update docs 25/12 14h30
Bot: ✅ Đã giao việc P-0042 cho @nam
    Hạn: 25/12/2025 14:30
```

**4. Trả lời tin nhắn của người:**
```
(Ai đó gửi tin nhắn "Need help with...")
Bạn: /giaoviec Fix this issue (trả lời tin nhắn)
Bot: ✅ Đã giao việc P-0042 cho người đó
```

**Lưu ý:**
- Được sử dụng trong nhóm chat hoặc tin nhắn riêng
- Hỗ trợ một hoặc nhiều người (@mention hoặc click tên)
- Tự động phát hiện thời gian từ lệnh
- Người được giao sẽ nhận thông báo (nếu bật)

---

### `/viecdagiao` - Xem Công Việc Đã Giao

**Mô tả:** Xem danh sách công việc bạn đã giao cho người khác

**Cách dùng:** `/viecdagiao`

**Ví dụ:**
```
Bạn: /viecdagiao
Bot: 📤 Công Việc Bạn Đã Giao (8)
━━━━━━━━━━━━━━━━━━━━
🔴 P-0042 Fix lỗi đăng nhập (cho @nam) - Đang làm
🟡 P-0038 Code review (cho @linh) - Chờ xử lý
🟢 P-0035 Update docs (cho @hoa) - Hoàn thành
...
```

---

## Thống Kê & Báo Cáo

### `/thongke` - Thống Kê Tổng Quan

**Mô tả:** Xem thống kê toàn bộ của bạn

**Cách dùng:** `/thongke`

**Ví dụ:**
```
Bạn: /thongke
Bot: 📊 Thống Kê Toàn Bộ
━━━━━━━━━━━━━━━━━━━━
📋 Công Việc Cá Nhân
   Tổng: 15 | Hoàn thành: 12 (80%)

📤 Công Việc Bạn Giao Cho Người Khác
   Tổng: 28 | Hoàn thành: 24 (86%)

📥 Công Việc Mọi Người Giao Cho Bạn
   Tổng: 18 | Hoàn thành: 16 (89%)

⏰ Công Việc Sắp Hết Hạn
   3 công việc hết hạn trong 7 ngày

[📅 Tuần] [📆 Tháng] [📊 Chi Tiết]
```

---

### `/thongketuan` - Thống Kê Tuần

**Mô tả:** Thống kê tuần này so với tuần trước

**Cách dùng:** `/thongketuan`

**Ví dụ:**
```
Bạn: /thongketuan
Bot: 📊 Thống Kê Tuần Này
━━━━━━━━━━━━━━━━━━━━
Tuần Này (17-23/12)
  Tạo: 5 công việc
  Hoàn thành: 4 công việc
  Hiệu suất: 80%

Tuần Trước (10-16/12)
  Tạo: 3 công việc
  Hoàn thành: 3 công việc
  Hiệu suất: 100%

Xu Hướng: 📈 Tăng 20%
```

---

### `/thongkethang` - Thống Kê Tháng

**Mô tả:** Thống kê tháng này so với tháng trước

**Cách dùng:** `/thongkethang`

---

### `/viectrehan` - Công Việc Sắp Hết Hạn

**Mô tả:** Xem công việc quá hạn hoặc sắp quá hạn

**Cách dùng:** `/viectrehan` hoặc `/viectrehan [thời_gian]`

**Ví dụ:**
```
Bạn: /viectrehan
Bot: ⏰ Công Việc Sắp/Đã Quá Hạn (Tháng Này)
━━━━━━━━━━━━━━━━━━━━
🔴 QUAZZ HẠN (3)
  P-0042 Fix lỗi (quá hạn 2 ngày)
  P-0038 Code review (quá hạn 5 giờ)
  P-0035 Update docs (quá hạn 1 ngày)

🟡 SAP QUAZZ HẠN (5)
  P-0041 New feature (2 giờ nữa)
  P-0039 Testing (6 giờ nữa)
  ...
```

---

### `/export` - Xuất Báo Cáo

**Mô tả:** Tải về báo cáo (CSV, Excel, hoặc PDF)

**Cách dùng:** `/export [định_dạng] [thời_kỳ]`

**Định dạng:**
- `csv` - Tệp CSV (có thể mở bằng Excel)
- `xlsx` - Tệp Excel (với biểu đồ)
- `pdf` - Tệp PDF (có biểu đồ)

**Thời kỳ:**
- `7days` - 7 ngày gần nhất
- `30days` - 30 ngày gần nhất
- `week` - Tuần này
- `month` - Tháng này
- `custom` - Chọn khoảng thời gian

**Ví dụ:**
```
Bạn: /export xlsx month
Bot: 📊 Đang tạo báo cáo...
     ⏳ Vui lòng chờ...

    (Sau 3-5 giây)

    ✅ Báo cáo sẵn sàng!
    📥 [Tải Xuống]

    ⚠️ Link hết hạn trong 72 giờ
    Mật khẩu: abc123xyz
```

---

## Cài Đặt & Tích Hợp

### `/nhacviec` - Đặt Nhắc Nhở

**Mô tả:** Tạo nhắc nhở cho một công việc

**Cách dùng:** `/nhacviec [ID] [thời_gian]`

**Ví dụ:**
```
Bạn: /nhacviec P-0042 24h
Bot: ⏰ Đặt nhắc nhở cho P-0042
    Nhắc 24 giờ trước hạn chót

    Bạn sẽ nhận thông báo vào:
    Thứ Tư, 24/12/2025 18:00

Bạn: /nhacviec P-0042 custom 2025-12-25 10h
Bot: ⏰ Nhắc nhở tùy chỉnh đặt thành công
    Nhắc: 25/12/2025 10:00
```

**Thời gian có sẵn:**
- `24h` - 24 giờ trước hạn
- `1h` - 1 giờ trước hạn
- `30m` - 30 phút trước hạn
- `5m` - 5 phút trước hạn
- `custom [ngày giờ]` - Thời gian tùy chỉnh

---

### `/caidat` - Cài Đặt Tùy Chọn

**Mô tả:** Cấu hình tùy chọn cá nhân

**Cách dùng:** `/caidat`

**Menu Cài Đặt:**
```
Bạn: /caidat
Bot: ⚙️ Cài Đặt Tài Khoản
━━━━━━━━━━━━━━━━━━━━
[🌍 Múi Giờ]
  Hiện tại: Asia/Ho_Chi_Minh

[🔔 Thông Báo]
  • Công việc mới giao: ✅ BẬT
  • Thay đổi trạng thái: ✅ BẬT
  • Nhắc nhở: ✅ BẬT
  • Báo cáo hàng tuần: ✅ BẬT
  • Báo cáo hàng tháng: ✅ BẬT

[📅 Google Calendar]
  Trạng thái: ❌ Chưa kết nối
  [🔗 Kết Nối]

[🔐 Bảo Mật]
  [Đổi Mật Khẩu]
```

---

### `/lichgoogle` - Kết Nối Google Calendar

**Mô tả:** Đồng bộ công việc với Google Calendar của bạn

**Cách dùng:** `/lichgoogle`

**Quá Trình:**
```
Bạn: /lichgoogle
Bot: 🔗 Kết Nối Google Calendar

    Bạn sắp chuyển đến Google để xác nhận...
    [🔗 Mở Link Xác Thực]

(Sau khi xác nhận)

Bot: ✅ Kết Nối Thành Công!

    Các công việc hoàn thành sẽ được tự động
    thêm vào Google Calendar của bạn.

    Bạn có thể chỉnh sửa trong /caidat
```

---

## Lệnh Phụ Trợ

### `/cancel` - Hủy Bỏ Hành Động

**Mô tả:** Hủy bỏ wizard hoặc hành động hiện tại

**Cách dùng:** `/cancel` hoặc gõ "hủy"

**Ví dụ:**
```
(Đang trong wizard tạo việc)
Bạn: /cancel
Bot: ❌ Đã hủy bỏ tạo việc
```

---

### `/menu` - Menu Chính

**Mô tả:** Hiển thị menu chính với các nút

**Cách dùng:** `/menu`

---

### `/thongtinbot` - Thông Tin Bot

**Mô tả:** Xem thông tin chi tiết về bot

**Cách dùng:** `/thongtinbot`

**Ví dụ:**
```
Bạn: /thongtinbot
Bot: ℹ️ Thông Tin TeleTask Bot
━━━━━━━━━━━━━━━━━━━━
Phiên bản: 1.0
Trạng thái: Hoạt động
Người dùng đang hoạt động: 42
Tổng công việc: 1,234
Tỷ lệ hoàn thành: 72%

Liên Hệ: @admin
Báo Cáo Lỗi: /feedback
```

---

### `/feedback` - Gửi Phản Hồi

**Mô tả:** Gửi phản hồi, báo lỗi, hoặc đề xuất cho nhóm phát triển

**Cách dùng:** `/feedback [nội_dung]`

**Ví dụ:**
```
Bạn: /feedback Nhắc nhở không hoạt động trong nhóm
Bot: ✅ Cảm ơn phản hồi của bạn!
    Chúng tôi sẽ xem xét và cải thiện.
```

---

## Ghi Chú Quan Trọng

### Thời Gian & Ngày Tháng

**Định Dạng Được Hỗ Trợ:**
- `ngày mai` - Hôm sau lúc 9h sáng
- `25/12` - 25/12 hiện tại hoặc năm sau, lúc 9h
- `25/12 14:30` - 25/12 lúc 14:30
- `14h30` - Hôm nay lúc 14:30
- `thứ 2` - Thứ 2 tuần tới lúc 9h
- `tuần tới` - Thứ 2 tuần tới lúc 9h

### ID Công Việc

- **P-XXXX:** Công việc cá nhân (P-0042, P-0100, ...)
- **G-XXXX:** Công việc nhóm (G-0001, G-0050, ...)

### Mức Ưu Tiên

- 🔴 **Khẩn Cấp** - Cần giải quyết ngay
- 🟡 **Cao** - Ưu tiên cao
- 🟢 **Thường** - Ưu tiên bình thường
- ⚪ **Thấp** - Có thể để sau

### Trạng Thái Công Việc

- 📋 **Chờ Xử Lý** - Mới tạo
- ⏳ **Đang Làm** - Đang xử lý
- ✅ **Hoàn Thành** - Đã xong
- ⏸️ **Tạm Dừng** - Tạm thời dừng

---

## Mẹo & Thủ Thuật

1. **Tìm kiếm nhanh:** Gõ tên công việc hoặc `/timviec từ_khóa`
2. **Cập nhật nhanh:** Dùng các nút inline thay vì gõ lệnh
3. **Nhắc nhở kịp thời:** Đặt nhiều nhắc nhở cho công việc quan trọng
4. **Báo cáo định kỳ:** Bật báo cáo tự động hàng tuần/tháng
5. **Chia sẻ:** Giao công việc để dễ quản lý nhóm

---

**Cập nhật lần cuối:** 2025-12-20
**Trạng thái:** Hoạt động
**Ngôn ngữ:** Tiếng Việt
