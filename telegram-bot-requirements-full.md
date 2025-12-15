# 📋 YÊU CẦU TẠO HỆ THỐNG QUẢN LÝ BOT TELEGRAM NHẮC VIỆC

---

## 🎯 TỔNG QUAN DỰ ÁN

Tôi cần bạn tạo một **hệ thống quản lý và tạo Bot Telegram Nhắc Việc** hoàn chỉnh. Hệ thống này cho phép:
- Cài đặt trên Ubuntu Server bằng 1 dòng lệnh duy nhất
- Quản lý nhiều bot Telegram trên cùng một server
- Mỗi bot là một instance độc lập với database riêng
- Giao diện CLI (botpanel) để quản lý toàn bộ hệ thống
- Hệ thống monitoring và alert cho admin

---

## 📦 PHẦN 1: YÊU CẦU CÀI ĐẶT

### 1.1. Cài đặt 1 dòng lệnh
```bash
curl -sSL https://domain/install.sh | sudo bash
```

Script `install.sh` phải tự động thực hiện:
- Cập nhật hệ thống Ubuntu
- Cài đặt dependencies: Python 3.11+, PostgreSQL 15+, PM2, Nginx, Git, Redis
- Tạo user `botpanel` để chạy hệ thống
- Tạo cấu trúc thư mục
- Cài đặt botpanel CLI tool
- Cấu hình PostgreSQL (tạo user, set password)
- Cấu hình PM2 chạy như service
- Thiết lập permissions phù hợp
- Cài đặt Prometheus + Grafana (optional)
- Hiển thị thông tin sau khi cài đặt thành công

### 1.2. Lệnh quản lý
```bash
botpanel    # Mở menu quản lý (KHÔNG cần sudo)
```

### 1.3. Cấu trúc thư mục
```
/home/botpanel/
├── botpanel.sh                 # CLI management tool
├── config/
│   ├── global.conf             # Cấu hình chung (PostgreSQL, timezone...)
│   └── admin.conf              # Cấu hình admin (Telegram ID nhận alert)
├── bots/
│   ├── bot_001/
│   │   ├── bot.py              # Source code bot
│   │   ├── config.json         # Cấu hình bot (token, db_name, tên bot...)
│   │   ├── ecosystem.config.js # PM2 config
│   │   └── .env                # Environment variables
│   ├── bot_002/
│   └── ...
├── templates/
│   └── bot_template/           # Template cho bot mới
├── logs/
│   ├── botpanel.log
│   ├── bot_001.log
│   └── bot_002.log
├── backups/
│   ├── daily/                  # Backup database hàng ngày (giữ 7 ngày)
│   └── manual/                 # Backup thủ công
├── scripts/
│   ├── backup.sh
│   ├── restore.sh
│   ├── update.sh
│   └── health_check.sh
└── monitoring/
    ├── prometheus/
    └── grafana/
```

---

## 🖥️ PHẦN 2: BOTPANEL - HỆ THỐNG QUẢN LÝ (CLI)

### 2.1. Menu chính
```
╔══════════════════════════════════════════════════════════════╗
║              🤖 BOTPANEL - QUẢN LÝ BOT TELEGRAM              ║
╠══════════════════════════════════════════════════════════════╣
║  1.  📋 Xem danh sách bot                                    ║
║  2.  ➕ Tạo bot mới                                          ║
║  3.  ⚙️  Quản lý bot (Start/Stop/Restart/Edit)               ║
║  4.  🗑️  Xóa bot                                             ║
║  5.  📄 Xem log bot                                          ║
║  6.  🔄 Cập nhật bot                                         ║
║  7.  🌍 Quản lý Timezone/UTC                                 ║
║  8.  💾 Backup & Restore                                     ║
║  9.  📊 Thông tin hệ thống                                   ║
║  10. 🔔 Cấu hình Admin Alert                                 ║
║  11. 📈 Monitoring & Metrics                                 ║
║  0.  🚪 Thoát                                                ║
╚══════════════════════════════════════════════════════════════╝
```

### 2.2. Chi tiết từng chức năng

#### [1] Xem danh sách bot
```
┌──────────────────────────────────────────────────────────────────────┐
│ #  │ Tên Bot          │ Trạng thái │ Uptime    │ Memory │ CPU  │ DB  │
├──────────────────────────────────────────────────────────────────────┤
│ 1  │ TaskBot_Company  │ 🟢 Active  │ 5d 12h    │ 45MB   │ 0.5% │ ✓   │
│ 2  │ TaskBot_Team     │ 🟢 Active  │ 3d 8h     │ 52MB   │ 0.3% │ ✓   │
│ 3  │ TaskBot_Personal │ 🔴 Stop    │ -         │ -      │ -    │ ✓   │
└──────────────────────────────────────────────────────────────────────┘
```

#### [2] Tạo bot mới
```
═══ TẠO BOT MỚI ═══

Bot Token (bắt buộc): 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
Tên bot [TaskBot]: MyCompanyBot
Tên hiển thị (cho /start, /help) [Task Manager Bot]: Bot Quản Lý Công Việc ABC
Mô tả bot []: Hệ thống quản lý và nhắc việc cho công ty ABC
Database name [mycompanybot_db]: (Enter để dùng mặc định)
Database password [auto]: (Enter để tạo ngẫu nhiên)

─── Thông tin hỗ trợ (hiển thị ở /help) ───
Telegram hỗ trợ [@support]: @mycompany_support
Số điện thoại []: 0901234567
Email []: support@company.com

─── Cấu hình Admin Alert ───
Admin Telegram ID (nhận thông báo lỗi): 123456789

✅ Tạo bot thành công!
   - Bot ID: bot_003
   - Tên hiển thị: Bot Quản Lý Công Việc ABC
   - Database: mycompanybot_db
   - Status: 🟢 Running
```

#### [3] Quản lý bot
```
═══ QUẢN LÝ BOT ═══

Chọn bot: 1

Bot: TaskBot_Company (🟢 Active)
1. 🔄 Restart
2. ⏹️  Stop
3. ▶️  Start
4. ✏️  Edit thông tin
5. 🔙 Quay lại

> Edit thông tin:
  - Tên bot
  - Tên hiển thị (cho lời chào)
  - Mô tả bot
  - Thông tin hỗ trợ (Telegram, SĐT, Email)
  - Token (cần restart sau khi đổi)
  - Admin Telegram ID
```

#### [4] Xóa bot
```
═══ XÓA BOT ═══

1. Xóa một bot cụ thể
2. Xóa toàn bộ bot (NGUY HIỂM)

> Chọn bot để xóa: TaskBot_Personal

⚠️  CẢNH BÁO: Hành động này sẽ xóa:
    - Source code bot
    - Database và toàn bộ dữ liệu
    - Logs và cấu hình

Nhập "DELETE TaskBot_Personal" để xác nhận:
```

#### [5] Xem log bot
```
═══ XEM LOG ═══

Chọn bot: 1
Số dòng log [100]: 50
Loại log:
  1. All logs
  2. Error only
  3. Activity only

[2024-12-10 14:30:22] INFO: Bot started
[2024-12-10 14:30:25] INFO: User @john created task #123
[2024-12-10 14:31:00] INFO: Reminder sent for task #120
[2024-12-10 14:32:15] ERROR: Failed to send message to user 123456
...

[F] Follow log realtime | [Q] Quit
```

#### [6] Cập nhật bot
```
═══ CẬP NHẬT BOT ═══

1. Cập nhật một bot
2. Cập nhật tất cả bot
3. Cập nhật + Migration database

> Đang cập nhật TaskBot_Company...
  ✓ Pull code mới
  ✓ Cài đặt dependencies
  ✓ Migration database
  ✓ Restart bot

✅ Cập nhật thành công!
```

