#!/bin/bash
#===============================================================================
# BotPanel CLI - TeleTask Bot Management
# Version: 1.0.0
# Vietnamese Telegram Bot Management System
#===============================================================================

set -e

#-------------------------------------------------------------------------------
# Configuration
#-------------------------------------------------------------------------------
BOTPANEL_HOME="/home/botpanel"
BOTS_DIR="$BOTPANEL_HOME/bots"
CONFIG_DIR="$BOTPANEL_HOME/config"
TEMPLATES_DIR="$BOTPANEL_HOME/templates"
BACKUP_DIR="$BOTPANEL_HOME/backups"
LOGS_DIR="$BOTPANEL_HOME/logs"

# Load global config
[[ -f "$CONFIG_DIR/global.conf" ]] && source "$CONFIG_DIR/global.conf"

#-------------------------------------------------------------------------------
# Colors
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

press_enter() {
    echo ""
    read -p "Nhan Enter de tiep tuc..." _
}

# Get bot directory by index number
get_bot_dir_by_index() {
    local index=$1
    local i=1
    for bot_dir in "$BOTS_DIR"/*/; do
        [[ ! -d "$bot_dir" ]] && continue
        if [[ $i -eq $index ]]; then
            echo "$bot_dir"
            return
        fi
        ((i++))
    done
}

# Get bot name from directory
get_bot_name() {
    basename "$1"
}

# List bots in simple format
list_bots_simple() {
    echo ""
    local i=1
    for bot_dir in "$BOTS_DIR"/*/; do
        [[ ! -d "$bot_dir" ]] && continue
        local bot_name=$(basename "$bot_dir")
        local status=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$bot_name\") | .pm2_env.status" 2>/dev/null || echo "unknown")

        if [[ "$status" == "online" ]]; then
            echo -e "  $i. $bot_name ${GREEN}[online]${NC}"
        else
            echo -e "  $i. $bot_name ${RED}[offline]${NC}"
        fi
        ((i++))
    done

    if [[ $i -eq 1 ]]; then
        echo -e "  ${YELLOW}Chua co bot nao${NC}"
    fi
    echo ""
}

# Generate random password
generate_password() {
    openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16
}

