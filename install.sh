#!/bin/bash
#===============================================================================
# TeleTask Bot - System Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash
#
# This script installs system dependencies and botpanel CLI.
# To create a bot, run: botpanel create
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BOTPANEL_USER="botpanel"
BOTPANEL_HOME="/home/$BOTPANEL_USER"
BOTS_DIR="$BOTPANEL_HOME/bots"
LOG_DIR="$BOTPANEL_HOME/logs"
BACKUP_DIR="$BOTPANEL_HOME/backups"
PYTHON_VERSION="3.11"
TIMEZONE="Asia/Ho_Chi_Minh"

#-------------------------------------------------------------------------------
# Helper functions
#-------------------------------------------------------------------------------
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    TeleTask Bot Installer                    ║"
    echo "║                Vietnamese Task Management Bot                ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root: sudo bash install.sh"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Step 1: System preparation
#-------------------------------------------------------------------------------
prepare_system() {
    log_info "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq

    log_info "Installing essential packages..."
    apt-get install -y -qq \
        build-essential \
        curl \
        wget \
        git \
        software-properties-common \
        ca-certificates \
        gnupg \
        lsb-release \
        openssl \
        sudo

    log_info "Setting timezone to $TIMEZONE..."
    timedatectl set-timezone "$TIMEZONE" 2>/dev/null || true

    log_success "System prepared"
}

#-------------------------------------------------------------------------------
# Step 2: Install PostgreSQL
#-------------------------------------------------------------------------------
install_postgresql() {
    log_info "Installing PostgreSQL..."
    apt-get install -y -qq postgresql postgresql-contrib

    systemctl start postgresql
    systemctl enable postgresql

    # Create botpanel database user
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$BOTPANEL_USER'" | grep -q 1; then
        log_warn "Database user '$BOTPANEL_USER' already exists"
    else
        # Generate a master password for botpanel user
        MASTER_DB_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
        sudo -u postgres psql -c "CREATE USER $BOTPANEL_USER WITH PASSWORD '$MASTER_DB_PASS' CREATEDB;"
        log_info "Database user created with CREATEDB privilege"
    fi

    log_success "PostgreSQL installed"
}

#-------------------------------------------------------------------------------
# Step 3: Install Python
#-------------------------------------------------------------------------------
install_python() {
    log_info "Installing Python $PYTHON_VERSION..."

    add-apt-repository ppa:deadsnakes/ppa -y
    apt-get update -qq
    apt-get install -y -qq python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python${PYTHON_VERSION}-dev

    log_success "Python $PYTHON_VERSION installed"
}

#-------------------------------------------------------------------------------
# Step 4: Install Node.js and PM2
#-------------------------------------------------------------------------------
install_nodejs() {
    log_info "Installing Node.js..."

    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs

    log_info "Installing PM2..."
    npm install -g pm2

    log_success "Node.js and PM2 installed"
}

#-------------------------------------------------------------------------------
# Step 5: Create botpanel user and directories
#-------------------------------------------------------------------------------
create_user() {
    log_info "Creating botpanel user..."

    if id "$BOTPANEL_USER" &>/dev/null; then
        log_warn "User '$BOTPANEL_USER' already exists"
    else
        useradd -m -s /bin/bash "$BOTPANEL_USER"
    fi

    # Create directories
    mkdir -p "$BOTS_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"

    chown -R "$BOTPANEL_USER:$BOTPANEL_USER" "$BOTPANEL_HOME"

    log_success "User and directories created"
}

#-------------------------------------------------------------------------------
# Step 6: Setup PM2 startup
#-------------------------------------------------------------------------------
setup_pm2_startup() {
    log_info "Configuring PM2 startup..."

    # Setup PM2 to start on boot
    pm2 startup systemd -u "$BOTPANEL_USER" --hp "$BOTPANEL_HOME"

    log_success "PM2 startup configured"
}

