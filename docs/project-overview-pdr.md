# TeleTask - Project Overview & Product Development Requirements (PDR)

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Project Version:** v1.2.0
**Status:** Active Development

---

## 1. Executive Summary

TeleTask là nền tảng quản lý công việc thông minh trên Telegram, được thiết kế để giúp cá nhân và nhóm tổ chức công việc hiệu quả. Dự án tập trung vào:

- Quản lý công việc cá nhân (P-ID) và nhóm (G-ID)
- Tích hợp Google Calendar với OAuth 2.0
- Hệ thống thông báo nhắc nhở tùy chỉnh
- Báo cáo chi tiết với nhiều định dạng export
- Hỗ trợ tiếng Việt hoàn toàn với xử lý thời gian tự nhiên

---

## 2. Product Vision

### 2.1 Tầm Nhìn Dài Hạn

Trở thành nền tảng quản lý công việc cho Telegram trang bị đầy đủ các tính năng cần thiết cho cá nhân, nhóm, và doanh nghiệp.

### 2.2 Mục Tiêu Chính (OKRs)

**Objective 1: Tăng Tính Hữu Ích Cho Người Dùng**
- Phát triển đầy đủ tính năng quản lý công việc (v1.2 hoàn thành)
- Hỗ trợ các trường hợp sử dụng khác nhau (cá nhân, nhóm, dự án)
- Tối ưu hóa hiệu suất và độ ổn định

**Objective 2: Mở Rộng Khả Năng Tích Hợp**
- Google Calendar: Tích hợp hoàn toàn với OAuth 2.0 (hoàn thành v1.1)
- Webhook và REST API cho các tích hợp bên thứ ba
- Hỗ trợ các dịch vụ bên ngoài (Slack, Discord, Trello)

**Objective 3: Nâng Cấp Độ An Toàn & Bảo Mật**
- Xác minh OAuth binding (v1.2 fix)
- Mã hóa mật khẩu báo cáo với PBKDF2
- Kiểm tra đầu vào và xác thực
- Ghi chép kiểm toán

**Objective 4: Hỗ Trợ Doanh Nghiệp**
- Dashboard quản trị đa bot
- Phân tích người dùng và độ hấp dẫn
- Quản lý nhóm/tổ chức
- Báo cáo hiệu suất theo nhóm

---

## 3. Các Tính Năng Chính

### 3.1 Quản Lý Công Việc (Hoàn Thành)

| Tính Năng | Mô Tả | Trạng Thái |
|-----------|--------|-----------|
| **Tạo công việc cá nhân** | Wizard tạo việc từng bước | ✅ |
| **Giao công việc nhóm** | G-ID/P-ID system, giao cho nhiều người | ✅ |
| **Xóa hàng loạt** | Xóa nhiều công việc, hoàn tác 10 giây | ✅ |
| **Công việc lặp lại** | Daily/weekly/monthly patterns | ✅ |
| **Tìm kiếm & lọc** | Theo từ khóa, mã, loại | ✅ |
| **Cập nhật tiến độ** | Đánh dấu xong, cập nhật % | ✅ |

### 3.2 Thông Báo & Nhắc Nhở (Hoàn Thành)

| Tính Năng | Mô Tả | Trạng Thái |
|-----------|--------|-----------|
| **Nhắc mặc định** | 4 trước hạn + 2 sau hạn | ✅ |
| **Tùy chỉnh nhắc** | 24h, 1h, 30m, 5m trước hạn | ✅ |
| **Cài đặt thông báo** | Giao việc, trạng thái, báo cáo | ✅ |
| **Nguồn nhắc** | Telegram hoặc Google Calendar | ✅ |
| **Báo cáo định kỳ** | Tuần, tháng | ✅ |

### 3.3 Tích Hợp Google Calendar (Hoàn Thành)

| Tính Năng | Mô Tả | Trạng Thái |
|-----------|--------|-----------|
| **OAuth 2.0** | Xác thực an toàn với Google | ✅ |
| **Đồng bộ tự động** | Cập nhật tự động khi thay đổi | ✅ |
| **Đồng bộ thủ công** | Đồng bộ toàn bộ công việc | ✅ |
| **Lịch trình đồng bộ** | Cấu hình chu kỳ đồng bộ | ✅ |

### 3.4 Thống Kê & Báo Cáo (Hoàn Thành)

| Tính Năng | Mô Tả | Trạng Thái |
|-----------|--------|-----------|
| **Thống kê tổng** | Tất cả, tuần, tháng | ✅ |
| **Công việc trễ hạn** | Theo dõi deadline miss | ✅ |
| **Export báo cáo** | PDF, Excel, CSV | ✅ |
| **Bảo vệ báo cáo** | PBKDF2 mã hóa mật khẩu | ✅ |