#### [7] Quản lý Timezone
```
═══ TIMEZONE/UTC ═══

Timezone hiện tại: Asia/Ho_Chi_Minh (UTC+7)

1. Đổi timezone cho một bot
2. Đổi timezone cho tất cả bot
3. Đổi timezone server

Danh sách timezone phổ biến:
  - Asia/Ho_Chi_Minh (UTC+7)
  - Asia/Bangkok (UTC+7)
  - Asia/Singapore (UTC+8)
  - UTC (UTC+0)
```

#### [8] Backup & Restore
```
═══ BACKUP & RESTORE ═══

1. Backup một bot
2. Backup tất cả bot
3. Restore từ backup
4. Cấu hình auto backup
5. Xem danh sách backup
6. Xóa backup cũ

Auto backup: ✅ Enabled
  - Thời gian: 3:00 AM hàng ngày
  - Giữ lại: 7 ngày gần nhất
  - Vị trí: /home/botpanel/backups/daily/

Danh sách backup gần đây:
┌─────────────────────────────────────────────────────────────┐
│ Ngày       │ Bot              │ Size   │ Status            │
├─────────────────────────────────────────────────────────────┤
│ 2024-12-10 │ TaskBot_Company  │ 15MB   │ ✅ Success        │
│ 2024-12-10 │ TaskBot_Team     │ 12MB   │ ✅ Success        │
│ 2024-12-09 │ TaskBot_Company  │ 14MB   │ ✅ Success        │
└─────────────────────────────────────────────────────────────┘
```

#### [9] Thông tin hệ thống
```
═══ THÔNG TIN HỆ THỐNG ═══

🖥️  Server Info:
    - OS: Ubuntu 24.04 LTS
    - Hostname: task-server
    - IP: 192.168.1.100
    - Uptime: 30 days

💾 Resources:
    - CPU: 15% (4 cores)
    - RAM: 2.1GB / 8GB (26%)
    - Disk: 45GB / 100GB (45%)

🤖 Bot Stats:
    - Total bots: 3
    - Running: 2
    - Stopped: 1

🐘 PostgreSQL:
    - Status: 🟢 Running
    - Version: 15.4
    - Databases: 3
    - Connections: 12/100

📦 PM2:
    - Status: 🟢 Running
    - Processes: 2

💾 Backup:
    - Auto backup: ✅ Enabled
    - Last backup: 2024-12-10 03:00
    - Total size: 45MB
```

#### [10] Cấu hình Admin Alert
```
═══ CẤU HÌNH ADMIN ALERT ═══

Admin nhận alert hiện tại:
  - Global: @admin (ID: 123456789)
  - TaskBot_Company: @manager (ID: 987654321)
  - TaskBot_Team: (Dùng Global)

1. Thay đổi Global Admin
2. Thay đổi Admin cho bot cụ thể
3. Test gửi alert
4. Cấu hình loại alert

Loại alert:
  [✓] Bot crash / restart
  [✓] Database connection error
  [✓] High memory usage (>80%)
  [✓] High CPU usage (>90%)
  [✓] Disk space low (<10%)
  [ ] Daily summary report
```

#### [11] Monitoring & Metrics
```
═══ MONITORING & METRICS ═══

1. Xem health status tất cả bot
2. Xem metrics realtime
3. Mở Grafana dashboard (port 3000)
4. Cấu hình Prometheus
5. Export metrics

Health Status:
┌─────────────────────────────────────────────────────────────┐
│ Bot              │ Status │ Response │ DB    │ Last Check  │
├─────────────────────────────────────────────────────────────┤
│ TaskBot_Company  │ ✅ OK  │ 45ms     │ ✅ OK │ 10s ago     │
│ TaskBot_Team     │ ✅ OK  │ 52ms     │ ✅ OK │ 10s ago     │
│ TaskBot_Personal │ ❌ Down│ -        │ ✅ OK │ 10s ago     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 PHẦN 3: TÍNH NĂNG BOT TELEGRAM

### 3.1. Lệnh khởi động và trợ giúp

#### /start
```
🎉 Chào mừng bạn đến với [TÊN BOT HIỂN THỊ]!

[MÔ TẢ BOT]

Tôi sẽ giúp bạn:
✅ Tạo và quản lý công việc cá nhân
✅ Giao việc cho đồng nghiệp trong nhóm
✅ Nhắc nhở deadline tự động
✅ Theo dõi tiến độ công việc
✅ Báo cáo thống kê tuần/tháng

📖 Gõ /help để xem hướng dẫn chi tiết

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆘 Hỗ trợ: @support_username
📞 Hotline: 0901234567
📧 Email: support@company.com
```

#### /help hoặc /huongdan
```
📖 HƯỚNG DẪN SỬ DỤNG [TÊN BOT HIỂN THỊ]

━━━ 📝 TẠO VIỆC CÁ NHÂN ━━━
/taoviec [nội dung] [deadline]
Ví dụ:
• /taoviec Làm báo cáo tuần
• /taoviec Họp team 14h30 10/12/2025
• /taoviec Gửi email ngày mai

━━━ 👥 GIAO VIỆC ━━━
/giaoviec @user [nội dung] [deadline]
Ví dụ:
• /giaoviec @nguyenlam Làm slide
• /giaoviec Nguyễn Văn A Báo cáo 15/12

━━━ 📊 XEM VIỆC ━━━
/xemviec - Việc của bạn
/viecnhom - Tất cả việc trong nhóm
/viectoilam - Việc cần làm
/viectoigiao - Việc bạn đã giao
/timviec [từ khóa] - Tìm kiếm

━━━ ✅ CẬP NHẬT ━━━
/xong [ID] - Hoàn thành
/danglam [ID] - Đang làm
/xoa [ID] - Xóa việc

━━━ ⏰ DEADLINE ━━━
/deadline 24h - Việc trong 24h tới
/nhacviec [ID] [thời gian] - Đặt nhắc

━━━ 🔄 VIỆC LẶP LẠI ━━━
/vieclaplai [nội dung] [chu kỳ]

📖 Chi tiết: /huongdan [tên lệnh]
🆘 Hỗ trợ: @support_username
```

### 3.2. Lệnh tạo việc cá nhân

```
/taoviec [nội dung] [deadline]
/taoviec [deadline] [nội dung]
```

**Ví dụ:**
```
/taoviec Làm báo cáo tuần
/taoviec Họp team 14h30 10/12/2025
/taoviec Gửi email khách hàng ngày mai
/taoviec Review code 10h sáng mai
/taoviec Họp với sếp 3h chiều thứ 6
```

**Phản hồi khi tạo thành công:**
```
✅ Tạo việc thành công!

👤 Việc cá nhân của Nguyễn Văn A
📌 Nội dung: Làm báo cáo tuần
🆔 ID: P-1234
🎯 Ưu tiên: 🟡 Trung bình
📊 Trạng thái: ⏳ Chưa làm
📅 Thời gian tạo: 14:30 10/12/2025
⏰ Deadline: 14:30 11/12/2025

[✏️ Sửa] [🎯 Ưu tiên] [🗑️ Xóa]
```

**Báo lỗi khi sai cú pháp:**
```
❌ Lỗi cú pháp!

Cách dùng đúng:
/taoviec [nội dung] [deadline]

Ví dụ:
• /taoviec Làm báo cáo tuần
• /taoviec Họp team 14h30 10/12/2025
• /taoviec Gửi email ngày mai

💡 Gõ /help taoviec để xem chi tiết
```

**Báo lỗi khi deadline trong quá khứ:**
```
❌ Không thể tạo việc!