#-------------------------------------------------------------------------------
# Step 7: Create botpanel CLI
#-------------------------------------------------------------------------------
create_botpanel_cli() {
    # Check if botpanel already exists
    if [ -f /usr/local/bin/botpanel ]; then
        log_warn "botpanel CLI already exists at /usr/local/bin/botpanel"
        read -p "Do you want to overwrite it? (y/N): " OVERWRITE < /dev/tty
        if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
            log_info "Skipping CLI creation to preserve existing configuration"
            return 0
        fi
        log_info "Backing up existing botpanel to /usr/local/bin/botpanel.bak"
        cp /usr/local/bin/botpanel /usr/local/bin/botpanel.bak
    fi

    log_info "Creating botpanel CLI tool..."

    cat > /usr/local/bin/botpanel << 'EOFCLI'
#!/bin/bash
#===============================================================================
# botpanel - TeleTask Bot Management CLI
# Usage: botpanel [command] [bot_name]
#===============================================================================

BOTPANEL_HOME="/home/botpanel"
BOTS_DIR="$BOTPANEL_HOME/bots"
LOG_DIR="$BOTPANEL_HOME/logs"
BACKUP_DIR="$BOTPANEL_HOME/backups"
PYTHON_VERSION="3.11"
TIMEZONE="Asia/Ho_Chi_Minh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              TeleTask - Quản lý Bot Telegram                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    print_banner
    echo -e "${GREEN}Cách dùng:${NC} botpanel [lệnh] [tên_bot]"
    echo ""
    echo -e "${YELLOW}Tạo Bot:${NC}"
    echo "  create              Tạo bot mới"
    echo "  list                Danh sách bot"
    echo "  delete <bot>        Xóa bot"
    echo ""
    echo -e "${YELLOW}Quản lý Bot:${NC}"
    echo "  start <bot>         Khởi động bot"
    echo "  stop <bot>          Dừng bot"
    echo "  restart <bot>       Khởi động lại bot"
    echo "  status [bot]        Trạng thái bot"
    echo "  logs <bot>          Xem logs"
    echo "  logs-err <bot>      Xem logs lỗi"
    echo ""
    echo -e "${YELLOW}Cơ sở dữ liệu:${NC}"
    echo "  db-status <bot>     Kiểm tra kết nối DB"
    echo "  db-migrate <bot>    Chạy migrations"
    echo "  db-backup <bot>     Sao lưu dữ liệu"
    echo "  db-restore <bot>    Khôi phục dữ liệu"
    echo ""
    echo -e "${YELLOW}Cấu hình:${NC}"
    echo "  config <bot>        Sửa cấu hình .env"
    echo "  token <bot>         Cập nhật token"
    echo "  gcal <bot>          Cài đặt Google Calendar"
    echo ""
    echo -e "${YELLOW}Bảo trì:${NC}"
    echo "  update <bot>        Cập nhật bot"
    echo "  deps <bot>          Cài lại thư viện"
    echo "  clean               Dọn logs và file tạm"
    echo "  info                Thông tin hệ thống"
    echo ""
    echo -e "${YELLOW}Ví dụ:${NC}"
    echo "  botpanel create"
    echo "  botpanel start mybot"
    echo "  botpanel logs taskbot"
    echo "  botpanel db-backup mybot"
}

