#!/bin/bash
#===============================================================================
# TeleTask Uninstallation Script
# Safely removes TeleTask installation
# Usage: sudo bash uninstall.sh
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
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Script phai chay voi quyen root. Su dung: sudo bash uninstall.sh"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Confirmation Prompts
#-------------------------------------------------------------------------------

confirm_uninstall() {
    echo ""
    echo -e "${RED}================================================================${NC}"
    echo -e "${RED}           CANH BAO: GO CAI DAT TELETASK${NC}"
    echo -e "${RED}================================================================${NC}"
    echo ""
    echo "Hanh dong nay se:"
    echo "  1. Dung tat ca bot dang chay"
    echo "  2. Xoa tat ca database cua bot"
    echo "  3. Xoa user ${BOTPANEL_USER} va thu muc ${BOTPANEL_HOME}"
    echo "  4. Xoa cau hinh PM2 startup"
    echo ""
    echo -e "${YELLOW}Luu y: Hanh dong nay KHONG THE HOAN TAC!${NC}"
    echo ""

    read -p "Nhap 'yes' de xac nhan go cai dat: " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo ""
        log_info "Huy go cai dat."
        exit 0
    fi
}

confirm_backup() {
    echo ""
    read -p "Ban co muon tao backup truoc khi go? (y/n): " backup_choice

    if [[ "$backup_choice" == "y" || "$backup_choice" == "Y" ]]; then
        create_final_backup
    fi
}

#-------------------------------------------------------------------------------
# Backup Functions
#-------------------------------------------------------------------------------

