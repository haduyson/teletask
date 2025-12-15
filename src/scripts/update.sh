#!/bin/bash
#===============================================================================
# TeleTask Update Script
# Updates system packages, bot templates, and running bots
# Usage: sudo bash update.sh [--all|--system|--bots|--template]
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
TEMPLATE_DIR="${BOTPANEL_HOME}/templates/bot_template"
BOTS_DIR="${BOTPANEL_HOME}/bots"
BACKUP_DIR="${BOTPANEL_HOME}/backups/manual"

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
        log_error "Script phai chay voi quyen root. Su dung: sudo bash update.sh"
        exit 1
    fi
}

show_usage() {
    echo "Su dung: sudo bash update.sh [options]"
    echo ""
    echo "Options:"
    echo "  --all       Cap nhat tat ca (mac dinh)"
    echo "  --system    Chi cap nhat system packages"
    echo "  --bots      Chi cap nhat cac bot"
    echo "  --template  Chi cap nhat bot template"
    echo "  --help      Hien thi huong dan nay"
    echo ""
}

#-------------------------------------------------------------------------------
# Backup Functions
#-------------------------------------------------------------------------------

backup_bot() {
    local bot_name="$1"
    local bot_dir="${BOTS_DIR}/${bot_name}"
    local backup_path="${BACKUP_DIR}/${bot_name}_$(date +%Y%m%d_%H%M%S)"

    log_info "  Backup ${bot_name}..."

    mkdir -p "$backup_path"

    # Copy bot files
    cp -r "$bot_dir" "$backup_path/"

    # Backup database
    local db_name="${bot_name}_db"
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$db_name"; then
        sudo -u postgres pg_dump "$db_name" > "${backup_path}/${db_name}.sql" 2>/dev/null || true
    fi

    # Compress
    tar -czf "${backup_path}.tar.gz" -C "$BACKUP_DIR" "$(basename "$backup_path")"
    rm -rf "$backup_path"

    log_success "  Backup luu tai: ${backup_path}.tar.gz"
}

#-------------------------------------------------------------------------------
# Update Functions
#-------------------------------------------------------------------------------

update_system_packages() {
    log_info "Dang cap nhat system packages..."

    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

    log_success "System packages da cap nhat"
}

update_pm2() {
    log_info "Dang cap nhat PM2..."

    npm update -g pm2 --silent 2>/dev/null || npm install -g pm2 --silent

    log_success "PM2 da cap nhat ($(pm2 --version))"
}

update_python_packages() {
    log_info "Dang cap nhat Python packages..."

    pip3 install --upgrade pip setuptools wheel -q

    log_success "Python packages da cap nhat"
}

update_template() {
    log_info "Dang cap nhat bot template..."

    if [[ ! -d "$TEMPLATE_DIR" ]]; then
        log_warn "Template directory khong ton tai: $TEMPLATE_DIR"
        return
    fi

    # If template is a git repo, pull latest
    if [[ -d "${TEMPLATE_DIR}/.git" ]]; then
        cd "$TEMPLATE_DIR"
        git fetch origin 2>/dev/null || true
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true
        log_success "Bot template da cap nhat tu git"
    else
        log_info "Template khong phai git repo, bo qua git pull"
    fi

    # Update template requirements
    if [[ -f "${TEMPLATE_DIR}/requirements.txt" ]]; then
        pip3 install -r "${TEMPLATE_DIR}/requirements.txt" -q --upgrade 2>/dev/null || true
        log_success "Template dependencies da cap nhat"
    fi
}

update_single_bot() {
    local bot_name="$1"
    local bot_dir="${BOTS_DIR}/${bot_name}"

    if [[ ! -d "$bot_dir" ]]; then
        log_warn "Bot khong ton tai: $bot_name"
        return 1
    fi

    log_info "Dang cap nhat bot: ${bot_name}..."

    # 1. Backup
    backup_bot "$bot_name"

    # 2. Stop bot
    log_info "  Dung bot..."
    su - "$BOTPANEL_USER" -c "pm2 stop $bot_name" 2>/dev/null || true

    # 3. Sync code from template (preserve config)
    log_info "  Dong bo code tu template..."
    if [[ -d "$TEMPLATE_DIR" ]]; then
        rsync -av --quiet \
            --exclude='.env' \
            --exclude='config.json' \
            --exclude='*.db' \
            --exclude='__pycache__' \
            --exclude='.git' \
            --exclude='logs/' \
            --exclude='venv/' \
            "${TEMPLATE_DIR}/" "${bot_dir}/" 2>/dev/null || true
    fi

    # 4. Update dependencies
    log_info "  Cap nhat dependencies..."
    if [[ -f "${bot_dir}/requirements.txt" ]]; then
        cd "$bot_dir"

        # Use venv if exists
        if [[ -d "${bot_dir}/venv" ]]; then
            source "${bot_dir}/venv/bin/activate"
            pip install -r requirements.txt -q --upgrade 2>/dev/null || true
            deactivate
        else
            pip3 install -r requirements.txt -q --upgrade 2>/dev/null || true
        fi
    fi

    # 5. Run database migrations
    log_info "  Chay database migrations..."
    if [[ -f "${bot_dir}/alembic.ini" ]]; then
        cd "$bot_dir"
        if [[ -d "${bot_dir}/venv" ]]; then
            source "${bot_dir}/venv/bin/activate"
            alembic upgrade head 2>/dev/null || log_warn "  Migration that bai hoac khong co migration moi"
            deactivate
        else
            alembic upgrade head 2>/dev/null || log_warn "  Migration that bai hoac khong co migration moi"
        fi
    fi

    # 6. Restart bot
    log_info "  Khoi dong lai bot..."
    su - "$BOTPANEL_USER" -c "pm2 restart $bot_name" 2>/dev/null || \
        su - "$BOTPANEL_USER" -c "pm2 start $bot_name" 2>/dev/null || true

    # 7. Verify
    sleep 2
    if su - "$BOTPANEL_USER" -c "pm2 show $bot_name" 2>/dev/null | grep -q "online"; then
        log_success "Bot ${bot_name} da cap nhat va dang chay"
    else
        log_warn "Bot ${bot_name} da cap nhat nhung co the khong chay. Kiem tra: pm2 logs $bot_name"
    fi
}