#-------------------------------------------------------------------------------
# Interactive Menu Functions
#-------------------------------------------------------------------------------
# Get list of bots as array
get_bots_array() {
    local bots=()
    if [ -d "$BOTS_DIR" ]; then
        for bot_dir in "$BOTS_DIR"/*/; do
            if [ -d "$bot_dir" ]; then
                bots+=("$(basename "$bot_dir")")
            fi
        done
    fi
    echo "${bots[@]}"
}

# Select bot from menu
select_bot() {
    local prompt="$1"
    local bots=($(get_bots_array))

    if [ ${#bots[@]} -eq 0 ]; then
        echo -e "${YELLOW}Chưa có bot nào. Hãy tạo bot trước.${NC}"
        echo ""
        read -p "Nhấn Enter để tiếp tục..."
        return 1
    fi

    echo -e "${YELLOW}$prompt${NC}"
    echo ""

    local i=1
    for bot in "${bots[@]}"; do
        # Check status
        if pm2 describe "$bot" &>/dev/null; then
            local status=$(pm2 jq "$bot" 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
            if [ "$status" = "online" ]; then
                echo -e "  ${GREEN}$i)${NC} $bot ${GREEN}(đang chạy)${NC}"
            else
                echo -e "  ${RED}$i)${NC} $bot ${RED}(lỗi)${NC}"
            fi
        else
            echo -e "  ${YELLOW}$i)${NC} $bot ${YELLOW}(đã dừng)${NC}"
        fi
        ((i++))
    done

    echo ""
    echo -e "  ${BLUE}0)${NC} Quay lại menu chính"
    echo ""

    read -p "Chọn bot [0-$((i-1))]: " choice

    if [ "$choice" = "0" ] || [ -z "$choice" ]; then
        return 1
    fi

    if [ "$choice" -ge 1 ] && [ "$choice" -lt "$i" ] 2>/dev/null; then
        SELECTED_BOT="${bots[$((choice-1))]}"
        return 0
    else
        echo -e "${RED}Lựa chọn không hợp lệ${NC}"
        sleep 1
        return 1
    fi
}

# Main interactive menu
interactive_menu() {
    while true; do
        clear
        print_banner

        # Show quick status
        local bots=($(get_bots_array))
        local online_count=0
        for bot in "${bots[@]}"; do
            if pm2 describe "$bot" &>/dev/null; then
                local status=$(pm2 jq "$bot" 2>/dev/null | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
                [ "$status" = "online" ] && ((online_count++))
            fi
        done

        echo -e "  Tổng: ${CYAN}${#bots[@]}${NC} bot, ${GREEN}${online_count}${NC} đang chạy"
        echo ""
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}  Quản lý Bot${NC}"
        echo "  1) Tạo bot mới"
        echo "  2) Danh sách bot"
        echo "  3) Khởi động bot"
        echo "  4) Dừng bot"
        echo "  5) Khởi động lại"
        echo "  6) Xem logs"
        echo ""
        echo -e "${GREEN}  Cơ sở dữ liệu${NC}"
        echo "  7) Trạng thái DB"
        echo "  8) Chạy migrations"
        echo "  9) Sao lưu dữ liệu"
        echo ""
        echo -e "${GREEN}  Cấu hình${NC}"
        echo "  10) Sửa cấu hình"
        echo "  11) Cập nhật token"
        echo "  12) Google Calendar"
        echo ""
        echo -e "${GREEN}  Bảo trì${NC}"
        echo "  13) Cập nhật bot"
        echo "  14) Xóa bot"
        echo "  15) Thông tin hệ thống"
        echo "  16) Dọn logs"
        echo ""
        echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${BLUE}h)${NC} Trợ giúp (danh sách lệnh)"
        echo -e "  ${RED}q)${NC} Thoát"
        echo ""

        read -p "Chọn: " choice

        case "$choice" in
            1)
                clear
                cmd_create
                echo ""
                read -p "Nhấn Enter để tiếp tục..."
                ;;
            2)
                clear
                cmd_list
                read -p "Nhấn Enter để tiếp tục..."
                ;;
            3)
                clear
                if select_bot "Chọn bot để KHỞI ĐỘNG:"; then
                    cmd_start "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            4)
                clear
                if select_bot "Chọn bot để DỪNG:"; then
                    cmd_stop "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            5)
                clear
                if select_bot "Chọn bot để KHỞI ĐỘNG LẠI:"; then
                    cmd_restart "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            6)
                clear
                if select_bot "Chọn bot để xem LOGS:"; then
                    echo -e "${BLUE}[INFO]${NC} Đang hiển thị logs '$SELECTED_BOT' (Ctrl+C để thoát)..."
                    echo ""
                    pm2 logs "$SELECTED_BOT" --lines 50
                fi
                ;;
            7)
                clear
                if select_bot "Chọn bot để kiểm tra DATABASE:"; then
                    cmd_db_status "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            8)
                clear
                if select_bot "Chọn bot để chạy MIGRATIONS:"; then
                    cmd_db_migrate "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            9)
                clear
                if select_bot "Chọn bot để SAO LƯU:"; then
                    cmd_db_backup "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            10)
                clear
                if select_bot "Chọn bot để SỬA CẤU HÌNH:"; then
                    cmd_config "$SELECTED_BOT"
                fi
                ;;
            11)
                clear
                if select_bot "Chọn bot để cập nhật TOKEN:"; then
                    cmd_token "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            12)
                clear
                if select_bot "Chọn bot để cài GOOGLE CALENDAR:"; then
                    cmd_gcal "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            13)
                clear
                if select_bot "Chọn bot để CẬP NHẬT:"; then
                    cmd_update "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            14)
                clear
                if select_bot "Chọn bot để XÓA:"; then
                    cmd_delete "$SELECTED_BOT"
                    echo ""
                    read -p "Nhấn Enter để tiếp tục..."
                fi
                ;;
            15)
                clear
                cmd_info
                read -p "Nhấn Enter để tiếp tục..."
                ;;
            16)
                clear
                cmd_clean
                echo ""
                read -p "Nhấn Enter để tiếp tục..."
                ;;
            h|H)
                clear
                print_help
                echo ""
                read -p "Nhấn Enter để tiếp tục..."
                ;;
            q|Q|0)
                clear
                echo -e "${CYAN}Tạm biệt!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Lựa chọn không hợp lệ${NC}"
                sleep 1
                ;;
        esac
    done
}

# Get bot directory
get_bot_dir() {
    local bot_name="$1"
    if [ -z "$bot_name" ]; then
        echo -e "${RED}[LỖI]${NC} Thiếu tên bot"
        return 1
    fi

    local bot_dir="$BOTS_DIR/$bot_name"
    if [ ! -d "$bot_dir" ]; then
        echo -e "${RED}[LỖI]${NC} Không tìm thấy bot '$bot_name'"
        echo "Các bot hiện có:"
        ls -1 "$BOTS_DIR" 2>/dev/null || echo "  (không có)"
        return 1
    fi

    echo "$bot_dir"
}

#-------------------------------------------------------------------------------
# Create new bot
#-------------------------------------------------------------------------------
cmd_create() {
    print_banner
    echo -e "${YELLOW}Tạo bot TeleTask mới${NC}"
    echo ""

    # Ask for bot name
    echo -e "Nhập tên cho bot (ví dụ: mybot, taskbot, companybot):"
    echo -e "Chỉ dùng chữ thường, số và dấu gạch dưới."
    echo ""
    read -p "Tên bot: " BOT_NAME_INPUT

    if [ -z "$BOT_NAME_INPUT" ]; then
        echo -e "${RED}[LỖI]${NC} Phải nhập tên bot!"
        exit 1
    fi

    # Convert to slug
    BOT_SLUG=$(echo "$BOT_NAME_INPUT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')

    if [ -z "$BOT_SLUG" ]; then
        echo -e "${RED}[LỖI]${NC} Tên bot không hợp lệ!"
        exit 1
    fi

    BOT_DIR="$BOTS_DIR/$BOT_SLUG"

    # Check if bot already exists
    if [ -d "$BOT_DIR" ]; then
        echo -e "${RED}[LỖI]${NC} Bot '$BOT_SLUG' đã tồn tại tại $BOT_DIR"
        exit 1
    fi

    echo -e "${BLUE}[INFO]${NC} Tên bot: $BOT_SLUG"
    echo ""

    # Ask for bot token
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                    CẤU HÌNH BOT TELEGRAM                     ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    read -p "Nhập Bot Token (lấy từ @BotFather): " BOT_TOKEN

    if [ -z "$BOT_TOKEN" ]; then
        echo -e "${RED}[LỖI]${NC} Phải nhập bot token!"
        exit 1
    fi

    read -p "Nhập Telegram User ID của bạn (để làm admin, tùy chọn): " ADMIN_ID

    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                    CẤU HÌNH DOMAIN                           ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Domain dùng để:"
    echo "  - Export báo cáo (PDF, Excel)"
    echo "  - Hướng dẫn sử dụng bot"
    echo "  - Google Calendar OAuth callback"
    echo ""
    read -p "Nhập domain (vd: teletask.example.com): " BOT_DOMAIN

    if [ -z "$BOT_DOMAIN" ]; then
        echo -e "${YELLOW}[CẢNH BÁO]${NC} Không có domain - export và OAuth sẽ không hoạt động"
        EXPORT_BASE_URL=""
        GOOGLE_REDIRECT_URI=""
    else
        # Remove protocol if user included it
        BOT_DOMAIN=$(echo "$BOT_DOMAIN" | sed 's|^https\?://||' | sed 's|/$||')
        EXPORT_BASE_URL="https://$BOT_DOMAIN"
        GOOGLE_REDIRECT_URI="https://$BOT_DOMAIN/oauth/callback"
        echo -e "${GREEN}[OK]${NC} Domain: $BOT_DOMAIN"
    fi

    echo ""
    echo -e "${BLUE}[INFO]${NC} Đang tạo bot '$BOT_SLUG'..."

    # Create bot directory
    mkdir -p "$BOT_DIR"

    # Clone template
    echo -e "${BLUE}[INFO]${NC} Đang tải template bot..."
    TEMP_DIR=$(mktemp -d)

    if git clone --depth 1 https://github.com/haduyson/teletask.git "$TEMP_DIR" 2>/dev/null; then
        if [ -d "$TEMP_DIR/src/templates/bot_template" ]; then
            cp -r "$TEMP_DIR/src/templates/bot_template/"* "$BOT_DIR/"
        else
            echo -e "${RED}[LỖI]${NC} Không tìm thấy template"
            rm -rf "$TEMP_DIR" "$BOT_DIR"
            exit 1
        fi
        rm -rf "$TEMP_DIR"
    else
        echo -e "${RED}[LỖI]${NC} Không thể tải template"
        rm -rf "$TEMP_DIR" "$BOT_DIR"
        exit 1
    fi

    echo -e "${GREEN}[OK]${NC} Đã tải template"

    # Setup Python environment
    echo -e "${BLUE}[INFO]${NC} Đang cài đặt môi trường Python..."
    cd "$BOT_DIR"
    python${PYTHON_VERSION} -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate

    echo -e "${GREEN}[OK]${NC} Môi trường Python sẵn sàng"

    # Create database
    echo -e "${BLUE}[INFO]${NC} Đang tạo database..."
    DB_NAME="${BOT_SLUG}_db"
    DB_USER="botpanel"
    DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

    # Create database using botpanel user's createdb privilege or postgres
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        echo -e "${YELLOW}[CẢNH BÁO]${NC} Database '$DB_NAME' đã tồn tại"
    else
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || {
            # Fallback: create with postgres
            sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
        }
    fi

    # Update user password
    sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true

    echo -e "${GREEN}[OK]${NC} Đã tạo database"

    # Create .env file
    echo -e "${BLUE}[INFO]${NC} Đang tạo cấu hình..."
    cat > "$BOT_DIR/.env" << EOF
#-------------------------------------------------------------------------------
# Telegram Bot
#-------------------------------------------------------------------------------
BOT_TOKEN=$BOT_TOKEN
BOT_NAME=$BOT_SLUG

#-------------------------------------------------------------------------------
# Database
#-------------------------------------------------------------------------------
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
DB_POOL_MIN=2
DB_POOL_MAX=10

#-------------------------------------------------------------------------------
# Timezone
#-------------------------------------------------------------------------------
TZ=$TIMEZONE

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=$LOG_DIR/${BOT_SLUG}.log

#-------------------------------------------------------------------------------
# Admin
#-------------------------------------------------------------------------------
ADMIN_IDS=$ADMIN_ID

#-------------------------------------------------------------------------------
# Domain & Export
#-------------------------------------------------------------------------------
EXPORT_BASE_URL=$EXPORT_BASE_URL

#-------------------------------------------------------------------------------
# Google Calendar (optional)
#-------------------------------------------------------------------------------
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=$GOOGLE_REDIRECT_URI
OAUTH_CALLBACK_PORT=8081

#-------------------------------------------------------------------------------
# Monitoring (optional)
#-------------------------------------------------------------------------------
METRICS_ENABLED=false
HEALTH_PORT=8080
EOF

    chmod 600 "$BOT_DIR/.env"
    echo -e "${GREEN}[OK]${NC} Đã tạo cấu hình"

    # Run migrations
    echo -e "${BLUE}[INFO]${NC} Đang chạy database migrations..."
    cd "$BOT_DIR"
    source venv/bin/activate
    if alembic upgrade head 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Migrations hoàn tất"
    else
        echo -e "${YELLOW}[CẢNH BÁO]${NC} Migrations lỗi. Chạy sau: botpanel db-migrate $BOT_SLUG"
    fi
    deactivate

    # Set ownership
    chown -R botpanel:botpanel "$BOT_DIR"

    # Start bot with PM2
    echo -e "${BLUE}[INFO]${NC} Đang khởi động bot..."
    cd "$BOT_DIR"

    pm2 start "$BOT_DIR/venv/bin/python" \
        --name "$BOT_SLUG" \
        --interpreter none \
        --cwd "$BOT_DIR" \
        --output "$LOG_DIR/${BOT_SLUG}-out.log" \
        --error "$LOG_DIR/${BOT_SLUG}-error.log" \
        --log "$LOG_DIR/${BOT_SLUG}.log" \
        -- "$BOT_DIR/bot.py"

    pm2 save

    echo -e "${GREEN}[OK]${NC} Bot đã khởi động"

    # Print summary
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  TẠO BOT THÀNH CÔNG!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Thông tin Bot:${NC}"
    echo "  Tên: $BOT_SLUG"
    echo "  Thư mục: $BOT_DIR"
    echo "  PM2: $BOT_SLUG"
    echo ""
    echo -e "${YELLOW}Database:${NC}"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Mật khẩu: (đã lưu trong .env)"
    echo ""
    echo -e "${YELLOW}Các lệnh:${NC}"
    echo "  botpanel status $BOT_SLUG"
    echo "  botpanel logs $BOT_SLUG"
    echo "  botpanel restart $BOT_SLUG"
    echo ""
    echo -e "${CYAN}Test bot trong Telegram: /start${NC}"
}

#-------------------------------------------------------------------------------
# List all bots
#-------------------------------------------------------------------------------
cmd_list() {
    print_banner
    echo -e "${YELLOW}Danh sách Bot:${NC}"
    echo ""

    if [ ! -d "$BOTS_DIR" ] || [ -z "$(ls -A "$BOTS_DIR" 2>/dev/null)" ]; then
        echo "  Chưa có bot nào."
        echo ""
        echo "  Tạo mới: botpanel create"
        return
    fi

    for bot_dir in "$BOTS_DIR"/*/; do
        if [ -d "$bot_dir" ]; then
            bot_name=$(basename "$bot_dir")

            # Check PM2 status
            if pm2 describe "$bot_name" &>/dev/null; then
                status=$(pm2 jq "$bot_name" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4 2>/dev/null || echo "unknown")
                if [ "$status" = "online" ]; then
                    status_icon="${GREEN}●${NC}"
                    status="đang chạy"
                else
                    status_icon="${RED}●${NC}"
                    status="lỗi"
                fi
            else
                status_icon="${YELLOW}○${NC}"
                status="đã dừng"
            fi

            echo -e "  $status_icon $bot_name ($status)"
        fi
    done
    echo ""
}

