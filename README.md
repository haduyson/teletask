# TeleTask Bot

Bot Telegram quản lý công việc bằng tiếng Việt, hỗ trợ cá nhân và nhóm. Tạo việc, đặt nhắc nhở, đồng bộ Google Calendar, xuất báo cáo - tất cả trong Telegram.

**Trạng thái**: Hoạt động | **Ngôn ngữ**: Python 3.11 | **Database**: PostgreSQL

---

## Cài Đặt Nhanh

### Yêu Cầu
- Ubuntu 22.04/24.04 (khuyến nghị)
- Python 3.11+
- PostgreSQL 12+
- Bot token từ @BotFather

### Cài Đặt Tự Động (Khuyến Nghị)

```bash
# 1. Clone repository
git clone <repo-url>
cd hasontechtask

# 2. Chạy installer với domain và email
sudo ./install.sh --domain teletask.example.com --email admin@example.com

# 3. Cấu hình bot token
nano .env
# Điền BOT_TOKEN và ADMIN_IDS

# 4. Khởi động bot
pm2 start ecosystem.config.js
pm2 save
```

**Installer tự động cài đặt:**
- Python 3.11 virtual environment
- PostgreSQL database
- Nginx reverse proxy với SSL (Let's Encrypt)
- PM2 process manager
- Cấu hình môi trường

**Tùy chọn Installer:**
```
./install.sh --help              # Xem tất cả tùy chọn
./install.sh --skip-nginx        # Bỏ qua nginx (dùng proxy có sẵn)
./install.sh --skip-db           # Bỏ qua database (dùng DB bên ngoài)
./install.sh --skip-ssl          # Bỏ qua SSL (cho test local)
```

### Cài Đặt Thủ Công

```bash
# 1. Clone và thiết lập
git clone <repo-url>
cd teletask
python3.11 -m venv venv
source venv/bin/activate

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Cấu hình môi trường
cp .env.example .env
nano .env  # Điền BOT_TOKEN và DATABASE_URL

# 4. Kiểm tra và khởi tạo database
python scripts/db_setup.py --check    # Kiểm tra kết nối
python scripts/db_setup.py            # Chạy migrations

# 5. Khởi động bot
python bot.py

# Hoặc dùng PM2 cho production
pm2 start ecosystem.config.js
pm2 save
```

### Database Setup Script

```bash
# Kiểm tra kết nối database
python scripts/db_setup.py --check

# Chạy tất cả migrations
python scripts/db_setup.py

# Reset database (XÓA TẤT CẢ DATA!)
python scripts/db_setup.py --reset
```

---

## Biến Môi Trường

**Bắt buộc:**
- `BOT_TOKEN`: Token từ @BotFather
- `DATABASE_URL`: Connection string PostgreSQL (asyncpg driver)

**Tùy chọn:**
- `BOT_NAME`: Tên hiển thị bot (mặc định: TeleTask Bot)
- `BOT_DOMAIN`: Domain cho giao diện web (vd: https://teletask.example.com)
- `TIMEZONE`: Múi giờ mặc định (mặc định: Asia/Ho_Chi_Minh)
- `ADMIN_IDS`: ID Telegram admin, phân cách bằng dấu phẩy
- `HEALTH_PORT`: Port health check (mặc định: 8080)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (mặc định: INFO)
- `GOOGLE_CALENDAR_ENABLED`: true/false (mặc định: false)
- `ENCRYPTION_KEY`: Khóa mã hóa token OAuth

**Ví dụ .env:**
```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/teletask
BOT_NAME=TeleTask Bot
BOT_DOMAIN=https://teletask.example.com
TIMEZONE=Asia/Ho_Chi_Minh
ADMIN_IDS=123456789,987654321
LOG_LEVEL=INFO
```

---

## Các Lệnh Chính

| Lệnh | Mô tả | Loại |
|------|-------|------|
| `/taoviec` | Tạo việc mới (wizard) | Cá nhân/Nhóm |
| `/xemviec` | Xem danh sách việc | Cá nhân/Nhóm |
| `/xong` | Đánh dấu hoàn thành | Cá nhân/Nhóm |
| `/danglam` | Đặt trạng thái đang làm | Cá nhân/Nhóm |
| `/tiendo` | Cập nhật tiến độ (%) | Cá nhân/Nhóm |
| `/giaoviec` | Giao việc cho người khác | Chỉ nhóm |
| `/xoa` | Xóa việc (30s hoàn tác) | Cá nhân/Nhóm |
| `/nhacviec` | Đặt nhắc nhở | Cá nhân/Nhóm |
| `/vieclaplai` | Tạo việc lặp lại | Cá nhân/Nhóm |
| `/thongke` | Xem thống kê | Cá nhân/Nhóm |
| `/export` | Xuất báo cáo (CSV/XLSX/PDF) | Cá nhân/Nhóm |
| `/lichgoogle` | Kết nối Google Calendar | Chỉ cá nhân |
| `/caidat` | Cài đặt thông báo, múi giờ | Chỉ cá nhân |

---

## Kiến Trúc

```
Telegram ↔ TeleTask Bot (async/await)
          ├─ 15 Handler Modules (commands & callbacks)
          ├─ 11 Service Modules (business logic)
          ├─ 10 Database Models (SQLAlchemy ORM)
          ├─ APScheduler (nhắc nhở, báo cáo)
          └─ Monitoring (health checks, alerts)
             ↓
          PostgreSQL (async pool, 2-10 connections)
          Google Calendar API (tùy chọn)
```

---

## Cấu Trúc Thư Mục

```
hasontechtask/
├── bot.py                    # Entry point
├── install.sh                # Installer tự động
├── requirements.txt          # Dependencies
├── ecosystem.config.js       # PM2 configuration
│
├── config/
│   └── settings.py           # Cấu hình môi trường
│
├── database/
│   ├── models.py             # 10 SQLAlchemy models
│   ├── connection.py         # Async connection pool
│   └── migrations/           # Alembic migrations
│
├── handlers/                 # 15 command handlers
├── services/                 # 11 business logic modules
├── scheduler/                # Reminder & report schedulers
├── monitoring/               # Health check & alerts
├── utils/                    # Helpers: formatters, keyboards
├── static/                   # HTML instruction files
└── docs/                     # Documentation
```

---

## Monitoring

### Health Check & Giao Diện Web
```bash
# Health check endpoint
curl https://your-domain.com/health

# Trang hướng dẫn
https://your-domain.com/              # Trang chính
https://your-domain.com/user-guide.html # Hướng dẫn chi tiết
https://your-domain.com/config.json     # Cấu hình bot
```

### Xem Logs
```bash
pm2 logs hasontechtask          # Xem logs
pm2 restart hasontechtask       # Khởi động lại
pm2 stop hasontechtask          # Dừng bot
```

---

## Triển Khai Production

### Checklist
- [ ] BOT_TOKEN đã cấu hình
- [ ] DATABASE_URL trỏ đúng database
- [ ] ADMIN_IDS đã thiết lập
- [ ] SSL/HTTPS hoạt động
- [ ] Health check passing
- [ ] PM2 startup configured (`pm2 startup && pm2 save`)

### Backup Database
```bash
pg_dump -U postgres teletask_db > backup.sql
```

---

## Xử Lý Sự Cố

### Lỗi Kết Nối Database
```bash
sudo service postgresql status    # Kiểm tra PostgreSQL
psql $DATABASE_URL               # Test kết nối
```

### Bot Không Phản Hồi
```bash
pm2 logs hasontechtask           # Xem lỗi
pm2 restart hasontechtask        # Khởi động lại
```

### SSL Không Hoạt Động
```bash
sudo certbot renew --dry-run     # Test renewal
sudo nginx -t                    # Test nginx config
```

---

## Tài Liệu Chi Tiết

Xem thêm trong thư mục `./docs/`:
- `project-overview-pdr.md` - Tổng quan dự án
- `codebase-summary.md` - Cấu trúc code
- `code-standards.md` - Quy chuẩn code
- `system-architecture.md` - Kiến trúc hệ thống

---

## English Summary

TeleTask is a Vietnamese-language task management Telegram bot. For English documentation, see files in `./docs/` directory.

**Quick Install:**
```bash
sudo ./install.sh --domain your-domain.com --email admin@your-domain.com
nano .env  # Set BOT_TOKEN and ADMIN_IDS
pm2 start ecosystem.config.js
```

---

**Cập nhật lần cuối**: 2025-12-19
**Phiên bản**: 1.0
