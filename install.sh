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
    echo "║                   TeleTask Bot Manager                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    print_banner
    echo -e "${GREEN}Usage:${NC} botpanel [command] [bot_name]"
    echo ""
    echo -e "${YELLOW}Bot Creation:${NC}"
    echo "  create              Create a new bot"
    echo "  list                List all bots"
    echo "  delete <bot>        Delete a bot"
    echo ""
    echo -e "${YELLOW}Bot Management:${NC}"
    echo "  start <bot>         Start a bot"
    echo "  stop <bot>          Stop a bot"
    echo "  restart <bot>       Restart a bot"
    echo "  status [bot]        Show bot status (all if no bot specified)"
    echo "  logs <bot>          Show bot logs (live)"
    echo "  logs-err <bot>      Show error logs"
    echo ""
    echo -e "${YELLOW}Database:${NC}"
    echo "  db-status <bot>     Check database connection"
    echo "  db-migrate <bot>    Run database migrations"
    echo "  db-backup <bot>     Backup database"
    echo "  db-restore <bot>    Restore database from backup"
    echo ""
    echo -e "${YELLOW}Configuration:${NC}"
    echo "  config <bot>        Edit .env configuration"
    echo "  token <bot>         Update bot token"
    echo "  gcal <bot>          Configure Google Calendar"
    echo ""
    echo -e "${YELLOW}Maintenance:${NC}"
    echo "  update <bot>        Update bot to latest version"
    echo "  deps <bot>          Reinstall dependencies"
    echo "  clean               Clean logs and temp files"
    echo "  info                Show system information"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  botpanel create"
    echo "  botpanel start mybot"
    echo "  botpanel logs taskbot"
    echo "  botpanel db-backup mybot"
}

# Get bot directory
get_bot_dir() {
    local bot_name="$1"
    if [ -z "$bot_name" ]; then
        echo -e "${RED}[ERROR]${NC} Bot name is required"
        return 1
    fi

    local bot_dir="$BOTS_DIR/$bot_name"
    if [ ! -d "$bot_dir" ]; then
        echo -e "${RED}[ERROR]${NC} Bot '$bot_name' not found"
        echo "Available bots:"
        ls -1 "$BOTS_DIR" 2>/dev/null || echo "  (none)"
        return 1
    fi

    echo "$bot_dir"
}

