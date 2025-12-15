# Phase 01 Testing Guide

## Prerequisites

- Fresh Ubuntu 22.04 or 24.04 VM
- Root access (sudo)
- Minimum: 1GB RAM, 20GB disk
- Internet connection

## Copy Scripts to VM

### Option 1: SCP from local machine
```bash
scp -r /root/teletask/src/scripts/* root@YOUR_VM_IP:/tmp/
scp -r /root/teletask/src/templates root@YOUR_VM_IP:/tmp/
```

### Option 2: Clone from repo (if pushed)
```bash
git clone YOUR_REPO_URL /tmp/teletask
cd /tmp/teletask/src/scripts
```

### Option 3: Direct copy (on VM)
```bash
# Create directory
mkdir -p /tmp/teletask/scripts /tmp/teletask/templates

# Copy script contents manually or use wget if hosted
```

## Test 1: Install Script

```bash
# SSH into VM
ssh root@YOUR_VM_IP

# Navigate to scripts
cd /tmp/teletask/scripts

# Make executable
chmod +x *.sh

# Run install
./install.sh
```

### Expected Output
- System update messages
- Python 3.11 installation
- PostgreSQL 15 installation
- Node.js 20 installation
- PM2 installation
- Redis installation
- Nginx installation
- User 'botpanel' created
- Directory structure created
- Success message with next steps

### Verify Installation

```bash
# Check services
systemctl status postgresql
systemctl status redis-server
systemctl status nginx

# Check versions
python3.11 --version
node --version
pm2 --version

# Check user
id botpanel
ls -la /home/botpanel/

# Check CLI
botpanel

# Check PostgreSQL user
sudo -u postgres psql -c "\\du" | grep botpanel

# Check directory structure
tree /home/botpanel/ 2>/dev/null || find /home/botpanel -type d
```

## Test 2: Update Script

```bash
# Test interactive mode
./update.sh

# Test with flags
./update.sh --system  # Only system packages
./update.sh --template  # Only template
```

### Expected Output
- Menu displayed (interactive)
- System packages updated
- PM2 updated
- Health check results

## Test 3: Uninstall Script

```bash
# Run uninstall
./uninstall.sh
```

### Prompts
1. Type 'yes' to confirm
2. Choose 'y' or 'n' for backup
3. Choose 'y' or 'n' for removing system packages

### Expected Output
- Backup created (if selected)
- PM2 processes stopped
- Databases dropped
- User and home directory removed
- CLI symlink removed
- Summary message

### Verify Uninstall

```bash
# Check user removed
id botpanel  # Should fail

# Check home removed
ls /home/botpanel  # Should not exist

# Check CLI removed
which botpanel  # Should return nothing

# Check PostgreSQL user removed
sudo -u postgres psql -c "\\du" | grep botpanel  # Should return nothing
```

## Common Issues

### Issue: Python 3.11 not found
```bash
# Add deadsnakes PPA manually
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install python3.11 python3.11-venv python3.11-dev
```

### Issue: PM2 startup fails
```bash
# Manual PM2 startup
pm2 startup systemd -u botpanel --hp /home/botpanel
```

### Issue: PostgreSQL permission denied
```bash
# Reset PostgreSQL user password
sudo -u postgres psql -c "ALTER USER botpanel WITH PASSWORD 'newpassword';"
```

## Checklist

### Install
- [ ] No errors during execution
- [ ] All services running (postgresql, redis, nginx)
- [ ] User 'botpanel' created
- [ ] Directory structure exists
- [ ] `botpanel` command works
- [ ] PostgreSQL user has CREATEDB privilege

### Update
- [ ] Interactive menu works
- [ ] CLI flags work (--system, --template, --bots)
- [ ] No errors during update

### Uninstall
- [ ] Backup created successfully (if chosen)
- [ ] All components removed
- [ ] No errors during uninstall

## Next Steps After Testing

1. Report any issues found
2. Fix bugs if needed
3. Proceed to Phase 02 (BotPanel CLI)
