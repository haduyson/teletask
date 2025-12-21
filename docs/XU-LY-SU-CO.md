# TeleTask Bot - Hướng Dẫn Xử Lý Sự Cố

**Cập nhật lần cuối:** 2025-12-20
**Phiên bản:** 1.0
**Ngôn ngữ:** Tiếng Việt

---

## Kiểm Tra Nhanh

### Bot Không Phản Hồi?

**Bước 1: Kiểm tra bot có hoạt động không**
```bash
curl https://your-domain.com/health
```

Nếu nhận được JSON response, bot đang chạy.

**Bước 2: Xem logs**
```bash
pm2 logs hasontechtask
```

Tìm dòng lỗi (ERROR, Exception, ...)

**Bước 3: Khởi động lại**
```bash
pm2 restart hasontechtask
```

---

## Các Sự Cố Thường Gặp

### 1. Bot Không Trả Lời Lệnh

**Dấu Hiệu:**
- Gửi `/taoviec` nhưng bot không phản hồi
- Các lệnh bị timeout

**Nguyên Nhân & Giải Pháp:**

**A. Cơ sở dữ liệu không kết nối**
```bash
# Kiểm tra PostgreSQL
sudo service postgresql status

# Nếu dừng, khởi động lại
sudo service postgresql start

# Kiểm tra kết nối
psql $DATABASE_URL
```

**B. Token bot không hợp lệ**
```bash
# Kiểm tra trong .env
grep BOT_TOKEN .env

# Tạo token mới từ @BotFather
# Cập nhật .env và khởi động lại
pm2 restart hasontechtask
```

**C. Bộ nhớ hết**
```bash
# Kiểm tra bộ nhớ
pm2 monit

# Nếu > 500MB, khởi động lại
pm2 restart hasontechtask
```

---

### 2. Wizard Tạo Việc Bị Treo

**Dấu Hiệu:**
- `/taoviec` không tiến hành được bước tiếp theo
- Wizard không lưu dữ liệu

**Giải Pháp:**

**Bước 1: Hủy wizard hiện tại**
```
Bạn: /cancel
hoặc /start
```

**Bước 2: Kiểm tra database**
```bash
psql $DATABASE_URL
SELECT * FROM users WHERE telegram_id = YOUR_ID;
```

Nếu không có, bạn chưa đăng ký. Gửi `/start` trước.

**Bước 3: Kiểm tra logs**
```bash
pm2 logs hasontechtask | grep -i "conversation\|state"
```

Tìm lỗi liên quan đến ConversationHandler.

---

### 3. Nhắc Nhở Không Gửi

**Dấu Hiệu:**
- Đặt nhắc nhở với `/nhacviec` nhưng không nhận thông báo
- Hạn chót đã tới nhưng không được nhắc

**Nguyên Nhân & Giải Pháp:**

**A. Tắt thông báo**
```bash
# Kiểm tra cài đặt
Gửi: /caidat
Bot: Kiểm tra xem "Nhắc nhở" có BẬT không

# Nếu TẮT, nhấn nút để bật
```

**B. Scheduler không chạy**
```bash
# Kiểm tra logs
pm2 logs hasontechtask | grep -i "scheduler"

# Nếu không thấy "process_reminders", scheduler bị lỗi
# Khởi động lại
pm2 restart hasontechtask
```

**C. Kiểm tra nhắc nhở trong database**
```bash
psql $DATABASE_URL
SELECT * FROM reminders
WHERE user_id = (SELECT id FROM users WHERE telegram_id = YOUR_ID)
AND is_sent = false;
```

Nếu trống, không có nhắc nhở nào đang chờ.

---

### 4. Công Việc Nhóm Không Hoạt Động

**Dấu Hiệu:**
- `/giaoviec @user1 @user2` không tạo công việc nhóm
- Thành viên không nhận thông báo

**Giải Pháp:**

**Bước 1: Kiểm tra nhóm đã đăng ký**
```bash
psql $DATABASE_URL
SELECT * FROM groups WHERE telegram_id = CHAT_ID;
```

Nếu không có, bot chưa tham gia nhóm hoặc chưa đăng ký.

**Bước 2: Kiểm tra thành viên trong database**
```bash
psql $DATABASE_URL
SELECT u.username, gm.role
FROM group_members gm
JOIN users u ON gm.user_id = u.id
WHERE gm.group_id = GROUP_ID;
```

**Bước 3: Gửi lệnh lại**
```
/giaoviec @user1 @user2 Nội dung
```

Bot sẽ tự động đăng ký nhóm nếu chưa.

---

### 5. Báo Cáo Không Tạo Được

**Dấu Hiệu:**
- `/export xlsx` không hoạt động
- Báo cáo tạo rất lâu
- Lỗi khi tải xuống

**Giải Pháp:**

**A. Kiểm tra thư mục exports**
```bash
# Kiểm tra quyền
ls -la /path/to/hasontechtask/exports/

# Nếu không có hoặc lỗi quyền
mkdir -p /path/to/hasontechtask/exports
chmod 755 /path/to/hasontechtask/exports
```

