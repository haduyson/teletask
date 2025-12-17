# TeleTask Bot

Bot quản lý công việc qua Telegram - Hỗ trợ tiếng Việt hoàn toàn.

## Giới thiệu

TeleTask là hệ thống quản lý công việc thông minh cho Telegram, giúp bạn:
- Tạo và theo dõi công việc cá nhân
- Giao việc cho thành viên trong nhóm
- Nhận thông báo nhắc nhở tự động
- Xem báo cáo thống kê tiến độ
- Đồng bộ với Google Calendar

## Cài đặt nhanh

```bash
curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash
```

Sau khi cài đặt, quản lý bot bằng lệnh `botpanel`:

```bash
botpanel status    # Xem trạng thái
botpanel logs      # Xem logs
botpanel restart   # Restart bot
botpanel help      # Xem tất cả lệnh
```

📖 [Hướng dẫn cài đặt chi tiết](installation.md)

## Tính năng chính

### Quản lý công việc
- **Wizard tạo việc** - Tạo việc từng bước với nút bấm hướng dẫn
- **Giao việc nhóm** - Giao việc cho nhiều người (hệ thống G-ID/P-ID)
- **Xóa hàng loạt** - Xóa tất cả việc với nút hoàn tác 10 giây
- **Tìm kiếm** - Tìm việc theo từ khóa hoặc mã việc
- **Lọc việc** - Lọc theo loại: Cá nhân (P-ID) / Nhóm (G-ID)

### Giao diện người dùng
- **Menu tương tác** (`/menu`) - Các nút bấm tính năng
- **Danh mục việc** (`/xemviec`) - Menu phân loại việc
- **Nhãn in đậm** - Thông tin việc dễ đọc
- **Đếm ngược hoàn tác** - 10 giây để khôi phục việc đã xóa

### Thống kê & Báo cáo
- **Thống kê tổng hợp** - Tuần, tháng, tổng thể
- **Việc trễ hạn** - Theo dõi và lọc theo tháng
- **Xuất báo cáo** - PDF/Excel/CSV với chọn khoảng thời gian

### Nhắc nhở & Cài đặt
- **Cài đặt thông báo** (`/caidat`) - Thông báo giao việc, trạng thái, nhắc việc, báo cáo
- **Cài đặt múi giờ** (`/caidat`) - Chọn múi giờ hiển thị
- **Nhắc tùy chỉnh** - Đặt nhắc theo thời gian cụ thể (24h, 1h, 30p, 5p)
- **Nguồn nhắc** - Chọn Telegram, Google Calendar, hoặc cả hai

### Tích hợp Google Calendar
- **Kết nối** (`/lichgoogle`) - Đăng nhập Google OAuth 2.0
- **Chế độ đồng bộ** - Tự động khi có thay đổi hoặc thủ công
- **Đồng bộ ngay** - Đồng bộ tất cả việc vào lịch

## Lệnh Bot

### Tạo việc
| Lệnh | Mô tả |
|------|-------|
| `/taoviec` | Tạo việc cá nhân (wizard) |
| `/giaoviec @user <nội dung>` | Giao việc cho người khác |
| `/vieclaplai <nội dung> <lịch>` | Tạo việc lặp lại |

### Xem việc
| Lệnh | Mô tả |
|------|-------|
| `/menu` | Menu tính năng (nút bấm) |
| `/xemviec` | Danh mục việc |
| `/xemviec <mã>` | Chi tiết việc |
| `/viecdagiao` | Việc đã giao |
| `/viecdanhan` | Việc được giao |
| `/timviec <từ khóa>` | Tìm kiếm |

### Cập nhật
| Lệnh | Mô tả |
|------|-------|
| `/xong <mã>` | Hoàn thành việc |
| `/tiendo <mã> <%>` | Cập nhật tiến độ |
| `/xoa <mã>` | Xóa việc (hoàn tác 10s) |
| `/xoanhieu <mã1,mã2,...>` | Xóa nhiều việc |
| `/xoatatca` | Xóa tất cả việc |

### Nhắc việc
| Lệnh | Mô tả |
|------|-------|
| `/nhacviec <mã> <thời gian>` | Đặt nhắc |
| `/xemnhac` | Xem nhắc đã đặt |
| `/caidat` | Cài đặt thông báo, múi giờ |

### Thống kê
| Lệnh | Mô tả |
|------|-------|
| `/thongke` | Thống kê tổng hợp |
| `/thongketuan` | Thống kê tuần |
| `/thongkethang` | Thống kê tháng |
| `/viectrehan` | Việc trễ hạn |
| `/export` | Xuất báo cáo |

### Khác
| Lệnh | Mô tả |
|------|-------|
| `/start` | Bắt đầu sử dụng |
| `/help` | Hướng dẫn |
| `/thongtin` | Thông tin tài khoản |
| `/lichgoogle` | Kết nối và cài đặt Google Calendar |

## Hệ thống mã việc

| Mã | Loại | Mô tả |
|----|------|-------|
| `P-xxx` | Cá nhân | Việc một người |
| `G-xxx` | Nhóm | Việc nhiều người (cha) |

## Công nghệ

- **Python 3.10+** - Ngôn ngữ lập trình
- **python-telegram-bot** - Thư viện Telegram Bot
- **PostgreSQL** - Cơ sở dữ liệu
- **Alembic** - Quản lý migration
- **APScheduler** - Lập lịch nhắc nhở
- **Google OAuth 2.0** - Xác thực Calendar

## Tài liệu

- **Hướng dẫn sử dụng:** https://teletask.haduyson.com
- **Release Notes:** [docs/release-notes-2025-12-17.md](docs/release-notes-2025-12-17.md)
- **Project Roadmap:** [docs/project-roadmap.md](docs/project-roadmap.md)

## Phiên bản

- **v1.2.0** - 17/12/2025 - Google Calendar settings, notification preferences, bot slug naming
- **v1.1.1** - 17/12/2025 - Automated installation script
- **v1.1.0** - 16/12/2025 - Reminder source & Google Calendar sync
- **v1.0.0** - 16/12/2025 - Phiên bản đầu tiên

## Tác giả

Ha Duy Son - [@haduyson](https://github.com/haduyson)

## Giấy phép

MIT License
