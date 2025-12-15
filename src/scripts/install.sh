#!/bin/bash
#===============================================================================
# TeleTask Installation Script
# One-command installation for Ubuntu 22.04/24.04 LTS
# Usage: curl -sSL https://domain/install.sh | sudo bash
#===============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BOTPANEL_USER="botpanel"
BOTPANEL_HOME="/home/$BOTPANEL_USER"
PG_VERSION="15"
NODE_VERSION="20"
PYTHON_VERSION="3.11"

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

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
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Script phai chay voi quyen root. Su dung: sudo bash install.sh"
    fi
}

check_ubuntu() {
    if ! grep -qE "Ubuntu (22|24)\." /etc/os-release 2>/dev/null; then
        log_error "Chi ho tro Ubuntu 22.04 hoac 24.04 LTS"
    fi
    log_success "He dieu hanh: $(lsb_release -ds)"
}

check_resources() {
    local mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_gb=$((mem_kb / 1024 / 1024))

    if [[ $mem_gb -lt 1 ]]; then
        log_warn "RAM < 1GB. Khuyen nghi toi thieu 1GB"
    fi

    local disk_gb=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
    if [[ $disk_gb -lt 20 ]]; then
        log_warn "Dung luong trong < 20GB. Khuyen nghi toi thieu 20GB"
    fi

    log_success "RAM: ${mem_gb}GB, Disk available: ${disk_gb}GB"
}

#-------------------------------------------------------------------------------
# Installation Steps
#-------------------------------------------------------------------------------

install_system_packages() {
    log_info "Dang cap nhat he thong..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

    log_info "Dang cai dat cac goi co ban..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        curl \
        wget \
        git \
        jq \
        unzip \
        build-essential \
        libssl-dev \
        libffi-dev

    log_success "Cai dat goi co ban thanh cong"
}

install_python() {
    log_info "Dang cai dat Python ${PYTHON_VERSION}..."

    # Add deadsnakes PPA for Python versions
    add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    apt-get update -qq

    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip

    # NOTE: Do NOT change system default python3 - it breaks apt on Ubuntu 24.04
    # Bots will explicitly use python3.11

    log_success "Python $(python${PYTHON_VERSION} --version) da cai dat"
}

install_postgresql() {
    log_info "Dang cai dat PostgreSQL ${PG_VERSION}..."

    # Add PostgreSQL APT repository
    wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg 2>/dev/null || true
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list

    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
        postgresql-${PG_VERSION} \
        postgresql-contrib-${PG_VERSION}

    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql

    log_success "PostgreSQL ${PG_VERSION} da cai dat va khoi dong"
}

install_nodejs() {
    log_info "Dang cai dat Node.js ${NODE_VERSION}..."

    # Install Node.js from NodeSource
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - > /dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs

    log_success "Node.js $(node --version) da cai dat"
}

install_pm2() {
    log_info "Dang cai dat PM2..."

    npm install -g pm2 --silent

    log_success "PM2 $(pm2 --version) da cai dat"
}

install_redis() {
    log_info "Dang cai dat Redis..."

    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq redis-server

    # Configure Redis
    sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf

    systemctl restart redis-server
    systemctl enable redis-server

    log_success "Redis da cai dat va khoi dong"
}

install_nginx() {
    log_info "Dang cai dat Nginx..."

    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx

    systemctl start nginx
    systemctl enable nginx

    log_success "Nginx da cai dat va khoi dong"
}

create_user() {
    log_info "Dang tao user ${BOTPANEL_USER}..."

    if id "$BOTPANEL_USER" &>/dev/null; then
        log_warn "User ${BOTPANEL_USER} da ton tai"
    else
        useradd -m -s /bin/bash "$BOTPANEL_USER"
        log_success "User ${BOTPANEL_USER} da tao"
    fi
}