**B. Kiểm tra dung lượng đĩa**
```bash
df -h /

# Nếu < 1GB, cần dọn dẹp
find /path/to/hasontechtask/exports -mtime +3 -delete
```

**C. Kiểm tra logs**
```bash
pm2 logs hasontechtask | grep -i "report\|export"
```

---

### 6. Google Calendar Không Kết Nối

**Dấu Hiệu:**
- `/lichgoogle` không hiển thị link
- OAuth callback lỗi

**Giải Pháp:**

**A. Kiểm tra tính năng có bật**
```bash
grep GOOGLE_CALENDAR_ENABLED .env

# Nếu không có hoặc = false, bật nó:
# GOOGLE_CALENDAR_ENABLED=true
pm2 restart hasontechtask
```

**B. Kiểm tra OAuth server**
```bash
pm2 logs hasontechtask | grep -i "oauth"

# Nên thấy "OAuth server listening..."
```

**C. Xóa token cũ**
```bash
psql $DATABASE_URL
UPDATE users
SET google_tokens = null, google_sync_enabled = false
WHERE telegram_id = YOUR_ID;

# Sau đó thử /lichgoogle lại
```

---

### 7. Bộ Nhớ Cao / Bot Bị Crash

**Dấu Hiệu:**
- Memory > 500MB
- `pm2 status` hiện exited
- Bot tự động restart

**Giải Pháp:**

**A. Kiểm tra bộ nhớ**
```bash
pm2 monit  # Xem live memory usage
```

**B. Kiểm tra task_history quá lớn**
```bash
psql $DATABASE_URL
SELECT pg_size_pretty(pg_total_relation_size('task_history'));

# Nếu > 100MB, xóa dữ liệu cũ:
DELETE FROM task_history
WHERE created_at < NOW() - INTERVAL '90 days';

VACUUM task_history;
```

**C. Kiểm tra kết nối database rò rỉ**
```bash
psql $DATABASE_URL
SELECT count(*) FROM pg_stat_activity;

# Nếu = 10 (max), pool cạn kiệt
# Khởi động lại bot
pm2 restart hasontechtask
```

---

### 8. Lỗi Database Migration

**Dấu Hiệu:**
- Lỗi "migration context"
- Trường dữ liệu mới không tồn tại

**Giải Pháp:**

```bash
# Kiểm tra migration status
alembic current    # Phiên bản hiện tại
alembic heads      # Phiên bản mới nhất

# Nếu khác, chạy migration
alembic upgrade head

# Khởi động lại bot
pm2 restart hasontechtask
```

---

### 9. Truy Vấn Chậm / Hiệu Suất Kém

**Dấu Hiệu:**
- Lệnh `/xemviec` mất > 5 giây
- Database CPU cao

**Giải Pháp:**

**A. Kiểm tra query chậm**
```bash
psql $DATABASE_URL
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**B. Kiểm tra indexes**
```bash
psql $DATABASE_URL
SELECT indexname FROM pg_indexes WHERE tablename = 'tasks';
```

Nên có: idx_tasks_assignee_status, idx_tasks_deadline, ...

**C. Tối ưu database**
```bash
psql $DATABASE_URL
VACUUM ANALYZE;  # Cập nhật thống kê
REINDEX TABLE tasks;  # Tái tạo indexes
```

---

## Kiểm Tra Sức Khỏe Hệ Thống

### Health Check API

```bash
curl https://your-domain.com/health
```

**Response Mẫu:**
```json
{
  "status": "healthy",
  "database": "connected",
  "uptime_seconds": 475800,
  "memory_mb": 256,
  "cpu_percent": 2.3,
  "tasks_today": 42
}
```

**Giải Thích:**
- `status: healthy` = Mọi thứ bình thường ✅
- `status: degraded` = Một số thành phần lỗi ⚠️
- `database: disconnected` = Lỗi cơ sở dữ liệu ❌

---

## Dãy Kiểm Tra Nhanh

Khi có sự cố, chạy tuần tự:

```bash
# 1. Kiểm tra bot có chạy?
pm2 status

# 2. Xem logs có lỗi?
pm2 logs hasontechtask --lines 50

# 3. Hệ thống khỏe không?
curl https://domain.com/health

# 4. Database có kết nối?
psql $DATABASE_URL -c "SELECT 1;"

# 5. Khôi phục nếu cần
pm2 restart hasontechtask
```

---

## Liên Hệ Hỗ Trợ

**Khi báo cáo sự cố, cung cấp:**
1. Logs từ: `pm2 logs hasontechtask > debug.log`
2. Health check: `curl https://domain.com/health > health.json`
3. Database version: `psql -c "SELECT VERSION();"`
4. Mô tả chi tiết các bước để tái hiện sự cố

---

**Cập nhật lần cuối:** 2025-12-20
**Trạng thái:** Hoạt động
**Ngôn ngữ:** Tiếng Việt
