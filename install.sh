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
# PHASE 7: START BOT
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
    echo "Quản lý bot:"
    echo "  pm2 logs $BOT_ID       # Xem logs"
    echo "  pm2 restart $BOT_ID    # Khởi động lại"
    echo "  pm2 stop $BOT_ID       # Dừng bot"
    echo ""
    echo "Cấu hình: $BOT_DIR/.env"
    echo ""
}

main "$@"