# Validate Telegram bot token format
validate_token() {
    local token="$1"
    if [[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        return 0
    fi
    return 1
}

# Format bytes to human readable
format_bytes() {
    local bytes=$1
    if [[ -z "$bytes" || "$bytes" == "null" || "$bytes" -eq 0 ]]; then
        echo "-"
        return
    fi

    if [[ $bytes -gt 1073741824 ]]; then
        echo "$((bytes / 1073741824))GB"
    elif [[ $bytes -gt 1048576 ]]; then
        echo "$((bytes / 1048576))MB"
    elif [[ $bytes -gt 1024 ]]; then
        echo "$((bytes / 1024))KB"
    else
        echo "${bytes}B"
    fi
}

# Format uptime
format_uptime() {
    local uptime_ms=$1
    if [[ -z "$uptime_ms" || "$uptime_ms" == "null" ]]; then
        echo "-"
        return
    fi

    local now_ms=$(date +%s%3N)
    local diff_s=$(( (now_ms - uptime_ms) / 1000 ))

    if [[ $diff_s -gt 86400 ]]; then
        echo "$((diff_s / 86400))d"
    elif [[ $diff_s -gt 3600 ]]; then
        echo "$((diff_s / 3600))h"
    elif [[ $diff_s -gt 60 ]]; then
        echo "$((diff_s / 60))m"
    else
        echo "${diff_s}s"
    fi
}

#-------------------------------------------------------------------------------
# Menu Display
#-------------------------------------------------------------------------------

show_menu() {
    clear
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}        ${BOLD}BOTPANEL - QUAN LY BOT TELEGRAM${NC}                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}        Version 1.0.0 - TeleTask                          ${BLUE}║${NC}"
    echo -e "${BLUE}╠══════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║${NC}                                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}1.${NC}  Xem danh sach bot                                 ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}2.${NC}  Tao bot moi                                       ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}3.${NC}  Quan ly bot (Start/Stop/Restart)                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}4.${NC}  Xoa bot                                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}5.${NC}  Xem log bot                                       ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}6.${NC}  Cap nhat bot                                      ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}7.${NC}  Quan ly Timezone                                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}8.${NC}  Backup & Restore                                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${CYAN}9.${NC}  Thong tin he thong                                ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${CYAN}10.${NC}  Cau hinh Admin Alert                              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${CYAN}11.${NC}  Monitoring & Metrics                              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   ${RED}0.${NC}  Thoat                                              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                          ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

#-------------------------------------------------------------------------------
# [1] List Bots
#-------------------------------------------------------------------------------

list_bots() {
    clear
    echo -e "\n${BOLD}=== DANH SACH BOT ===${NC}\n"

    # Header
    printf "${CYAN}%-4s %-20s %-12s %-10s %-10s %-8s${NC}\n" "#" "Ten Bot" "Trang thai" "Uptime" "Memory" "CPU"
    echo "────────────────────────────────────────────────────────────────────"

    local i=1
    local total_bots=0
    local online_bots=0

    for bot_dir in "$BOTS_DIR"/*/; do
        [[ ! -d "$bot_dir" ]] && continue

        local bot_name=$(basename "$bot_dir")
        ((total_bots++))

        # Get PM2 info
        local pm2_info=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$bot_name\")" 2>/dev/null)

        if [[ -n "$pm2_info" ]]; then
            local status=$(echo "$pm2_info" | jq -r '.pm2_env.status' 2>/dev/null)
            local uptime_ms=$(echo "$pm2_info" | jq -r '.pm2_env.pm_uptime' 2>/dev/null)
            local memory=$(echo "$pm2_info" | jq -r '.monit.memory' 2>/dev/null)
            local cpu=$(echo "$pm2_info" | jq -r '.monit.cpu' 2>/dev/null)

            if [[ "$status" == "online" ]]; then
                local status_fmt="${GREEN}Online${NC}"
                ((online_bots++))
            elif [[ "$status" == "stopped" ]]; then
                local status_fmt="${YELLOW}Stopped${NC}"
            else
                local status_fmt="${RED}Error${NC}"
            fi

            local uptime_fmt=$(format_uptime "$uptime_ms")
            local memory_fmt=$(format_bytes "$memory")
            local cpu_fmt="${cpu:-0}%"
        else
            local status_fmt="${RED}Not PM2${NC}"
            local uptime_fmt="-"
            local memory_fmt="-"
            local cpu_fmt="-"
        fi

        printf "%-4s %-20s %-12b %-10s %-10s %-8s\n" "$i" "$bot_name" "$status_fmt" "$uptime_fmt" "$memory_fmt" "$cpu_fmt"
        ((i++))
    done

    if [[ $total_bots -eq 0 ]]; then
        echo -e "${YELLOW}Chua co bot nao. Chon menu 2 de tao bot moi.${NC}"
    else
        echo ""
        echo -e "Tong: ${BOLD}$total_bots${NC} bot | Online: ${GREEN}$online_bots${NC} | Offline: ${RED}$((total_bots - online_bots))${NC}"
    fi

    press_enter
}

#-------------------------------------------------------------------------------
# [2] Create Bot
#-------------------------------------------------------------------------------

create_bot() {
    clear
    echo -e "\n${BOLD}=== TAO BOT MOI ===${NC}\n"

    # Step 1: Bot Token
    echo -e "${CYAN}Buoc 1: Thong tin Telegram Bot${NC}"
    echo "Lay token tu @BotFather tren Telegram"
    echo ""
    read -p "Bot Token: " bot_token

    if [[ -z "$bot_token" ]]; then
        log_error "Token khong duoc de trong"
        press_enter
        return
    fi

    if ! validate_token "$bot_token"; then
        log_error "Token khong hop le. Format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        press_enter
        return
    fi

    # Step 2: Bot Info
    echo ""
    echo -e "${CYAN}Buoc 2: Thong tin bot${NC}"
    read -p "Ten bot [taskbot]: " bot_name
    bot_name=${bot_name:-taskbot}
    bot_name=$(echo "$bot_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd 'a-z0-9_')

    read -p "Ten hien thi [Bot Quan Ly Cong Viec]: " display_name
    display_name=${display_name:-"Bot Quan Ly Cong Viec"}

    read -p "Mo ta []: " description

    # Step 3: Database
    echo ""
    echo -e "${CYAN}Buoc 3: Database${NC}"
    local db_name="${bot_name}_db"
    read -p "Database name [$db_name]: " custom_db
    db_name=${custom_db:-$db_name}

    local db_pass=$(generate_password)

    # Step 4: Support Info
    echo ""
    echo -e "${CYAN}Buoc 4: Thong tin ho tro (tuy chon)${NC}"
    read -p "Telegram ho tro [@support]: " support_tg
    support_tg=${support_tg:-@support}
    read -p "So dien thoai []: " support_phone
    read -p "Email []: " support_email

    # Step 5: Admin
    echo ""
    echo -e "${CYAN}Buoc 5: Admin${NC}"
    read -p "Admin Telegram ID (de nhan thong bao): " admin_id

    # Generate bot ID
    local bot_count=$(ls -d "$BOTS_DIR"/bot_* 2>/dev/null | wc -l)
    local bot_id="bot_$(printf '%03d' $((bot_count + 1)))"
    local bot_path="$BOTS_DIR/$bot_id"

    # Confirmation
    echo ""
    echo -e "${YELLOW}=== XAC NHAN THONG TIN ===${NC}"
    echo "Bot ID:       $bot_id"
    echo "Bot Name:     $bot_name"
    echo "Display Name: $display_name"
    echo "Database:     $db_name"
    echo "Admin ID:     $admin_id"
    echo ""
    read -p "Tao bot? (y/n) [y]: " confirm
    confirm=${confirm:-y}

    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        log_warn "Huy tao bot"
        press_enter
        return
    fi

    echo ""
    log_info "Dang tao bot..."

    # Create database
    log_info "Tao database..."
    if ! sudo -u postgres psql -c "CREATE DATABASE $db_name OWNER botpanel;" 2>/dev/null; then
        log_error "Khong the tao database. Co the da ton tai."
        press_enter
        return
    fi

    # Create bot directory
    log_info "Tao thu muc bot..."
    cp -r "$TEMPLATES_DIR/bot_template" "$bot_path"

    # Create config.json
    cat > "$bot_path/config.json" << EOF
{
    "bot_id": "$bot_id",
    "bot_name": "$bot_name",
    "display_name": "$display_name",
    "description": "$description",
    "database_name": "$db_name",
    "support_telegram": "$support_tg",
    "support_phone": "$support_phone",
    "support_email": "$support_email",
    "admin_telegram_id": "$admin_id",
    "timezone": "${TZ:-Asia/Ho_Chi_Minh}",
    "created_at": "$(date -Iseconds)"
}
EOF

    # Create .env
    cat > "$bot_path/.env" << EOF
# TeleTask Bot Configuration
# Bot: $bot_id - $bot_name

BOT_TOKEN=$bot_token
BOT_NAME=$bot_name
DATABASE_URL=postgresql://botpanel:${PG_PASSWORD:-changeme}@localhost:5432/$db_name
ADMIN_IDS=$admin_id
TZ=${TZ:-Asia/Ho_Chi_Minh}
LOG_LEVEL=INFO
LOG_FILE=$LOGS_DIR/${bot_id}.log
EOF

    # Create ecosystem.config.js for PM2
    cat > "$bot_path/ecosystem.config.js" << EOF
module.exports = {
    apps: [{
        name: '$bot_id',
        script: 'bot.py',
        interpreter: 'python3.11',
        cwd: '$bot_path',
        env: {
            NODE_ENV: 'production'
        },
        watch: false,
        autorestart: true,
        max_restarts: 10,
        restart_delay: 5000,
        log_file: '$LOGS_DIR/${bot_id}.log',
        error_file: '$LOGS_DIR/${bot_id}-error.log',
        out_file: '$LOGS_DIR/${bot_id}-out.log',
        time: true
    }]
};
EOF

    # Set permissions
    chmod 600 "$bot_path/.env"
    chown -R botpanel:botpanel "$bot_path"

    # Create virtual environment and install dependencies
    log_info "Tao virtual environment..."
    cd "$bot_path"
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q 2>/dev/null || log_warn "Mot so package chua cai duoc"
    deactivate

    # Start with PM2
    log_info "Khoi dong bot..."
    pm2 start "$bot_path/ecosystem.config.js" 2>/dev/null || log_warn "Bot chua the khoi dong (code chua hoan thien)"
    pm2 save 2>/dev/null || true

    echo ""
    log_success "Tao bot thanh cong!"
    echo ""
    echo -e "${BOLD}Thong tin bot:${NC}"
    echo "  Bot ID:     $bot_id"
    echo "  Bot Path:   $bot_path"
    echo "  Database:   $db_name"
    echo "  Log File:   $LOGS_DIR/${bot_id}.log"
    echo ""
    echo -e "${YELLOW}Luu y: Bot se hoat dong sau khi Phase 04 hoan thanh.${NC}"

    press_enter
}

#-------------------------------------------------------------------------------
# [3] Manage Bot
#-------------------------------------------------------------------------------

manage_bot() {
    clear
    echo -e "\n${BOLD}=== QUAN LY BOT ===${NC}"
    list_bots_simple

    read -p "Chon bot (so thu tu): " bot_num

    local bot_dir=$(get_bot_dir_by_index "$bot_num")
    if [[ -z "$bot_dir" || ! -d "$bot_dir" ]]; then
        log_error "Bot khong ton tai"
        press_enter
        return
    fi

    local bot_name=$(get_bot_name "$bot_dir")
    local config_file="$bot_dir/config.json"
    local display_name=$(jq -r '.display_name // .bot_name' "$config_file" 2>/dev/null || echo "$bot_name")

    while true; do
        clear
        echo -e "\n${BOLD}=== QUAN LY: $display_name ($bot_name) ===${NC}\n"

        # Get current status
        local status=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$bot_name\") | .pm2_env.status" 2>/dev/null || echo "unknown")

        if [[ "$status" == "online" ]]; then
            echo -e "Trang thai: ${GREEN}Online${NC}"
        elif [[ "$status" == "stopped" ]]; then
            echo -e "Trang thai: ${YELLOW}Stopped${NC}"
        else
            echo -e "Trang thai: ${RED}$status${NC}"
        fi

        echo ""
        echo "1. Restart bot"
        echo "2. Stop bot"
        echo "3. Start bot"
        echo "4. Xem thong tin chi tiet"
        echo "5. Sua cau hinh"
        echo "0. Quay lai"
        echo ""
        read -p "Chon: " action

        case $action in
            1)
                pm2 restart "$bot_name" 2>/dev/null && log_success "Da restart $bot_name" || log_error "Khong the restart"
                sleep 1
                ;;
            2)
                pm2 stop "$bot_name" 2>/dev/null && log_success "Da stop $bot_name" || log_error "Khong the stop"
                sleep 1
                ;;
            3)
                pm2 start "$bot_name" 2>/dev/null && log_success "Da start $bot_name" || log_error "Khong the start"
                sleep 1
                ;;
            4)
                echo ""
                echo -e "${CYAN}=== THONG TIN CHI TIET ===${NC}"
                pm2 show "$bot_name" 2>/dev/null || echo "Khong co thong tin PM2"
                press_enter
                ;;
            5)
                edit_bot_config "$bot_dir"
                ;;
            0)
                return
                ;;
        esac
    done
}

# Edit bot configuration
edit_bot_config() {
    local bot_dir="$1"
    local config_file="$bot_dir/config.json"

    if [[ ! -f "$config_file" ]]; then
        log_error "File config khong ton tai"
        return
    fi

    echo ""
    echo -e "${CYAN}=== SUA CAU HINH ===${NC}"
    echo "1. Sua bang nano"
    echo "2. Sua bang vi"
    echo "0. Huy"

    read -p "Chon: " editor_choice

    case $editor_choice in
        1) nano "$config_file" ;;
        2) vi "$config_file" ;;
        0) return ;;
    esac
}

#-------------------------------------------------------------------------------
# [4] Delete Bot
#-------------------------------------------------------------------------------

delete_bot() {
    clear
    echo -e "\n${BOLD}=== XOA BOT ===${NC}"
    echo -e "${RED}Canh bao: Hanh dong nay khong the hoan tac!${NC}"
    list_bots_simple

    read -p "Chon bot can xoa (so thu tu): " bot_num

    local bot_dir=$(get_bot_dir_by_index "$bot_num")
    if [[ -z "$bot_dir" || ! -d "$bot_dir" ]]; then
        log_error "Bot khong ton tai"
        press_enter
        return
    fi

    local bot_name=$(get_bot_name "$bot_dir")
    local config_file="$bot_dir/config.json"
    local db_name=$(jq -r '.database_name // empty' "$config_file" 2>/dev/null)
    [[ -z "$db_name" ]] && db_name="${bot_name}_db"

    echo ""
    echo -e "${YELLOW}Bot se bi xoa:${NC} $bot_name"
    echo -e "${YELLOW}Database:${NC} $db_name"
    echo ""

    # Backup option
    read -p "Tao backup truoc khi xoa? (y/n) [y]: " backup_choice
    backup_choice=${backup_choice:-y}

    if [[ "$backup_choice" == "y" || "$backup_choice" == "Y" ]]; then
        backup_single_bot_internal "$bot_name" "$db_name"
    fi

    # Final confirmation
    read -p "Nhap '$bot_name' de xac nhan xoa: " confirm

    if [[ "$confirm" != "$bot_name" ]]; then
        log_warn "Huy xoa bot"
        press_enter
        return
    fi

    log_info "Dang xoa bot..."

    # Stop PM2 process
    pm2 delete "$bot_name" 2>/dev/null || true
    pm2 save 2>/dev/null || true

    # Drop database
    sudo -u postgres dropdb "$db_name" 2>/dev/null || log_warn "Khong the xoa database"

    # Remove directory
    rm -rf "$bot_dir"

    log_success "Da xoa bot $bot_name"
    press_enter
}

#-------------------------------------------------------------------------------
# [5] View Logs
#-------------------------------------------------------------------------------

view_logs() {
    clear
    echo -e "\n${BOLD}=== XEM LOG BOT ===${NC}"
    list_bots_simple

    read -p "Chon bot (so thu tu): " bot_num

    local bot_dir=$(get_bot_dir_by_index "$bot_num")
    if [[ -z "$bot_dir" || ! -d "$bot_dir" ]]; then
        log_error "Bot khong ton tai"
        press_enter
        return
    fi

    local bot_name=$(get_bot_name "$bot_dir")

    echo ""
    echo "1. Xem log moi nhat (50 dong)"
    echo "2. Xem log realtime (Ctrl+C de thoat)"
    echo "3. Xem error log"
    echo "4. Xem PM2 log"
    echo "0. Quay lai"
    echo ""
    read -p "Chon: " log_choice

    case $log_choice in
        1)
            echo ""
            echo -e "${CYAN}=== LOG: $bot_name ===${NC}"
            pm2 logs "$bot_name" --lines 50 --nostream 2>/dev/null || \
                tail -50 "$LOGS_DIR/${bot_name}.log" 2>/dev/null || \
                echo "Khong tim thay log"
            press_enter
            ;;
        2)
            echo ""
            echo -e "${CYAN}=== REALTIME LOG: $bot_name (Ctrl+C de thoat) ===${NC}"
            pm2 logs "$bot_name" 2>/dev/null || \
                tail -f "$LOGS_DIR/${bot_name}.log" 2>/dev/null || \
                echo "Khong tim thay log"
            ;;
        3)
            echo ""
            echo -e "${CYAN}=== ERROR LOG: $bot_name ===${NC}"
            tail -50 "$LOGS_DIR/${bot_name}-error.log" 2>/dev/null || \
                echo "Khong co error log"
            press_enter
            ;;
        4)
            pm2 show "$bot_name" 2>/dev/null || echo "Khong tim thay PM2 process"
            press_enter
            ;;
        0)
            return
            ;;
    esac
}

#-------------------------------------------------------------------------------
# [6] Update Bot
#-------------------------------------------------------------------------------

update_bot() {
    clear
    echo -e "\n${BOLD}=== CAP NHAT BOT ===${NC}"
    echo ""
    echo "1. Cap nhat mot bot"
    echo "2. Cap nhat tat ca bot"
    echo "3. Cap nhat template"
    echo "0. Quay lai"
    echo ""
    read -p "Chon: " update_choice

    case $update_choice in
        1)
            list_bots_simple
            read -p "Chon bot (so thu tu): " bot_num

            local bot_dir=$(get_bot_dir_by_index "$bot_num")
            if [[ -z "$bot_dir" || ! -d "$bot_dir" ]]; then
                log_error "Bot khong ton tai"
                press_enter
                return
            fi

            update_single_bot "$bot_dir"
            ;;
        2)
            update_all_bots
            ;;
        3)
            update_template
            ;;
        0)
            return
            ;;
    esac

    press_enter
}

update_single_bot() {
    local bot_dir="$1"
    local bot_name=$(get_bot_name "$bot_dir")

    log_info "Dang cap nhat $bot_name..."

    # Backup first
    backup_single_bot_internal "$bot_name" ""

    # Stop bot
    pm2 stop "$bot_name" 2>/dev/null || true

    # Sync from template (preserve config)
    rsync -av --quiet \
        --exclude='.env' \
        --exclude='config.json' \
        --exclude='venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='ecosystem.config.js' \
        "$TEMPLATES_DIR/bot_template/" "$bot_dir/" 2>/dev/null || true

    # Update dependencies
    if [[ -d "$bot_dir/venv" ]]; then
        cd "$bot_dir"
        source venv/bin/activate
        pip install -r requirements.txt -q --upgrade 2>/dev/null || true
        deactivate
    fi

    # Run migrations if alembic exists
    if [[ -f "$bot_dir/alembic.ini" ]]; then
        cd "$bot_dir"
        source venv/bin/activate 2>/dev/null || true
        alembic upgrade head 2>/dev/null || log_warn "Migration that bai"
        deactivate 2>/dev/null || true
    fi

    # Restart
    pm2 restart "$bot_name" 2>/dev/null || pm2 start "$bot_name" 2>/dev/null || true

    log_success "Da cap nhat $bot_name"
}

update_all_bots() {
    log_info "Dang cap nhat tat ca bot..."

    for bot_dir in "$BOTS_DIR"/*/; do
        [[ ! -d "$bot_dir" ]] && continue
        update_single_bot "$bot_dir"
    done

    log_success "Da cap nhat tat ca bot"
}

update_template() {
    log_info "Dang cap nhat template..."

    if [[ -d "$TEMPLATES_DIR/bot_template/.git" ]]; then
        cd "$TEMPLATES_DIR/bot_template"
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || log_warn "Khong the pull tu git"
    fi

    log_success "Template da cap nhat"
}

#-------------------------------------------------------------------------------
# [7] Manage Timezone
#-------------------------------------------------------------------------------

manage_timezone() {
    clear
    echo -e "\n${BOLD}=== QUAN LY TIMEZONE ===${NC}\n"

    echo "Timezone hien tai: ${TZ:-Asia/Ho_Chi_Minh}"
    echo ""
    echo "Timezone pho bien:"
    echo "  1. Asia/Ho_Chi_Minh (UTC+7)"
    echo "  2. Asia/Bangkok (UTC+7)"
    echo "  3. Asia/Singapore (UTC+8)"
    echo "  4. Asia/Tokyo (UTC+9)"
    echo "  5. UTC"
    echo "  6. Nhap timezone khac"
    echo "  0. Quay lai"
    echo ""
    read -p "Chon: " tz_choice

    local new_tz=""
    case $tz_choice in
        1) new_tz="Asia/Ho_Chi_Minh" ;;
        2) new_tz="Asia/Bangkok" ;;
        3) new_tz="Asia/Singapore" ;;
        4) new_tz="Asia/Tokyo" ;;
        5) new_tz="UTC" ;;
        6)
            read -p "Nhap timezone: " new_tz
            ;;
        0) return ;;
    esac

    if [[ -n "$new_tz" ]]; then
        # Update global config
        sed -i "s/^TZ=.*/TZ=$new_tz/" "$CONFIG_DIR/global.conf"

        # Update all bot .env files
        for bot_dir in "$BOTS_DIR"/*/; do
            [[ ! -d "$bot_dir" ]] && continue
            if [[ -f "$bot_dir/.env" ]]; then
                sed -i "s/^TZ=.*/TZ=$new_tz/" "$bot_dir/.env"
            fi
        done

        log_success "Da cap nhat timezone thanh $new_tz"
        log_info "Restart cac bot de ap dung thay doi"
    fi

    press_enter
}