#-------------------------------------------------------------------------------
# Create new bot
#-------------------------------------------------------------------------------
cmd_create() {
    print_banner
    echo -e "${YELLOW}Create a new TeleTask bot${NC}"
    echo ""

    # Ask for bot name
    echo -e "Enter a name for your bot (e.g., mybot, taskbot, companybot):"
    echo -e "Only lowercase letters, numbers, and underscores allowed."
    echo ""
    read -p "Bot name: " BOT_NAME_INPUT

    if [ -z "$BOT_NAME_INPUT" ]; then
        echo -e "${RED}[ERROR]${NC} Bot name is required!"
        exit 1
    fi

    # Convert to slug
    BOT_SLUG=$(echo "$BOT_NAME_INPUT" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//')

    if [ -z "$BOT_SLUG" ]; then
        echo -e "${RED}[ERROR]${NC} Invalid bot name!"
        exit 1
    fi

    BOT_DIR="$BOTS_DIR/$BOT_SLUG"

    # Check if bot already exists
    if [ -d "$BOT_DIR" ]; then
        echo -e "${RED}[ERROR]${NC} Bot '$BOT_SLUG' already exists at $BOT_DIR"
        exit 1
    fi

    echo -e "${BLUE}[INFO]${NC} Bot slug: $BOT_SLUG"
    echo ""

    # Ask for bot token
    echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                  TELEGRAM BOT CONFIGURATION                  ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    read -p "Enter your Telegram Bot Token (from @BotFather): " BOT_TOKEN

    if [ -z "$BOT_TOKEN" ]; then
        echo -e "${RED}[ERROR]${NC} Bot token is required!"
        exit 1
    fi

    read -p "Enter your Telegram User ID (for admin, optional): " ADMIN_ID

    echo ""
    echo -e "${BLUE}[INFO]${NC} Creating bot '$BOT_SLUG'..."

    # Create bot directory
    mkdir -p "$BOT_DIR"

    # Clone template
    echo -e "${BLUE}[INFO]${NC} Downloading bot template..."
    TEMP_DIR=$(mktemp -d)

    if git clone --depth 1 https://github.com/haduyson/teletask.git "$TEMP_DIR" 2>/dev/null; then
        if [ -d "$TEMP_DIR/src/templates/bot_template" ]; then
            cp -r "$TEMP_DIR/src/templates/bot_template/"* "$BOT_DIR/"
        else
            echo -e "${RED}[ERROR]${NC} Template not found in repository"
            rm -rf "$TEMP_DIR" "$BOT_DIR"
            exit 1
        fi
        rm -rf "$TEMP_DIR"
    else
        echo -e "${RED}[ERROR]${NC} Failed to download template"
        rm -rf "$TEMP_DIR" "$BOT_DIR"
        exit 1
    fi

    echo -e "${GREEN}[OK]${NC} Template downloaded"

    # Setup Python environment
    echo -e "${BLUE}[INFO]${NC} Setting up Python environment..."
    cd "$BOT_DIR"
    python${PYTHON_VERSION} -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate

    echo -e "${GREEN}[OK]${NC} Python environment ready"

    # Create database
    echo -e "${BLUE}[INFO]${NC} Creating database..."
    DB_NAME="${BOT_SLUG}_db"
    DB_USER="botpanel"
    DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)

    # Create database using botpanel user's createdb privilege or postgres
    if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        echo -e "${YELLOW}[WARN]${NC} Database '$DB_NAME' already exists"
    else
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || {
            # Fallback: create with postgres
            sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
        }
    fi

    # Update user password
    sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true

    echo -e "${GREEN}[OK]${NC} Database created"

    # Create .env file
    echo -e "${BLUE}[INFO]${NC} Creating configuration..."
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

    chmod 600 "$BOT_DIR/.env"
    echo -e "${GREEN}[OK]${NC} Configuration created"

    # Run migrations
    echo -e "${BLUE}[INFO]${NC} Running database migrations..."
    cd "$BOT_DIR"
    source venv/bin/activate
    if alembic upgrade head 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Migrations completed"
    else
        echo -e "${YELLOW}[WARN]${NC} Migrations failed. Run later: botpanel db-migrate $BOT_SLUG"
    fi
    deactivate

    # Set ownership
    chown -R botpanel:botpanel "$BOT_DIR"

    # Start bot
    echo -e "${BLUE}[INFO]${NC} Starting bot..."
    sudo -u botpanel bash -c "
        cd '$BOT_DIR'
        source venv/bin/activate
        pm2 start '$BOT_DIR/venv/bin/python' \
            --name '$BOT_SLUG' \
            --interpreter none \
            -- '$BOT_DIR/bot.py'
        pm2 save
    "

    echo -e "${GREEN}[OK]${NC} Bot started"

    # Print summary
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  BOT CREATED SUCCESSFULLY                    ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Bot Information:${NC}"
    echo "  Name: $BOT_SLUG"
    echo "  Directory: $BOT_DIR"
    echo "  PM2 Name: $BOT_SLUG"
    echo ""
    echo -e "${YELLOW}Database (save these!):${NC}"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASSWORD"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  botpanel status $BOT_SLUG"
    echo "  botpanel logs $BOT_SLUG"
    echo "  botpanel restart $BOT_SLUG"
    echo ""
    echo -e "${CYAN}Test your bot in Telegram: /start${NC}"
}

