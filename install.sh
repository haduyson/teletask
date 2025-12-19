#!/bin/bash
#
# TeleTask Bot - Cài Đặt Tự Động
# Hỗ trợ Ubuntu 22.04/24.04
#
# Cài đặt một lệnh:
#   curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/master/install.sh | sudo bash
#
# Hoặc với tham số:
#   curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/master/install.sh | sudo bash -s -- \
#     --domain teletask.example.com --email admin@example.com --bot-id mybot
#

set -e

# ============================================================================
# COLORS & HELPERS
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║   ████████╗███████╗██╗     ███████╗████████╗ █████╗ ███████╗██╗  ██╗  ║"
    echo "║   ╚══██╔══╝██╔════╝██║     ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝  ║"
    echo "║      ██║   █████╗  ██║     █████╗     ██║   ███████║███████╗█████╔╝   ║"
    echo "║      ██║   ██╔══╝  ██║     ██╔══╝     ██║   ██╔══██║╚════██║██╔═██╗   ║"
    echo "║      ██║   ███████╗███████╗███████╗   ██║   ██║  ██║███████║██║  ██╗  ║"
    echo "║      ╚═╝   ╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  ║"
    echo "║                                                           ║"
    echo "║           Bot Quản Lý Công Việc Telegram                  ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ============================================================================
# DEFAULT VALUES
# ============================================================================
REPO_URL="https://github.com/haduyson/teletask.git"
BOTPANEL_DIR="/home/botpanel"
BOTS_DIR="$BOTPANEL_DIR/bots"
LOGS_DIR="$BOTPANEL_DIR/logs"
PYTHON_VERSION="python3.11"
HEALTH_PORT=8080

# Parse arguments
BOT_ID=""
DOMAIN=""
EMAIL=""
BOT_TOKEN=""
ADMIN_IDS=""
SKIP_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --bot-id)      BOT_ID="$2"; shift 2 ;;
        --domain)      DOMAIN="$2"; shift 2 ;;
        --email)       EMAIL="$2"; shift 2 ;;
        --bot-token)   BOT_TOKEN="$2"; shift 2 ;;
        --admin-ids)   ADMIN_IDS="$2"; shift 2 ;;
        --skip-interactive) SKIP_INTERACTIVE=true; shift ;;
        --help)
            echo "Sử dụng: install.sh [TÙY CHỌN]"
            echo ""
            echo "Tùy chọn:"
            echo "  --bot-id ID        ID cho bot (vd: mybot)"
            echo "  --domain DOMAIN    Domain cho nginx (vd: teletask.example.com)"
            echo "  --email EMAIL      Email cho SSL Let's Encrypt"
            echo "  --bot-token TOKEN  Bot token từ @BotFather"
            echo "  --admin-ids IDS    Telegram user IDs (phân cách bằng dấu phẩy)"
            echo "  --skip-interactive Bỏ qua các câu hỏi tương tác"
            echo "  --help             Hiện hướng dẫn này"
            exit 0
            ;;
        *) log_error "Tùy chọn không hợp lệ: $1"; exit 1 ;;
    esac
done

# ============================================================================
# CHECK PREREQUISITES
# ============================================================================
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Script này cần chạy với quyền root (sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
        log_warn "Script được thiết kế cho Ubuntu. Hệ điều hành khác có thể gặp lỗi."
        read -p "Tiếp tục? (y/n): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
}