#-------------------------------------------------------------------------------
# [8] Backup & Restore
#-------------------------------------------------------------------------------

backup_restore() {
    while true; do
        clear
        echo -e "\n${BOLD}=== BACKUP & RESTORE ===${NC}\n"
        echo "1. Backup mot bot"
        echo "2. Backup tat ca bot"
        echo "3. Restore tu backup"
        echo "4. Xem danh sach backup"
        echo "5. Xoa backup cu"
        echo "0. Quay lai"
        echo ""
        read -p "Chon: " br_choice

        case $br_choice in
            1)
                list_bots_simple
                read -p "Chon bot: " bot_num
                local bot_dir=$(get_bot_dir_by_index "$bot_num")
                if [[ -n "$bot_dir" && -d "$bot_dir" ]]; then
                    local bot_name=$(get_bot_name "$bot_dir")
                    local config_file="$bot_dir/config.json"
                    local db_name=$(jq -r '.database_name // empty' "$config_file" 2>/dev/null)
                    backup_single_bot_internal "$bot_name" "$db_name"
                fi
                press_enter
                ;;
            2)
                backup_all_bots_internal
                press_enter
                ;;
            3)
                restore_from_backup
                ;;
            4)
                list_backups
                press_enter
                ;;
            5)
                cleanup_old_backups
                press_enter
                ;;
            0)
                return
                ;;
        esac
    done
}