⚠️ Deadline "09:00 05/12/2025" đã là quá khứ.

Vui lòng chọn deadline trong tương lai.
Thời gian hiện tại: 14:30 10/12/2025

💡 Ví dụ deadline hợp lệ:
• ngày mai
• 15/12/2025
• 10h sáng thứ 6
```

### 3.3. Lệnh giao việc cho người khác

```
/giaoviec @username [nội dung] [deadline]
/giaoviec [Tên người dùng] [nội dung] [deadline]
/giaoviec @user1 @user2 [nội dung] [deadline]
```

**Lưu ý quan trọng về Telegram User:**
- Một số người dùng Telegram không có username (@user)
- Bot hỗ trợ mention bằng tên hiển thị: `Nguyễn Văn A`
- Khi reply tin nhắn của ai đó + gõ /giaoviec, sẽ giao cho người đó

**Ví dụ:**
```
/giaoviec @nguyenlam Làm slide thuyết trình
/giaoviec Nguyễn Văn A Báo cáo tuần 15/12
/giaoviec @user1 @user2 Chuẩn bị tài liệu họp
```

**Phản hồi cho người giao việc:**
```
✅ Giao việc thành công!

📌 Công việc: Làm slide thuyết trình
🆔 ID: P-1235
👥 Nhóm: Team Marketing
👤 Người nhận: Nguyễn Lâm
🎯 Ưu tiên: 🟡 Trung bình
📅 Thời gian tạo: 14:35 10/12/2025
⏰ Deadline: 14:35 11/12/2025

[📊 Xem tiến độ] [✏️ Sửa] [🗑️ Xóa]
```

**Thông báo cho người nhận việc (tin nhắn riêng):**
```
📬 Bạn vừa được giao 1 công việc mới!

📌 Công việc: Làm slide thuyết trình
🆔 ID: P-1235
👥 Nhóm: Team Marketing
👨‍💼 Người giao: Trần Văn B
🎯 Ưu tiên: 🟡 Trung bình
📅 Thời gian tạo: 14:35 10/12/2025
⏰ Deadline: 14:35 11/12/2025

[✅ Nhận việc] [🔄 Đang làm] [❓ Hỏi thêm]
```

**Báo lỗi khi không tìm thấy người nhận:**
```
❌ Không thể giao việc!

⚠️ Không tìm thấy người dùng "Nguyễn Văn X" trong nhóm.

💡 Gợi ý:
• Đảm bảo người đó đã tham gia nhóm
• Thử mention trực tiếp hoặc reply tin nhắn của họ
• Kiểm tra lại tên người dùng
```

### 3.4. Giao việc cho nhiều người

```
/giaoviec @user1 @user2 @user3 [nội dung] [deadline]
/giaoviec Nguyễn A, Trần B, Lê C [nội dung] [deadline]
```

**Phản hồi:**
```
✅ Giao việc thành công!

📌 Công việc: Chuẩn bị tài liệu họp
🆔 ID chung: G-500
👥 Nhóm: Team Marketing
🎯 Ưu tiên: 🟡 Trung bình
👤 Người nhận (3):
   • Nguyễn Văn A → P-1236
   • Trần Thị B → P-1237
   • Lê Văn C → P-1238
📅 Thời gian tạo: 14:40 10/12/2025
⏰ Deadline: 09:00 15/12/2025

📊 Tiến độ: ░░░░░░░░░░ 0%

[📊 Chi tiết] [✏️ Sửa] [🗑️ Xóa]
```

### 3.5. Mức độ ưu tiên công việc

**Cách đặt ưu tiên khi tạo việc:**
```
/taoviec [!cao] Báo cáo khẩn 17h hôm nay
/taoviec [!thấp] Dọn dẹp email tuần sau
/giaoviec @user [!khẩn] Fix bug ngay 30 phút
```

**Ký hiệu ưu tiên:**
| Mức | Ký hiệu | Từ khóa | Icon |
|-----|---------|---------|------|
| Khẩn cấp | `[!khẩn]` hoặc `[!urgent]` | khẩn, urgent, gấp | 🔴 |
| Cao | `[!cao]` hoặc `[!high]` | cao, high, quan trọng | 🟠 |
| Trung bình | (mặc định) | - | 🟡 |
| Thấp | `[!thấp]` hoặc `[!low]` | thấp, low | 🟢 |

**Thay đổi ưu tiên sau khi tạo:**
```
/uutien P-1234 cao
```

**Hoặc dùng inline button:**
```
[🔴 Khẩn] [🟠 Cao] [🟡 TB] [🟢 Thấp]
```

### 3.6. Lệnh xem việc

| Lệnh | Mô tả |
|------|-------|
| `/xemviec` | Xem việc liên quan đến bạn |
| `/viecnhom` hoặc `/danhsach` | Xem tất cả việc trong nhóm |
| `/viectoilam` | Việc bạn cần làm (được giao + tự tạo) |
| `/viectoigiao` | Việc bạn đã giao cho người khác |
| `/xemviechomnay` | Việc trong ngày hôm nay |
| `/xemviectuan` | Việc trong tuần này |
| `/xemviecthang` | Việc trong tháng này |
| `/xemviecngay [ngày]` | Xem việc ngày cụ thể |
| `/timviec [từ khóa]` | Tìm kiếm công việc |

**Ví dụ tìm kiếm:**
```
/timviec báo cáo
/timviec slide
/timviec @nguyenlam
```

**Hiển thị danh sách việc:**
```
📋 DANH SÁCH CÔNG VIỆC - 15/12/2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 [KHẨN] Làm slide thuyết trình
🆔 ID: P-1235
👤 Người nhận: Nguyễn Lâm
👨‍💼 Người giao: Trần Văn B
📊 Trạng thái: 🔄 Đang làm
📅 Tạo lúc: 14:35 10/12/2025
⏰ Deadline: 09:00 15/12/2025
⏱️ Còn lại: 18 giờ 25 phút
📈 Tiến độ: ██████░░░░ 60%

[✅ Xong] [📝 Cập nhật %] [💬 Ghi chú]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟡 Chuẩn bị tài liệu họp
🆔 ID: G-500 (P-1236)
👤 Người nhận: Nguyễn A, Trần B, Lê C
👨‍💼 Người giao: Trần Văn B
📊 Trạng thái: ⏳ Chưa làm
⏰ Deadline: 14:00 15/12/2025
📈 Tiến độ: ░░░░░░░░░░ 0% (0/3 người xong)

[👀 Chi tiết] [📊 Tiến độ nhóm]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Tổng: 2 việc | 🔴 1 khẩn | ⏳ 1 chưa làm | 🔄 1 đang làm
```

### 3.7. Lệnh xem deadline

```
/deadline [thời gian]
```

**Ví dụ:**
```
/deadline 2h      # Việc trong 2 giờ tới
/deadline 24h     # Việc trong 24 giờ tới
/deadline 3ngay   # Việc trong 3 ngày tới
```

### 3.8. Lệnh cập nhật trạng thái

| Lệnh | Mô tả |
|------|-------|
| `/hoanthanh [ID]` | Đánh dấu hoàn thành |
| `/xong [ID]` | Alias của hoàn thành |
| `/done [ID]` | Alias của hoàn thành |
| `/danglam [ID]` | Đánh dấu đang làm |
| `/chualam [ID]` | Khôi phục về chưa làm |
| `/tiendo [ID] [%]` | Cập nhật tiến độ (0-100%) |

**Hỗ trợ nhiều ID:**
```
/hoanthanh 123
/xong 123, 456, 789
/danglam 123, 456
/tiendo P-1234 75
```

**Hỗ trợ Reaction Emoji:**
- 👍 trên tin nhắn việc = Đánh dấu hoàn thành
- 🔄 trên tin nhắn việc = Đánh dấu đang làm
- ❌ trên tin nhắn việc = Từ chối/Hủy việc

**Phản hồi khi hoàn thành:**
```
🎉 Chúc mừng Nguyễn Lâm!