update_all_bots() {
    log_info "Dang cap nhat tat ca bot..."

    if [[ ! -d "$BOTS_DIR" ]]; then
        log_warn "Thu muc bots khong ton tai"
        return
    fi

    local bot_count=0
    for bot_dir in "${BOTS_DIR}"/*/; do
        if [[ -d "$bot_dir" ]]; then
            bot_name=$(basename "$bot_dir")
            update_single_bot "$bot_name"
            ((bot_count++))
            echo ""
        fi
    done

    if [[ $bot_count -eq 0 ]]; then
        log_info "Khong co bot nao de cap nhat"
    else
        log_success "Da cap nhat ${bot_count} bot"
    fi
}

#-------------------------------------------------------------------------------
# Health Check
#-------------------------------------------------------------------------------

health_check() {
    log_info "Kiem tra trang thai sau cap nhat..."

    echo ""
    echo -e "${BLUE}Services:${NC}"
    echo "  PostgreSQL: $(systemctl is-active postgresql 2>/dev/null || echo 'unknown')"
    echo "  Redis:      $(systemctl is-active redis-server 2>/dev/null || echo 'unknown')"
    echo "  Nginx:      $(systemctl is-active nginx 2>/dev/null || echo 'unknown')"

    echo ""
    echo -e "${BLUE}PM2 Processes:${NC}"
    su - "$BOTPANEL_USER" -c "pm2 list" 2>/dev/null || echo "  Khong the lay danh sach PM2"

    echo ""
}

#-------------------------------------------------------------------------------
# Main Menu
#-------------------------------------------------------------------------------

interactive_menu() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}           TELETASK UPDATE MENU${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
    echo "Chon loai cap nhat:"
    echo ""
    echo "  1) Cap nhat tat ca"
    echo "  2) Chi cap nhat system packages"
    echo "  3) Chi cap nhat bot template"
    echo "  4) Chi cap nhat cac bot"
    echo "  5) Cap nhat mot bot cu the"
    echo "  6) Thoat"
    echo ""

    read -p "Lua chon [1-6]: " choice

    case $choice in
        1)
            update_system_packages
            update_pm2
            update_python_packages
            update_template
            update_all_bots
            ;;
        2)
            update_system_packages
            update_pm2
            update_python_packages
            ;;
        3)
            update_template
            ;;
        4)
            update_all_bots
            ;;
        5)
            echo ""
            read -p "Nhap ten bot: " bot_name
            if [[ -n "$bot_name" ]]; then
                update_single_bot "$bot_name"
            fi
            ;;
        6)
            log_info "Thoat."
            exit 0
            ;;
        *)
            log_warn "Lua chon khong hop le"
            exit 1
            ;;
    esac

    health_check
}

#-------------------------------------------------------------------------------
# Print Summary
#-------------------------------------------------------------------------------

print_summary() {
    echo ""
    echo -e "${GREEN}================================================================${NC}"
    echo -e "${GREEN}           CAP NHAT HOAN TAT${NC}"
    echo -e "${GREEN}================================================================${NC}"
    echo ""
    echo "Thoi gian: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo -e "${BLUE}Kiem tra logs neu co loi:${NC}"
    echo "  pm2 logs"
    echo "  tail -f ${BOTPANEL_HOME}/logs/*.log"
    echo ""
    echo -e "${GREEN}================================================================${NC}"
}

#-------------------------------------------------------------------------------
# Main Execution
#-------------------------------------------------------------------------------

main() {
    check_root

    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --all)
            update_system_packages
            update_pm2
            update_python_packages
            update_template
            update_all_bots
            health_check
            print_summary
            ;;
        --system)
            update_system_packages
            update_pm2
            update_python_packages
            health_check
            print_summary
            ;;
        --bots)
            update_all_bots
            health_check
            print_summary
            ;;
        --template)
            update_template
            print_summary
            ;;
        --bot)
            if [[ -n "${2:-}" ]]; then
                update_single_bot "$2"
                health_check
                print_summary
            else
                log_error "Vui long chi dinh ten bot: --bot <bot_name>"
                exit 1
            fi
            ;;
        "")
            # Interactive mode if no arguments
            interactive_menu
            print_summary
            ;;
        *)
            log_error "Option khong hop le: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