### 3.5 Giao Diện & Trải Nghiệm (Hoàn Thành)

| Tính Năng | Mô Tả | Trạng Thái |
|-----------|--------|-----------|
| **Menu tương tác** | Nút bấm tính năng chính | ✅ |
| **Danh mục việc** | Danh sách phân loại | ✅ |
| **Định dạng thời gian** | "ngày mai 14h30", "thứ 6 15h" | ✅ |
| **Countdown hoàn tác** | 10 giây để khôi phục | ✅ |
| **Hỗ trợ Tiếng Việt** | Giao diện & văn bản hoàn toàn | ✅ |

---

## 4. Công Nghệ & Stack

### 4.1 Backend

- **Python 3.11+** - Ngôn ngữ lập trình chính
- **python-telegram-bot** - Framework Telegram Bot
- **asyncio** - Xử lý đơn luồng không chặn
- **SQLAlchemy 2.0** - ORM để truy cập database
- **asyncpg** - Driver PostgreSQL bất đồng bộ
- **APScheduler** - Lập lịch và cron jobs
- **Google OAuth 2.0** - Xác thực Google

### 4.2 Database

- **PostgreSQL 15+** - Cơ sở dữ liệu chính
- **Alembic** - Quản lý database migrations
- **JSONB** - Lưu cấu hình phức tạp

### 4.3 DevOps & Deployment

- **PM2** - Quản lý tiến trình Node.js/Python
- **Nginx** - Web server & reverse proxy
- **Bash scripts** - Automation (install, update, uninstall)
- **Systemd** - Quản lý service Linux

### 4.4 Development

- **Git** - Version control
- **repomix** - Tổng hợp codebase
- **Black** - Code formatter (khuyến nghị)

---

## 5. Kiến Trúc Hệ Thống

### 5.1 Sơ Đồ Thành Phần

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Users                       │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌────────────────────┐
│ Telegram Bot API │      │ Google Calendar    │
│ (python-telegram-bot)   │     OAuth 2.0      │
└────────┬─────────┘      └────────┬───────────┘
         │                         │
         └────────────┬────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   TeleTask Bot Core        │
        │  (src/templates/bot_template)
        │                            │
        │ ┌──────────────────────┐  │
        │ │ Handlers (14 modules)│  │
        │ ├──────────────────────┤  │
        │ │ Services (10 modules)│  │
        │ ├──────────────────────┤  │
        │ │ Scheduler & Jobs     │  │
        │ ├──────────────────────┤  │
        │ │ Utils & Formatters   │  │
        │ └──────────────────────┘  │
        └────────────┬───────────────┘
                     │
        ┌────────────▼────────────┐
        │   PostgreSQL 15+        │
        │  (9 Database Tables)    │
        └─────────────────────────┘