✅ Đã hoàn thành công việc:
📌 Làm slide thuyết trình
🆔 ID: P-1235
⏱️ Hoàn thành trước deadline: 2 giờ 30 phút
🏆 Tuyệt vời! Bạn đã hoàn thành đúng hạn!
```

**Thông báo cho người giao việc:**
```
✅ Công việc đã được hoàn thành!

📌 Làm slide thuyết trình
🆔 ID: P-1235
👤 Người hoàn thành: Nguyễn Lâm
⏱️ Hoàn thành lúc: 06:30 15/12/2025
📊 Trước deadline: 2 giờ 30 phút

[👍 Xác nhận] [💬 Góp ý]
```

**Cập nhật tiến độ với progress bar:**
```
📊 Cập nhật tiến độ thành công!

📌 Làm slide thuyết trình
🆔 ID: P-1235
📈 Tiến độ: ███████░░░ 75%
📊 Trạng thái: 🔄 Đang làm
⏰ Deadline: 09:00 15/12/2025
⏱️ Còn lại: 18 giờ 25 phút

[100% ✅] [+10%] [Ghi chú]
```

**Khi việc nhóm có người hoàn thành:**
```
📊 Cập nhật tiến độ công việc nhóm

📌 Chuẩn bị tài liệu họp
🆔 ID: G-500
✅ Nguyễn Văn A đã hoàn thành (P-1236)
📈 Tiến độ: ███░░░░░░░ 33% (1/3 người)
⏳ Còn lại: Trần Thị B, Lê Văn C
```

**Khi toàn bộ nhóm hoàn thành:**
```
🎉 CHÚC MỪNG! Công việc nhóm đã hoàn thành!

📌 Chuẩn bị tài liệu họp
🆔 ID: G-500
📈 Tiến độ: ██████████ 100%
👥 Đã hoàn thành:
   ✅ Nguyễn Văn A - 08:30 15/12
   ✅ Trần Thị B - 09:15 15/12
   ✅ Lê Văn C - 09:45 15/12
⏱️ Trước deadline: 4 giờ 15 phút

🏆 Cả nhóm làm việc tuyệt vời!
```

### 3.9. Lệnh xóa việc

```
/xoa [ID]
/xoa 123, 456, 789    # Xóa nhiều việc
```

**Lưu ý:** Chỉ người tạo/giao việc mới được xóa.

**Xác nhận trước khi xóa (inline button):**
```
⚠️ Xác nhận xóa việc?

📌 Làm slide thuyết trình
🆔 ID: P-1235
👤 Người nhận: Nguyễn Lâm

[✅ Xác nhận xóa] [❌ Hủy]
```

**Phản hồi sau khi xóa:**
```
✅ Đã xóa việc thành công!
🆔 ID đã xóa: P-1235

💡 Bạn có thể hoàn tác trong 30 giây

[↩️ Hoàn tác]
```

**Thông báo cho người nhận việc:**
```
⚠️ Công việc đã bị xóa

📌 Làm slide thuyết trình
🆔 ID: P-1235
🗑️ Xóa bởi: Trần Văn B
📅 Thời gian: 10:00 15/12/2025
```

### 3.10. Nhắc việc tùy chỉnh

```
/nhacviec [ID] [thời gian]
```

**Ví dụ:**
```
/nhacviec 123 13h30 27/12
/nhacviec 456 14h 25/12/2025
/nhacviec P-1234 2 tiếng trước deadline
```

**Phản hồi:**
```
✅ Đã đặt nhắc việc!

📌 Làm slide thuyết trình
🆔 ID: P-1235
🔔 Sẽ nhắc lúc: 13:30 27/12/2025

[🗑️ Hủy nhắc] [➕ Thêm nhắc khác]
```

### 3.11. Hệ thống nhắc việc tự động

**Trước deadline:**
| Thời gian | Mức độ |
|-----------|--------|
| 3 ngày trước | 🔔 Thông thường |
| 24 giờ trước | 🔔 Thông thường |
| 3 giờ trước | ⚠️ Cảnh báo |
| 1 giờ trước | ⚠️ Cảnh báo |
| 30 phút trước | 🚨 Khẩn cấp |
| 15 phút trước | 🚨 Khẩn cấp |

**Sau deadline (việc trễ):**
| Thời gian | Mức độ |
|-----------|--------|
| 1 phút sau | 🚨 Trễ |
| 5 phút sau | 🚨 Trễ |
| 15 phút sau | 🚨 Trễ |
| 30 phút sau | 🚨 Trễ |
| 1 giờ sau | 🚨 Trễ nghiêm trọng |
| 1 ngày sau | 🚨 Trễ nghiêm trọng |
| 3 ngày sau | 🚨 Trễ nghiêm trọng |
| 1 tuần sau | 🚨 Trễ rất nghiêm trọng |
| 1 tháng sau | 🚨 Trễ rất nghiêm trọng |

**Mẫu tin nhắn nhắc việc:**
```
⚠️ NHẮC VIỆC - Còn 1 giờ!

📌 Làm slide thuyết trình
🆔 ID: P-1235
🎯 Ưu tiên: 🔴 Khẩn cấp
📊 Trạng thái: 🔄 Đang làm
📈 Tiến độ: ██████░░░░ 60%
⏰ Deadline: 09:00 15/12/2025
⏱️ Còn lại: 1 giờ

[✅ Đã xong] [🔄 Cập nhật %] [⏰ Nhắc sau]
```

**Mẫu tin nhắn việc trễ:**
```
🚨 VIỆC TRỄ DEADLINE!

📌 Làm slide thuyết trình
🆔 ID: P-1235
🎯 Ưu tiên: 🔴 Khẩn cấp
📊 Trạng thái: ⏳ Chưa làm
⏰ Deadline: 09:00 15/12/2025
⏱️ Đã trễ: 30 phút

⚠️ Vui lòng hoàn thành sớm nhất có thể!

[✅ Đã xong] [💬 Báo cáo lý do]
```

### 3.12. Việc lặp lại (Recurring Tasks)

```
/vieclaplai [nội dung] [chu kỳ] [thời gian bắt đầu]
```

**Chu kỳ hỗ trợ:**
| Chu kỳ | Ví dụ |
|--------|-------|
| Hàng ngày | `hangngay`, `mỗi ngày`, `daily` |
| Hàng tuần | `hangtuan`, `mỗi tuần`, `weekly` |
| Hàng tháng | `hangthang`, `mỗi tháng`, `monthly` |
| Ngày cụ thể trong tuần | `thứ 2`, `thứ 2 và thứ 5` |
| Ngày cụ thể trong tháng | `ngày 1`, `ngày 15 và ngày 30` |

**Ví dụ:**
```
/vieclaplai Báo cáo ngày hangngay 17h
/vieclaplai Họp team hangtuan thứ 2 9h sáng
/vieclaplai Review KPI hangthang ngày 25 14h
/vieclaplai Backup data thứ 2 và thứ 5 23h
```

**Phản hồi:**
```
✅ Tạo việc lặp lại thành công!

📌 Nội dung: Báo cáo ngày
🆔 ID: R-100
🔄 Chu kỳ: Hàng ngày
⏰ Thời gian: 17:00
📅 Bắt đầu từ: 10/12/2025
📅 Việc tiếp theo: 17:00 10/12/2025