create_directories() {
    log_info "Dang tao cau truc thu muc..."

    mkdir -p "${BOTPANEL_HOME}"/{bots,config,logs,scripts,templates,monitoring}
    mkdir -p "${BOTPANEL_HOME}/backups"/{daily,manual}

    # Create global config file
    cat > "${BOTPANEL_HOME}/config/global.conf" << 'EOF'
# TeleTask Global Configuration
# Generated by install.sh

# Database
PG_HOST=localhost
PG_PORT=5432
PG_USER=botpanel

# Timezone
TZ=Asia/Ho_Chi_Minh

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30

# Backup
BACKUP_RETENTION_DAYS=7
BACKUP_TIME="03:00"

# Monitoring (optional)
PROMETHEUS_ENABLED=false
GRAFANA_ENABLED=false
EOF

    # Create admin config file
    cat > "${BOTPANEL_HOME}/config/admin.conf" << 'EOF'
# Admin Configuration
# Add Telegram user IDs for admin notifications

ADMIN_IDS=()
ALERT_ON_ERROR=true
ALERT_ON_RESTART=true
EOF

    log_success "Cau truc thu muc da tao"
}

configure_postgresql() {
    log_info "Dang cau hinh PostgreSQL..."

    # Generate random password
    local pg_password=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

    # Create PostgreSQL user
    sudo -u postgres psql -c "CREATE USER ${BOTPANEL_USER} WITH PASSWORD '${pg_password}';" 2>/dev/null || \
        sudo -u postgres psql -c "ALTER USER ${BOTPANEL_USER} WITH PASSWORD '${pg_password}';"

    # Grant CREATEDB privilege
    sudo -u postgres psql -c "ALTER USER ${BOTPANEL_USER} CREATEDB;"

    # Save password to config
    echo "PG_PASSWORD=${pg_password}" >> "${BOTPANEL_HOME}/config/global.conf"
    chmod 600 "${BOTPANEL_HOME}/config/global.conf"

    log_success "PostgreSQL user da cau hinh"
}

setup_pm2_startup() {
    log_info "Dang cau hinh PM2 startup..."

    # Setup PM2 startup for botpanel user
    env PATH=$PATH:/usr/bin pm2 startup systemd -u "$BOTPANEL_USER" --hp "$BOTPANEL_HOME" --silent

    # Initialize PM2 for user
    su - "$BOTPANEL_USER" -c "pm2 save" 2>/dev/null || true

    log_success "PM2 startup da cau hinh"
}

install_botpanel_cli() {
    log_info "Dang cai dat BotPanel CLI..."

    # Copy CLI script (will be created in Phase 02)
    # For now, create placeholder
    cat > "${BOTPANEL_HOME}/botpanel.sh" << 'BOTPANEL_SCRIPT'
#!/bin/bash
#===============================================================================
# BotPanel CLI - TeleTask Bot Management
# Version: 1.0.0
#===============================================================================

echo "BotPanel CLI"
echo "Se duoc cap nhat trong Phase 02"
echo ""
echo "Phien ban hien tai: Placeholder"
BOTPANEL_SCRIPT

    chmod +x "${BOTPANEL_HOME}/botpanel.sh"

    # Create symlink for system-wide access
    ln -sf "${BOTPANEL_HOME}/botpanel.sh" /usr/local/bin/botpanel

    log_success "BotPanel CLI da cai dat (chay: botpanel)"
}

copy_bot_template() {
    log_info "Dang tao bot template..."

    local template_dir="${BOTPANEL_HOME}/templates/bot_template"
    mkdir -p "$template_dir"

    # Create template structure (will be populated in later phases)
    mkdir -p "${template_dir}"/{handlers,services,utils,config,scheduler,database,monitoring}

    # Create placeholder requirements.txt
    cat > "${template_dir}/requirements.txt" << 'EOF'
# TeleTask Bot Dependencies
python-telegram-bot>=21.0
asyncpg>=0.29.0
APScheduler>=3.10.0
alembic>=1.13.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
pytz>=2024.1
redis>=5.0.0
EOF

    # Create placeholder bot.py
    cat > "${template_dir}/bot.py" << 'EOF'
#!/usr/bin/env python3
"""
TeleTask Bot - Entry Point
Template file - will be implemented in Phase 04
"""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("TeleTask Bot starting...")
    logger.info("Template - Se duoc cap nhat trong Phase 04")

if __name__ == "__main__":
    asyncio.run(main())
EOF

    # Create .env.example
    cat > "${template_dir}/.env.example" << 'EOF'
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token
BOT_NAME=my_bot

# Database
DATABASE_URL=postgresql://botpanel:password@localhost:5432/bot_db

# Timezone
TZ=Asia/Ho_Chi_Minh

# Logging
LOG_LEVEL=INFO

# Admin
ADMIN_IDS=123456789,987654321
EOF

    log_success "Bot template da tao"
}

