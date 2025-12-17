#!/bin/bash
#===============================================================================
# TeleTask Bot - Automated Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash
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
LOG_DIR="$BOTPANEL_HOME/logs"
BACKUP_DIR="$BOTPANEL_HOME/backups"
PYTHON_VERSION="3.11"
TIMEZONE="Asia/Ho_Chi_Minh"

# Will be set after asking for bot name
BOT_SLUG=""
BOT_DIR=""
DB_NAME=""
DB_USER="botpanel"
DB_PASSWORD=""

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
# Ask for bot name and set up variables
#-------------------------------------------------------------------------------
setup_bot_config() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    TeleTask Bot Installer                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "${YELLOW}Enter a name for your bot (e.g., mybot, taskbot, companybot):${NC}"
    echo -e "This will be used as folder name and database name."
    echo -e "Only lowercase letters, numbers, and underscores allowed.\n"

    read -p "Bot name: " BOT_NAME_INPUT < /dev/tty

    if [ -z "$BOT_NAME_INPUT" ]; then
        log_error "Bot name is required!"
        exit 1
    fi

    # Convert to slug: lowercase, replace spaces/special chars with underscore
    BOT_SLUG=$(echo "$BOT_NAME_INPUT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')

    if [ -z "$BOT_SLUG" ]; then
        log_error "Invalid bot name!"
        exit 1
    fi

    # Set derived variables
    BOT_DIR="$BOTPANEL_HOME/bots/$BOT_SLUG"
    DB_NAME="${BOT_SLUG}_db"
    DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

    log_info "Bot slug: $BOT_SLUG"
    log_info "Bot directory: $BOT_DIR"
    log_info "Database name: $DB_NAME"
    echo ""
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

    log_success "PostgreSQL installed"
}