[⏸️ Tạm dừng] [✏️ Sửa] [🗑️ Xóa]
```

**Quản lý việc lặp lại:**
```
/xemvieclaplai - Xem tất cả việc lặp lại
/dungvieclaplai [ID] - Tạm dừng
/tieptucvieclaplai [ID] - Tiếp tục
/xoavieclaplai [ID] - Xóa vĩnh viễn
```

### 3.13. Thống kê báo cáo

**Tự động gửi:**
- Báo cáo tuần: 17h Thứ 7 hàng tuần
- Báo cáo tháng: 17h ngày cuối tháng

**Xem thống kê thủ công:**
```
/thongke - Thống kê tổng quan
/thongketuan - Báo cáo tuần này
/thongkethang - Báo cáo tháng này
```

**Mẫu báo cáo tuần:**
```
📊 BÁO CÁO CÔNG VIỆC TUẦN
📅 09/12/2025 - 15/12/2025
👤 Nguyễn Văn A

━━━ 📤 VIỆC BẠN ĐÃ GIAO ━━━
📊 Tổng: 15 việc
✅ Hoàn thành: 10 (67%)
🔄 Đang làm: 3
⏳ Chưa làm: 2
🚨 Trễ deadline: 1

📈 ██████████████░░░░░░ 67%

━━━ 📥 VIỆC BẠN NHẬN ━━━
📊 Tổng: 8 việc
✅ Hoàn thành: 6 (75%)
🔄 Đang làm: 1
⏳ Chưa làm: 1
🚨 Trễ deadline: 0

📈 ███████████████░░░░░ 75%

━━━ 📝 VIỆC CÁ NHÂN ━━━
📊 Tổng: 5 việc
✅ Hoàn thành: 4 (80%)
🔄 Đang làm: 1
⏳ Chưa làm: 0
🚨 Trễ deadline: 0

📈 ████████████████░░░░ 80%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 Hiệu suất tuần này: 74% (Tốt!)
📈 So với tuần trước: +5%
🏆 Xếp hạng trong nhóm: #2/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[📊 Chi tiết] [📥 Xuất Excel]
```

### 3.14. Tích hợp Google Calendar (Tùy chọn)

```
/linkcalendar - Liên kết với Google Calendar
/synccalendar - Đồng bộ việc với Calendar
/unlinkcalendar - Hủy liên kết
```

**Khi liên kết thành công:**
```
✅ Đã liên kết Google Calendar!

📅 Tài khoản: user@gmail.com
🔄 Tự động đồng bộ: ✅ Bật

Các việc có deadline sẽ tự động được thêm vào Calendar của bạn.

[⚙️ Cài đặt] [🔓 Hủy liên kết]
```

### 3.15. Lệnh thông tin

| Lệnh | Mô tả |
|------|-------|
| `/help` hoặc `/huongdan` | Xem hướng dẫn sử dụng |
| `/help [tên lệnh]` | Xem hướng dẫn chi tiết lệnh |
| `/thongtin` | Xem thông tin về bot |
| `/gioithieu` | Giới thiệu về bot |
| `/start` | Bắt đầu sử dụng bot |
| `/caidat` | Cài đặt cá nhân |

### 3.16. Cài đặt cá nhân

```
/caidat
```

```
⚙️ CÀI ĐẶT CÁ NHÂN

🔔 Thông báo:
   • Nhắc việc: ✅ Bật
   • Báo cáo tuần: ✅ Bật
   • Báo cáo tháng: ✅ Bật

⏰ Thời gian:
   • Timezone: Asia/Ho_Chi_Minh (UTC+7)
   • Định dạng: 24h

📅 Google Calendar:
   • Trạng thái: ❌ Chưa liên kết

[🔔 Thông báo] [⏰ Timezone] [📅 Calendar]
```

---

## ⏰ PHẦN 4: ĐỊNH DẠNG THỜI GIAN

### 4.1. Định dạng chuẩn
```
12h50 10/12/2025
14:30 10/12
9h 20/12
15/12/2025
10h30
14:45
```

### 4.2. Hỗ trợ "giờ" và "h"
```
10h = 10 giờ = 10:00
10h30 = 10 giờ 30 = 10:30
14h45 = 14 giờ 45 = 14:45
```

### 4.3. Hỗ trợ "sáng", "chiều", "tối", "trưa"
| Input | Output |
|-------|--------|
| `10h sáng` | 10:00 (AM) |
| `10 giờ sáng` | 10:00 (AM) |
| `11h trưa` | 11:00 (AM) |
| `12h trưa` | 12:00 (PM) |
| `2h chiều` | 14:00 (PM) |
| `3 giờ chiều` | 15:00 (PM) |
| `7h tối` | 19:00 (PM) |
| `8 giờ tối` | 20:00 (PM) |
| `11h đêm` | 23:00 (PM) |

**Quy tắc chi tiết:**
- **Sáng:** 5:00 - 11:59 → giữ nguyên
- **Trưa:** 11:00 - 13:00 → giữ nguyên (11h, 12h, 1h)
- **Chiều:** 12:00 - 18:00 → +12 nếu < 12
- **Tối:** 18:00 - 23:00 → +12 nếu < 12
- **Đêm:** 21:00 - 4:00 → +12 nếu < 12

### 4.4. Từ khóa tự nhiên
```
ngày mai
hôm nay
hôm qua (chỉ để xem, không tạo việc)
thứ 2, thứ 3, ... thứ 7, chủ nhật
thứ 3 tuần sau
thứ 6 tuần này
cuối tuần (= Thứ 7)
đầu tuần (= Thứ 2)
tuần sau
tuần này
tháng sau
tháng này
qua tuần (= tuần sau)
15 ngày
2 tuần
1 tháng
```

### 4.5. Từ khóa deadline
```
deadline thứ 6
hạn chót 14h mai
hạn 15/12
DL 10h sáng thứ 2
```

### 4.6. Quy tắc mặc định
| Trường hợp | Mặc định |
|------------|----------|
| Không có thời gian | Hiện tại + 24h |
| Chỉ có ngày | Giờ hiện tại + ngày đó |
| Chỉ ngày (không tháng) | Tháng/năm hiện tại |
| Chỉ ngày/tháng | Năm hiện tại |
| "ngày mai" | Ngày mai, cùng giờ hiện tại |

---

## 🛡️ PHẦN 5: XỬ LÝ LỖI VÀ VALIDATION

### 5.1. Báo lỗi cú pháp

**Lỗi tạo việc:**
```
❌ Lỗi cú pháp lệnh /taoviec

⚠️ Thiếu nội dung công việc.

✅ Cách dùng đúng:
/taoviec [nội dung] [deadline]

📝 Ví dụ:
• /taoviec Làm báo cáo tuần
• /taoviec Họp team 14h30 ngày mai
• /taoviec [!cao] Review code 10h sáng thứ 6

💡 Gõ /help taoviec để xem chi tiết
```

**Lỗi giao việc:**
```
❌ Lỗi cú pháp lệnh /giaoviec

⚠️ Thiếu người nhận việc.

✅ Cách dùng đúng:
/giaoviec @user [nội dung] [deadline]
/giaoviec [Tên người] [nội dung] [deadline]

📝 Ví dụ:
• /giaoviec @nguyenlam Làm slide
• /giaoviec Nguyễn Văn A Báo cáo 15/12

💡 Tip: Reply tin nhắn + /giaoviec để giao cho người đó

💡 Gõ /help giaoviec để xem chi tiết
```

**Lỗi ID không tồn tại:**
```
❌ Không tìm thấy công việc!

⚠️ ID "P-9999" không tồn tại hoặc đã bị xóa.