# ============================================================================
# INTERACTIVE PROMPTS
# ============================================================================
prompt_config() {
    if $SKIP_INTERACTIVE; then
        return
    fi

    echo ""
    log_info "Cấu hình bot mới"
    echo "─────────────────────────────────────────"

    # Bot ID
    if [[ -z "$BOT_ID" ]]; then
        while true; do
            read -p "Bot ID (chữ thường, không dấu, vd: mybot): " BOT_ID
            if [[ "$BOT_ID" =~ ^[a-z][a-z0-9_-]*$ ]]; then
                break
            fi
            log_error "ID không hợp lệ. Chỉ dùng chữ thường, số, gạch ngang."
        done
    fi

    # Domain
    if [[ -z "$DOMAIN" ]]; then
        read -p "Domain (vd: teletask.example.com, để trống nếu không dùng): " DOMAIN
    fi

    # Email (required if domain is set)
    if [[ -n "$DOMAIN" && -z "$EMAIL" ]]; then
        read -p "Email cho SSL ($DOMAIN): " EMAIL
    fi

    # Bot Token
    if [[ -z "$BOT_TOKEN" ]]; then
        read -p "Bot Token từ @BotFather: " BOT_TOKEN
    fi

    # Admin IDs
    if [[ -z "$ADMIN_IDS" ]]; then
        read -p "Admin Telegram ID (ID của bạn, để nhận thông báo): " ADMIN_IDS
    fi

    echo ""
    log_info "Xác nhận cấu hình:"
    echo "  Bot ID:    $BOT_ID"
    echo "  Domain:    ${DOMAIN:-'(không)'}"
    echo "  Email:     ${EMAIL:-'(không)'}"
    echo "  Bot Token: ${BOT_TOKEN:0:10}..."
    echo "  Admin IDs: $ADMIN_IDS"
    echo ""

    read -p "Tiếp tục cài đặt? (y/n): " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
}

# ============================================================================
# PHASE 1: SYSTEM DEPENDENCIES
# ============================================================================
install_system_deps() {
    log_info "Đang cài đặt dependencies hệ thống..."

    apt update -qq

    # Python
    apt install -y -qq software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    apt update -qq
    apt install -y -qq \
        $PYTHON_VERSION \
        $PYTHON_VERSION-venv \
        $PYTHON_VERSION-dev \
        build-essential \
        libpq-dev \
        curl \
        git

    log_success "Dependencies hệ thống đã cài"
}

# ============================================================================
# PHASE 2: POSTGRESQL
# ============================================================================
install_postgresql() {
    if command -v psql &> /dev/null; then
        log_info "PostgreSQL đã được cài"
        return
    fi

    log_info "Đang cài PostgreSQL..."
    apt install -y -qq postgresql postgresql-contrib
    systemctl start postgresql
    systemctl enable postgresql
    log_success "PostgreSQL đã cài và chạy"
}

setup_database() {
    log_info "Đang tạo database..."

    DB_NAME="${BOT_ID//-/_}_db"
    DB_USER="${BOT_ID//-/_}_user"
    DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)

    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true

    DATABASE_URL="postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    log_success "Database '$DB_NAME' đã tạo"
}

# ============================================================================
# PHASE 3: NGINX
# ============================================================================
install_nginx() {
    if [[ -z "$DOMAIN" ]]; then
        log_info "Bỏ qua nginx (không có domain)"
        return
    fi

    if ! command -v nginx &> /dev/null; then
        log_info "Đang cài Nginx..."
        apt install -y -qq nginx
        systemctl start nginx
        systemctl enable nginx
    fi

    log_info "Đang cấu hình Nginx cho $DOMAIN..."

    cat > "/etc/nginx/sites-available/$DOMAIN" << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:$HEALTH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
EOF

    ln -sf "/etc/nginx/sites-available/$DOMAIN" /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx

    log_success "Nginx đã cấu hình"
}

# ============================================================================
# PHASE 4: SSL CERTIFICATE
# ============================================================================
setup_ssl() {
    if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
        return
    fi

    log_info "Đang lấy chứng chỉ SSL..."

    apt install -y -qq certbot python3-certbot-nginx

    certbot --nginx -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --redirect || log_warn "SSL thất bại, kiểm tra DNS"

    log_success "SSL đã cài"
}

# ============================================================================
# PHASE 5: NODE.JS & PM2
# ============================================================================
install_pm2() {
    if command -v pm2 &> /dev/null; then
        log_info "PM2 đã được cài"
        return
    fi

    log_info "Đang cài Node.js và PM2..."

    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y -qq nodejs
    fi

    npm install -g pm2
    log_success "PM2 đã cài"
}

