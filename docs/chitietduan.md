# TeleTask Bot - Tài Liệu Chi Tiết Dự Án

**Ngày cập nhật:** 2025-12-20
**Phiên bản:** 1.0
**Trạng thái:** Hoạt động
**Ngôn ngữ tài liệu:** Tiếng Việt

---

## Mục Lục

1. [Tổng Quan Dự Án](#1-tổng-quan-dự-án)
2. [Yêu Cầu Phát Triển Sản Phẩm (PDR)](#2-yêu-cầu-phát-triển-sản-phẩm-pdr)
3. [Kiến Trúc Hệ Thống](#3-kiến-trúc-hệ-thống)
4. [Cấu Trúc Mã Nguồn](#4-cấu-trúc-mã-nguồn)
5. [Cơ Sở Dữ Liệu](#5-cơ-sở-dữ-liệu)
6. [Các Module Chính](#6-các-module-chính)
7. [Luồng Hoạt Động](#7-luồng-hoạt-động)
8. [Tiêu Chuẩn Mã Nguồn](#8-tiêu-chuẩn-mã-nguồn)
9. [Bảo Mật](#9-bảo-mật)
10. [Giám Sát & Vận Hành](#10-giám-sát--vận-hành)
11. [Cấu Hình & Triển Khai](#11-cấu-hình--triển-khai)
12. [Danh Sách Lệnh](#12-danh-sách-lệnh)
13. [Lộ Trình Phát Triển](#13-lộ-trình-phát-triển)

---

## 1. Tổng Quan Dự Án

### 1.1 Giới Thiệu

**TeleTask Bot** là một bot Telegram quản lý công việc hoàn toàn bằng tiếng Việt, được thiết kế cho cá nhân và nhóm để theo dõi công việc, nhắc nhở và báo cáo tiến độ.

### 1.2 Thông Tin Kỹ Thuật

| Thuộc Tính | Giá Trị |
|------------|---------|
| **Ngôn ngữ lập trình** | Python 3.11+ |
| **Framework Bot** | python-telegram-bot 21.0+ |
| **Cơ sở dữ liệu** | PostgreSQL 12+ (asyncpg) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Lập lịch** | APScheduler 3.10+ |
| **Quản lý tiến trình** | PM2 |
| **Web Server** | aiohttp |
| **Tổng dòng mã** | ~21,666 dòng |
| **Số file** | 68 files |

### 1.3 Đối Tượng Sử Dụng

- **Cá nhân:** Người Việt cần quản lý công việc cá nhân
- **Nhóm trưởng:** Quản lý công việc nhóm qua Telegram
- **Đội dự án:** Phối hợp công việc và theo dõi tiến độ

### 1.4 Tính Năng Chính

| Tính Năng | Mô Tả |
|-----------|-------|
| **Tạo việc** | Wizard nhiều bước với phân tích thời gian tiếng Việt |
| **Xem việc** | Lọc theo trạng thái, ưu tiên, người giao/nhận |
| **Giao việc** | Giao cho một hoặc nhiều người trong nhóm |
| **Nhắc nhở** | Tự động nhắc trước/sau deadline |
| **Thống kê** | Báo cáo tuần/tháng với so sánh |
| **Xuất báo cáo** | CSV, Excel (có biểu đồ), PDF |
| **Google Calendar** | Đồng bộ công việc qua OAuth 2.0 |
| **Việc lặp lại** | Tạo mẫu việc theo chu kỳ |

---

## 2. Yêu Cầu Phát Triển Sản Phẩm (PDR)

### 2.1 Mục Tiêu Sản Phẩm

- Quản lý công việc hiệu quả ngay trong Telegram (không cần chuyển app)
- Hỗ trợ cả cá nhân và nhóm
- Nhắc nhở thông minh theo deadline
- Tạo báo cáo và thống kê tự động
- Tích hợp Google Calendar
- Hỗ trợ hoàn toàn tiếng Việt

### 2.2 Yêu Cầu Chức Năng

#### Quản Lý Việc Cơ Bản
- Tạo việc với tiêu đề, mô tả, deadline, ưu tiên
- Xem danh sách việc với lọc và phân trang
- Cập nhật trạng thái (chờ xử lý → đang làm → hoàn thành)
- Cập nhật tiến độ (0-100%)
- Xóa mềm với khả năng hoàn tác 30 giây

#### Việc Nhóm
- Giao việc cho một hoặc nhiều người
- Tạo việc nhóm (G-ID) với nhiều việc con (P-ID)
- Theo dõi việc đã giao/đã nhận

#### Nhắc Nhở
- Nhắc trước deadline: 24h, 1h, 30m, 5m
- Nhắc sau deadline: 1h, 1d (escalation)
- Nhắc tùy chỉnh
- Thông báo cho người tạo khi việc quá hạn

#### Báo Cáo
- Thống kê tổng quan
- Báo cáo tuần/tháng với so sánh
- Xuất CSV, Excel, PDF
- Link tải có mật khẩu, hết hạn 72 giờ

### 2.3 Yêu Cầu Phi Chức Năng

| Yêu Cầu | Chỉ Tiêu |
|---------|----------|
| **Thời gian phản hồi** | < 3 giây |
| **Uptime** | 99.9% |
| **Tạo việc** | < 2 giây |
| **Nhắc nhở** | Trong vòng 1 phút |
| **Tạo báo cáo** | < 5 giây |
| **RAM** | < 200MB |
| **CPU** | < 30% (bình thường) |
| **Người dùng đồng thời** | 100+ |

### 2.4 Hệ Thống ID Công Việc

| Loại | Format | Ví Dụ | Mô Tả |
|------|--------|-------|-------|
| **Personal** | P-XXXX | P-0042, P-9999 | Việc cá nhân |
| **Group** | G-XXXX | G-0001, G-0500 | Việc nhóm (cha) |

- Tạo từ PostgreSQL sequence (atomic, an toàn đa luồng)
- Format xác định loại việc trong truy vấn

---

## 3. Kiến Trúc Hệ Thống

### 3.1 Sơ Đồ Tổng Quan

```
┌─────────────────────────────────────────────────────────────────┐
│                     Người Dùng Telegram                          │
│                    (Chat cá nhân & Nhóm)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ▼        │        ▼
            ┌────────────────────────────────┐
            │     Telegram Bot API (HTTPS)   │
            │       Long Polling             │
            └───────────────┬────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │       TeleTask Bot (Python 3.11)    │
        │           Entry: bot.py             │
        │                                     │
        │  ┌────────────────────────────────┐ │
        │  │      Tầng Handler (15 module)  │ │
        │  │  • CommandHandler              │ │
        │  │  • ConversationHandler         │ │
        │  │  • CallbackQueryHandler        │ │
        │  └──────────────┬─────────────────┘ │
        │                 │                   │
        │  ┌──────────────▼─────────────────┐ │
        │  │      Tầng Service (11 module)  │ │
        │  │  • TaskService                 │ │
        │  │  • ReminderService             │ │
        │  │  • NotificationService         │ │
        │  │  • ReportService               │ │
        │  │  • CalendarService             │ │
        │  └──────────────┬─────────────────┘ │
        │                 │                   │
        │  ┌──────────────▼─────────────────┐ │
        │  │      Tầng Data Access          │ │
        │  │  • SQLAlchemy ORM (10 Models)  │ │
        │  │  • Async Session Manager       │ │
        │  └──────────────┬─────────────────┘ │
        │                 │                   │
        │  ┌──────────────▼─────────────────┐ │
        │  │      Background Schedulers     │ │
        │  │  • APScheduler                 │ │
        │  │  • Reminder Scheduler (30s)    │ │
        │  │  • Report Scheduler            │ │
        │  └──────────────┬─────────────────┘ │
        │                 │                   │
        │  ┌──────────────▼─────────────────┐ │
        │  │      Monitoring (Tùy chọn)     │ │
        │  │  • Health Check Server         │ │
        │  │  • Resource Monitor            │ │
        │  │  • Alert Service               │ │
        │  └──────────────┬─────────────────┘ │
        └─────────────────┼───────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
    ▼   ▼                 ▼                  ▼
┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│  PostgreSQL  │  │     Google      │  │  Prometheus  │
│   Database   │  │  Calendar API   │  │  (tùy chọn)  │
│   (asyncpg)  │  │   OAuth 2.0     │  │   Metrics    │
└──────────────┘  └─────────────────┘  └──────────────┘
```

### 3.2 Luồng Xử Lý Request

```
Telegram Update
    ↓
Handler (start.py, task_wizard.py, callbacks.py, ...)
    ↓
Kiểm tra quyền (nếu cần)
    ↓
Validate đầu vào
    ↓
Gọi Service Layer
    ↓
Format Response
    ↓
Gửi về Telegram
```

### 3.3 Các Thành Phần Chính

| Thành Phần | Mô Tả | Files |
|------------|-------|-------|
| **Handlers** | Xử lý lệnh và callback | 15 modules (~250KB) |
| **Services** | Logic nghiệp vụ | 11 modules (~180KB) |
| **Database** | Models và connection | 10 models + pool |
| **Scheduler** | Jobs nền (nhắc nhở, báo cáo) | 2 modules |
| **Monitoring** | Health check, metrics | 4 modules |
| **Utils** | Formatters, keyboards, validators | 5 modules |

---

## 4. Cấu Trúc Mã Nguồn

### 4.1 Cây Thư Mục

```
hasontechtask/
├── bot.py                          # Entry point (290 dòng)
├── requirements.txt                # Dependencies
├── alembic.ini                     # Migration config
├── ecosystem.config.js             # PM2 config
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Biến môi trường (105 dòng)
│
├── database/
│   ├── __init__.py                 # Database getter
│   ├── connection.py               # Async pool manager
│   ├── models.py                   # 10 SQLAlchemy models
│   └── migrations/
│       ├── env.py                  # Alembic config
│       └── versions/               # 9 schema versions
│           ├── 20241214_0001_initial_schema.py
│           ├── 20241215_0002_recurring_templates.py
│           ├── 20241215_0003_group_tasks.py
│           ├── 20251216_0004_export_reports.py
│           ├── 20251216_0005_reminder_source.py
│           ├── 20251216_0006_calendar_sync_interval.py
│           ├── 20251217_0001_notification_settings.py
│           ├── 20251217_0007_user_reminder_prefs.py
│           └── 20251218_0009_task_id_sequence.py
│
├── handlers/                       # 15 handler modules
│   ├── __init__.py                 # Handler registration
│   ├── start.py                    # /start, /help
│   ├── task_create.py              # Tạo việc nhanh
│   ├── task_wizard.py              # Wizard tạo việc (70KB)
│   ├── task_view.py                # /xemviec
│   ├── task_update.py              # /xong, /danglam, /tiendo
│   ├── task_assign.py              # /giaoviec, /viecdagiao
│   ├── task_delete.py              # /xoa (25KB)
│   ├── callbacks.py                # 50+ button handlers (48KB)
│   ├── reminder.py                 # /nhacviec
│   ├── recurring_task.py           # /vieclaplai
│   ├── statistics.py               # /thongke
│   ├── export.py                   # /export
│   ├── calendar.py                 # /lichgoogle
│   └── settings.py                 # /caidat
│
├── services/                       # 11 service modules
│   ├── __init__.py
│   ├── task_service.py             # CRUD việc (51KB)
│   ├── notification.py             # Gửi tin nhắn
│   ├── reminder_service.py         # Quản lý nhắc nhở
│   ├── recurring_service.py        # Việc lặp lại (18KB)
│   ├── calendar_service.py         # Google Calendar (17KB)
│   ├── statistics_service.py       # Tính toán thống kê
│   ├── report_service.py           # Tạo báo cáo (31KB)
│   ├── time_parser.py              # Parse thời gian tiếng Việt
│   ├── user_service.py             # CRUD người dùng
│   └── oauth_callback.py           # Google OAuth server
│
├── scheduler/                      # Background jobs
│   ├── __init__.py
│   ├── reminder_scheduler.py       # Xử lý nhắc nhở
│   └── report_scheduler.py         # Báo cáo tuần/tháng
│
├── monitoring/                     # Giám sát (tùy chọn)
│   ├── __init__.py
│   ├── health_check.py             # HTTP server (port 8080)
│   ├── resource_monitor.py         # CPU/RAM/DB
│   ├── metrics.py                  # Prometheus metrics
│   └── alert.py                    # Cảnh báo admin
│
├── utils/                          # Tiện ích
│   ├── __init__.py
│   ├── formatters.py               # Format hiển thị
│   ├── keyboards.py                # Inline keyboards
│   ├── messages.py                 # Template tiếng Việt
│   ├── validators.py               # Validate đầu vào
│   └── db_utils.py                 # Database helpers
│
├── static/                         # Static files
│   └── user-guide.html
│
├── exports/                        # Thư mục báo cáo (runtime)
│
├── .env                            # Biến môi trường
└── .env.example                    # Template .env
```

### 4.2 Files Quan Trọng Theo Kích Thước

| File | Kích Thước | Mục Đích |
|------|------------|----------|
| `handlers/task_wizard.py` | 70KB | Wizard tạo việc nhiều bước |
| `handlers/callbacks.py` | 48KB | 50+ inline button handlers |
| `services/task_service.py` | 51KB | CRUD việc chính |
| `services/report_service.py` | 31KB | Tạo báo cáo CSV/XLSX/PDF |
| `handlers/task_delete.py` | 25KB | Xóa mềm + hoàn tác |

---

## 5. Cơ Sở Dữ Liệu

### 5.1 Tổng Quan

- **Engine:** PostgreSQL 12+
- **Driver:** asyncpg (async)
- **ORM:** SQLAlchemy 2.0
- **Pool:** 2-10 connections
- **Migrations:** Alembic (9 versions)

### 5.2 Sơ Đồ Entity-Relationship

```
┌─────────────────┐         ┌──────────────────┐
│      User       │         │      Group       │
├─────────────────┤         ├──────────────────┤
│ id (PK)         │         │ id (PK)          │
│ telegram_id     │         │ telegram_id      │
│ username        │         │ title            │
│ first_name      │         │ is_active        │
│ timezone        │────┬────│ created_at       │
│ google_tokens   │    │    │ updated_at       │
│ notify_prefs    │    │    └──────────────────┘
│ created_at      │    │
└────────┬────────┘    │    ┌──────────────────┐
         │             ├───→│   GroupMember    │
         │             │    ├──────────────────┤
         │             │    │ group_id (FK)    │
         │             │    │ user_id (FK)     │
         │             │    │ role             │
         │             │    │ joined_at        │
         │             │    └──────────────────┘
         │             │
         │             │    ┌──────────────────┐
         │             ├───→│       Task       │
         │                  ├──────────────────┤
         │                  │ id (PK)          │
         │                  │ public_id (P/G)  │
         │                  │ content          │
         │                  │ status           │
         │                  │ priority         │
         │                  │ progress (%)     │
         │                  │ creator_id (FK)  │
         │                  │ assignee_id (FK) │
         │                  │ group_id (FK)    │
         │                  │ deadline         │
         │                  │ is_deleted       │
         │                  │ google_event_id  │
         │                  └────────┬─────────┘
         │                           │
         ├──────────────────────────┤
         │                          │
    ▼    ▼                      ▼   ▼
┌──────────────────┐  ┌──────────────────┐
│    Reminder      │  │   TaskHistory    │
├──────────────────┤  ├──────────────────┤
│ id (PK)          │  │ id (PK)          │
│ task_id (FK)     │  │ task_id (FK)     │
│ user_id (FK)     │  │ user_id (FK)     │
│ remind_at        │  │ action           │
│ reminder_type    │  │ changed_fields   │
│ is_sent          │  │ created_at       │
│ sent_at          │  └──────────────────┘
│ error_message    │
└──────────────────┘

Các bảng khác:
├── RecurringTemplate  # Mẫu việc lặp lại
├── UserStatistics     # Thống kê tuần/tháng
├── DeletedTaskUndo    # Buffer hoàn tác (30s)
├── ExportReport       # Báo cáo đã tạo
└── BotConfig          # Cấu hình runtime
```

### 5.3 Chi Tiết Các Bảng

#### Bảng User
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'Asia/Ho_Chi_Minh',
    language VARCHAR(10) DEFAULT 'vi',

    -- Notification preferences
    notify_reminder BOOLEAN DEFAULT true,
    notify_weekly_report BOOLEAN DEFAULT true,
    notify_monthly_report BOOLEAN DEFAULT true,
    notify_task_assigned BOOLEAN DEFAULT true,
    notify_task_status BOOLEAN DEFAULT true,

    -- Google Calendar
    google_calendar_token TEXT,
    google_calendar_refresh_token TEXT,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
```

#### Bảng Task
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    public_id VARCHAR(20) UNIQUE NOT NULL,  -- P-0042, G-0001
    group_task_id VARCHAR(20),              -- Liên kết việc nhóm

    content TEXT NOT NULL,
    description TEXT,

    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed')),
    priority VARCHAR(20) DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    progress INTEGER DEFAULT 0
        CHECK (progress >= 0 AND progress <= 100),

    creator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,

    deadline TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Recurring
    is_recurring BOOLEAN DEFAULT false,
    recurring_pattern VARCHAR(20),
    recurring_config JSONB,
    parent_recurring_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,

    -- Google Calendar
    google_event_id VARCHAR(255),

    -- Soft delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes cho performance
CREATE INDEX idx_tasks_assignee_status ON tasks(assignee_id, status)
    WHERE is_deleted = false;
CREATE INDEX idx_tasks_deadline ON tasks(deadline)
    WHERE is_deleted = false AND status != 'completed';
CREATE INDEX idx_tasks_creator ON tasks(creator_id)
    WHERE is_deleted = false;
CREATE INDEX idx_tasks_group ON tasks(group_id)
    WHERE is_deleted = false;
```

#### Bảng Reminder
```sql
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    remind_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reminder_type VARCHAR(50) NOT NULL
        CHECK (reminder_type IN ('before_deadline', 'after_deadline',
                                  'custom', 'creator_overdue')),
    reminder_offset VARCHAR(20),  -- '24h', '1h', '30m', '5m'

    is_sent BOOLEAN DEFAULT false,
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_reminders_pending ON reminders(remind_at)
    WHERE is_sent = false;
```

### 5.4 Quản Lý Connection

```python
class Database:
    """Singleton quản lý async connection pool."""

    def __init__(self, url: str):
        self._engine = create_async_engine(
            url,
            pool_size=2,      # Min connections
            max_overflow=8,   # Max additional
            pool_timeout=30,
            echo=False
        )
        self._session_factory = async_sessionmaker(self._engine)

    @asynccontextmanager
    async def session(self):
        """Context manager cho session với auto-cleanup."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
```

---

## 6. Các Module Chính

### 6.1 Handlers (15 modules)

| Module | Lệnh | Mô Tả |
|--------|------|-------|
| `start.py` | /start, /help | Khởi động, menu chính |
| `task_create.py` | /taoviec | Tạo việc nhanh |
| `task_wizard.py` | (multi-step) | Wizard tạo việc đầy đủ |
| `task_view.py` | /xemviec | Xem danh sách/chi tiết việc |
| `task_update.py` | /xong, /danglam, /tiendo | Cập nhật trạng thái |
| `task_assign.py` | /giaoviec, /viecdagiao | Giao việc, xem đã giao |
| `task_delete.py` | /xoa | Xóa mềm + hoàn tác |
| `callbacks.py` | (buttons) | 50+ inline button handlers |
| `reminder.py` | /nhacviec | Đặt nhắc nhở |
| `recurring_task.py` | /vieclaplai | Việc lặp lại |
| `statistics.py` | /thongke, /thongketuan, /thongkethang | Thống kê |
| `export.py` | /export | Xuất báo cáo |
| `calendar.py` | /lichgoogle | Google Calendar OAuth |
| `settings.py` | /caidat | Cài đặt người dùng |

#### Pattern Handler

```python
# ConversationHandler cho wizard nhiều bước
ConversationHandler(
    entry_points=[CommandHandler("taoviec", task_wizard_start)],
    states={
        STATE_TITLE: [MessageHandler(filters.TEXT, handle_title)],
        STATE_DESCRIPTION: [MessageHandler(filters.TEXT, handle_desc)],
        STATE_DEADLINE: [MessageHandler(filters.TEXT, handle_deadline)],
        STATE_CONFIRM: [CallbackQueryHandler(handle_confirm)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# CommandHandler cho lệnh đơn
CommandHandler("xemviec", view_tasks)

# CallbackQueryHandler cho nút bấm
CallbackQueryHandler(update_status, pattern="^update_task_")
```

### 6.2 Services (11 modules)

| Module | Chức Năng | Methods Chính |
|--------|-----------|---------------|
| `task_service.py` | CRUD việc | create_task, get_user_tasks, update_task, soft_delete_task |
| `notification.py` | Gửi tin nhắn | format_task_summary, send_notification, send_bulk |
| `reminder_service.py` | Nhắc nhở | create_reminder, get_pending_reminders, mark_sent |
| `recurring_service.py` | Việc lặp | generate_next_occurrence, apply_pattern |
| `calendar_service.py` | Google Calendar | sync_task_to_calendar, get_events |
| `statistics_service.py` | Tính toán | get_user_stats, get_weekly_stats |
| `report_service.py` | Báo cáo | generate_csv, generate_xlsx, generate_pdf |
| `time_parser.py` | Parse thời gian | parse_datetime ("ngày mai", "25/12") |
| `user_service.py` | CRUD user | get_or_create_user, update_preferences |
| `oauth_callback.py` | OAuth server | handle_callback |

#### Pattern Service

```python
class TaskService:
    """Service stateless với static methods."""

    @staticmethod
    async def create_task(
        user_id: int,
        content: str,
        deadline: Optional[datetime] = None,
        group_id: Optional[int] = None,
    ) -> Task:
        """Tạo việc mới với ID tự động."""
        db = get_db()
        async with db.session() as session:
            task = Task(
                creator_id=user_id,
                content=content,
                deadline=deadline,
                group_id=group_id,
            )
            session.add(task)
            await session.flush()

            # Tạo public_id
            task.public_id = f"P-{task.id:04d}" if not group_id else f"G-{task.id:04d}"

            await session.commit()
            return task
```

### 6.3 Scheduler (2 modules)

#### Reminder Scheduler
```python
# Chạy mỗi 30 giây
async def process_pending_reminders():
    """Xử lý nhắc nhở đến hạn."""
    reminders = await ReminderService.get_pending_reminders()
    for reminder in reminders:
        await NotificationService.send_reminder(reminder)
        await ReminderService.mark_sent(reminder.id)
```

#### Report Scheduler
```python
# Báo cáo tuần: Chủ nhật 00:00
# Báo cáo tháng: Ngày 1 mỗi tháng 00:00
async def generate_weekly_reports():
    """Tạo và gửi báo cáo tuần cho tất cả users."""
    users = await get_users_with_weekly_report_enabled()
    for user in users:
        stats = await StatisticsService.get_weekly_stats(user.id)
        report = await ReportService.generate_xlsx(stats)
        await NotificationService.send_file(user.telegram_id, report)
```

### 6.4 Monitoring (4 modules)

| Module | Chức Năng |
|--------|-----------|
| `health_check.py` | HTTP server port 8080, endpoint /health |
| `resource_monitor.py` | Theo dõi CPU/RAM/DB connections |
| `metrics.py` | Prometheus metrics (tùy chọn) |
| `alert.py` | Cảnh báo admin khi có lỗi |

#### Health Check Response
```json
{
  "status": "healthy",
  "uptime": "2d 5h 30m",
  "uptime_seconds": 187800,
  "memory_mb": 145.23,
  "cpu_percent": 2.5,
  "database": "connected",
  "tasks_today": 12,
  "completed_today": 8
}
```

### 6.5 Utils (5 modules)

| Module | Chức Năng |
|--------|-----------|
| `formatters.py` | Format hiển thị (datetime, status, progress bar) |
| `keyboards.py` | Tạo inline/reply keyboards |
| `messages.py` | Template tin nhắn tiếng Việt |
| `validators.py` | Validate đầu vào |
| `db_utils.py` | Database helpers |

---

## 7. Luồng Hoạt Động

### 7.1 Tạo Việc Cá Nhân

```
Người dùng: /taoviec
    ↓
handlers/task_wizard.py:task_wizard_start()
    ├─ Kiểm tra/tạo user (get_or_create_user)
    └─ Hỏi tiêu đề → STATE_TITLE
    ↓
Người dùng: "Fix lỗi đăng nhập"
    ↓
task_wizard_title()
    ├─ Lưu vào context.user_data["title"]
    └─ Hỏi mô tả → STATE_DESCRIPTION
    ↓
[Tiếp tục qua các bước...]
    ↓
task_wizard_confirm()
    ├─ Validate tất cả fields
    ├─ TaskService.create_task()
    │   ├─ INSERT vào bảng Task
    │   ├─ Tạo public_id (P-0042)
    │   └─ Trả về Task object
    ├─ NotificationService.format_task_summary(task)
    └─ Gửi xác nhận với chi tiết việc
    ↓
Người dùng thấy:
✅ Tạo thành công!
📋 P-0042: Fix lỗi đăng nhập
Hạn: [deadline]
```

### 7.2 Đặt Nhắc Nhở

```
Người dùng: /nhacviec P-0042
    ↓
reminder.py:set_reminder_wizard()
    ├─ Parse public_id P-0042
    ├─ Lấy task qua TaskService.get_task_by_public_id()
    └─ Kiểm tra quyền (creator/assignee)
    ↓
[Wizard chọn thời gian nhắc]
    ↓
reminder.py:confirm_reminder()
    ├─ Parse biểu thức thời gian ("1 ngày trước hạn")
    ├─ Tính remind_at = deadline - 1 day
    ├─ ReminderService.create_reminder()
    │   ├─ INSERT vào bảng Reminder
    │   └─ reminder_type = "before_deadline"
    └─ Gửi xác nhận
    ↓
Scheduler chạy mỗi 30 giây:
    ├─ Query: SELECT * FROM reminders WHERE remind_at <= NOW() AND is_sent = false
    ├─ Với mỗi reminder:
    │   ├─ Lấy chi tiết task
    │   ├─ NotificationService.send_reminder(task, user_id)
    │   ├─ UPDATE: is_sent = true, sent_at = NOW()
    │   └─ Log vào TaskHistory
    └─ Cập nhật metrics
```

### 7.3 Xóa Mềm và Hoàn Tác

```
Người dùng: /xoa P-0042
    ↓
task_delete.py:delete_task()
    ├─ Lấy task
    ├─ Kiểm tra quyền (chỉ creator)
    └─ Hiển thị 2 lựa chọn: [Xóa] [Hủy]
    ↓
Người dùng: [Xóa]
    ↓
task_delete.py:confirm_delete()
    ├─ TaskService.soft_delete_task(task_id, user_id)
    │   ├─ UPDATE tasks SET is_deleted=true, deleted_at=NOW()
    │   ├─ INSERT vào deleted_task_undo(task_id, deleted_by, deleted_at)
    │   └─ Trả về task đã xóa
    ├─ Hiển thị nút [↩️ Hoàn Tác] với đếm ngược 30s
    └─ Gửi xác nhận
    ↓
[Trong vòng 30 giây]
Người dùng: [Hoàn Tác]
    ├─ task_delete.py:undo_delete()
    ├─ TaskService.restore_task(task_id)
    │   └─ UPDATE tasks SET is_deleted=false WHERE id=?
    └─ Xác nhận đã khôi phục
    ↓
[Sau 30 giây]
    ├─ Scheduler chạy cleanup
    ├─ DELETE FROM deleted_task_undo WHERE deleted_at < NOW() - INTERVAL '30s'
    └─ Nút [Hoàn Tác] bị disable
```

### 7.4 Báo Cáo Tuần Tự Động

```
Mỗi Chủ nhật 00:00 (APScheduler)
    ↓
report_scheduler.py:generate_weekly_reports()
    ├─ Query: SELECT * FROM users WHERE notify_weekly_report = true
    ↓
Với mỗi user:
    ├─ StatisticsService.calculate_stats(user_id, period='weekly')
    │   ├─ COUNT(*) WHERE status='completed' AND week_of_year=current_week
    │   ├─ COUNT cho overdue, in_progress, pending
    │   └─ Trả về stats object
    ├─ ReportService.generate_xlsx(stats)
    │   ├─ Tạo workbook với matplotlib charts
    │   ├─ Lưu vào exports/weekly_[user_id]_[date].xlsx
    │   └─ Trả về file path
    ├─ NotificationService.send_file()
    │   └─ Upload XLSX qua Telegram
    └─ Log metrics
    ↓
Người dùng nhận:
📊 Báo cáo tuần này
[File XLSX đính kèm với biểu đồ]
```

---

## 8. Tiêu Chuẩn Mã Nguồn

### 8.1 Quy Tắc Đặt Tên

```python
# Constants: UPPER_SNAKE_CASE
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"
MAX_TASK_TITLE_LENGTH = 500

# Functions/Methods: snake_case
async def create_task(user_id: int, content: str) -> Task:
    pass

# Classes: PascalCase
class TaskService:
    pass

# Private: _leading_underscore
_internal_helper = ...

# Variables: snake_case
user_tasks = []
current_user_id = 123
```

### 8.2 Async/Await

```python
# ĐÚNG: Đánh dấu async cho tất cả I/O operations
async def get_user_tasks(user_id: int) -> List[Task]:
    async with db.session() as session:
        result = await session.execute(select(...))
        return result.scalars().all()

# SAI: Blocking I/O trong async function
async def process_task(task_id: int):
    time.sleep(1)  # Blocks event loop!
```

### 8.3 Type Hints

```python
# BẮT BUỘC cho function signatures
async def update_task(
    task_id: int,
    status: str,
    progress: int = 0,
) -> Optional[Task]:
    """Update task status and progress.

    Args:
        task_id: ID của task cần update
        status: Trạng thái mới (pending/in_progress/completed)
        progress: Phần trăm tiến độ (0-100)

    Returns:
        Task object đã update hoặc None nếu không tìm thấy

    Raises:
        ValueError: Nếu status không hợp lệ
    """
    pass
```

### 8.4 Error Handling

```python
async def safe_task_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler với error handling đúng cách."""
    try:
        user_id = update.effective_user.id
        task_id = int(context.args[0]) if context.args else None

        if not task_id:
            await update.message.reply_text(
                "❌ Vui lòng cung cấp ID việc\nCú pháp: /cmd <task_id>"
            )
            return

        task = await TaskService.get_task(task_id)
        if not task:
            await update.message.reply_text(f"❌ Không tìm thấy việc {task_id}")
            return

        # Logic chính
        result = await TaskService.update_task(task_id, status="completed")
        await update.message.reply_text(f"✅ Cập nhật thành công: {result.public_id}")

    except ValueError as e:
        logger.warning(f"Invalid input from {update.effective_user.id}: {e}")
        await update.message.reply_text(f"❌ Dữ liệu không hợp lệ: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await update.message.reply_text("❌ Lỗi hệ thống, vui lòng thử lại sau")
```

### 8.5 Design Patterns

| Pattern | Sử Dụng | Ví Dụ |
|---------|---------|-------|
| **Singleton** | Settings qua @lru_cache() | `get_settings()` |
| **Factory** | Tạo keyboards/messages | `task_actions_keyboard()` |
| **Strategy** | Format status/priority | Nhiều hàm `format_*` |
| **Whitelist** | Bảo mật database | `USER_SETTING_COLUMNS` |
| **Callback Data** | Telegram interactions | `action:task_id:value` |

---

## 9. Bảo Mật

### 9.1 Tổng Quan

| Tính Năng | Triển Khai | Vị Trí |
|-----------|------------|--------|
| **Validate Input** | Min/max length, format | `validators.py` |
| **Escape HTML** | Chống XSS | `formatters.py` |
| **Escape Markdown** | MarkdownV2 chars | `formatters.py` |
| **Mã hóa Token** | Fernet encryption | `security.py` |
| **Whitelist Columns** | Chống SQL injection | `db_utils.py` |
| **Process Lock** | Ngăn duplicate | `bot.py` |
| **Admin Check** | Role-based access | `settings.py` |

### 9.2 Validate Input

```python
from utils.validators import validate_task_title, validate_deadline

async def create_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate tất cả đầu vào trước khi xử lý."""
    title = update.message.text.strip()

    # Validate length
    if not title or len(title) > 500:
        await update.message.reply_text("❌ Tiêu đề phải từ 1-500 ký tự")
        return

    # Sanitize cho hiển thị
    safe_title = html.escape(title)

    # Tạo task
    task = await TaskService.create_task(
        user_id=update.effective_user.id,
        content=safe_title,
    )
```

### 9.3 Permission Check

```python
async def delete_group_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chỉ admin nhóm mới được xóa việc nhóm."""
    user_id = update.effective_user.id
    group_id = update.effective_chat.id
    task_id = int(context.args[0])

    # Kiểm tra admin
    is_admin = await GroupService.is_admin(group_id, user_id)
    if not is_admin:
        await update.message.reply_text("❌ Chỉ admin nhóm mới có quyền xóa")
        return

    task = await TaskService.get_task(task_id)
    if task.group_id != group_id:
        await update.message.reply_text("❌ Việc này không thuộc nhóm")
        return

    # An toàn để xóa
    await TaskService.soft_delete_task(task_id, user_id)
```

### 9.4 Logging An Toàn

```python
logger = logging.getLogger(__name__)

# ĐÚNG: Log events quan trọng không có dữ liệu nhạy cảm
logger.info(f"Task created: {task.public_id} by user {user_id}")

# SAI: Logging token/password
logger.debug(f"API token: {bot_token}")  # KHÔNG BAO GIỜ!

# ĐÚNG: Log response không có credentials
logger.debug(f"Google Calendar sync: status={status_code}")
```

---

## 10. Giám Sát & Vận Hành

### 10.1 Health Check Server

```
Port: 8080 (configurable via HEALTH_PORT)

Endpoints:
├── GET /health       → JSON status
├── GET /metrics      → Prometheus format
├── GET /report/{id}  → Password entry page
└── POST /report/{id} → Download file
```

### 10.2 Resource Monitor

```python
# Thresholds (configurable via env)
MEMORY_THRESHOLD_MB = 500    # Default
CPU_THRESHOLD = 90           # Default
DISK_THRESHOLD_PERCENT = 10  # Default
MONITOR_INTERVAL = 60        # Seconds

# Alerts khi vượt ngưỡng
- High memory: alert_service.alert_high_memory()
- High CPU: alert_service.alert_high_cpu()
- Low disk: alert_service.alert_disk_low()
```

### 10.3 Alert Service

| Alert | Level | Cooldown | Trigger |
|-------|-------|----------|---------|
| Bot start | success | 60s | Khởi động bot |
| Bot crash | critical | 60s | Exception không xử lý |
| DB error | critical | 120s | Mất kết nối database |
| High memory | warning | 600s | RAM > threshold |
| High CPU | warning | 600s | CPU > threshold |
| Disk low | critical | 3600s | Disk < threshold |

### 10.4 Prometheus Metrics

```
bot_uptime_seconds          # Thời gian chạy
bot_memory_bytes            # RAM sử dụng
bot_cpu_percent             # CPU sử dụng
tasks_created_total         # Tổng việc tạo
tasks_completed_total       # Tổng việc hoàn thành
tasks_overdue_current       # Số việc quá hạn hiện tại
messages_received_total     # Tổng tin nhắn nhận
messages_sent_total         # Tổng tin nhắn gửi
errors_total                # Tổng lỗi theo loại
```

---

## 11. Cấu Hình & Triển Khai

### 11.1 Biến Môi Trường

#### Bắt Buộc
```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/teletask
```

#### Khuyến Nghị
```env
BOT_NAME=TeleTask Bot
TZ=Asia/Ho_Chi_Minh
ADMIN_IDS=123456789,987654321
LOG_LEVEL=INFO
HEALTH_PORT=8080
DB_POOL_MIN=2
DB_POOL_MAX=10
```

#### Tùy Chọn
```env
# Google Calendar
GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CREDENTIALS_FILE=/path/to/credentials.json
ENCRYPTION_KEY=<Fernet-key-base64>

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090

# Caching
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_FILE=/var/log/teletask/bot.log
```

### 11.2 PM2 Configuration

```javascript
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'teletask-bot',
    script: './bot.py',
    interpreter: 'python3',
    instances: 1,
    watch: false,
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

### 11.3 Các Bước Triển Khai

```bash
# 1. Clone repository
git clone https://github.com/your-org/teletask-bot.git
cd teletask-bot

# 2. Tạo virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Cài đặt dependencies
pip install -r requirements.txt

# 4. Cấu hình môi trường
cp .env.example .env
nano .env  # Chỉnh sửa BOT_TOKEN, DATABASE_URL, etc.

# 5. Chạy migrations
alembic upgrade head

# 6. Khởi động với PM2
pm2 start ecosystem.config.js

# 7. Kiểm tra trạng thái
pm2 status
curl http://localhost:8080/health
```

### 11.4 Database Pool

```
Min connections: 2
Max connections: 10
Command timeout: 60s
Timezone: Asia/Ho_Chi_Minh
```

---

## 12. Danh Sách Lệnh

### 12.1 Lệnh Cơ Bản

| Lệnh | Mô Tả |
|------|-------|
| `/start` | Khởi động bot, hiển thị menu |
| `/help` | Xem trợ giúp |
| `/menu` | Hiển thị menu chính |

### 12.2 Quản Lý Việc

| Lệnh | Mô Tả |
|------|-------|
| `/taoviec` | Tạo việc mới (wizard) |
| `/xemviec [ID]` | Xem danh sách/chi tiết việc |
| `/xong [ID]` | Đánh dấu hoàn thành |
| `/danglam [ID]` | Đánh dấu đang làm |
| `/tiendo [ID] [%]` | Cập nhật tiến độ |
| `/xoa [ID]` | Xóa việc (có hoàn tác 30s) |

### 12.3 Việc Nhóm

| Lệnh | Mô Tả |
|------|-------|
| `/giaoviec @user [nội dung]` | Giao việc cho người khác |
| `/viecdagiao` | Xem việc đã giao |
| `/viecdanhan` | Xem việc được giao |

### 12.4 Thống Kê & Báo Cáo

| Lệnh | Mô Tả |
|------|-------|
| `/thongke` | Thống kê tổng quan |
| `/thongketuan` | Báo cáo tuần |
| `/thongkethang` | Báo cáo tháng |
| `/viectrehan` | Việc quá/sắp hạn |
| `/export [format] [period]` | Xuất báo cáo |

### 12.5 Cài Đặt

| Lệnh | Mô Tả |
|------|-------|
| `/nhacviec [ID] [time]` | Đặt nhắc nhở |
| `/vieclaplai` | Tạo việc lặp lại |
| `/caidat` | Cài đặt tùy chọn |
| `/lichgoogle` | Kết nối Google Calendar |

### 12.6 Format Thời Gian

Bot hỗ trợ các biểu thức thời gian tiếng Việt:

| Biểu Thức | Ý Nghĩa |
|-----------|---------|
| `ngày mai` | Ngày mai 9h sáng |
| `25/12` | 25/12 lúc 9h |
| `25/12 14:30` | 25/12 lúc 14:30 |
| `14h30` | Hôm nay 14:30 |
| `thứ 2` | Thứ 2 tuần tới |
| `tuần tới` | Thứ 2 tuần tới |

---

## 13. Lộ Trình Phát Triển

### Phase 1 (Hiện tại) ✅
- Quản lý việc cơ bản (CRUD)
- Việc cá nhân + nhóm
- Hệ thống nhắc nhở
- Thống kê & xuất báo cáo
- Giám sát và cảnh báo

### Phase 2 (Đang phát triển)
- Google Calendar sync
- Mẫu việc lặp lại
- Tìm kiếm & lọc nâng cao
- Webhook callbacks

### Phase 3 (Tương lai)
- Ứng dụng mobile native
- Quản lý workspace team
- Tích hợp Jira, Asana
- Đề xuất việc bằng AI

---

## Thông Tin Liên Hệ

- **Repository:** https://github.com/your-org/teletask-bot
- **Báo lỗi:** Tạo issue trên GitHub
- **Admin:** @admin

---

**Cập nhật lần cuối:** 2025-12-20
**Phiên bản tài liệu:** 1.0
**Trạng thái:** Hoạt động