backup_single_bot_internal() {
    local bot_name="$1"
    local db_name="$2"

    [[ -z "$db_name" ]] && db_name="${bot_name}_db"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/manual/${bot_name}_${timestamp}"

    mkdir -p "$backup_path"

    log_info "Backup $bot_name..."

    # Backup database
    pg_dump -U botpanel -F c "$db_name" > "$backup_path/database.dump" 2>/dev/null || \
        log_warn "Khong the backup database"

    # Backup config files
    if [[ -d "$BOTS_DIR/$bot_name" ]]; then
        cp "$BOTS_DIR/$bot_name/.env" "$backup_path/" 2>/dev/null || true
        cp "$BOTS_DIR/$bot_name/config.json" "$backup_path/" 2>/dev/null || true
    fi

    # Compress
    tar -czf "${backup_path}.tar.gz" -C "$BACKUP_DIR/manual" "$(basename "$backup_path")"
    rm -rf "$backup_path"

    log_success "Backup luu tai: ${backup_path}.tar.gz"
}

backup_all_bots_internal() {
    log_info "Backup tat ca bot..."

    for bot_dir in "$BOTS_DIR"/*/; do
        [[ ! -d "$bot_dir" ]] && continue
        local bot_name=$(get_bot_name "$bot_dir")
        local config_file="$bot_dir/config.json"
        local db_name=$(jq -r '.database_name // empty' "$config_file" 2>/dev/null)
        backup_single_bot_internal "$bot_name" "$db_name"
    done

    log_success "Da backup tat ca bot"
}

list_backups() {
    echo ""
    echo -e "${CYAN}=== DANH SACH BACKUP ===${NC}"
    echo ""
    echo "Manual backups:"
    ls -lh "$BACKUP_DIR/manual/"*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  Khong co backup"
    echo ""
    echo "Daily backups:"
    ls -lh "$BACKUP_DIR/daily/"*.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  Khong co backup"
}

restore_from_backup() {
    echo ""
    echo -e "${CYAN}=== RESTORE TU BACKUP ===${NC}"
    echo ""

    # List available backups
    local backups=("$BACKUP_DIR/manual/"*.tar.gz)
    if [[ ${#backups[@]} -eq 0 || ! -f "${backups[0]}" ]]; then
        log_warn "Khong co backup nao"
        press_enter
        return
    fi

    local i=1
    for backup in "${backups[@]}"; do
        echo "  $i. $(basename "$backup")"
        ((i++))
    done

    echo ""
    read -p "Chon backup (so thu tu): " backup_num

    local selected_backup="${backups[$((backup_num-1))]}"
    if [[ ! -f "$selected_backup" ]]; then
        log_error "Backup khong ton tai"
        press_enter
        return
    fi

    log_warn "Restore se ghi de du lieu hien tai!"
    read -p "Tiep tuc? (y/n): " confirm

    if [[ "$confirm" != "y" ]]; then
        return
    fi

    # Extract and restore
    local temp_dir=$(mktemp -d)
    tar -xzf "$selected_backup" -C "$temp_dir"

    local backup_name=$(ls "$temp_dir")
    local bot_name=$(echo "$backup_name" | sed 's/_[0-9]*_[0-9]*$//')

    # Restore database if dump exists
    if [[ -f "$temp_dir/$backup_name/database.dump" ]]; then
        log_info "Restore database..."
        local db_name="${bot_name}_db"
        pg_restore -U botpanel -d "$db_name" -c "$temp_dir/$backup_name/database.dump" 2>/dev/null || \
            log_warn "Restore database co loi"
    fi

    # Restore config files
    if [[ -d "$BOTS_DIR/$bot_name" ]]; then
        cp "$temp_dir/$backup_name/.env" "$BOTS_DIR/$bot_name/" 2>/dev/null || true
        cp "$temp_dir/$backup_name/config.json" "$BOTS_DIR/$bot_name/" 2>/dev/null || true
    fi

    rm -rf "$temp_dir"

    log_success "Restore thanh cong"
    press_enter
}

cleanup_old_backups() {
    local days=7
    read -p "Xoa backup cu hon bao nhieu ngay? [$days]: " custom_days
    days=${custom_days:-$days}

    log_info "Xoa backup cu hon $days ngay..."

    find "$BACKUP_DIR/manual" -name "*.tar.gz" -mtime +$days -delete 2>/dev/null
    find "$BACKUP_DIR/daily" -name "*.gz" -mtime +$days -delete 2>/dev/null

    log_success "Da xoa backup cu"
}

#-------------------------------------------------------------------------------
# [9] System Info
#-------------------------------------------------------------------------------

system_info() {
    clear
    echo -e "\n${BOLD}=== THONG TIN HE THONG ===${NC}\n"

    # System info
    echo -e "${CYAN}He thong:${NC}"
    echo "  OS:       $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "  Kernel:   $(uname -r)"
    echo "  Hostname: $(hostname)"
    echo "  Uptime:   $(uptime -p)"
    echo ""

    # Resources
    echo -e "${CYAN}Tai nguyen:${NC}"
    local mem_total=$(free -h | awk '/^Mem:/ {print $2}')
    local mem_used=$(free -h | awk '/^Mem:/ {print $3}')
    local mem_free=$(free -h | awk '/^Mem:/ {print $4}')
    local disk_total=$(df -h / | awk 'NR==2 {print $2}')
    local disk_used=$(df -h / | awk 'NR==2 {print $3}')
    local disk_free=$(df -h / | awk 'NR==2 {print $4}')
    local disk_percent=$(df -h / | awk 'NR==2 {print $5}')

    echo "  RAM:      $mem_used / $mem_total (free: $mem_free)"
    echo "  Disk:     $disk_used / $disk_total (free: $disk_free) [$disk_percent used]"
    echo "  Load:     $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
    echo ""

    # Services
    echo -e "${CYAN}Dich vu:${NC}"
    printf "  %-15s %s\n" "PostgreSQL:" "$(systemctl is-active postgresql 2>/dev/null || echo 'unknown')"
    printf "  %-15s %s\n" "Redis:" "$(systemctl is-active redis-server 2>/dev/null || echo 'unknown')"
    printf "  %-15s %s\n" "Nginx:" "$(systemctl is-active nginx 2>/dev/null || echo 'unknown')"
    printf "  %-15s %s\n" "PM2:" "$(pm2 --version 2>/dev/null || echo 'not installed')"
    echo ""

    # Versions
    echo -e "${CYAN}Phien ban:${NC}"
    echo "  Python:     $(python3.11 --version 2>/dev/null | awk '{print $2}' || echo 'not found')"
    echo "  Node.js:    $(node --version 2>/dev/null || echo 'not found')"
    echo "  PostgreSQL: $(psql --version 2>/dev/null | awk '{print $3}' || echo 'not found')"
    echo "  Redis:      $(redis-cli --version 2>/dev/null | awk '{print $2}' || echo 'not found')"
    echo ""

    # Bot summary
    echo -e "${CYAN}Bot:${NC}"
    local total_bots=$(ls -d "$BOTS_DIR"/*/ 2>/dev/null | wc -l)
    local online_bots=$(pm2 jlist 2>/dev/null | jq '[.[] | select(.pm2_env.status=="online")] | length' 2>/dev/null || echo 0)
    echo "  Tong so:    $total_bots"
    echo "  Online:     $online_bots"
    echo "  Offline:    $((total_bots - online_bots))"

    press_enter
}