# ============================================================================
# PHASE 6: CLONE & SETUP BOT
# ============================================================================
setup_bot() {
    log_info "Đang cài đặt bot..."

    # Create directories
    mkdir -p "$BOTS_DIR" "$LOGS_DIR"

    BOT_DIR="$BOTS_DIR/$BOT_ID"

    # Clone repository
    if [[ -d "$BOT_DIR" ]]; then
        log_warn "Thư mục $BOT_DIR đã tồn tại"
        read -p "Ghi đè? (y/n): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && rm -rf "$BOT_DIR"
    fi

    git clone "$REPO_URL" "$BOT_DIR"
    cd "$BOT_DIR"

    # Create virtual environment
    $PYTHON_VERSION -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    # Generate encryption key
    ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    # Create .env file
    cat > "$BOT_DIR/.env" << EOF
# TeleTask Bot Configuration
# Bot ID: $BOT_ID
# Generated: $(date)

# Telegram Bot
BOT_TOKEN=$BOT_TOKEN
BOT_NAME=$BOT_ID

# Database
DATABASE_URL=$DATABASE_URL

# Domain
BOT_DOMAIN=${DOMAIN:+https://$DOMAIN}

# Timezone
TZ=Asia/Ho_Chi_Minh

# Monitoring
ADMIN_IDS=$ADMIN_IDS
HEALTH_PORT=$HEALTH_PORT
LOG_LEVEL=INFO

# Security
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Optional
GOOGLE_CALENDAR_ENABLED=false
METRICS_ENABLED=false
REDIS_ENABLED=false
EOF

    # Update ecosystem.config.js
    sed -i "s|BOT_ID_PLACEHOLDER|$BOT_ID|g" ecosystem.config.js

    # Update static/config.json
    cat > "$BOT_DIR/static/config.json" << EOF
{
  "bot_name": "$BOT_ID",
  "domain": "${DOMAIN:+https://$DOMAIN}"
}
EOF

    # Run database migrations
    log_info "Đang chạy database migrations..."
    alembic upgrade head

    log_success "Bot đã cài đặt tại $BOT_DIR"
}

# ============================================================================
# PHASE 7: INSTALL BOTPANEL
# ============================================================================
install_botpanel() {
    log_info "Đang cài đặt BotPanel..."

    # Download botpanel script
    BOTPANEL_SCRIPT="$BOTPANEL_DIR/botpanel"

    cat > "$BOTPANEL_SCRIPT" << 'BOTPANEL_EOF'
#!/bin/bash
#
# BotPanel - Quản Lý Telegram Bots
# Hỗ trợ Ubuntu 22.04/24.04
#
# Sử dụng:
#   botpanel          # Menu tương tác
#   botpanel status   # Xem trạng thái
#   botpanel logs <bot-id>
#

# ============================================================================
# COLORS & HELPERS
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

BOTPANEL_DIR="/home/botpanel"
BOTS_DIR="$BOTPANEL_DIR/bots"
LOGS_DIR="$BOTPANEL_DIR/logs"
BACKUPS_DIR="$BOTPANEL_DIR/backups"
INSTALLER_URL="https://raw.githubusercontent.com/haduyson/teletask/master/install.sh"

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================================
# BANNER
# ============================================================================
print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║   ██████╗  ██████╗ ████████╗██████╗  █████╗ ███╗   ██╗   ║"
    echo "║   ██╔══██╗██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗████╗  ██║   ║"
    echo "║   ██████╔╝██║   ██║   ██║   ██████╔╝███████║██╔██╗ ██║   ║"
    echo "║   ██╔══██╗██║   ██║   ██║   ██╔═══╝ ██╔══██║██║╚██╗██║   ║"
    echo "║   ██████╔╝╚██████╔╝   ██║   ██║     ██║  ██║██║ ╚████║   ║"
    echo "║   ╚═════╝  ╚═════╝    ╚═╝   ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝   ║"
    echo "║                                                           ║"
    echo "║              Quản Lý Telegram Bots                        ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ============================================================================
# BOT STATUS HELPERS
# ============================================================================

get_bot_status() {
    local bot_name="$1"
    pm2 jlist 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for p in data:
        if p['name'] == '$bot_name':
            print(p['pm2_env']['status'])
            break
    else:
        print('not_running')
except:
    print('unknown')
" 2>/dev/null
}

# ============================================================================
# BOT MANAGEMENT FUNCTIONS
# ============================================================================

# List all bots
list_bots() {
    echo -e "\n${BOLD}Danh sách bots:${NC}"
    echo "─────────────────────────────────────────"

    if [[ ! -d "$BOTS_DIR" ]] || [[ -z "$(ls -A "$BOTS_DIR" 2>/dev/null)" ]]; then
        echo -e "${YELLOW}Chưa có bot nào được cài đặt${NC}"
        return
    fi

    for bot_dir in "$BOTS_DIR"/*/; do
        if [[ -d "$bot_dir" ]]; then
            bot_name=$(basename "$bot_dir")
            status=$(get_bot_status "$bot_name")

            case "$status" in
                "online")
                    status_icon="${GREEN}●${NC}"
                    status_text="${GREEN}Đang chạy${NC}"
                    ;;
                "stopped")
                    status_icon="${RED}●${NC}"
                    status_text="${RED}Đã dừng${NC}"
                    ;;
                "errored")
                    status_icon="${RED}●${NC}"
                    status_text="${RED}Lỗi${NC}"
                    ;;
                *)
                    status_icon="${YELLOW}●${NC}"
                    status_text="${YELLOW}Không chạy${NC}"
                    ;;
            esac

            echo -e "  $status_icon ${BOLD}$bot_name${NC} - $status_text"
        fi
    done
    echo ""
}

# Select a bot from list
select_bot() {
    local prompt="$1"
    local bots=()
    local i=1

    if [[ ! -d "$BOTS_DIR" ]] || [[ -z "$(ls -A "$BOTS_DIR" 2>/dev/null)" ]]; then
        log_warn "Chưa có bot nào được cài đặt"
        SELECTED_BOT=""
        return 1
    fi

    echo -e "\n${BOLD}$prompt${NC}"
    echo "─────────────────────────────────────────"

    for bot_dir in "$BOTS_DIR"/*/; do
        if [[ -d "$bot_dir" ]]; then
            local bot_name=$(basename "$bot_dir")
            local status=$(get_bot_status "$bot_name")
            local status_icon
            case "$status" in
                "online") status_icon="${GREEN}●${NC}" ;;
                "stopped") status_icon="${RED}●${NC}" ;;
                *) status_icon="${YELLOW}●${NC}" ;;
            esac
            echo -e "  ${DIM}$i)${NC} $status_icon $bot_name"
            bots+=("$bot_name")
            ((i++))
        fi
    done
    echo -e "  ${DIM}0)${NC} Quay lại"
    echo ""

    read -p "Chọn [0-$((i-1))]: " choice

    if [[ "$choice" == "0" ]] || [[ -z "$choice" ]]; then
        SELECTED_BOT=""
        return 1
    fi

    if [[ "$choice" =~ ^[0-9]+$ ]] && [[ $choice -ge 1 ]] && [[ $choice -le ${#bots[@]} ]]; then
        SELECTED_BOT="${bots[$((choice-1))]}"
        return 0
    else
        log_error "Lựa chọn không hợp lệ"
        SELECTED_BOT=""
        return 1
    fi
}

# Show PM2 status
show_status() {
    echo -e "\n${BOLD}Trạng thái PM2:${NC}"
    echo "─────────────────────────────────────────"
    pm2 status
}

# Start a bot
start_bot() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để khởi động:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    local bot_dir="$BOTS_DIR/$bot_id"

    if [[ ! -d "$bot_dir" ]]; then
        log_error "Bot '$bot_id' không tồn tại"
        return 1
    fi

    log_info "Đang khởi động $bot_id..."

    if pm2 describe "$bot_id" &>/dev/null; then
        pm2 start "$bot_id"
    else
        cd "$bot_dir"
        if [[ -f "ecosystem.config.js" ]]; then
            pm2 start ecosystem.config.js
        else
            source venv/bin/activate
            pm2 start bot.py --name "$bot_id" --interpreter "$bot_dir/venv/bin/python"
        fi
    fi

    pm2 save
    log_success "Bot '$bot_id' đã khởi động"
}

# Stop a bot
stop_bot() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để dừng:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    log_info "Đang dừng $bot_id..."
    pm2 stop "$bot_id"
    pm2 save
    log_success "Bot '$bot_id' đã dừng"
}