setup_database() {
    log_info "Setting up database..."

    # Check if user exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
        log_warn "Database user '$DB_USER' already exists, updating password..."
        sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    else
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    fi

    # Check if database exists
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        log_warn "Database '$DB_NAME' already exists"
    else
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    fi

    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

    log_success "Database configured"
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
# Step 5: Create botpanel user
#-------------------------------------------------------------------------------
create_user() {
    log_info "Creating botpanel user..."

    if id "$BOTPANEL_USER" &>/dev/null; then
        log_warn "User '$BOTPANEL_USER' already exists"
    else
        useradd -m -s /bin/bash "$BOTPANEL_USER"
    fi

    # Create directories
    mkdir -p "$BOT_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"

    chown -R "$BOTPANEL_USER:$BOTPANEL_USER" "$BOTPANEL_HOME"

    log_success "User and directories created"
}

#-------------------------------------------------------------------------------
# Step 6: Clone repository
#-------------------------------------------------------------------------------
clone_repository() {
    log_info "Cloning TeleTask repository..."

    # Check if bot files already exist
    if [ -f "$BOT_DIR/bot.py" ]; then
        log_warn "Bot files already exist, skipping clone"
        log_success "Repository ready"
        return 0
    fi

    # Clone to temp directory and copy template
    TEMP_DIR=$(mktemp -d)

    git clone --depth 1 https://github.com/haduyson/teletask.git "$TEMP_DIR" || {
        log_warn "Clone failed, checking for local template..."
        rm -rf "$TEMP_DIR"
        if [ -d "/root/teletask/src/templates/bot_template" ]; then
            cp -r /root/teletask/src/templates/bot_template/* "$BOT_DIR/"
            chown -R "$BOTPANEL_USER:$BOTPANEL_USER" "$BOT_DIR"
            log_success "Repository ready"
            return 0
        else
            log_error "No source found. Please clone manually."
            exit 1
        fi
    }

    # Copy only the bot template files
    if [ -d "$TEMP_DIR/src/templates/bot_template" ]; then
        cp -r "$TEMP_DIR/src/templates/bot_template/"* "$BOT_DIR/"
        chown -R "$BOTPANEL_USER:$BOTPANEL_USER" "$BOT_DIR"
    else
        log_error "Template not found in repository"
        rm -rf "$TEMP_DIR"
        exit 1
    fi

    # Cleanup temp directory
    rm -rf "$TEMP_DIR"

    log_success "Repository ready"
}

#-------------------------------------------------------------------------------
# Step 7: Setup Python environment
#-------------------------------------------------------------------------------
setup_python_env() {
    log_info "Setting up Python virtual environment..."

    sudo -u "$BOTPANEL_USER" bash -c "
        cd '$BOT_DIR'
        python${PYTHON_VERSION} -m venv venv
        source venv/bin/activate
        pip install --upgrade pip -q
        pip install -r requirements.txt -q
    "

    log_success "Python environment configured"
}

#-------------------------------------------------------------------------------
# Step 8: Configure environment
#-------------------------------------------------------------------------------
configure_env() {
    log_info "Creating .env configuration..."

    # Prompt for bot token
    echo -e "${YELLOW}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                  TELEGRAM BOT CONFIGURATION                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    read -p "Enter your Telegram Bot Token (from @BotFather): " BOT_TOKEN < /dev/tty

    if [ -z "$BOT_TOKEN" ]; then
        log_error "Bot token is required!"
        exit 1
    fi

    read -p "Enter your Telegram User ID (for admin notifications, optional): " ADMIN_ID < /dev/tty

    # Create .env file
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
LOG_FILE=$LOG_DIR/teletask.log

#-------------------------------------------------------------------------------
# Admin
#-------------------------------------------------------------------------------
ADMIN_IDS=$ADMIN_ID

#-------------------------------------------------------------------------------
# Features (optional)
#-------------------------------------------------------------------------------
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
OAUTH_CALLBACK_PORT=8081

METRICS_ENABLED=false
HEALTH_PORT=8080
EOF

    chown "$BOTPANEL_USER:$BOTPANEL_USER" "$BOT_DIR/.env"
    chmod 600 "$BOT_DIR/.env"

    log_success "Environment configured"
}

#-------------------------------------------------------------------------------
# Step 9: Run database migrations
#-------------------------------------------------------------------------------
run_migrations() {
    log_info "Running database migrations..."

    if sudo -u "$BOTPANEL_USER" bash -c "
        cd '$BOT_DIR'
        source venv/bin/activate
        alembic upgrade head
    "; then
        log_success "Database migrations completed"
    else
        log_warn "Database migrations failed. You can run manually later: botpanel db-migrate"
    fi
}

#-------------------------------------------------------------------------------
# Step 10: Create botpanel CLI
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
# Usage: botpanel [command]
#===============================================================================

BOT_DIR="__BOT_DIR__"
LOG_DIR="/home/botpanel/logs"
BACKUP_DIR="/home/botpanel/backups"
PM2_NAME="__PM2_NAME__"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                   TeleTask Bot Manager                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    print_banner
    echo -e "${GREEN}Usage:${NC} botpanel [command]"
    echo ""
    echo -e "${YELLOW}Bot Management:${NC}"
    echo "  start       Start the bot"
    echo "  stop        Stop the bot"
    echo "  restart     Restart the bot"
    echo "  status      Show bot status"
    echo "  logs        Show bot logs (live)"
    echo "  logs-err    Show error logs"
    echo ""
    echo -e "${YELLOW}Database:${NC}"
    echo "  db-status   Check database connection"
    echo "  db-migrate  Run database migrations"
    echo "  db-backup   Backup database"
    echo "  db-restore  Restore database from backup"
    echo ""
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  config      Edit .env configuration"
    echo "  token       Update bot token"
    echo "  gcal        Configure Google Calendar"
    echo ""
    echo -e "${YELLOW}Maintenance:${NC}"
    echo "  update      Update bot to latest version"
    echo "  deps        Reinstall dependencies"
    echo "  clean       Clean logs and temp files"
    echo "  info        Show system information"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  botpanel start"
    echo "  botpanel logs"
    echo "  botpanel db-backup"
}

cmd_start() {
    echo -e "${BLUE}[INFO]${NC} Starting TeleTask bot..."

    if pm2 describe "$PM2_NAME" &>/dev/null; then
        pm2 restart "$PM2_NAME"
    else
        cd "$BOT_DIR"
        pm2 start "$BOT_DIR/venv/bin/python" \
            --name "$PM2_NAME" \
            --interpreter none \
            -- "$BOT_DIR/bot.py"
        pm2 save
    fi

    echo -e "${GREEN}[OK]${NC} Bot started"
    pm2 status "$PM2_NAME"
}

cmd_stop() {
    echo -e "${BLUE}[INFO]${NC} Stopping TeleTask bot..."
    pm2 stop "$PM2_NAME" 2>/dev/null || true
    echo -e "${GREEN}[OK]${NC} Bot stopped"
}

cmd_restart() {
    echo -e "${BLUE}[INFO]${NC} Restarting TeleTask bot..."
    pm2 restart "$PM2_NAME"
    echo -e "${GREEN}[OK]${NC} Bot restarted"
}

cmd_status() {
    print_banner
    echo -e "${YELLOW}Bot Status:${NC}"
    pm2 status "$PM2_NAME"
    echo ""
    echo -e "${YELLOW}System:${NC}"
    echo "  Uptime: $(uptime -p)"
    echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
    echo "  Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
}

cmd_logs() {
    pm2 logs "$PM2_NAME" --lines 100
}

cmd_logs_err() {
    pm2 logs "$PM2_NAME" --err --lines 100
}

cmd_db_status() {
    echo -e "${BLUE}[INFO]${NC} Checking database connection..."
    source "$BOT_DIR/.env"

    # Extract DB credentials from DATABASE_URL
    DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
    DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

    if PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Database connection successful"

        # Show table counts
        echo ""
        echo -e "${YELLOW}Table Statistics:${NC}"
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT 'users' as table_name, COUNT(*) as count FROM users
            UNION ALL
            SELECT 'tasks', COUNT(*) FROM tasks
            UNION ALL
            SELECT 'reminders', COUNT(*) FROM reminders;
        "
    else
        echo -e "${RED}[ERROR]${NC} Database connection failed"
    fi
}

cmd_db_migrate() {
    echo -e "${BLUE}[INFO]${NC} Running database migrations..."
    cd "$BOT_DIR"
    source venv/bin/activate
    alembic upgrade head
    echo -e "${GREEN}[OK]${NC} Migrations completed"
}

cmd_db_backup() {
    echo -e "${BLUE}[INFO]${NC} Creating database backup..."
    source "$BOT_DIR/.env"

    # Extract DB credentials from DATABASE_URL
    DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
    DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"

    PGPASSWORD="$DB_PASS" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${GREEN}[OK]${NC} Backup created: $BACKUP_FILE"
        echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    else
        echo -e "${RED}[ERROR]${NC} Backup failed"
    fi
}

cmd_db_restore() {
    echo -e "${YELLOW}Available backups:${NC}"
    ls -la "$BACKUP_DIR"/*.sql 2>/dev/null || {
        echo "No backups found in $BACKUP_DIR"
        return
    }

    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE

    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        source "$BOT_DIR/.env"
        DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
        DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
        DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

        echo -e "${BLUE}[INFO]${NC} Restoring database..."
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" "$DB_NAME" < "$BACKUP_DIR/$BACKUP_FILE"
        echo -e "${GREEN}[OK]${NC} Database restored"
    else
        echo -e "${RED}[ERROR]${NC} Backup file not found"
    fi
}

cmd_config() {
    ${EDITOR:-nano} "$BOT_DIR/.env"
    echo -e "${YELLOW}[WARN]${NC} Restart bot to apply changes: botpanel restart"
}

cmd_token() {
    read -p "Enter new Bot Token: " NEW_TOKEN
    if [ -n "$NEW_TOKEN" ]; then
        sed -i "s/^BOT_TOKEN=.*/BOT_TOKEN=$NEW_TOKEN/" "$BOT_DIR/.env"
        echo -e "${GREEN}[OK]${NC} Token updated. Restart bot: botpanel restart"
    fi
}

cmd_gcal() {
    echo -e "${CYAN}Google Calendar Configuration${NC}"
    echo ""

    read -p "Enable Google Calendar? (y/n): " ENABLE_GCAL

    if [[ "$ENABLE_GCAL" =~ ^[Yy]$ ]]; then
        read -p "Google Client ID: " GCAL_CLIENT_ID
        read -p "Google Client Secret: " GCAL_CLIENT_SECRET
        read -p "Redirect URI (e.g., https://yourdomain.com/oauth/callback): " GCAL_REDIRECT

        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=true/" "$BOT_DIR/.env"
        sed -i "s/^GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=$GCAL_CLIENT_ID/" "$BOT_DIR/.env"
        sed -i "s/^GOOGLE_CLIENT_SECRET=.*/GOOGLE_CLIENT_SECRET=$GCAL_CLIENT_SECRET/" "$BOT_DIR/.env"
        sed -i "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=$GCAL_REDIRECT|" "$BOT_DIR/.env"

        echo -e "${GREEN}[OK]${NC} Google Calendar configured. Restart bot: botpanel restart"
    else
        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=false/" "$BOT_DIR/.env"
        echo -e "${GREEN}[OK]${NC} Google Calendar disabled"
    fi
}

cmd_update() {
    echo -e "${BLUE}[INFO]${NC} Updating TeleTask bot..."

    # Stop bot
    pm2 stop "$PM2_NAME" 2>/dev/null || true

    # Pull latest
    cd "$BOT_DIR"
    git pull origin main

    # Update dependencies
    source venv/bin/activate
    pip install -r requirements.txt -q

    # Run migrations
    alembic upgrade head

    # Restart
    pm2 restart "$PM2_NAME"

    echo -e "${GREEN}[OK]${NC} Update completed"
}

cmd_deps() {
    echo -e "${BLUE}[INFO]${NC} Reinstalling dependencies..."
    cd "$BOT_DIR"
    source venv/bin/activate
    pip install -r requirements.txt --force-reinstall -q
    echo -e "${GREEN}[OK]${NC} Dependencies reinstalled"
}

cmd_clean() {
    echo -e "${BLUE}[INFO]${NC} Cleaning logs and temp files..."

    # Clean old logs
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete

    # Clean PM2 logs
    pm2 flush

    # Clean old backups (keep last 10)
    cd "$BACKUP_DIR" && ls -t *.sql 2>/dev/null | tail -n +11 | xargs -r rm --

    echo -e "${GREEN}[OK]${NC} Cleanup completed"
}

cmd_info() {
    print_banner
    echo -e "${YELLOW}System Information:${NC}"
    echo "  OS: $(lsb_release -d | cut -f2)"
    echo "  Kernel: $(uname -r)"
    echo "  Python: $(python3.11 --version 2>/dev/null || echo 'Not found')"
    echo "  Node.js: $(node --version 2>/dev/null || echo 'Not found')"
    echo "  PM2: $(pm2 --version 2>/dev/null || echo 'Not found')"
    echo "  PostgreSQL: $(psql --version 2>/dev/null | head -1 || echo 'Not found')"
    echo ""
    echo -e "${YELLOW}Bot Information:${NC}"
    echo "  Directory: $BOT_DIR"
    echo "  Logs: $LOG_DIR"
    echo "  Backups: $BACKUP_DIR"

    if [ -f "$BOT_DIR/.env" ]; then
        source "$BOT_DIR/.env"
        echo "  Bot Name: $BOT_NAME"
        echo "  Timezone: $TZ"
        echo "  Google Calendar: $GOOGLE_CALENDAR_ENABLED"
    fi
}

# Main
case "$1" in
    start)      cmd_start ;;
    stop)       cmd_stop ;;
    restart)    cmd_restart ;;
    status)     cmd_status ;;
    logs)       cmd_logs ;;
    logs-err)   cmd_logs_err ;;
    db-status)  cmd_db_status ;;
    db-migrate) cmd_db_migrate ;;
    db-backup)  cmd_db_backup ;;
    db-restore) cmd_db_restore ;;
    config)     cmd_config ;;
    token)      cmd_token ;;
    gcal)       cmd_gcal ;;
    update)     cmd_update ;;
    deps)       cmd_deps ;;
    clean)      cmd_clean ;;
    info)       cmd_info ;;
    help|--help|-h|"")
        print_help ;;
    *)
        echo -e "${RED}[ERROR]${NC} Unknown command: $1"
        echo "Run 'botpanel help' for usage"
        exit 1 ;;