💡 Gợi ý:
• Kiểm tra lại ID công việc
• Dùng /xemviec để xem danh sách việc của bạn
• ID có dạng P-xxxx (việc cá nhân) hoặc G-xxxx (việc nhóm)
```

**Lỗi không có quyền:**
```
❌ Không có quyền thực hiện!

⚠️ Bạn không phải người tạo công việc này.

📌 Công việc: Làm slide thuyết trình
🆔 ID: P-1235
👨‍💼 Người tạo: Trần Văn B

💡 Chỉ người tạo việc mới có quyền xóa.
```

### 5.2. Validation deadline

**Deadline trong quá khứ:**
```
❌ Không thể tạo/giao việc!

⚠️ Deadline không hợp lệ!
📅 Bạn nhập: 09:00 05/12/2025
⏰ Thời gian hiện tại: 14:30 10/12/2025

❌ Deadline đã là quá khứ, vui lòng chọn thời gian trong tương lai.

💡 Gợi ý deadline:
• ngày mai
• 15/12/2025
• 10h sáng thứ 6
• 2 ngày
```

**Deadline không rõ ràng:**
```
⚠️ Xác nhận deadline

Bạn nhập: "thứ 6"
Hôm nay: Thứ 4, 11/12/2025

Bot hiểu là: Thứ 6, 13/12/2025 (2 ngày nữa)

Đúng chưa?

[✅ Đúng rồi] [❌ Thứ 6 tuần sau]
```

### 5.3. Xử lý user không có username

**Khi mention user không có @username:**
```
Bot sẽ sử dụng:
1. Telegram User ID (nội bộ)
2. Tên hiển thị (First Name + Last Name)
3. Cho phép mention bằng tên: "Nguyễn Văn A"
```

**Hiển thị trong thông báo:**
```
👤 Người nhận: Nguyễn Văn A (không có @username)
👨‍💼 Người giao: Trần Thị B
```

**Khi giao việc cho user không có username:**
```
/giaoviec Nguyễn Văn A Làm báo cáo ngày mai
```

Bot sẽ:
1. Tìm trong danh sách thành viên nhóm
2. Match theo tên hiển thị (fuzzy search)
3. Nếu có nhiều người trùng tên → hỏi xác nhận

```
⚠️ Tìm thấy nhiều người có tên tương tự:

1. Nguyễn Văn A (ID: 123456)
2. Nguyễn Văn An (ID: 789012)

Bạn muốn giao cho ai?

[1️⃣ Nguyễn Văn A] [2️⃣ Nguyễn Văn An] [❌ Hủy]
```

---

## 🔔 PHẦN 6: HỆ THỐNG ADMIN ALERT

### 6.1. Các loại alert

| Loại | Mức độ | Mô tả |
|------|--------|-------|
| Bot crash | 🚨 Critical | Bot bị crash, không phản hồi |
| Auto-restart | ⚠️ Warning | Bot tự động restart |
| DB connection error | 🚨 Critical | Không kết nối được database |
| High memory | ⚠️ Warning | RAM > 80% |
| High CPU | ⚠️ Warning | CPU > 90% |
| Disk space low | 🚨 Critical | Disk < 10% |
| Backup failed | ⚠️ Warning | Backup thất bại |
| Rate limit | ℹ️ Info | User bị rate limit |

### 6.2. Mẫu tin nhắn alert

**Bot crash:**
```
🚨 CRITICAL ALERT - BOT CRASH

🤖 Bot: TaskBot_Company
📅 Thời gian: 14:30:22 10/12/2025
❌ Lỗi: Process exited with code 1

📝 Error log:
```
TypeError: Cannot read property 'id' of undefined
    at handleMessage (/home/botpanel/bots/bot_001/handlers/task.py:125)
```

🔄 Auto-restart: Đang thực hiện...

[📄 Xem full log] [🔄 Restart thủ công]
```

**Database error:**
```
🚨 CRITICAL ALERT - DATABASE ERROR

🤖 Bot: TaskBot_Company
📅 Thời gian: 14:30:22 10/12/2025
🐘 Database: taskbot_company_db

❌ Lỗi: Connection refused

📝 Chi tiết:
psycopg2.OperationalError: could not connect to server

🔄 Đang thử kết nối lại... (1/3)

[📄 Xem log] [🔧 Kiểm tra PostgreSQL]
```

**High memory warning:**
```
⚠️ WARNING - HIGH MEMORY USAGE

🤖 Bot: TaskBot_Company
📅 Thời gian: 14:30:22 10/12/2025

💾 Memory: 85% (6.8GB / 8GB)
📊 Bot memory: 450MB

💡 Khuyến nghị:
• Kiểm tra memory leak
• Restart bot
• Tăng RAM server

[🔄 Restart bot] [📊 Chi tiết]
```

### 6.3. Health check endpoint

Bot sẽ expose HTTP endpoint để monitoring:

```
GET /health

Response:
{
  "status": "healthy",
  "bot_name": "TaskBot_Company",
  "uptime": "5d 12h 30m",
  "memory_mb": 45,
  "cpu_percent": 0.5,
  "database": "connected",
  "last_activity": "2024-12-10T14:30:00Z",
  "tasks_today": 25,
  "errors_today": 0
}
```

### 6.4. Prometheus metrics

```
# Bot metrics
bot_uptime_seconds{bot_name="TaskBot_Company"} 475200
bot_memory_bytes{bot_name="TaskBot_Company"} 47185920
bot_cpu_percent{bot_name="TaskBot_Company"} 0.5

# Task metrics
tasks_created_total{bot_name="TaskBot_Company"} 1250
tasks_completed_total{bot_name="TaskBot_Company"} 980
tasks_overdue_total{bot_name="TaskBot_Company"} 45

# Message metrics
messages_received_total{bot_name="TaskBot_Company"} 5000
messages_sent_total{bot_name="TaskBot_Company"} 8500

# Error metrics
errors_total{bot_name="TaskBot_Company",type="database"} 2
errors_total{bot_name="TaskBot_Company",type="telegram_api"} 5
```

---

## 🔧 PHẦN 7: YÊU CẦU KỸ THUẬT

### 7.1. Stack công nghệ

| Thành phần | Công nghệ |
|------------|-----------|
| Ngôn ngữ | Python 3.11+ |
| Telegram Library | python-telegram-bot v20+ |
| Database | PostgreSQL 15+ |
| Cache | Redis (optional) |
| Process Manager | PM2 |
| Web Server | Nginx (reverse proxy) |
| Task Scheduler | APScheduler |
| Migration | Alembic |
| Monitoring | Prometheus + Grafana |

### 7.2. Database Schema

#### Bảng `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),          -- Có thể NULL nếu user không có @username
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    display_name VARCHAR(500),      -- Tên hiển thị đầy đủ
    timezone VARCHAR(50) DEFAULT 'Asia/Ho_Chi_Minh',
    language VARCHAR(10) DEFAULT 'vi',
    
    -- Cài đặt thông báo
    notify_reminder BOOLEAN DEFAULT true,
    notify_weekly_report BOOLEAN DEFAULT true,
    notify_monthly_report BOOLEAN DEFAULT true,
    
    -- Google Calendar
    google_calendar_token TEXT,
    google_calendar_refresh_token TEXT,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_username ON users(username);