#-------------------------------------------------------------------------------
# List all bots
#-------------------------------------------------------------------------------
cmd_list() {
    print_banner
    echo -e "${YELLOW}Available Bots:${NC}"
    echo ""

    if [ ! -d "$BOTS_DIR" ] || [ -z "$(ls -A "$BOTS_DIR" 2>/dev/null)" ]; then
        echo "  No bots found."
        echo ""
        echo "  Create one with: botpanel create"
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
                else
                    status_icon="${RED}●${NC}"
                fi
            else
                status_icon="${YELLOW}○${NC}"
                status="not started"
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

    echo -e "${YELLOW}[WARN]${NC} This will delete bot '$bot_name' and ALL its data!"
    read -p "Are you sure? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Cancelled."
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
        echo -e "${GREEN}[OK]${NC} Database '$DB_NAME' dropped"
    fi

    # Remove directory
    rm -rf "$bot_dir"

    echo -e "${GREEN}[OK]${NC} Bot '$bot_name' deleted"
}

#-------------------------------------------------------------------------------
# Bot management commands
#-------------------------------------------------------------------------------
cmd_start() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Starting bot '$bot_name'..."

    if pm2 describe "$bot_name" &>/dev/null; then
        pm2 restart "$bot_name"
    else
        sudo -u botpanel bash -c "
            cd '$bot_dir'
            source venv/bin/activate
            pm2 start '$bot_dir/venv/bin/python' \
                --name '$bot_name' \
                --interpreter none \
                -- '$bot_dir/bot.py'
            pm2 save
        "
    fi

    echo -e "${GREEN}[OK]${NC} Bot started"
    pm2 status "$bot_name"
}

cmd_stop() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    echo -e "${BLUE}[INFO]${NC} Stopping bot '$bot_name'..."
    pm2 stop "$bot_name" 2>/dev/null || true
    echo -e "${GREEN}[OK]${NC} Bot stopped"
}

cmd_restart() {
    local bot_name="$1"
    get_bot_dir "$bot_name" >/dev/null || exit 1

    echo -e "${BLUE}[INFO]${NC} Restarting bot '$bot_name'..."
    pm2 restart "$bot_name"
    echo -e "${GREEN}[OK]${NC} Bot restarted"
}

cmd_status() {
    local bot_name="$1"

    print_banner

    if [ -z "$bot_name" ]; then
        echo -e "${YELLOW}All Bots Status:${NC}"
        pm2 status
    else
        get_bot_dir "$bot_name" >/dev/null || exit 1
        echo -e "${YELLOW}Bot '$bot_name' Status:${NC}"
        pm2 status "$bot_name"
    fi

    echo ""
    echo -e "${YELLOW}System:${NC}"
    echo "  Uptime: $(uptime -p)"
    echo "  Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
    echo "  Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
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

    echo -e "${BLUE}[INFO]${NC} Checking database connection..."
    source "$bot_dir/.env"

    DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
    DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/')
    DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\/\([^:]*\):.*/\1/')

    if PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Database connection successful"
        echo ""
        echo -e "${YELLOW}Table Statistics:${NC}"
        PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT 'users' as table_name, COUNT(*) as count FROM users
            UNION ALL SELECT 'tasks', COUNT(*) FROM tasks
            UNION ALL SELECT 'reminders', COUNT(*) FROM reminders;
        " 2>/dev/null || echo "  (tables not created yet)"
    else
        echo -e "${RED}[ERROR]${NC} Database connection failed"
    fi
}

cmd_db_migrate() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Running database migrations..."
    cd "$bot_dir"
    source venv/bin/activate
    alembic upgrade head
    echo -e "${GREEN}[OK]${NC} Migrations completed"
}

cmd_db_backup() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Creating database backup..."
    source "$bot_dir/.env"

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
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${YELLOW}Available backups:${NC}"
    ls -la "$BACKUP_DIR"/*.sql 2>/dev/null || {
        echo "No backups found in $BACKUP_DIR"
        return
    }

    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE

    if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        source "$bot_dir/.env"
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

#-------------------------------------------------------------------------------
# Configuration commands
#-------------------------------------------------------------------------------
cmd_config() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    ${EDITOR:-nano} "$bot_dir/.env"
    echo -e "${YELLOW}[WARN]${NC} Restart bot to apply changes: botpanel restart $bot_name"
}

cmd_token() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    read -p "Enter new Bot Token: " NEW_TOKEN
    if [ -n "$NEW_TOKEN" ]; then
        sed -i "s/^BOT_TOKEN=.*/BOT_TOKEN=$NEW_TOKEN/" "$bot_dir/.env"
        echo -e "${GREEN}[OK]${NC} Token updated. Restart bot: botpanel restart $bot_name"
    fi
}

