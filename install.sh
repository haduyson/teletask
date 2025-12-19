#!/bin/bash
#
# TeleTask Bot - Cài Đặt Tự Động
# Hỗ trợ Ubuntu 22.04/24.04
#
# Sử dụng: ./install.sh [TÙY CHỌN]
#   --domain DOMAIN    Domain cho nginx (vd: teletask.example.com)
#   --email EMAIL      Email cho chứng chỉ SSL Let's Encrypt
#   --bot-name NAME    Tên bot (mặc định: TeleTask Bot)
#   --skip-nginx       Bỏ qua cài nginx
#   --skip-ssl         Bỏ qua cài SSL
#   --skip-db          Bỏ qua cài PostgreSQL (dùng database bên ngoài)
#   --help             Hiện hướng dẫn
#
# Ví dụ:
#   sudo ./install.sh --domain teletask.example.com --email admin@example.com
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
BOT_NAME="TeleTask Bot"
SKIP_NGINX=false
SKIP_SSL=false
SKIP_DB=false
PYTHON_VERSION="python3.11"
HEALTH_PORT=8080
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_ID="$(basename "$BOT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --bot-name)
            BOT_NAME="$2"
            shift 2
            ;;
        --skip-nginx)
            SKIP_NGINX=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --help)
            head -20 "$0" | tail -17
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run with sudo privileges"
        exit 1
    fi
}

check_ubuntu() {
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        log_warn "This script is designed for Ubuntu. Proceed with caution on other distributions."
    fi
}

# ============================================================================
# PHASE 1: System Dependencies
# ============================================================================
install_system_deps() {
    log_info "Installing system dependencies..."

    apt update
    apt install -y \
        $PYTHON_VERSION \
        $PYTHON_VERSION-venv \
        $PYTHON_VERSION-dev \
        build-essential \
        libpq-dev \
        curl \
        git \
        supervisor

    log_success "System dependencies installed"
}

# ============================================================================
# PHASE 2: PostgreSQL Database
# ============================================================================
install_postgresql() {
    if $SKIP_DB; then
        log_info "Skipping PostgreSQL installation (--skip-db)"
        return
    fi

    log_info "Installing PostgreSQL..."

    apt install -y postgresql postgresql-contrib

    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql

    log_success "PostgreSQL installed and running"
}

setup_database() {
    if $SKIP_DB; then
        log_info "Skipping database setup (--skip-db)"
        return
    fi

    log_info "Setting up database..."

    # Generate random password
    DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    DB_NAME="${BOT_ID//-/_}_db"
    DB_USER="${BOT_ID//-/_}_user"

    # Create database and user
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

    # Save to .env
    echo "DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME" >> "$BOT_DIR/.env"

    log_success "Database '$DB_NAME' created with user '$DB_USER'"
}

# ============================================================================
# PHASE 3: Python Virtual Environment
# ============================================================================
setup_python_venv() {
    log_info "Setting up Python virtual environment..."

    cd "$BOT_DIR"

    # Create virtual environment
    $PYTHON_VERSION -m venv venv

    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    log_success "Python virtual environment ready"
}

# ============================================================================
# PHASE 4: Nginx Reverse Proxy
# ============================================================================
install_nginx() {
    if $SKIP_NGINX; then
        log_info "Skipping nginx installation (--skip-nginx)"
        return
    fi

    log_info "Installing nginx..."

    apt install -y nginx

    systemctl start nginx
    systemctl enable nginx

    log_success "Nginx installed and running"
}