#-------------------------------------------------------------------------------
# Delete bot
#-------------------------------------------------------------------------------
cmd_delete() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${YELLOW}[CẢNH BÁO]${NC} Sẽ xóa bot '$bot_name' và TẤT CẢ dữ liệu!"
    read -p "Bạn chắc chắn? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Đã hủy."
        return
    fi

    # Stop PM2 process
    pm2 stop "$bot_name" 2>/dev/null || true
    pm2 delete "$bot_name" 2>/dev/null || true
    pm2 save 2>/dev/null || true

    # Get database name from .env
    if [ -f "$bot_dir/.env" ]; then
        source "$bot_dir/.env"
        DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')

        # Drop database
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
        echo -e "${GREEN}[OK]${NC} Đã xóa database '$DB_NAME'"
    fi

    # Remove directory
    rm -rf "$bot_dir"

    echo -e "${GREEN}[OK]${NC} Đã xóa bot '$bot_name'"
}

#-------------------------------------------------------------------------------
# Bot management commands
#-------------------------------------------------------------------------------
cmd_start() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang khởi động bot '$bot_name'..."

    if pm2 describe "$bot_name" &>/dev/null; then
        pm2 restart "$bot_name"
    else
        # Bot not in PM2 yet, start fresh
        pm2 start "$bot_dir/venv/bin/python" \
            --name "$bot_name" \
            --interpreter none \
            --cwd "$bot_dir" \
            --output "$LOG_DIR/${bot_name}-out.log" \
            --error "$LOG_DIR/${bot_name}-error.log" \
            --log "$LOG_DIR/${bot_name}.log" \
            -- "$bot_dir/bot.py"
        pm2 save
    fi

    echo -e "${GREEN}[OK]${NC} Bot đã khởi động"
    pm2 status "$bot_name"
}

