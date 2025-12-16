# Hướng dẫn cài đặt TeleTask Bot

Tài liệu hướng dẫn cài đặt TeleTask Bot trên máy chủ Ubuntu/Debian.

---

## Cài đặt nhanh (1 lệnh)

Chỉ cần chạy 1 lệnh duy nhất để cài đặt toàn bộ hệ thống:

```bash
curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash
```

**Yêu cầu:**
- Ubuntu 20.04+ hoặc Debian 11+
- Quyền root (sudo)
- Bot Token từ [@BotFather](https://t.me/BotFather)

**Script sẽ tự động cài đặt:**
- PostgreSQL database
- Python 3.11 + virtual environment
- Node.js + PM2
- Tất cả dependencies
- Database migrations
- Công cụ quản lý `botpanel`

**Sau khi cài xong, quản lý bot bằng lệnh `botpanel`:**

```bash
botpanel status    # Xem trạng thái
botpanel logs      # Xem logs
botpanel restart   # Restart bot
botpanel config    # Sửa cấu hình
botpanel help      # Xem tất cả lệnh
```

---

## Mục lục

- [Cài đặt nhanh (1 lệnh)](#cài-đặt-nhanh-1-lệnh)
- [Quản lý với botpanel CLI](#quản-lý-với-botpanel-cli)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt thủ công](#cài-đặt-thủ-công)
  - [1. Chuẩn bị máy chủ](#1-chuẩn-bị-máy-chủ)
  - [2. Cài đặt PostgreSQL](#2-cài-đặt-postgresql)
  - [3. Cài đặt Python](#3-cài-đặt-python)
  - [4. Tạo Telegram Bot](#4-tạo-telegram-bot)
  - [5. Clone và cấu hình](#5-clone-và-cấu-hình)
  - [6. Cài đặt dependencies](#6-cài-đặt-dependencies)
  - [7. Khởi tạo database](#7-khởi-tạo-database)
  - [8. Chạy bot](#8-chạy-bot)
  - [9. Quản lý với PM2](#9-quản-lý-với-pm2)
- [Cấu hình nâng cao](#cấu-hình-nâng-cao)
  - [Google Calendar](#google-calendar-tùy-chọn)
  - [Nginx Reverse Proxy](#nginx-reverse-proxy-tùy-chọn)
- [Khắc phục sự cố](#khắc-phục-sự-cố)
- [Backup & Restore](#backup--restore)

---

## Quản lý với botpanel CLI

Sau khi cài đặt, sử dụng lệnh `botpanel` để quản lý bot:

### Quản lý Bot

| Lệnh | Mô tả |
|------|-------|
| `botpanel start` | Khởi động bot |
| `botpanel stop` | Dừng bot |
| `botpanel restart` | Restart bot |
| `botpanel status` | Xem trạng thái |
| `botpanel logs` | Xem logs (live) |
| `botpanel logs-err` | Xem error logs |

### Database

| Lệnh | Mô tả |
|------|-------|
| `botpanel db-status` | Kiểm tra kết nối database |
| `botpanel db-migrate` | Chạy migrations |
| `botpanel db-backup` | Backup database |
| `botpanel db-restore` | Restore từ backup |

### Cấu hình

| Lệnh | Mô tả |
|------|-------|
| `botpanel config` | Sửa file .env |
| `botpanel token` | Đổi bot token |
| `botpanel gcal` | Cấu hình Google Calendar |

### Bảo trì

| Lệnh | Mô tả |
|------|-------|
| `botpanel update` | Cập nhật phiên bản mới |
| `botpanel deps` | Cài lại dependencies |
| `botpanel clean` | Dọn logs cũ |
| `botpanel info` | Xem thông tin hệ thống |

### Ví dụ sử dụng

```bash
# Kiểm tra trạng thái bot
botpanel status

# Xem logs real-time
botpanel logs

# Backup database trước khi update
botpanel db-backup

# Cập nhật bot
botpanel update

# Cấu hình Google Calendar
botpanel gcal
```

---

## Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|------------|---------------------|
| Ubuntu/Debian | 20.04+ / 11+ |
| Python | 3.10+ |
| PostgreSQL | 13+ |
| Node.js | 18+ (cho PM2) |
| RAM | 1GB+ |
| Disk | 10GB+ |

---

## Cài đặt thủ công

Nếu bạn muốn cài đặt từng bước thủ công, làm theo hướng dẫn bên dưới.

### 1. Chuẩn bị máy chủ

#### Cập nhật hệ thống

```bash
sudo apt update && sudo apt upgrade -y
```

### Cài đặt các gói cần thiết

```bash
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release
```

### Cấu hình múi giờ

```bash
sudo timedatectl set-timezone Asia/Ho_Chi_Minh
timedatectl
```

---

## 2. Cài đặt PostgreSQL

### Cài đặt PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
```

### Khởi động và kích hoạt service

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Tạo database và user

```bash
# Đăng nhập PostgreSQL
sudo -u postgres psql
```

Trong psql shell:

```sql
-- Tạo user cho bot
CREATE USER botpanel WITH PASSWORD 'your_secure_password';

-- Tạo database
CREATE DATABASE teletask_db OWNER botpanel;

-- Cấp quyền
GRANT ALL PRIVILEGES ON DATABASE teletask_db TO botpanel;

-- Thoát
\q
```

### Kiểm tra kết nối

```bash
PGPASSWORD=your_secure_password psql -h localhost -U botpanel -d teletask_db -c "SELECT version();"
```

---

## 3. Cài đặt Python

### Cài đặt Python 3.11

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### Kiểm tra phiên bản

```bash
python3.11 --version
```

---

## 4. Tạo Telegram Bot

1. Mở Telegram, tìm [@BotFather](https://t.me/BotFather)
2. Gửi lệnh `/newbot`
3. Đặt tên bot (ví dụ: `TeleTask Bot`)
4. Đặt username bot (ví dụ: `teletask_bot`)
5. Lưu lại **Bot Token** (dạng `123456789:ABCdefGHI...`)

### Cấu hình bot (tùy chọn)

Trong BotFather:

```
/setdescription - Mô tả bot
/setabouttext - Giới thiệu
/setuserpic - Ảnh đại diện
```

---

## 5. Clone và cấu hình

### Tạo thư mục và user (khuyên dùng)

```bash
# Tạo user riêng cho bot
sudo useradd -m -s /bin/bash botpanel
sudo mkdir -p /home/botpanel/bots/bot_001
sudo mkdir -p /home/botpanel/logs
sudo chown -R botpanel:botpanel /home/botpanel
```

### Clone source code

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    git clone https://github.com/haduyson/teletask.git .
"
```

Hoặc copy từ template:

```bash
sudo cp -r /path/to/teletask/src/templates/bot_template/* /home/botpanel/bots/bot_001/
sudo chown -R botpanel:botpanel /home/botpanel/bots/bot_001
```

### Tạo file .env

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    cp .env.example .env
"
```

### Chỉnh sửa cấu hình

```bash
sudo -u botpanel nano /home/botpanel/bots/bot_001/.env
```

Nội dung file `.env`:

```env
#-------------------------------------------------------------------------------
# Telegram Bot
#-------------------------------------------------------------------------------
BOT_TOKEN=your_telegram_bot_token_from_botfather
BOT_NAME=TeleTask

#-------------------------------------------------------------------------------
# Database
#-------------------------------------------------------------------------------
DATABASE_URL=postgresql://botpanel:your_secure_password@localhost:5432/teletask_db

# Connection pool settings
DB_POOL_MIN=2
DB_POOL_MAX=10

#-------------------------------------------------------------------------------
# Timezone
#-------------------------------------------------------------------------------
TZ=Asia/Ho_Chi_Minh

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=/home/botpanel/logs/teletask.log

#-------------------------------------------------------------------------------
# Admin (Telegram user IDs, dấu phẩy phân cách)
#-------------------------------------------------------------------------------
ADMIN_IDS=123456789

#-------------------------------------------------------------------------------
# Features (tùy chọn)
#-------------------------------------------------------------------------------
# Google Calendar
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
OAUTH_CALLBACK_PORT=8081

# Monitoring
METRICS_ENABLED=false
HEALTH_PORT=8080
```

---

## 6. Cài đặt dependencies

### Tạo virtual environment

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"
```

### Các packages chính

| Package | Mô tả |
|---------|-------|
| python-telegram-bot | Framework Telegram Bot |
| asyncpg | PostgreSQL async driver |
| sqlalchemy | ORM |
| alembic | Database migrations |
| APScheduler | Lập lịch nhắc nhở |
| python-dotenv | Đọc file .env |
| aiohttp | HTTP client async |
| pytz | Timezone support |

---

## 7. Khởi tạo database

### Chạy migrations

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    source venv/bin/activate
    alembic upgrade head
"
```

### Kiểm tra trạng thái migration

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    source venv/bin/activate
    alembic current
"
```

### Các bảng database

| Bảng | Mô tả |
|------|-------|
| users | Người dùng Telegram |
| groups | Nhóm Telegram |
| group_members | Quan hệ user-group |
| tasks | Công việc |
| reminders | Lịch nhắc |
| task_history | Lịch sử thay đổi |
| user_statistics | Thống kê người dùng |
| deleted_tasks_undo | Buffer hoàn tác |
| bot_config | Cấu hình bot |

---

## 8. Chạy bot

### Chạy trực tiếp (test)

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    source venv/bin/activate
    python bot.py
"
```

Bot sẽ hiển thị:

```
============================================================
TeleTask Bot Starting...
============================================================
Bot Name: TeleTask
Timezone: Asia/Ho_Chi_Minh
Log Level: INFO
Connecting to database...
Database connected
Handlers registered
Reminder scheduler started
Report scheduler started
Bot initialization complete
Starting polling...
Bot is running. Press Ctrl+C to stop.
```

### Dừng bot

Nhấn `Ctrl+C`

---

## 9. Quản lý với PM2

PM2 giúp chạy bot liên tục, tự restart khi crash.

### Cài đặt Node.js và PM2

```bash
# Cài Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Cài PM2
sudo npm install -g pm2
```

### Tạo file ecosystem

```bash
sudo -u botpanel nano /home/botpanel/bots/bot_001/ecosystem.config.js
```

Nội dung:

```javascript
module.exports = {
  apps: [{
    name: 'teletask-bot',
    script: '/home/botpanel/bots/bot_001/venv/bin/python',
    args: '/home/botpanel/bots/bot_001/bot.py',
    cwd: '/home/botpanel/bots/bot_001',
    interpreter: 'none',
    env: {
      PATH: '/home/botpanel/bots/bot_001/venv/bin:' + process.env.PATH
    },
    max_memory_restart: '500M',
    restart_delay: 5000,
    autorestart: true,
    watch: false,
    log_file: '/home/botpanel/logs/teletask-combined.log',
    out_file: '/home/botpanel/logs/teletask-out.log',
    error_file: '/home/botpanel/logs/teletask-error.log',
    time: true
  }]
};
```

### Khởi động bot với PM2

```bash
cd /home/botpanel/bots/bot_001
pm2 start ecosystem.config.js
```

### Các lệnh PM2 hữu ích

```bash
# Xem trạng thái
pm2 status

# Xem logs
pm2 logs teletask-bot

# Restart bot
pm2 restart teletask-bot

# Dừng bot
pm2 stop teletask-bot

# Xóa khỏi PM2
pm2 delete teletask-bot

# Lưu cấu hình để tự chạy khi reboot
pm2 save
pm2 startup
```

---

## 10. Cấu hình Google Calendar (Tùy chọn)

### Bước 1: Tạo project Google Cloud

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới
3. Bật **Google Calendar API**:
   - Menu > APIs & Services > Library
   - Tìm "Google Calendar API"
   - Click **Enable**

### Bước 2: Tạo OAuth credentials

1. Menu > APIs & Services > Credentials
2. Click **Create Credentials** > **OAuth client ID**
3. Application type: **Web application**
4. Name: `TeleTask Bot`
5. Authorized redirect URIs:
   ```
   https://yourdomain.com/oauth/callback
   ```
6. Click **Create**
7. Lưu **Client ID** và **Client Secret**

### Bước 3: Cấu hình OAuth consent screen

1. Menu > APIs & Services > OAuth consent screen
2. User Type: **External**
3. Điền thông tin app
4. Scopes: Thêm `https://www.googleapis.com/auth/calendar`
5. Test users: Thêm email để test

### Bước 4: Cập nhật .env

```env
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/oauth/callback
OAUTH_CALLBACK_PORT=8081
```

### Bước 5: Restart bot

```bash
pm2 restart teletask-bot
```

---

## 11. Cấu hình Nginx Reverse Proxy (Tùy chọn)

Cần thiết nếu dùng Google Calendar với HTTPS.

### Cài đặt Nginx

```bash
sudo apt install -y nginx
```

### Tạo cấu hình site

```bash
sudo nano /etc/nginx/sites-available/teletask
```

Nội dung:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL certificates (Certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # OAuth callback proxy
    location /oauth/callback {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check (optional)
    location /health {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

### Kích hoạt site

```bash
sudo ln -s /etc/nginx/sites-available/teletask /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Cài đặt SSL với Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Khắc phục sự cố

### Bot không khởi động

1. **Kiểm tra logs:**
   ```bash
   pm2 logs teletask-bot --lines 50
   ```

2. **Kiểm tra .env:**
   ```bash
   cat /home/botpanel/bots/bot_001/.env | grep -v "^#"
   ```

3. **Kiểm tra database:**
   ```bash
   PGPASSWORD=your_password psql -h localhost -U botpanel -d teletask_db -c "SELECT 1;"
   ```

### Database connection error

1. **Kiểm tra PostgreSQL:**
   ```bash
   sudo systemctl status postgresql
   ```

2. **Kiểm tra kết nối:**
   ```bash
   sudo -u postgres psql -c "\l"
   ```

3. **Kiểm tra pg_hba.conf:**
   ```bash
   sudo nano /etc/postgresql/*/main/pg_hba.conf
   ```
   Thêm dòng:
   ```
   local   all   botpanel   md5
   host    all   botpanel   127.0.0.1/32   md5
   ```
   Restart PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

### Migration lỗi

1. **Xem trạng thái:**
   ```bash
   cd /home/botpanel/bots/bot_001
   source venv/bin/activate
   alembic current
   alembic history
   ```

2. **Rollback nếu cần:**
   ```bash
   alembic downgrade -1
   ```

### Bot không nhận lệnh

1. **Kiểm tra token:**
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getMe"
   ```

2. **Kiểm tra webhook (nếu có):**
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

   Xóa webhook để dùng polling:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
   ```

### Google Calendar không hoạt động

1. **Kiểm tra cấu hình:**
   ```bash
   grep GOOGLE /home/botpanel/bots/bot_001/.env
   ```

2. **Kiểm tra OAuth server:**
   ```bash
   curl http://localhost:8081/health
   ```

3. **Kiểm tra Nginx:**
   ```bash
   sudo nginx -t
   curl -I https://yourdomain.com/oauth/callback
   ```

### Logs đầy disk

1. **Xem dung lượng:**
   ```bash
   du -sh /home/botpanel/logs/*
   ```

2. **Cấu hình logrotate:**
   ```bash
   sudo nano /etc/logrotate.d/teletask
   ```
   Nội dung:
   ```
   /home/botpanel/logs/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
       create 644 botpanel botpanel
   }
   ```

---

## Cập nhật bot

### Pull code mới

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    git pull origin main
"
```

### Cài dependencies mới (nếu có)

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    source venv/bin/activate
    pip install -r requirements.txt
"
```

### Chạy migrations mới (nếu có)

```bash
sudo -u botpanel bash -c "
    cd /home/botpanel/bots/bot_001
    source venv/bin/activate
    alembic upgrade head
"
```

### Restart bot

```bash
pm2 restart teletask-bot
```

---

## Backup & Restore

### Backup database

```bash
PGPASSWORD=your_password pg_dump -h localhost -U botpanel teletask_db > backup_$(date +%Y%m%d).sql
```

### Restore database

```bash
PGPASSWORD=your_password psql -h localhost -U botpanel teletask_db < backup_20251216.sql
```

### Cron job backup tự động

```bash
crontab -e
```

Thêm dòng (backup lúc 3:00 AM hàng ngày):

```cron
0 3 * * * PGPASSWORD=your_password pg_dump -h localhost -U botpanel teletask_db > /home/botpanel/backups/teletask_$(date +\%Y\%m\%d).sql
```

---

## Liên hệ hỗ trợ

- **GitHub Issues:** https://github.com/haduyson/teletask/issues
- **Documentation:** https://teletask.haduyson.com

---

*Tài liệu cập nhật: 17/12/2025*