# Restart a bot
restart_bot() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để khởi động lại:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    log_info "Đang khởi động lại $bot_id..."
    pm2 restart "$bot_id"
    pm2 save
    log_success "Bot '$bot_id' đã khởi động lại"
}

# View logs
view_logs() {
    local bot_id="$1"
    local lines="${2:-50}"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để xem logs:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    echo -e "\n${BOLD}Logs của $bot_id (${lines} dòng cuối):${NC}"
    echo "─────────────────────────────────────────"
    echo -e "${YELLOW}Nhấn Ctrl+C để thoát${NC}\n"

    pm2 logs "$bot_id" --lines "$lines"
}

# Add new bot
add_bot() {
    echo -e "\n${BOLD}Thêm Bot Mới${NC}"
    echo "─────────────────────────────────────────"
    echo -e "  ${DIM}1)${NC} 📦 Cài đặt từ GitHub (TeleTask)"
    echo -e "  ${DIM}2)${NC} 📁 Cài đặt từ thư mục local"
    echo -e "  ${DIM}0)${NC} Quay lại"
    echo ""

    read -p "Chọn [0-2]: " choice

    case $choice in
        1)
            log_info "Đang tải installer..."
            curl -fsSL "$INSTALLER_URL" | sudo bash
            ;;
        2)
            read -p "Đường dẫn thư mục bot: " bot_path
            if [[ ! -d "$bot_path" ]]; then
                log_error "Thư mục không tồn tại"
                return 1
            fi

            read -p "Bot ID (tên thư mục trong bots/): " bot_id
            if [[ -z "$bot_id" ]]; then
                log_error "Chưa nhập Bot ID"
                return 1
            fi

            local dest="$BOTS_DIR/$bot_id"
            if [[ -d "$dest" ]]; then
                log_error "Bot '$bot_id' đã tồn tại"
                return 1
            fi

            log_info "Đang copy bot..."
            cp -r "$bot_path" "$dest"
            log_success "Bot đã được thêm vào $dest"

            read -p "Khởi động bot ngay? (y/n): " -n 1 -r
            echo
            [[ $REPLY =~ ^[Yy]$ ]] && start_bot "$bot_id"
            ;;
        0|"")
            return 0
            ;;
        *)
            log_error "Lựa chọn không hợp lệ"
            ;;
    esac
}