cmd_stop() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang dừng bot '$bot_name'..."
    pm2 stop "$bot_name" 2>/dev/null || true
    echo -e "${GREEN}[OK]${NC} Bot đã dừng"
}

cmd_restart() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang khởi động lại bot '$bot_name'..."
    pm2 restart "$bot_name"
    echo -e "${GREEN}[OK]${NC} Bot đã khởi động lại"
}

cmd_status() {
    local bot_name="$1"

    print_banner

    if [ -z "$bot_name" ]; then
        echo -e "${YELLOW}Trạng thái tất cả Bot:${NC}"
        pm2 status
    else
        get_bot_dir "$bot_name" >/dev/null || exit 1
        echo -e "${YELLOW}Trạng thái Bot '$bot_name':${NC}"
        pm2 status "$bot_name"
    fi

    echo ""
    echo -e "${YELLOW}Hệ thống:${NC}"
    echo "  Uptime: $(uptime -p)"
    echo "  Bộ nhớ: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
    echo "  Ổ đĩa: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
}

cmd_logs() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    pm2 logs "$bot_name" --lines 100
}

cmd_logs_err() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    pm2 logs "$bot_name" --err --lines 100
}

#-------------------------------------------------------------------------------
# Database commands
#-------------------------------------------------------------------------------
cmd_db_status() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang kiểm tra kết nối database..."
    source "$bot_dir/.env"

    DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
    DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

    if PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Kết nối database thành công"
        echo ""
        echo -e "${YELLOW}Thống kê bảng:${NC}"
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT 'users' as table_name, COUNT(*) as count FROM users
            UNION ALL SELECT 'tasks', COUNT(*) FROM tasks
            UNION ALL SELECT 'reminders', COUNT(*) FROM reminders;
        " 2>/dev/null || echo "  (chưa tạo bảng)"
    else
        echo -e "${RED}[LỖI]${NC} Kết nối database thất bại"
    fi
}