esac
EOFCLI

    # Replace placeholders with actual values
    sed -i "s|__BOT_DIR__|$BOT_DIR|g" /usr/local/bin/botpanel
    sed -i "s|__PM2_NAME__|$BOT_SLUG|g" /usr/local/bin/botpanel

    chmod +x /usr/local/bin/botpanel

    log_success "botpanel CLI created"
}

#-------------------------------------------------------------------------------
# Step 11: Setup PM2 startup
#-------------------------------------------------------------------------------
setup_pm2_startup() {
    log_info "Configuring PM2 startup..."

    # Setup PM2 to start on boot
    pm2 startup systemd -u "$BOTPANEL_USER" --hp "$BOTPANEL_HOME"

    log_success "PM2 startup configured"
}

#-------------------------------------------------------------------------------
# Step 12: Start bot
#-------------------------------------------------------------------------------
start_bot() {
    log_info "Starting TeleTask bot..."

    # Start with PM2
    sudo -u "$BOTPANEL_USER" bash -c "
        cd '$BOT_DIR'
        source venv/bin/activate
        pm2 start '$BOT_DIR/venv/bin/python' \
            --name '$BOT_SLUG' \
            --interpreter none \
            -- '$BOT_DIR/bot.py'
        pm2 save
    "

    log_success "Bot started"
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

    echo -e "${YELLOW}Bot Information:${NC}"
    echo "  Bot Name: $BOT_SLUG"
    echo "  PM2 Name: $BOT_SLUG"
    echo "  Directory: $BOT_DIR"
    echo ""

    echo -e "${YELLOW}Database Credentials (save these!):${NC}"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASSWORD"
    echo ""

    echo -e "${YELLOW}Bot Management:${NC}"
    echo "  Use 'botpanel' command to manage the bot"
    echo ""
    echo "  botpanel status    - Check bot status"
    echo "  botpanel logs      - View logs"
    echo "  botpanel restart   - Restart bot"
    echo "  botpanel config    - Edit configuration"
    echo "  botpanel help      - Show all commands"
    echo ""

    echo -e "${YELLOW}Files:${NC}"
    echo "  Config: $BOT_DIR/.env"
    echo "  Logs: $LOG_DIR/"
    echo "  Backups: $BACKUP_DIR/"
    echo ""

    echo -e "${CYAN}Test your bot in Telegram: /start${NC}"
    echo ""
    echo -e "${YELLOW}Note:${NC} PM2 process name is '$BOT_SLUG' - use 'pm2 logs $BOT_SLUG' for raw logs"
}

#-------------------------------------------------------------------------------
# Main installation
#-------------------------------------------------------------------------------
main() {
    check_root
    setup_bot_config

    log_info "Starting TeleTask Bot installation..."
    echo ""

    prepare_system
    install_postgresql
    setup_database
    install_python
    install_nodejs
    create_user
    clone_repository
    setup_python_env
    configure_env
    run_migrations
    create_botpanel_cli
    setup_pm2_startup
    start_bot

    print_summary
}

# Run main
main "$@"