# Remove bot
remove_bot() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để xóa:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    local bot_dir="$BOTS_DIR/$bot_id"

    if [[ ! -d "$bot_dir" ]]; then
        log_error "Bot '$bot_id' không tồn tại"
        return 1
    fi

    echo -e "\n${RED}CẢNH BÁO: Bạn sắp xóa bot '$bot_id'${NC}"
    echo "Thư mục: $bot_dir"
    read -p "Nhập 'DELETE' để xác nhận: " confirm

    if [[ "$confirm" != "DELETE" ]]; then
        log_warn "Đã hủy xóa"
        return 1
    fi

    pm2 stop "$bot_id" 2>/dev/null
    pm2 delete "$bot_id" 2>/dev/null
    pm2 save

    local backup_name="${bot_id}_$(date +%Y%m%d_%H%M%S).tar.gz"
    log_info "Đang backup trước khi xóa..."
    mkdir -p "$BACKUPS_DIR"
    tar -czf "$BACKUPS_DIR/$backup_name" -C "$BOTS_DIR" "$bot_id"
    log_success "Backup: $BACKUPS_DIR/$backup_name"

    rm -rf "$bot_dir"
    log_success "Bot '$bot_id' đã xóa"
}

# Backup bot
backup_bot() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để backup:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    local bot_dir="$BOTS_DIR/$bot_id"

    if [[ ! -d "$bot_dir" ]]; then
        log_error "Bot '$bot_id' không tồn tại"
        return 1
    fi

    mkdir -p "$BACKUPS_DIR"
    local backup_name="${bot_id}_$(date +%Y%m%d_%H%M%S).tar.gz"

    log_info "Đang backup $bot_id..."

    tar --exclude='venv' --exclude='__pycache__' --exclude='.git' \
        -czf "$BACKUPS_DIR/$backup_name" -C "$BOTS_DIR" "$bot_id"

    local size=$(du -h "$BACKUPS_DIR/$backup_name" | cut -f1)
    log_success "Backup hoàn tất: $BACKUPS_DIR/$backup_name ($size)"
}