cmd_db_migrate() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang chạy database migrations..."
    cd "$bot_dir"
    source venv/bin/activate
    alembic upgrade head
    echo -e "${GREEN}[OK]${NC} Migrations hoàn tất"
}

cmd_db_backup() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang tạo bản sao lưu database..."
    source "$bot_dir/.env"

    DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
    DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"

    PGPASSWORD="$DB_PASS" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${GREEN}[OK]${NC} Đã tạo backup: $BACKUP_FILE"
        echo "  Kích thước: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo -e "${RED}[LỖI]${NC} Sao lưu thất bại"
    fi
}

cmd_db_restore() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${YELLOW}Các bản backup có sẵn:${NC}"
    ls -la "$BACKUP_DIR"/*.sql 2>/dev/null || {
        echo "Không tìm thấy backup trong $BACKUP_DIR"
        return
    }

    echo ""
    read -p "Nhập tên file backup để khôi phục: " BACKUP_FILE

    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        source "$bot_dir/.env"
        DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
        DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
        DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

        echo -e "${BLUE}[INFO]${NC} Đang khôi phục database..."
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" "$DB_NAME" < "$BACKUP_DIR/$BACKUP_FILE"
        echo -e "${GREEN}[OK]${NC} Đã khôi phục database"
    else
        echo -e "${RED}[LỖI]${NC} Không tìm thấy file backup"
    fi
}

#-------------------------------------------------------------------------------
# Configuration commands
#-------------------------------------------------------------------------------
cmd_config() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    ${EDITOR:-nano} "$bot_dir/.env"
    echo -e "${YELLOW}[LƯU Ý]${NC} Khởi động lại bot để áp dụng: botpanel restart $bot_name"
}

cmd_token() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    read -p "Nhập Bot Token mới: " NEW_TOKEN
    if [ -n "$NEW_TOKEN" ]; then
        sed -i "s/^BOT_TOKEN=.*/BOT_TOKEN=$NEW_TOKEN/" "$bot_dir/.env"
        echo -e "${GREEN}[OK]${NC} Đã cập nhật token. Khởi động lại: botpanel restart $bot_name"
    fi
}