configure_nginx() {
    if $SKIP_NGINX; then
        log_info "Skipping nginx configuration (--skip-nginx)"
        return
    fi

    if [[ -z "$DOMAIN" ]]; then
        log_warn "No domain specified. Skipping nginx configuration."
        log_warn "Run with --domain to configure reverse proxy."
        return
    fi

    log_info "Configuring nginx for $DOMAIN..."

    # Create nginx configuration
    cat > "/etc/nginx/sites-available/$DOMAIN" << EOF
# Nginx reverse proxy for TeleTask Bot
# Domain: $DOMAIN
# Backend: localhost:$HEALTH_PORT (HealthCheckServer)
# Generated by install.sh on $(date)

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Reverse proxy to bot health server
    location / {
        proxy_pass http://127.0.0.1:$HEALTH_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

    # Enable site
    ln -sf "/etc/nginx/sites-available/$DOMAIN" /etc/nginx/sites-enabled/

    # Test configuration
    nginx -t

    # Reload nginx
    systemctl reload nginx

    log_success "Nginx configured for $DOMAIN"
}

# ============================================================================
# PHASE 5: SSL Certificate (Let's Encrypt)
# ============================================================================
setup_ssl() {
    if $SKIP_SSL || $SKIP_NGINX; then
        log_info "Skipping SSL setup"
        return
    fi

    if [[ -z "$DOMAIN" ]]; then
        log_warn "No domain specified. Skipping SSL setup."
        return
    fi

    if [[ -z "$EMAIL" ]]; then
        log_warn "No email specified. Skipping SSL setup."
        log_warn "Run with --email to configure SSL certificate."
        return
    fi

    log_info "Installing certbot and configuring SSL..."

    apt install -y certbot python3-certbot-nginx

    # Get certificate
    certbot --nginx -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --redirect

    log_success "SSL certificate installed for $DOMAIN"
}

# ============================================================================
# PHASE 6: Environment Configuration
# ============================================================================
setup_environment() {
    log_info "Setting up environment configuration..."

    cd "$BOT_DIR"

    # Create .env if not exists
    if [[ ! -f .env ]]; then
        cat > .env << EOF
# TeleTask Bot Configuration
# Generated by install.sh on $(date)

# Required: Get from @BotFather on Telegram
BOT_TOKEN=

# Database (auto-configured if --skip-db not used)
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Bot Settings
BOT_NAME=$BOT_NAME
TZ=Asia/Ho_Chi_Minh
LOG_LEVEL=INFO

# Domain (for static file serving)
BOT_DOMAIN=${DOMAIN:+https://$DOMAIN}

# Monitoring (comma-separated Telegram user IDs)
ADMIN_IDS=

# Health check port
HEALTH_PORT=$HEALTH_PORT

# Optional: Google Calendar
GOOGLE_CALENDAR_ENABLED=false
# GOOGLE_CREDENTIALS_FILE=

# Optional: Metrics
METRICS_ENABLED=false

# Optional: Redis caching
REDIS_ENABLED=false
# REDIS_URL=redis://localhost:6379/0

# Security: Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=
EOF
        log_info "Created .env file - please configure BOT_TOKEN and ADMIN_IDS"
    fi

    # Update config.json with domain
    if [[ -n "$DOMAIN" ]]; then
        cat > "$BOT_DIR/static/config.json" << EOF
{
  "bot_name": "$BOT_NAME",
  "domain": "https://$DOMAIN"
}
EOF
        log_info "Updated static/config.json with domain"
    fi

    log_success "Environment configuration ready"
}

# ============================================================================
# PHASE 7: PM2 Process Manager
# ============================================================================
setup_pm2() {
    log_info "Setting up PM2 process manager..."

    # Install Node.js if needed
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs
    fi

    # Install PM2 globally
    npm install -g pm2

    # Update ecosystem.config.js with actual values
    cd "$BOT_DIR"
    sed -i "s|BOT_ID_PLACEHOLDER|$BOT_ID|g" ecosystem.config.js

    # Create logs directory
    mkdir -p /home/botpanel/logs

    log_success "PM2 configured"
}

# ============================================================================
# PHASE 8: Database Migrations
# ============================================================================
run_migrations() {
    log_info "Running database migrations..."

    cd "$BOT_DIR"
    source venv/bin/activate

    # Check if DATABASE_URL is set
    if grep -q "^DATABASE_URL=" .env; then
        alembic upgrade head
        log_success "Database migrations completed"
    else
        log_warn "DATABASE_URL not configured. Skipping migrations."
        log_warn "Configure DATABASE_URL in .env, then run: alembic upgrade head"
    fi
}

# ============================================================================
# PHASE 9: Generate Encryption Key
# ============================================================================
generate_encryption_key() {
    log_info "Generating encryption key..."

    cd "$BOT_DIR"
    source venv/bin/activate

    # Generate key
    ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    # Add to .env if not already set
    if grep -q "^ENCRYPTION_KEY=$" .env; then
        sed -i "s|^ENCRYPTION_KEY=$|ENCRYPTION_KEY=$ENCRYPTION_KEY|" .env
        log_success "Encryption key generated and saved to .env"
    else
        log_info "Encryption key already configured"
    fi
}

# ============================================================================
# MAIN INSTALLATION
# ============================================================================
main() {
    echo ""
    echo "=============================================="
    echo "  TeleTask Bot - Full Stack Installer"
    echo "=============================================="
    echo ""
    echo "Bot Directory: $BOT_DIR"
    echo "Bot ID: $BOT_ID"
    [[ -n "$DOMAIN" ]] && echo "Domain: $DOMAIN"
    [[ -n "$EMAIL" ]] && echo "Email: $EMAIL"
    echo ""

    # Check prerequisites
    check_ubuntu

    # Run installation phases
    install_system_deps
    install_postgresql
    setup_database
    setup_python_venv
    install_nginx
    configure_nginx
    setup_ssl
    setup_environment
    setup_pm2
    generate_encryption_key

    # Only run migrations if database was set up
    if ! $SKIP_DB && grep -q "^DATABASE_URL=" "$BOT_DIR/.env"; then
        run_migrations
    fi

    echo ""
    echo "=============================================="
    echo "  Installation Complete!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env and set BOT_TOKEN (from @BotFather)"
    echo "  2. Edit .env and set ADMIN_IDS (your Telegram user ID)"
    echo "  3. Start the bot:"
    echo "     cd $BOT_DIR"
    echo "     pm2 start ecosystem.config.js"
    echo "     pm2 save"
    echo ""
    if [[ -n "$DOMAIN" ]]; then
        echo "  Your bot will be accessible at:"
        echo "    https://$DOMAIN/"
        echo "    https://$DOMAIN/health"
        echo "    https://$DOMAIN/user-guide.html"
        echo ""
    fi
    echo "  View logs: pm2 logs $BOT_ID"
    echo "  Restart:   pm2 restart $BOT_ID"
    echo "  Stop:      pm2 stop $BOT_ID"
    echo ""
}

# Run main if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