create_final_backup() {
    log_info "Dang tao backup cuoi cung..."

    local backup_dir="/tmp/teletask_final_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup databases
    log_info "Dang backup databases..."
    for db in $(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE '%_db' AND datname NOT IN ('postgres', 'template0', 'template1');" 2>/dev/null); do
        db=$(echo "$db" | xargs)  # Trim whitespace
        if [[ -n "$db" ]]; then
            log_info "  Backup database: $db"
            sudo -u postgres pg_dump "$db" > "${backup_dir}/${db}.sql" 2>/dev/null || true
        fi
    done

    # Backup config files
    if [[ -d "${BOTPANEL_HOME}/config" ]]; then
        log_info "Dang backup config..."
        cp -r "${BOTPANEL_HOME}/config" "${backup_dir}/" 2>/dev/null || true
    fi

    # Backup bot configs
    if [[ -d "${BOTPANEL_HOME}/bots" ]]; then
        log_info "Dang backup bot configs..."
        for bot_dir in "${BOTPANEL_HOME}/bots"/*/; do
            if [[ -d "$bot_dir" ]]; then
                bot_name=$(basename "$bot_dir")
                mkdir -p "${backup_dir}/bots/${bot_name}"
                cp "${bot_dir}/.env" "${backup_dir}/bots/${bot_name}/" 2>/dev/null || true
                cp "${bot_dir}/config.json" "${backup_dir}/bots/${bot_name}/" 2>/dev/null || true
            fi
        done
    fi

    # Compress backup
    tar -czf "${backup_dir}.tar.gz" -C /tmp "$(basename "$backup_dir")"
    rm -rf "$backup_dir"

    echo ""
    log_success "Backup da luu tai: ${backup_dir}.tar.gz"
    echo ""
}

#-------------------------------------------------------------------------------
# Uninstall Steps
#-------------------------------------------------------------------------------

stop_all_bots() {
    log_info "Dang dung tat ca bot..."

    if id "$BOTPANEL_USER" &>/dev/null; then
        su - "$BOTPANEL_USER" -c "pm2 delete all" 2>/dev/null || true
        su - "$BOTPANEL_USER" -c "pm2 kill" 2>/dev/null || true
    fi

    log_success "Tat ca bot da dung"
}

remove_pm2_startup() {
    log_info "Dang xoa PM2 startup..."

    pm2 unstartup systemd 2>/dev/null || true

    # Remove PM2 systemd service
    systemctl stop pm2-${BOTPANEL_USER} 2>/dev/null || true
    systemctl disable pm2-${BOTPANEL_USER} 2>/dev/null || true
    rm -f /etc/systemd/system/pm2-${BOTPANEL_USER}.service 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true

    log_success "PM2 startup da xoa"
}

drop_databases() {
    log_info "Dang xoa databases..."

    # Find and drop all bot databases
    for db in $(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE '%_db' AND datname NOT IN ('postgres', 'template0', 'template1');" 2>/dev/null); do
        db=$(echo "$db" | xargs)  # Trim whitespace
        if [[ -n "$db" ]]; then
            log_info "  Xoa database: $db"
            sudo -u postgres dropdb "$db" 2>/dev/null || true
        fi
    done

    # Drop botpanel user from PostgreSQL
    sudo -u postgres psql -c "DROP USER IF EXISTS ${BOTPANEL_USER};" 2>/dev/null || true

    log_success "Databases da xoa"
}

remove_user_and_home() {
    log_info "Dang xoa user va thu muc..."

    # Remove cron jobs
    crontab -u "$BOTPANEL_USER" -r 2>/dev/null || true

    # Remove user and home directory
    if id "$BOTPANEL_USER" &>/dev/null; then
        userdel -r "$BOTPANEL_USER" 2>/dev/null || true
    fi

    # Force remove home directory if still exists
    if [[ -d "$BOTPANEL_HOME" ]]; then
        rm -rf "$BOTPANEL_HOME"
    fi

    log_success "User va thu muc da xoa"
}

remove_cli_symlink() {
    log_info "Dang xoa CLI symlink..."

    rm -f /usr/local/bin/botpanel 2>/dev/null || true

    log_success "CLI symlink da xoa"
}

cleanup_apt_sources() {
    log_info "Dang don dep APT sources..."

    # Remove NodeSource repository
    rm -f /etc/apt/sources.list.d/nodesource.list 2>/dev/null || true

    # Remove PostgreSQL repository (optional - keep if user wants to keep PostgreSQL)
    # rm -f /etc/apt/sources.list.d/pgdg.list 2>/dev/null || true

    apt-get update -qq 2>/dev/null || true

    log_success "APT sources da don dep"
}

#-------------------------------------------------------------------------------
# Optional: Remove System Packages
#-------------------------------------------------------------------------------

ask_remove_packages() {
    echo ""
    echo -e "${YELLOW}Cac goi he thong da cai dat:${NC}"
    echo "  - PostgreSQL"
    echo "  - Node.js & PM2"
    echo "  - Redis"
    echo "  - Nginx"
    echo ""
    read -p "Ban co muon go cac goi nay? (y/n) [mac dinh: n]: " remove_packages

    if [[ "$remove_packages" == "y" || "$remove_packages" == "Y" ]]; then
        remove_system_packages
    else
        log_info "Giu lai cac goi he thong"
    fi
}

remove_system_packages() {
    log_info "Dang go cac goi he thong..."

    # Stop services first
    systemctl stop nginx 2>/dev/null || true
    systemctl stop redis-server 2>/dev/null || true
    systemctl stop postgresql 2>/dev/null || true

    # Remove packages
    apt-get remove --purge -y \
        nodejs \
        redis-server \
        nginx \
        2>/dev/null || true

    # Note: Not removing PostgreSQL by default as it may contain other databases

    # Remove PM2 globally
    npm uninstall -g pm2 2>/dev/null || true

    apt-get autoremove -y 2>/dev/null || true

    log_success "Cac goi he thong da go"
}

#-------------------------------------------------------------------------------
# Print Summary
#-------------------------------------------------------------------------------

print_summary() {
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}           GO CAI DAT TELETASK HOAN TAT${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo ""
    echo "Da xoa:"
    echo "  - Tat ca bot va processes"
    echo "  - Tat ca databases cua bot"
    echo "  - User ${BOTPANEL_USER}"
    echo "  - Thu muc ${BOTPANEL_HOME}"
    echo "  - PM2 startup service"
    echo "  - BotPanel CLI"
    echo ""

    if [[ -f "/tmp/teletask_final_backup_"*.tar.gz ]]; then
        echo -e "${YELLOW}Backup da luu tai:${NC}"
        ls /tmp/teletask_final_backup_*.tar.gz 2>/dev/null
        echo ""
    fi

    echo -e "${BLUE}Luu y:${NC}"
    echo "  - PostgreSQL service van con (co the chua databases khac)"
    echo "  - De go PostgreSQL hoan toan: sudo apt remove --purge postgresql*"
    echo ""
    echo -e "${GREEN}================================================================${NC}"
}

#-------------------------------------------------------------------------------
# Main Execution
#-------------------------------------------------------------------------------

main() {
    check_root
    confirm_uninstall
    confirm_backup

    stop_all_bots
    remove_pm2_startup
    drop_databases
    remove_user_and_home
    remove_cli_symlink
    cleanup_apt_sources

    ask_remove_packages

    print_summary
}

# Run main function
main "$@"
