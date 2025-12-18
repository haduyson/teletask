# TeleTask Deployment Guide

**Document Version:** 1.0
**Last Updated:** December 18, 2025
**Target:** Ubuntu 20.04+ / Debian 11+
**Python:** 3.11+
**Database:** PostgreSQL 15+

---

## 1. Prerequisites

### 1.1 System Requirements

**Hardware (Minimum):**
- CPU: 1 core (2+ cores recommended)
- RAM: 512 MB (1 GB+ recommended)
- Storage: 10 GB (for application + backups)
- Network: Public or private IP (for OAuth callback)

**Supported OS:**
- Ubuntu 20.04 LTS or later
- Debian 11 or later
- Other Linux distributions (with adaptations)

**Software Requirements:**
- Python 3.11 or higher
- PostgreSQL 15 or higher
- Nginx (optional, for reverse proxy)
- Git (for updates)

### 1.2 Required Credentials

Before starting installation, prepare:

1. **Telegram Bot Token**
   - Create bot via [@BotFather](https://t.me/botfather)
   - Format: `123456789:ABCDefghijklmnopqrSTUvwxyz123`

2. **Google OAuth Credentials** (optional, for Google Calendar)
   - Create project in [Google Cloud Console](https://console.cloud.google.com)
   - Create OAuth 2.0 credentials (Desktop application)
   - Get Client ID and Client Secret
   - Configure redirect URI: `http://your-server-ip:8080/oauth_callback`

3. **Database Credentials**
   - PostgreSQL username (create new user for TeleTask)
   - PostgreSQL password (strong, random)

### 1.3 Network Configuration

**For OAuth Callback:**
- If using Google Calendar, bot needs callback URL
- Must be accessible from Google servers
- Can use localhost (127.0.0.1) if no public access needed
- If behind NAT, use reverse proxy (Nginx)

---

## 2. Automatic Installation

### 2.1 Quick Start (Recommended)

TeleTask provides an automated installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/haduyson/teletask/main/install.sh | sudo bash
```

**What the script does:**
1. Checks system requirements
2. Installs Python dependencies
3. Sets up PostgreSQL database
4. Configures bot credentials
5. Sets up Google OAuth (if enabled)
6. Registers with PM2 for auto-start
7. Configures Nginx reverse proxy
8. Verifies installation

**Installation takes:** 5-10 minutes

### 2.2 Installation Script Phases

The `install.sh` script runs through 7 phases:

**Phase 1: System Check**
```bash
- Detect OS (Ubuntu/Debian)
- Check Python version (3.11+)
- Check PostgreSQL installation
- Check required tools (git, curl, etc)
```

**Phase 2: Python Environment**
```bash
- Create virtual environment
- Install pip packages
- Create application directory
- Clone repository
```

**Phase 3: Database Setup**
```bash
- Create PostgreSQL database
- Create bot user with permissions
- Run Alembic migrations
- Initialize schema
```

**Phase 4: Bot Configuration**
```bash
- Prompt for Telegram token
- Prompt for database URL
- Prompt for webhook host:port
- Create .env file
```

**Phase 5: Google OAuth Setup** (optional)
```bash
- Prompt for Google Client ID
- Prompt for Google Client Secret
- Save to .env file
- Generate OAuth URL
```

**Phase 6: PM2 Service**
```bash
- Install PM2 globally
- Create ecosystem.config.js
- Register bot with PM2
- Enable auto-start on reboot
```

**Phase 7: Nginx Configuration** (optional)
```bash
- Create Nginx config
- Enable reverse proxy
- Configure SSL (Let's Encrypt)
- Test configuration
```

---

## 3. Manual Installation

If you prefer manual setup or the script fails:

### 3.1 System Dependencies

```bash
# Update package manager
sudo apt update
sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev
sudo apt install -y build-essential libpq-dev

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Nginx (optional)
sudo apt install -y nginx

# Install Node.js (for PM2)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2
sudo npm install -g pm2
```

### 3.2 PostgreSQL Setup

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Connect as postgres user
sudo -u postgres psql

# In psql shell:
CREATE DATABASE teletask;
CREATE USER teletask_bot WITH PASSWORD 'your_strong_password_here';
ALTER ROLE teletask_bot SET client_encoding TO 'utf8';
ALTER ROLE teletask_bot SET default_transaction_isolation TO 'read committed';
ALTER ROLE teletask_bot SET default_transaction_deferrable TO on;
ALTER ROLE teletask_bot CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE teletask TO teletask_bot;
\q  # Exit psql
```

### 3.3 Application Setup

```bash
# Create application directory
sudo mkdir -p /opt/teletask
sudo chown $USER:$USER /opt/teletask
cd /opt/teletask

# Clone repository
git clone https://github.com/haduyson/teletask.git .

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r src/templates/bot_template/requirements.txt
```

### 3.4 Environment Configuration

Create `.env` file in application directory:

```bash
# .env file
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=123456789:ABCDefghijklmnopqrSTUvwxyz123
WEBHOOK_HOST=127.0.0.1
WEBHOOK_PORT=8080

# Database Configuration
DATABASE_URL=postgresql+asyncpg://teletask_bot:your_password@localhost:5432/teletask

# Google OAuth Configuration (optional)
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://your-server-ip:8080/oauth_callback

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/teletask/bot.log

# Server
SERVER_TIMEZONE=Asia/Ho_Chi_Minh
ENVIRONMENT=production
```

**File permissions:**
```bash
chmod 600 .env  # Only readable by owner
```

### 3.5 Database Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run Alembic migrations
cd src/templates/bot_template
alembic upgrade head

# Verify schema created
psql -U teletask_bot -d teletask -c "\dt"  # List tables
```

### 3.6 PM2 Configuration

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'teletask-bot',
      script: './src/templates/bot_template/main.py',
      interpreter: './venv/bin/python',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production'
      },
      error_file: '/var/log/teletask/error.log',
      out_file: '/var/log/teletask/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
```

Register with PM2:

```bash
# Start with PM2
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Enable auto-start on reboot
pm2 startup systemd -u $USER --hp /home/$USER
```

### 3.7 Nginx Configuration (Optional)

Create `/etc/nginx/sites-available/teletask.conf`:

```nginx
upstream teletask_backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    # OAuth callback routing
    location /oauth_callback {
        proxy_pass http://teletask_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://teletask_backend;
    }
}
```

Enable configuration:

```bash
sudo ln -s /etc/nginx/sites-available/teletask.conf \
           /etc/nginx/sites-enabled/teletask.conf

sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## 4. Post-Installation Verification

### 4.1 Health Checks

```bash
# Check PM2 process status
pm2 status

# Check bot logs
pm2 logs teletask-bot

# Check database connectivity
psql -U teletask_bot -d teletask -c "SELECT 1"

# Check Telegram API connection
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Check system resources
free -h
df -h
top -b -n 1 | head -15
```

### 4.2 BotPanel CLI

After installation, manage bot using `botpanel` command:

```bash
# View all commands
botpanel help

# Check bot status
botpanel status

# View recent logs
botpanel logs tail

# Restart bot
botpanel restart

# View configuration
botpanel config show
```

### 4.3 First Run Testing

1. **Start the bot:**
   ```bash
   /start  # in Telegram
   ```

2. **Create a test task:**
   ```bash
   /taoviec Test task  # in Telegram
   ```

3. **Check logs:**
   ```bash
   botpanel logs tail 20
   ```

4. **Verify database:**
   ```bash
   psql -U teletask_bot -d teletask
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM tasks;
   \q
   ```

---

## 5. Configuration Guide

### 5.1 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot token from @BotFather |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `WEBHOOK_HOST` | No | 127.0.0.1 | Webhook server host |
| `WEBHOOK_PORT` | No | 8080 | Webhook server port |
| `GOOGLE_CLIENT_ID` | No | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | - | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | - | OAuth redirect URL |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FILE` | No | logs/bot.log | Log file path |
| `SERVER_TIMEZONE` | No | Asia/Ho_Chi_Minh | Server timezone |
| `ENVIRONMENT` | No | production | Environment (development/production) |

### 5.2 Database Configuration

Supported databases:
- PostgreSQL 15+ (recommended)

Connection string format:
```
postgresql+asyncpg://username:password@host:port/database
```

Example:
```
postgresql+asyncpg://teletask_bot:mypassword@localhost:5432/teletask
```

### 5.3 Telegram Bot Commands

Register commands with Telegram (so they appear in suggestions):

```bash
curl -X POST https://api.telegram.org/bot<TOKEN>/setMyCommands \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {"command": "start", "description": "Bắt đầu sử dụng"},
      {"command": "taoviec", "description": "Tạo công việc mới"},
      {"command": "xemviec", "description": "Xem danh sách công việc"},
      {"command": "giaoviec", "description": "Giao việc cho người khác"},
      {"command": "thongke", "description": "Xem thống kê"},
      {"command": "export", "description": "Xuất báo cáo"},
      {"command": "lichgoogle", "description": "Cài đặt Google Calendar"},
      {"command": "caidat", "description": "Cài đặt thông báo"},
      {"command": "help", "description": "Hiển thị trợ giúp"}
    ]
  }'
```

---

## 6. Backup & Recovery

### 6.1 Database Backup

**Manual backup:**

```bash
# Backup database
pg_dump -U teletask_bot -d teletask -F c -f teletask_backup.sql

# Compressed backup
pg_dump -U teletask_bot -d teletask | gzip > teletask_backup_$(date +%Y%m%d).sql.gz

# Backup to remote server (SSH)
pg_dump -U teletask_bot -d teletask | \
  ssh user@backup-server "cat > /backups/teletask_$(date +%Y%m%d).sql"
```

**Automated backup with cron:**

Create `/home/user/backup_teletask.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups/teletask"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/teletask_$DATE.sql.gz"

mkdir -p "$BACKUP_DIR"

pg_dump -U teletask_bot -d teletask | gzip > "$BACKUP_FILE"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "teletask_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:

```bash
# Run daily at 2:00 AM
crontab -e
# Add line:
0 2 * * * /home/user/backup_teletask.sh >> /var/log/teletask_backup.log 2>&1
```

### 6.2 Database Restore

```bash
# Restore from compressed backup
gunzip -c teletask_backup.sql.gz | psql -U teletask_bot -d teletask

# Or restore from plain SQL
psql -U teletask_bot -d teletask < teletask_backup.sql

# Verify restored data
psql -U teletask_bot -d teletask -c "SELECT COUNT(*) FROM users;"
```

### 6.3 Full System Backup

```bash
# Backup entire application directory
tar -czf teletask_app_$(date +%Y%m%d).tar.gz /opt/teletask/

# Backup with database
tar -czf teletask_full_$(date +%Y%m%d).tar.gz \
  /opt/teletask/ \
  /etc/nginx/sites-available/teletask.conf

# Restore
tar -xzf teletask_app_$(date +%Y%m%d).tar.gz -C /
```

---

## 7. System Updates

### 7.1 Update Bot

Using BotPanel:

```bash
botpanel update
```

This will:
1. Backup database
2. Pull latest code
3. Run migrations
4. Restart bot
5. Verify health

### 7.2 Manual Update

```bash
cd /opt/teletask

# Backup database
pg_dump -U teletask_bot -d teletask > backup_before_update.sql

# Pull latest code
git fetch origin
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r src/templates/bot_template/requirements.txt --upgrade

# Run migrations
cd src/templates/bot_template
alembic upgrade head
cd /opt/teletask

# Restart bot
pm2 restart teletask-bot
```

### 7.3 Update System Packages

```bash
# Update package manager
sudo apt update
sudo apt upgrade -y

# Update PostgreSQL (if needed)
sudo apt install postgresql-15 -y

# Update Python packages
source venv/bin/activate
pip install --upgrade -r src/templates/bot_template/requirements.txt
```

---

## 8. Monitoring & Maintenance

### 8.1 System Monitoring

**View CPU and Memory Usage:**

```bash
# Real-time monitoring
top

# PM2 monitoring
pm2 monit

# Disk usage
df -h
du -h /opt/teletask
```

**PostgreSQL Connection Monitoring:**

```bash
psql -U teletask_bot -d teletask
SELECT count(*) FROM pg_stat_activity;
\q
```

### 8.2 Log Management

**View logs:**

```bash
# Recent logs
pm2 logs teletask-bot

# Tail logs (last 50 lines)
pm2 logs teletask-bot --lines 50

# Export logs
pm2 logs teletask-bot > teletask_logs.txt
```

**Log rotation:**

Create `/etc/logrotate.d/teletask`:

```
/var/log/teletask/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nobody adm
}
```

### 8.3 Scheduled Maintenance

**Weekly maintenance:**

```bash
# Check disk space
df -h | grep -E "/$|/var"

# Check database bloat
psql -U teletask_bot -d teletask -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# Clean old logs
find /var/log/teletask -name "*.log.*" -mtime +30 -delete
```

---

## 9. Troubleshooting

### 9.1 Common Issues

**Bot won't start:**

```bash
# Check logs
botpanel logs tail 100

# Common causes:
# 1. Invalid TELEGRAM_BOT_TOKEN
# 2. Database connection failed
# 3. Port 8080 already in use
# 4. Python version < 3.11

# Solution: verify .env file
cat /opt/teletask/.env

# Check port usage
sudo netstat -tlnp | grep 8080

# Kill conflicting process
sudo kill -9 <PID>
```

**Database connection error:**

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -U teletask_bot -d teletask -h localhost

# Check credentials in .env
grep DATABASE_URL /opt/teletask/.env

# Verify database exists
sudo -u postgres psql -l | grep teletask
```

**Out of memory:**

```bash
# Check memory usage
free -h

# Check process memory
ps aux | grep python | grep teletask

# Increase PM2 memory limit in ecosystem.config.js:
# max_memory_restart: '1G'

# Restart
pm2 restart teletask-bot
```

**Nginx connection refused:**

```bash
# Check Nginx status
sudo systemctl status nginx

# Test Nginx config
sudo nginx -t

# Check if bot is running
botpanel status

# Restart Nginx
sudo systemctl restart nginx
```

### 9.2 Debug Mode

Enable debug logging:

```bash
# Edit .env
LOG_LEVEL=DEBUG

# Restart bot
botpanel restart

# Tail logs
botpanel logs tail -f
```

### 9.3 Performance Tuning

**Slow queries:**

```bash
# Enable query logging
psql -U teletask_bot -d teletask
ALTER DATABASE teletask SET log_statement = 'all';
ALTER DATABASE teletask SET log_duration = on;
\q

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check slow query log
sudo tail -f /var/log/postgresql/postgresql.log
```

**High memory usage:**

```bash
# Check PM2 process memory
pm2 info teletask-bot

# Options to reduce memory:
# 1. Reduce connection pool size (database/connection.py)
# 2. Disable caching if unnecessary
# 3. Increase swap (not recommended)
```

---

## 10. Security Hardening

### 10.1 Firewall Configuration

```bash
# Install UFW (if not installed)
sudo apt install ufw

# Enable firewall
sudo ufw enable

# Allow SSH (critical!)
sudo ufw allow 22/tcp

# Allow Nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL (local only)
sudo ufw allow from 127.0.0.1 to any port 5432

# Check rules
sudo ufw status numbered
```

### 10.2 SSL/TLS Certificate

Using Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --nginx -d your-domain.com

# Update Nginx config with SSL
sudo certbot --nginx -d your-domain.com

# Auto-renew certificates
sudo systemctl enable certbot.timer
```

### 10.3 User Permissions

```bash
# Create dedicated user for bot (if needed)
sudo useradd -m -s /bin/bash teletask

# Give permissions to application directory
sudo chown -R teletask:teletask /opt/teletask

# Restrict .env file permissions
sudo chmod 600 /opt/teletask/.env

# Run bot as dedicated user in PM2
# Update ecosystem.config.js:
# user: 'teletask'
```

### 10.4 Regular Security Updates

```bash
# Enable automatic security updates (Ubuntu)
sudo apt install unattended-upgrades

# Configure auto-updates
sudo dpkg-reconfigure -plow unattended-upgrades

# Check pending updates
apt list --upgradable
```

---

## 11. Uninstallation

### 11.1 Safe Uninstall (Keep Data)

```bash
# Stop bot
pm2 stop teletask-bot
pm2 delete teletask-bot

# Backup database before removal
pg_dump -U teletask_bot -d teletask > final_backup.sql.gz

# Remove application
sudo rm -rf /opt/teletask

# Remove Nginx config (if used)
sudo rm /etc/nginx/sites-available/teletask.conf
sudo rm /etc/nginx/sites-enabled/teletask.conf
sudo systemctl restart nginx

# Keep PostgreSQL database for future restore
# (optional) sudo -u postgres dropdb teletask
# (optional) sudo -u postgres dropuser teletask_bot
```

### 11.2 Complete Uninstall

```bash
# Run uninstall script
/opt/teletask/uninstall.sh

# Or manually remove everything:
sudo rm -rf /opt/teletask
sudo rm -rf /var/log/teletask
sudo -u postgres dropdb teletask
sudo -u postgres dropuser teletask_bot
```

---

## 12. Support & Resources

**Documentation:**
- GitHub: https://github.com/haduyson/teletask
- Issues: https://github.com/haduyson/teletask/issues
- Discussions: https://github.com/haduyson/teletask/discussions

**BotPanel Commands:**

```bash
botpanel help              # Show all commands
botpanel status            # Show bot status
botpanel logs tail         # Show recent logs
botpanel logs tail -f      # Follow logs
botpanel restart           # Restart bot
botpanel stop              # Stop bot
botpanel start             # Start bot
botpanel backup-db         # Backup database
botpanel restore-db        # Restore database
botpanel update            # Update bot
botpanel config show       # Show configuration
botpanel config edit       # Edit configuration
botpanel version           # Show version
```

---

**End of Document**