```

### 5.2 Cấu Trúc Thư Mục Chính

```
teletask/
├── src/
│   ├── templates/bot_template/
│   │   ├── handlers/           (14 handler modules)
│   │   ├── services/           (10 service modules)
│   │   ├── database/           (Models & migrations)
│   │   ├── scheduler/          (Job scheduling)
│   │   ├── monitoring/         (Health & metrics)
│   │   ├── utils/              (Utilities)
│   │   ├── config/             (Settings)
│   │   └── static/             (Static files)
│   ├── scripts/                (Utility scripts)
│   └── botpanel.sh             (CLI management tool)
├── install.sh                  (1,280 lines - auto setup)
├── update.sh                   (Bot/system updates)
├── uninstall.sh                (Safe removal)
├── docs/                       (Documentation)
└── README.md                   (Project overview)
```

---

## 6. Cơ Sở Dữ Liệu

### 6.1 Các Bảng Chính

| Bảng | Mục Đích | Mô Tả |
|------|---------|-------|
| **users** | Tài khoản người dùng | Telegram ID, settings, Google OAuth |
| **groups** | Thông tin nhóm | Telegram group metadata |
| **group_members** | Thành viên nhóm | Liên kết users - groups |
| **tasks** | Công việc | Task data, deadline, status |
| **reminders** | Nhắc nhở | Reminder schedule & settings |
| **task_history** | Lịch sử thay đổi | Audit trail cho công việc |
| **user_statistics** | Thống kê người dùng | Aggregate stats theo tuần/tháng |
| **deleted_tasks_undo** | Công việc xóa | Cho phép hoàn tác 10 giây |
| **bot_config** | Cấu hình bot | Settings toàn cục |

### 6.2 Phiên Bản Migrations

| Phiên Bản | Ngày | Thay Đổi |
|-----------|------|---------|
| 20241214_0001 | Dec 14, 2024 | Schema ban đầu |
| 20241215_0002 | Dec 15, 2024 | Recurring tasks |
| 20251216_0004 | Dec 16, 2025 | Export & reports |
| 20251217_0001 | Dec 17, 2025 | Notification settings |
| 20251217_0007 | Dec 17, 2025 | User reminder preferences |
| 20251216_0005 | Dec 16, 2025 | Reminder source |
| 20251216_0006 | Dec 16, 2025 | Calendar sync interval |
| 20251215_0003 | Dec 15, 2024 | Group tasks |

---

## 7. Yêu Cầu Chức Năng (Functional Requirements)

### 7.1 Đã Hoàn Thành (v1.0 - v1.2)

- [x] CRUD công việc cá nhân (P-ID)
- [x] CRUD công việc nhóm (G-ID)
- [x] Hệ thống giao việc với xác thực
- [x] Wizard tạo việc tương tác
- [x] Nhắc nhở tự động với APScheduler
- [x] Xóa soft với khôi phục 10 giây
- [x] Công việc lặp lại (recurring)
- [x] Tích hợp Google Calendar OAuth 2.0
- [x] Báo cáo thống kê (tuần, tháng, tổng)
- [x] Export PDF/Excel/CSV với mã hóa PBKDF2
- [x] Cài đặt thông báo & múi giờ
- [x] Tìm kiếm & lọc công việc
- [x] BotPanel CLI cho quản lý bot

### 7.2 Đang Hoạch Định (v1.3 - v2.0)

- [ ] Task priority levels
- [ ] Task categories/tags
- [ ] Task dependencies
- [ ] Subtasks support
- [ ] Team/workspace features
- [ ] Role-based access control
- [ ] Admin dashboard web
- [ ] REST API & webhooks
- [ ] Slack/Discord integration
- [ ] Multi-bot management

---

## 8. Yêu Cầu Phi Chức Năng (Non-Functional Requirements)

### 8.1 Hiệu Suất

- **Response Time:** < 2 giây cho các hoạt động CRUD
- **Throughput:** 1000+ concurrent users
- **Database Query:** < 500ms cho queries phức tạp
- **Memory:** < 500MB cho bot instance

### 8.2 Bảo Mật

- OAuth 2.0 cho Google Calendar
- PBKDF2-SHA256 với 100,000 iterations cho mật khẩu báo cáo
- Input validation trên tất cả endpoints
- SQL injection prevention thông qua ORM
- Binding OAuth callback đến 127.0.0.1 (localhost)

### 8.3 Tính Sẵn Sàng

- Uptime target: 99%
- Graceful shutdown với signal handling
- Database connection pooling
- Error logging & monitoring

### 8.4 Tính Bảo Trì

- Code trong Python 3.11+ (type hints)
- Modular architecture (handlers, services, utils)
- Database versioning thông qua Alembic
- Comprehensive logging
- Clear documentation

### 8.5 Khả Năng Mở Rộng

- Modular handler system để thêm commands
- Service layer tách biệt business logic
- Database connection pooling
- Scheduler cho background jobs

---

## 9. Hạn Chế & Giả Định

### 9.1 Hạn Chế Kỹ Thuật

- Chỉ hỗ trợ PostgreSQL 15+
- Telegram Bot API rate limits (30 messages/second)
- Google Calendar API quotas
- Python 3.11+ bắt buộc

### 9.2 Giả Định

- Người dùng có tài khoản Telegram
- PostgreSQL instance sẵn sàng
- Google OAuth credentials có sẵn
- Nginx hoặc reverse proxy cho OAuth callback

---

## 10. Thành Công & Metrics

### 10.1 Tiêu Chí Chấp Nhận

- [x] Tất cả 25+ commands hoạt động đúng
- [x] Thống kê chính xác trong 99% trường hợp
- [x] Exports không bị lỗi
- [x] Google Calendar sync đồng bộ
- [x] Reminder gửi đúng thời gian

### 10.2 Metrics Theo Dõi

- Số lượng users hoạt động
- Số lượng tasks được tạo/hoàn thành/trễ hạn
- Uptime & error rates
- Average response time
- Google Calendar sync success rate

---

## 11. Lộ Trình Phiên Bản

### 11.1 Hiện Tại (v1.2.x)

- Bot core hoàn thành
- Google Calendar fully integrated
- Notification system matured
- Security fixes (v1.2.0+)

### 11.2 Sắp Tới (v1.3 - v2.0)

**v1.3:** Task priorities, categories, dependencies
**v1.4:** Team features, collaboration
**v1.5:** Admin dashboard, monitoring
**v1.6:** External integrations (Slack, Discord)
**v2.0:** Enterprise features, multi-tenancy

---

## 12. Liên Hệ & Hỗ Trợ

**Repository:** https://github.com/haduyson/teletask
**Issues:** https://github.com/haduyson/teletask/issues
**Author:** Ha Duy Son (@haduyson)
**License:** MIT

---

**End of Document**