# List backups
list_backups() {
    echo -e "\n${BOLD}Danh sách Backups:${NC}"
    echo "─────────────────────────────────────────"

    if [[ ! -d "$BACKUPS_DIR" ]] || [[ -z "$(ls -A "$BACKUPS_DIR" 2>/dev/null)" ]]; then
        echo -e "${YELLOW}Chưa có backup nào${NC}"
        return
    fi

    ls -lh "$BACKUPS_DIR"/*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
}

# Restore bot
restore_bot() {
    if [[ ! -d "$BACKUPS_DIR" ]] || [[ -z "$(ls -A "$BACKUPS_DIR"/*.tar.gz 2>/dev/null)" ]]; then
        log_warn "Chưa có backup nào"
        return 1
    fi

    echo -e "\n${BOLD}Chọn backup để restore:${NC}"
    echo "─────────────────────────────────────────"

    local backups=()
    local i=1
    for f in "$BACKUPS_DIR"/*.tar.gz; do
        local fname=$(basename "$f")
        local size=$(du -h "$f" | cut -f1)
        echo -e "  ${DIM}$i)${NC} $fname ($size)"
        backups+=("$f")
        ((i++))
    done
    echo -e "  ${DIM}0)${NC} Quay lại"
    echo ""

    read -p "Chọn [0-$((i-1))]: " choice

    if [[ "$choice" == "0" ]] || [[ -z "$choice" ]]; then
        return 1
    fi

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ $choice -lt 1 ]] || [[ $choice -gt ${#backups[@]} ]]; then
        log_error "Lựa chọn không hợp lệ"
        return 1
    fi

    local backup_file="${backups[$((choice-1))]}"
    log_info "Đang restore từ $backup_file..."

    local bot_id=$(basename "$backup_file" | sed 's/_[0-9]*_[0-9]*.tar.gz//')

    read -p "Bot ID để restore (mặc định: $bot_id): " new_bot_id
    new_bot_id="${new_bot_id:-$bot_id}"

    local dest="$BOTS_DIR/$new_bot_id"

    if [[ -d "$dest" ]]; then
        log_warn "Bot '$new_bot_id' đã tồn tại"
        read -p "Ghi đè? (y/n): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && return 1
        rm -rf "$dest"
    fi

    tar -xzf "$backup_file" -C "$BOTS_DIR"

    if [[ "$bot_id" != "$new_bot_id" ]]; then
        mv "$BOTS_DIR/$bot_id" "$dest"
    fi

    log_success "Restore hoàn tất: $dest"

    log_info "Đang tạo lại virtual environment..."
    cd "$dest"
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q

    log_success "Virtual environment đã tạo"

    read -p "Khởi động bot ngay? (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && start_bot "$new_bot_id"
}

# Edit .env
edit_env() {
    local bot_id="$1"

    if [[ -z "$bot_id" ]]; then
        if ! select_bot "Chọn bot để chỉnh sửa .env:"; then
            return 1
        fi
        bot_id="$SELECTED_BOT"
    fi

    if [[ -z "$bot_id" ]]; then
        return 1
    fi

    local env_file="$BOTS_DIR/$bot_id/.env"

    if [[ ! -f "$env_file" ]]; then
        log_error "File .env không tồn tại: $env_file"
        return 1
    fi

    ${EDITOR:-nano} "$env_file"

    read -p "Khởi động lại bot để áp dụng? (y/n): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && restart_bot "$bot_id"
}

# System info
system_info() {
    echo -e "\n${BOLD}Thông Tin Hệ Thống:${NC}"
    echo "─────────────────────────────────────────"

    echo -e "${CYAN}OS:${NC} $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo -e "${CYAN}Kernel:${NC} $(uname -r)"
    echo -e "${CYAN}Uptime:${NC} $(uptime -p)"
    echo -e "${CYAN}Load:${NC} $(cat /proc/loadavg | awk '{print $1, $2, $3}')"

    echo ""
    echo -e "${CYAN}Memory:${NC}"
    free -h | grep -E "^Mem:" | awk '{printf "  Total: %s | Used: %s | Free: %s\n", $2, $3, $4}'

    echo ""
    echo -e "${CYAN}Disk (/home):${NC}"
    df -h /home | tail -1 | awk '{printf "  Total: %s | Used: %s (%s) | Free: %s\n", $2, $3, $5, $4}'

    echo ""
    echo -e "${CYAN}PM2:${NC}"
    echo "  Version: $(pm2 -v)"
    echo "  Processes: $(pm2 jlist 2>/dev/null | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)"

    echo ""
    echo -e "${CYAN}PostgreSQL:${NC}"
    if systemctl is-active postgresql &>/dev/null; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${RED}Stopped${NC}"
    fi

    echo ""
    echo -e "${CYAN}Nginx:${NC}"
    if systemctl is-active nginx &>/dev/null; then
        echo -e "  Status: ${GREEN}Running${NC}"
    else
        echo -e "  Status: ${RED}Stopped${NC}"
    fi

    echo ""
}

# ============================================================================
# MAIN MENU
# ============================================================================
show_menu() {
    echo -e "${BOLD}Menu Chính:${NC}"
    echo "─────────────────────────────────────────"
    echo ""
    echo -e "  ${DIM}1)${NC} 📊 Xem trạng thái bots"
    echo -e "  ${DIM}2)${NC} ▶️  Khởi động bot"
    echo -e "  ${DIM}3)${NC} ⏹️  Dừng bot"
    echo -e "  ${DIM}4)${NC} 🔄 Khởi động lại bot"
    echo -e "  ${DIM}5)${NC} 📋 Xem logs"
    echo ""
    echo -e "  ${DIM}6)${NC} ➕ Thêm bot mới"
    echo -e "  ${DIM}7)${NC} 🗑️  Xóa bot"
    echo -e "  ${DIM}8)${NC} ⚙️  Chỉnh sửa .env"
    echo ""
    echo -e "  ${DIM}9)${NC} 💾 Backup bot"
    echo -e "  ${DIM}10)${NC} 📥 Restore bot"
    echo -e "  ${DIM}11)${NC} 📁 Danh sách backups"
    echo ""
    echo -e "  ${DIM}12)${NC} ℹ️  Thông tin hệ thống"
    echo ""
    echo -e "  ${DIM}0)${NC} 🚪 Thoát"
    echo ""
}

interactive_menu() {
    while true; do
        print_banner
        list_bots
        show_menu

        read -p "Chọn [0-12]: " choice

        case $choice in
            1) show_status; read -p "Nhấn Enter để tiếp tục..." ;;
            2) start_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            3) stop_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            4) restart_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            5) view_logs ;;
            6) add_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            7) remove_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            8) edit_env ;;
            9) backup_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            10) restore_bot; read -p "Nhấn Enter để tiếp tục..." ;;
            11) list_backups; read -p "Nhấn Enter để tiếp tục..." ;;
            12) system_info; read -p "Nhấn Enter để tiếp tục..." ;;
            0|"") echo -e "\n${GREEN}Tạm biệt!${NC}\n"; exit 0 ;;
            *) log_error "Lựa chọn không hợp lệ" ;;
        esac
    done
}

# ============================================================================
# CLI MODE
# ============================================================================
print_usage() {
    echo "Sử dụng: botpanel [LỆNH] [TÙY CHỌN]"
    echo ""
    echo "Lệnh:"
    echo "  status              Xem trạng thái tất cả bots"
    echo "  list                Liệt kê các bots"
    echo "  start <bot-id>      Khởi động bot"
    echo "  stop <bot-id>       Dừng bot"
    echo "  restart <bot-id>    Khởi động lại bot"
    echo "  logs <bot-id>       Xem logs (thêm -f để follow)"
    echo "  add                 Thêm bot mới"
    echo "  remove <bot-id>     Xóa bot"
    echo "  backup <bot-id>     Backup bot"
    echo "  restore <file>      Restore từ backup"
    echo "  backups             Liệt kê backups"
    echo "  env <bot-id>        Chỉnh sửa .env"
    echo "  info                Thông tin hệ thống"
    echo "  help                Hiển thị trợ giúp"
    echo ""
    echo "Không có lệnh: Mở menu tương tác"
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    if [[ $# -eq 0 ]]; then
        interactive_menu
        exit 0
    fi

    case "$1" in
        status)
            show_status
            ;;
        list)
            list_bots
            ;;
        start)
            start_bot "$2"
            ;;
        stop)
            stop_bot "$2"
            ;;
        restart)
            restart_bot "$2"
            ;;
        logs)
            if [[ "$3" == "-f" ]] || [[ "$2" == "-f" ]]; then
                pm2 logs "${2:-}" --lines 100
            else
                view_logs "$2" 50
            fi
            ;;
        add)
            add_bot
            ;;
        remove|delete)
            remove_bot "$2"
            ;;
        backup)
            backup_bot "$2"
            ;;
        restore)
            restore_bot "$2"
            ;;
        backups)
            list_backups
            ;;
        env)
            edit_env "$2"
            ;;
        info)
            system_info
            ;;
        help|--help|-h)
            print_usage
            ;;
        *)
            log_error "Lệnh không hợp lệ: $1"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
BOTPANEL_EOF

    chmod +x "$BOTPANEL_SCRIPT"
    ln -sf "$BOTPANEL_SCRIPT" /usr/local/bin/botpanel

    log_success "BotPanel đã cài đặt (chạy: botpanel)"
}

# ============================================================================
# PHASE 8: START BOT
# ============================================================================
start_bot() {
    log_info "Đang khởi động bot..."

    cd "$BOT_DIR"
    pm2 start ecosystem.config.js
    pm2 save

    # Setup PM2 startup
    pm2 startup systemd -u root --hp /root 2>/dev/null || true

    log_success "Bot đã khởi động"
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    print_banner

    check_root
    check_ubuntu
    prompt_config

    # Validate required fields
    if [[ -z "$BOT_ID" || -z "$BOT_TOKEN" ]]; then
        log_error "Thiếu Bot ID hoặc Bot Token"
        exit 1
    fi

    echo ""
    log_info "Bắt đầu cài đặt..."
    echo "═══════════════════════════════════════════════════════════"

    install_system_deps
    install_postgresql
    setup_database
    install_nginx
    setup_ssl
    install_pm2
    setup_bot
    install_botpanel
    start_bot

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${GREEN}CÀI ĐẶT HOÀN TẤT!${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Bot đã được cài đặt tại: $BOT_DIR"
    echo ""
    if [[ -n "$DOMAIN" ]]; then
        echo "Truy cập:"
        echo "  https://$DOMAIN/"
        echo "  https://$DOMAIN/health"
        echo "  https://$DOMAIN/user-guide.html"
        echo ""
    fi
    echo -e "${CYAN}Quản lý bot với BotPanel:${NC}"
    echo "  botpanel              # Menu tương tác (phím mũi tên)"
    echo "  botpanel status       # Xem trạng thái"
    echo "  botpanel logs $BOT_ID # Xem logs"
    echo "  botpanel restart $BOT_ID"
    echo ""
    echo "Cấu hình: $BOT_DIR/.env"
    echo ""
}

main "$@"