cmd_gcal() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${CYAN}Cấu hình Google Calendar${NC}"
    echo ""

    read -p "Bật Google Calendar? (y/n): " ENABLE_GCAL

    if [[ "$ENABLE_GCAL" =~ ^[Yy]$ ]]; then
        read -p "Google Client ID: " GCAL_CLIENT_ID
        read -p "Google Client Secret: " GCAL_CLIENT_SECRET
        read -p "Redirect URI (vd: https://domain.com/oauth/callback): " GCAL_REDIRECT

        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=true/" "$bot_dir/.env"
        sed -i "s/^GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=$GCAL_CLIENT_ID/" "$bot_dir/.env"
        sed -i "s/^GOOGLE_CLIENT_SECRET=.*/GOOGLE_CLIENT_SECRET=$GCAL_CLIENT_SECRET/" "$bot_dir/.env"
        sed -i "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=$GCAL_REDIRECT|" "$bot_dir/.env"

        echo -e "${GREEN}[OK]${NC} Đã cấu hình Google Calendar. Khởi động lại: botpanel restart $bot_name"
    else
        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=false/" "$bot_dir/.env"
        echo -e "${GREEN}[OK]${NC} Đã tắt Google Calendar"
    fi
}

#-------------------------------------------------------------------------------
# Maintenance commands
#-------------------------------------------------------------------------------
cmd_update() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang cập nhật bot '$bot_name'..."

    # Stop bot
    pm2 stop "$bot_name" 2>/dev/null || true

    # Download latest template
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/haduyson/teletask.git "$TEMP_DIR" 2>/dev/null || {
        echo -e "${RED}[LỖI]${NC} Không thể tải bản cập nhật"
        rm -rf "$TEMP_DIR"
        exit 1
    }

    # Backup .env
    cp "$bot_dir/.env" "$bot_dir/.env.bak"

    # Copy new files (preserve .env, venv, __pycache__)
    rsync -av --exclude='.env' --exclude='venv' --exclude='__pycache__' \
        "$TEMP_DIR/src/templates/bot_template/" "$bot_dir/"

    rm -rf "$TEMP_DIR"

    # Restore .env
    mv "$bot_dir/.env.bak" "$bot_dir/.env"

    # Update dependencies
    cd "$bot_dir"
    source venv/bin/activate
    pip install -r requirements.txt -q

    # Run migrations
    alembic upgrade head 2>/dev/null || true

    deactivate

    # Set ownership
    chown -R botpanel:botpanel "$bot_dir"

    # Restart
    pm2 restart "$bot_name"

    echo -e "${GREEN}[OK]${NC} Cập nhật hoàn tất"
}