cmd_gcal() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${CYAN}Google Calendar Configuration${NC}"
    echo ""

    read -p "Enable Google Calendar? (y/n): " ENABLE_GCAL

    if [[ "$ENABLE_GCAL" =~ ^[Yy]$ ]]; then
        read -p "Google Client ID: " GCAL_CLIENT_ID
        read -p "Google Client Secret: " GCAL_CLIENT_SECRET
        read -p "Redirect URI (e.g., https://yourdomain.com/oauth/callback): " GCAL_REDIRECT

        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=true/" "$bot_dir/.env"
        sed -i "s/^GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=$GCAL_CLIENT_ID/" "$bot_dir/.env"
        sed -i "s/^GOOGLE_CLIENT_SECRET=.*/GOOGLE_CLIENT_SECRET=$GCAL_CLIENT_SECRET/" "$bot_dir/.env"
        sed -i "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=$GCAL_REDIRECT|" "$bot_dir/.env"

        echo -e "${GREEN}[OK]${NC} Google Calendar configured. Restart bot: botpanel restart $bot_name"
    else
        sed -i "s/^GOOGLE_CALENDAR_ENABLED=.*/GOOGLE_CALENDAR_ENABLED=false/" "$bot_dir/.env"
        echo -e "${GREEN}[OK]${NC} Google Calendar disabled"
    fi
}

#-------------------------------------------------------------------------------
# Maintenance commands
#-------------------------------------------------------------------------------
cmd_update() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Updating bot '$bot_name'..."

    # Stop bot
    pm2 stop "$bot_name" 2>/dev/null || true

    # Download latest template
    TEMP_DIR=$(mktemp -d)
    git clone --depth 1 https://github.com/haduyson/teletask.git "$TEMP_DIR" 2>/dev/null || {
        echo -e "${RED}[ERROR]${NC} Failed to download update"
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

    echo -e "${GREEN}[OK]${NC} Update completed"
}

cmd_deps() {
    local bot_name="$1"
    local bot_dir=$(get_bot_dir "$bot_name") || exit 1

    echo -e "${BLUE}[INFO]${NC} Reinstalling dependencies..."
    cd "$bot_dir"
    source venv/bin/activate
    pip install -r requirements.txt --force-reinstall -q
    echo -e "${GREEN}[OK]${NC} Dependencies reinstalled"
}

cmd_clean() {
    echo -e "${BLUE}[INFO]${NC} Cleaning logs and temp files..."

    # Clean old logs
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true

    # Clean PM2 logs
    pm2 flush 2>/dev/null || true

    # Clean old backups (keep last 10 per bot)
    for backup_prefix in $(ls "$BACKUP_DIR"/*.sql 2>/dev/null | sed 's/_[0-9]*_[0-9]*.sql$//' | sort -u); do
        ls -t "${backup_prefix}"_*.sql 2>/dev/null | tail -n +11 | xargs -r rm -- 2>/dev/null || true
    done

    echo -e "${GREEN}[OK]${NC} Cleanup completed"
}

cmd_info() {
    print_banner
    echo -e "${YELLOW}System Information:${NC}"
    echo "  OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo 'Unknown')"
    echo "  Kernel: $(uname -r)"
    echo "  Python: $(python${PYTHON_VERSION} --version 2>/dev/null || echo 'Not found')"
    echo "  Node.js: $(node --version 2>/dev/null || echo 'Not found')"
    echo "  PM2: $(pm2 --version 2>/dev/null || echo 'Not found')"
    echo "  PostgreSQL: $(psql --version 2>/dev/null | head -1 || echo 'Not found')"
    echo ""
    echo -e "${YELLOW}Directories:${NC}"
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
    help|--help|-h|"")
        print_help ;;
    *)
        echo -e "${RED}[ERROR]${NC} Unknown command: $1"
        echo "Run 'botpanel help' for usage"
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