set_permissions() {
    log_info "Dang cau hinh quyen truy cap..."

    chown -R "${BOTPANEL_USER}:${BOTPANEL_USER}" "$BOTPANEL_HOME"
    chmod 700 "${BOTPANEL_HOME}/config"
    chmod 600 "${BOTPANEL_HOME}/config"/*.conf

    log_success "Quyen truy cap da cau hinh"
}

setup_cron_backup() {
    log_info "Dang cau hinh backup tu dong..."

    # Create backup script
    cat > "${BOTPANEL_HOME}/scripts/daily_backup.sh" << 'EOF'
#!/bin/bash
# Daily backup script for TeleTask

BACKUP_DIR="/home/botpanel/backups/daily"
DATE=$(date +%Y%m%d)
RETENTION_DAYS=7

# Backup each bot database
for bot_dir in /home/botpanel/bots/*/; do
    if [[ -d "$bot_dir" ]]; then
        bot_name=$(basename "$bot_dir")
        db_name="${bot_name}_db"

        # Dump database
        pg_dump -U botpanel "$db_name" > "${BACKUP_DIR}/${bot_name}_${DATE}.sql" 2>/dev/null || true

        # Compress
        gzip -f "${BACKUP_DIR}/${bot_name}_${DATE}.sql" 2>/dev/null || true
    fi
done

# Remove old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

echo "Backup completed: $(date)"
EOF

    chmod +x "${BOTPANEL_HOME}/scripts/daily_backup.sh"

    # Add cron job for botpanel user
    (crontab -u "$BOTPANEL_USER" -l 2>/dev/null; echo "0 3 * * * ${BOTPANEL_HOME}/scripts/daily_backup.sh >> ${BOTPANEL_HOME}/logs/backup.log 2>&1") | sort -u | crontab -u "$BOTPANEL_USER" -

    log_success "Backup tu dong da cau hinh (03:00 hang ngay)"
}

print_summary() {
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}           CAI DAT TELETASK THANH CONG!${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo ""
    echo -e "  ${BLUE}Thu muc:${NC}        ${BOTPANEL_HOME}"
    echo -e "  ${BLUE}User:${NC}           ${BOTPANEL_USER}"
    echo -e "  ${BLUE}CLI:${NC}            botpanel"
    echo ""
    echo -e "  ${BLUE}Dich vu:${NC}"
    echo "    - PostgreSQL ${PG_VERSION}: $(systemctl is-active postgresql)"
    echo "    - Redis:               $(systemctl is-active redis-server)"
    echo "    - Nginx:               $(systemctl is-active nginx)"
    echo "    - PM2:                 installed"
    echo ""
    echo -e "  ${YELLOW}Buoc tiep theo:${NC}"
    echo "    1. Chay: botpanel"
    echo "    2. Chon 'Tao bot moi' de tao bot dau tien"
    echo "    3. Nhap Telegram Bot Token tu @BotFather"
    echo ""
    echo -e "${GREEN}================================================================${NC}"
}

#-------------------------------------------------------------------------------
# Main Execution
#-------------------------------------------------------------------------------

main() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}           TELETASK INSTALLATION SCRIPT${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""

    check_root
    check_ubuntu
    check_resources

    install_system_packages
    install_python
    install_postgresql
    install_nodejs
    install_pm2
    install_redis
    install_nginx

    create_user
    create_directories
    configure_postgresql
    setup_pm2_startup
    install_botpanel_cli
    copy_bot_template
    set_permissions
    setup_cron_backup

    print_summary
}

# Run main function
main "$@"