```

#### Bảng `groups`
```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    title VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_groups_telegram_id ON groups(telegram_id);
```

#### Bảng `group_members`
```sql
CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',  -- admin, member
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(group_id, user_id)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);
```

#### Bảng `tasks`
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    public_id VARCHAR(20) UNIQUE NOT NULL,  -- P-1234 hoặc G-500
    group_task_id VARCHAR(20),               -- G-ID nếu là việc nhóm
    
    content TEXT NOT NULL,
    description TEXT,
    
    status VARCHAR(20) DEFAULT 'pending',    -- pending, in_progress, completed
    priority VARCHAR(20) DEFAULT 'normal',   -- low, normal, high, urgent
    progress INTEGER DEFAULT 0,              -- 0-100%
    
    creator_id INTEGER REFERENCES users(id),
    assignee_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    
    deadline TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Recurring task
    is_recurring BOOLEAN DEFAULT false,
    recurring_pattern VARCHAR(100),          -- daily, weekly, monthly, custom
    recurring_config JSONB,                  -- Chi tiết cấu hình lặp
    parent_recurring_id INTEGER REFERENCES tasks(id),
    
    -- Google Calendar
    google_event_id VARCHAR(255),
    
    is_personal BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tasks_public_id ON tasks(public_id);
CREATE INDEX idx_tasks_creator ON tasks(creator_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_group ON tasks(group_id);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);
CREATE INDEX idx_tasks_status ON tasks(status);
```

#### Bảng `reminders`
```sql
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    
    remind_at TIMESTAMP NOT NULL,
    reminder_type VARCHAR(50),  -- before_deadline, after_deadline, custom
    reminder_config VARCHAR(100), -- 3d, 24h, 1h, etc.
    
    is_sent BOOLEAN DEFAULT false,
    sent_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reminders_task ON reminders(task_id);
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);
CREATE INDEX idx_reminders_is_sent ON reminders(is_sent);
```

#### Bảng `task_history`
```sql
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    
    action VARCHAR(50) NOT NULL,  -- created, assigned, status_changed, deleted, progress_updated
    old_value TEXT,
    new_value TEXT,
    note TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_history_task ON task_history(task_id);
```

#### Bảng `user_statistics`
```sql
CREATE TABLE user_statistics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    
    period_type VARCHAR(20),      -- weekly, monthly
    period_start DATE,
    period_end DATE,
    
    -- Việc đã giao
    tasks_assigned_total INTEGER DEFAULT 0,
    tasks_assigned_completed INTEGER DEFAULT 0,
    tasks_assigned_in_progress INTEGER DEFAULT 0,
    tasks_assigned_pending INTEGER DEFAULT 0,
    tasks_assigned_overdue INTEGER DEFAULT 0,
    
    -- Việc đã nhận
    tasks_received_total INTEGER DEFAULT 0,
    tasks_received_completed INTEGER DEFAULT 0,
    tasks_received_in_progress INTEGER DEFAULT 0,
    tasks_received_pending INTEGER DEFAULT 0,
    tasks_received_overdue INTEGER DEFAULT 0,
    
    -- Việc cá nhân
    tasks_personal_total INTEGER DEFAULT 0,
    tasks_personal_completed INTEGER DEFAULT 0,
    tasks_personal_in_progress INTEGER DEFAULT 0,
    tasks_personal_pending INTEGER DEFAULT 0,
    tasks_personal_overdue INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_statistics_user ON user_statistics(user_id);
CREATE INDEX idx_user_statistics_period ON user_statistics(period_type, period_start);
```

#### Bảng `deleted_tasks` (để hỗ trợ Undo)
```sql
CREATE TABLE deleted_tasks (
    id SERIAL PRIMARY KEY,
    original_task_id INTEGER,
    task_data JSONB NOT NULL,
    deleted_by INTEGER REFERENCES users(id),
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- Thời gian hết hạn undo (30 giây)
    is_restored BOOLEAN DEFAULT false
);

CREATE INDEX idx_deleted_tasks_expires ON deleted_tasks(expires_at);
```

#### Bảng `bot_config`
```sql
CREATE TABLE bot_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cấu hình mặc định
INSERT INTO bot_config (key, value, description) VALUES
('bot_name', 'Task Manager Bot', 'Tên hiển thị của bot'),
('bot_description', 'Hệ thống quản lý và nhắc việc', 'Mô tả bot'),
('support_telegram', '@support', 'Telegram hỗ trợ'),
('support_phone', '', 'Số điện thoại hỗ trợ'),
('support_email', '', 'Email hỗ trợ'),
('admin_telegram_id', '', 'ID Telegram của admin nhận alert'),
('timezone', 'Asia/Ho_Chi_Minh', 'Timezone mặc định');
```

### 7.3. Cấu trúc code bot

```
bot_template/
├── bot.py                  # Entry point
├── config.json             # Cấu hình bot
├── .env                    # Environment variables
├── requirements.txt        # Dependencies
├── ecosystem.config.js     # PM2 config
│
├── handlers/
│   ├── __init__.py
│   ├── start.py            # /start, /help, /thongtin
│   ├── task_create.py      # /taoviec
│   ├── task_assign.py      # /giaoviec
│   ├── task_view.py        # /xemviec, /viecnhom, /timviec...
│   ├── task_update.py      # /hoanthanh, /danglam, /tiendo...
│   ├── task_delete.py      # /xoa
│   ├── task_recurring.py   # /vieclaplai
│   ├── reminder.py         # /nhacviec
│   ├── deadline.py         # /deadline
│   ├── statistics.py       # /thongke
│   ├── settings.py         # /caidat
│   ├── callbacks.py        # Xử lý inline button callbacks
│   └── reactions.py        # Xử lý emoji reactions
│
├── services/
│   ├── __init__.py
│   ├── task_service.py     # Business logic cho tasks
│   ├── user_service.py     # Quản lý user, tìm user
│   ├── reminder_service.py # Logic nhắc việc
│   ├── notification.py     # Gửi thông báo
│   ├── statistics.py       # Thống kê báo cáo
│   ├── time_parser.py      # Parse thời gian tự nhiên
│   ├── calendar_service.py # Google Calendar integration
│   └── undo_service.py     # Xử lý undo delete
│
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── group.py
│   ├── task.py
│   ├── reminder.py
│   └── statistics.py
│
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── migrations/
│   │   ├── versions/
│   │   └── env.py
│   └── alembic.ini
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   ├── validators.py       # Validate input, deadline
│   ├── formatters.py       # Format tin nhắn
│   ├── keyboards.py        # Inline keyboards
│   ├── error_messages.py   # Các mẫu báo lỗi
│   └── progress_bar.py     # Tạo progress bar
│
├── scheduler/
│   ├── __init__.py
│   ├── reminder_scheduler.py
│   ├── report_scheduler.py
│   ├── recurring_scheduler.py
│   └── cleanup_scheduler.py  # Dọn dẹp deleted_tasks
│
├── monitoring/
│   ├── __init__.py
│   ├── health_check.py
│   ├── metrics.py          # Prometheus metrics
│   └── alert.py            # Gửi alert cho admin
│
└── locales/
    ├── vi.json             # Tiếng Việt
    └── en.json             # Tiếng Anh (optional)
```

### 7.4. Time Parser chi tiết