#-------------------------------------------------------------------------------
# [10] Admin Alert Config
#-------------------------------------------------------------------------------

admin_alert() {
    clear
    echo -e "\n${BOLD}=== CAU HINH ADMIN ALERT ===${NC}\n"

    local admin_conf="$CONFIG_DIR/admin.conf"

    # Show current config
    echo "Cau hinh hien tai:"
    if [[ -f "$admin_conf" ]]; then
        cat "$admin_conf"
    else
        echo "  Chua co cau hinh"
    fi

    echo ""
    echo "1. Them Admin ID"
    echo "2. Xoa Admin ID"
    echo "3. Bat/Tat thong bao loi"
    echo "4. Bat/Tat thong bao restart"
    echo "5. Test thong bao"
    echo "0. Quay lai"
    echo ""
    read -p "Chon: " alert_choice

    case $alert_choice in
        1)
            read -p "Nhap Admin Telegram ID: " new_admin_id
            if [[ -n "$new_admin_id" ]]; then
                # Add to ADMIN_IDS array in admin.conf
                echo "# Admin ID: $new_admin_id" >> "$admin_conf"
                log_success "Da them Admin ID: $new_admin_id"
            fi
            ;;
        2)
            read -p "Nhap Admin ID can xoa: " del_admin_id
            if [[ -n "$del_admin_id" ]]; then
                sed -i "/$del_admin_id/d" "$admin_conf"
                log_success "Da xoa Admin ID"
            fi
            ;;
        3)
            if grep -q "ALERT_ON_ERROR=true" "$admin_conf"; then
                sed -i 's/ALERT_ON_ERROR=true/ALERT_ON_ERROR=false/' "$admin_conf"
                log_info "Da tat thong bao loi"
            else
                sed -i 's/ALERT_ON_ERROR=false/ALERT_ON_ERROR=true/' "$admin_conf"
                log_info "Da bat thong bao loi"
            fi
            ;;
        4)
            if grep -q "ALERT_ON_RESTART=true" "$admin_conf"; then
                sed -i 's/ALERT_ON_RESTART=true/ALERT_ON_RESTART=false/' "$admin_conf"
                log_info "Da tat thong bao restart"
            else
                sed -i 's/ALERT_ON_RESTART=false/ALERT_ON_RESTART=true/' "$admin_conf"
                log_info "Da bat thong bao restart"
            fi
            ;;
        5)
            log_info "Tinh nang test thong bao se co trong Phase 10"
            ;;
        0)
            return
            ;;
    esac

    press_enter
}