cmd_deps() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Đang cài lại thư viện..."
    cd "$bot_dir"
    source venv/bin/activate
    pip install -r requirements.txt --force-reinstall -q
    echo -e "${GREEN}[OK]${NC} Đã cài lại thư viện"
}

cmd_clean() {
    echo -e "${BLUE}[INFO]${NC} Đang dọn logs và file tạm..."

    # Clean old logs
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true

    # Clean PM2 logs
    pm2 flush 2>/dev/null || true

    # Clean old backups (keep last 10 per bot)
    for backup_prefix in $(ls "$BACKUP_DIR"/*.sql 2>/dev/null | sed 's/_[0-9]*_[0-9]*.sql$//' | sort -u); do
        ls -t "${backup_prefix}"_*.sql 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
    done

    echo -e "${GREEN}[OK]${NC} Đã dọn xong"
}

cmd_info() {
    print_banner
    echo -e "${YELLOW}Thông tin hệ thống:${NC}"
    echo "  Hệ điều hành: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Không rõ')"
    echo "  Kernel: $(uname -r)"
    echo "  Python: $(python${PYTHON_VERSION} --version 2>/dev/null || echo 'Không tìm thấy')"
    echo "  Node.js: $(node --version 2>/dev/null || echo 'Không tìm thấy')"
    echo "  PM2: $(pm2 --version 2>/dev/null || echo 'Không tìm thấy')"
    echo "  PostgreSQL: $(psql --version 2>/dev/null | head -1 || echo 'Không tìm thấy')"
    echo ""
    echo -e "${YELLOW}Thư mục:${NC}"
    echo "  Bots: $BOTS_DIR"
    echo "  Logs: $LOG_DIR"
    echo "  Backups: $BACKUP_DIR"
    echo ""

    # List bots
    cmd_list
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------
case "$1" in
    create)     cmd_create ;;
    list)       cmd_list ;;
    delete)     cmd_delete "$2" ;;
    start)      cmd_start "$2" ;;
    stop)       cmd_stop "$2" ;;
    restart)    cmd_restart "$2" ;;
    status)     cmd_status "$2" ;;
    logs)       cmd_logs "$2" ;;
    logs-err)   cmd_logs_err "$2" ;;
    db-status)  cmd_db_status "$2" ;;
    db-migrate) cmd_db_migrate "$2" ;;
    db-backup)  cmd_db_backup "$2" ;;
    db-restore) cmd_db_restore "$2" ;;
    config)     cmd_config "$2" ;;
    token)      cmd_token "$2" ;;
    gcal)       cmd_gcal "$2" ;;
    update)     cmd_update "$2" ;;
    deps)       cmd_deps "$2" ;;
    clean)      cmd_clean ;;
    info)       cmd_info ;;
    help|--help|-h)
        print_help ;;
    "")
        interactive_menu ;;
    *)
        echo -e "${RED}[LỖI]${NC} Lệnh không hợp lệ: $1"
        echo "Chạy 'botpanel help' để xem hướng dẫn"
        exit 1 ;;
esac
EOFCLI

    chmod +x /usr/local/bin/botpanel

    log_success "botpanel CLI created"
}

#-------------------------------------------------------------------------------
# Final summary
#-------------------------------------------------------------------------------
print_summary() {
    echo ""
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              INSTALLATION COMPLETED SUCCESSFULLY             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "${YELLOW}System Components Installed:${NC}"
    echo "  ✓ PostgreSQL database server"
    echo "  ✓ Python $PYTHON_VERSION"
    echo "  ✓ Node.js + PM2"
    echo "  ✓ botpanel CLI tool"
    echo ""

    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Create your first bot:"
    echo ""
    echo -e "     ${CYAN}botpanel create${NC}"
    echo ""
    echo "  2. Manage your bots:"
    echo ""
    echo "     botpanel list          - List all bots"
    echo "     botpanel status <bot>  - Check bot status"
    echo "     botpanel logs <bot>    - View logs"
    echo "     botpanel help          - Show all commands"
    echo ""

    echo -e "${YELLOW}Directories:${NC}"
    echo "  Bots: $BOTS_DIR/"
    echo "  Logs: $LOG_DIR/"
    echo "  Backups: $BACKUP_DIR/"
    echo ""
}

#-------------------------------------------------------------------------------
# Main installation
#-------------------------------------------------------------------------------
main() {
    print_banner
    check_root

    log_info "Starting TeleTask system installation..."
    echo ""

    prepare_system
    install_postgresql
    install_python
    install_nodejs
    create_user
    setup_pm2_startup
    create_botpanel_cli

    print_summary
}

# Run main
main "$@"