```python
# services/time_parser.py

class TimeParser:
    """
    Parse thời gian từ ngôn ngữ tự nhiên tiếng Việt
    
    Hỗ trợ:
    - 10h, 10 giờ, 10:00
    - 10h30, 10 giờ 30, 10:30
    - 10h sáng, 10 giờ sáng → 10:00
    - 2h chiều, 2 giờ chiều → 14:00
    - 7h tối → 19:00
    - 11h trưa → 11:00
    - ngày mai, hôm nay
    - thứ 2, thứ 3, ... chủ nhật
    - thứ 2 tuần sau
    - cuối tuần, đầu tuần
    - 15/12, 15/12/2025
    - deadline, hạn chót, DL
    """
    
    TIME_PATTERNS = {
        'hour_h': r'(\d{1,2})h(\d{2})?',           # 10h, 10h30
        'hour_gio': r'(\d{1,2})\s*giờ\s*(\d{2})?', # 10 giờ, 10 giờ 30
        'hour_colon': r'(\d{1,2}):(\d{2})',        # 10:30
    }
    
    PERIOD_KEYWORDS = {
        'sáng': (5, 12),     # 5:00 - 11:59
        'trưa': (11, 14),    # 11:00 - 13:59
        'chiều': (12, 18),   # 12:00 - 17:59 (cộng 12 nếu < 12)
        'tối': (18, 24),     # 18:00 - 23:59 (cộng 12 nếu < 12)
        'đêm': (21, 5),      # 21:00 - 4:59 (cộng 12 nếu < 12)
    }
    
    WEEKDAY_KEYWORDS = {
        'thứ 2': 0, 'thứ hai': 0, 't2': 0,
        'thứ 3': 1, 'thứ ba': 1, 't3': 1,
        'thứ 4': 2, 'thứ tư': 2, 't4': 2,
        'thứ 5': 3, 'thứ năm': 3, 't5': 3,
        'thứ 6': 4, 'thứ sáu': 4, 't6': 4,
        'thứ 7': 5, 'thứ bảy': 5, 't7': 5,
        'chủ nhật': 6, 'cn': 6,
    }
    
    RELATIVE_KEYWORDS = {
        'hôm nay': 0,
        'ngày mai': 1,
        'ngày kia': 2,
        'tuần sau': 7,
        'tuần này': 0,
        'tháng sau': 30,
        'qua tuần': 7,
        'cuối tuần': 'saturday',
        'đầu tuần': 'monday',
    }
```

### 7.5. Yêu cầu bảo mật

1. **Token bảo mật:**
   - Mã hóa bot token trong config
   - Sử dụng environment variables
   - Không log token

2. **Rate limiting:**
   - 30 requests/phút/user
   - Chống spam commands
   - Alert khi có user spam

3. **Validation:**
   - Validate tất cả input
   - Sanitize data trước khi lưu
   - Escape HTML trong messages
   - Check deadline không trong quá khứ

4. **Database:**
   - SSL connection cho PostgreSQL
   - User riêng cho mỗi bot database
   - Regular backup
   - Audit log

### 7.6. Yêu cầu hiệu năng

1. **Async/Await:**
   - Sử dụng async cho tất cả I/O
   - Connection pooling cho database

2. **Caching:**
   - Cache user info trong Redis
   - Cache group members

3. **Scheduler:**
   - Batch process reminders
   - Không block main thread
   - Graceful shutdown

---

## 📁 PHẦN 8: OUTPUT YÊU CẦU

Hãy tạo đầy đủ các file sau:

### 8.1. Scripts cài đặt
- [ ] `install.sh` - Script cài đặt 1 lệnh
- [ ] `uninstall.sh` - Script gỡ cài đặt
- [ ] `update.sh` - Script cập nhật hệ thống

### 8.2. BotPanel CLI
- [ ] `botpanel.sh` - CLI management tool với 11 menu
- [ ] Tất cả sub-functions

### 8.3. Bot Template
- [ ] Toàn bộ source code theo cấu trúc ở mục 7.3
- [ ] `requirements.txt`
- [ ] `config.json` mẫu
- [ ] `.env.example`

### 8.4. Database
- [ ] Schema SQL đầy đủ (tất cả bảng ở mục 7.2)
- [ ] Alembic migration scripts
- [ ] Seed data

### 8.5. Cấu hình
- [ ] PM2 ecosystem config
- [ ] Nginx config
- [ ] Prometheus config
- [ ] Grafana dashboard JSON

### 8.6. Documentation
- [ ] `README.md` - Hướng dẫn chi tiết
- [ ] `CHANGELOG.md` - Lịch sử thay đổi
- [ ] `COMMANDS.md` - Mô tả tất cả commands
- [ ] `API.md` - Health check API

---

## 🚀 PHẦN 9: HƯỚNG DẪN CHIA NHỎ

Nếu không thể tạo hết trong 1 lần, hãy chia thành các phần sau:

### Phần 1: Cài đặt và cấu trúc
```
- install.sh
- Cấu trúc thư mục
- uninstall.sh
```

### Phần 2: BotPanel CLI
```
- botpanel.sh
- Menu 1-11
- Tất cả sub-functions
```

### Phần 3: Database
```
- Schema SQL (tất cả bảng)
- Alembic setup
- Migration scripts
```

### Phần 4: Core Bot - Lệnh cơ bản
```
- bot.py (entry point)
- handlers/start.py
- handlers/task_create.py
- handlers/task_assign.py
- services/time_parser.py (quan trọng!)
- services/user_service.py
- utils/validators.py
- utils/error_messages.py
```

### Phần 5: Xem và cập nhật việc
```
- handlers/task_view.py
- handlers/task_update.py
- handlers/task_delete.py
- handlers/callbacks.py
- handlers/reactions.py
- services/undo_service.py
- utils/keyboards.py
- utils/progress_bar.py
```

### Phần 6: Nhắc việc tự động
```
- handlers/reminder.py
- handlers/deadline.py
- services/reminder_service.py
- services/notification.py
- scheduler/reminder_scheduler.py
```

### Phần 7: Thống kê báo cáo
```
- handlers/statistics.py
- services/statistics.py
- scheduler/report_scheduler.py
```

### Phần 8: Việc nhóm (G-ID, P-ID)
```
- Cập nhật task_assign.py
- Cập nhật task_view.py
- Cập nhật task_update.py
- Logic xử lý việc nhóm
```

### Phần 9: Tính năng nâng cao
```
- handlers/task_recurring.py
- scheduler/recurring_scheduler.py
- services/calendar_service.py
- handlers/settings.py
```

### Phần 10: Monitoring & Alert
```
- monitoring/health_check.py
- monitoring/metrics.py
- monitoring/alert.py
- Prometheus config
- Grafana dashboard
```

---

## 📝 GHI CHÚ QUAN TRỌNG

### Về ID công việc
- ID là duy nhất, không tái sử dụng
- Việc cá nhân/giao cho 1 người: `P-xxxx`
- Việc nhóm (ID chung): `G-xxxx`
- Mỗi người trong việc nhóm có ID riêng: `P-xxxx`

### Về user không có username
- Lưu telegram_id (bắt buộc, unique)
- Lưu display_name = first_name + last_name
- Cho phép tìm/mention bằng tên hiển thị
- Hỗ trợ reply message + command để giao việc

### Về thông báo
- Việc cá nhân: chỉ tin nhắn riêng với bot
- Việc nhóm: thông báo vào nhóm + tin nhắn riêng
- Nhắc việc: luôn gửi tin nhắn riêng
- Alert admin: tin nhắn riêng cho admin

### Về quyền hạn
- Chỉ người tạo/giao việc mới được xóa
- Người nhận có thể cập nhật trạng thái, tiến độ
- Việc trong nhóm nào thì thông báo vào nhóm đó

### Về timezone
- Mặc định: Asia/Ho_Chi_Minh (UTC+7)
- Có thể thay đổi cho từng bot
- Có thể thay đổi cho từng user

### Về backup
- Tự động backup hàng ngày lúc 3:00 AM
- Giữ 7 ngày gần nhất
- Hỗ trợ backup/restore thủ công

---

## ⚡ BẮT ĐẦU

Hãy bắt đầu với **Phần 1: Cài đặt và cấu trúc**.

Sau khi hoàn thành mỗi phần, thông báo để tôi review trước khi tiếp tục phần tiếp theo.

---

*Tài liệu này được tạo để hướng dẫn AI tạo hệ thống Bot Telegram Nhắc Việc hoàn chỉnh.*