#-------------------------------------------------------------------------------
# [11] Monitoring & Metrics
#-------------------------------------------------------------------------------

monitoring() {
    clear
    echo -e "\n${BOLD}=== MONITORING & METRICS ===${NC}\n"

    echo "1. Xem PM2 monit (realtime)"
    echo "2. Xem PM2 status"
    echo "3. Cau hinh Prometheus"
    echo "4. Mo Grafana Dashboard"
    echo "0. Quay lai"
    echo ""
    read -p "Chon: " mon_choice

    case $mon_choice in
        1)
            echo ""
            echo "Nhan 'q' de thoat PM2 monit"
            sleep 1
            pm2 monit
            ;;
        2)
            echo ""
            pm2 status
            press_enter
            ;;
        3)
            echo ""
            log_info "Prometheus se duoc cau hinh trong Phase 10"
            press_enter
            ;;
        4)
            echo ""
            if [[ "${GRAFANA_ENABLED:-false}" == "true" ]]; then
                echo "Grafana URL: http://localhost:3000"
            else
                log_info "Grafana chua duoc bat. Cau hinh trong Phase 10"
            fi
            press_enter
            ;;
        0)
            return
            ;;
    esac
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    # Check if running as botpanel user or root
    if [[ $EUID -ne 0 && "$(whoami)" != "botpanel" ]]; then
        echo -e "${RED}Vui long chay voi user botpanel hoac root${NC}"
        exit 1
    fi

    while true; do
        show_menu
        read -p "Chon: " choice
        case $choice in
            1) list_bots ;;
            2) create_bot ;;
            3) manage_bot ;;
            4) delete_bot ;;
            5) view_logs ;;
            6) update_bot ;;
            7) manage_timezone ;;
            8) backup_restore ;;
            9) system_info ;;
            10) admin_alert ;;
            11) monitoring ;;
            0)
                echo ""
                log_info "Tam biet!"
                exit 0
                ;;
            *)
                log_error "Lua chon khong hop le"
                sleep 1
                ;;
        esac
    done
}

# Run
main "$@"
