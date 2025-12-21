# TeleTask Bot - Troubleshooting Guide

**Last Updated:** 2025-12-20
**Version:** 1.0

---

## Quick Diagnostics

### Check Bot Health
```bash
# Health check endpoint
curl https://your-domain.com/health

# Expected response:
{
  "status": "healthy",
  "bot_name": "TeleTask",
  "uptime_seconds": 475800,
  "memory_mb": 256.5,
  "cpu_percent": 2.3,
  "database": "connected",
  "tasks_today": 42,
  "completed_today": 15
}
```

### View PM2 Logs
```bash
pm2 logs hasontechtask        # Live logs
pm2 logs hasontechtask --lines 50  # Last 50 lines
pm2 describe hasontechtask    # Process info
```

---

## Common Issues & Solutions

### 1. Bot Not Responding to Commands

**Symptoms:**
- Commands like `/taoviec`, `/xemviec` timeout
- Bot doesn't acknowledge messages
- Handler doesn't trigger

**Diagnosis:**
```bash
# Check if bot process is running
pm2 status

# If stopped, restart
pm2 restart hasontechtask

# Check for Python errors
pm2 logs hasontechtask | grep -i error
```

**Root Causes & Fixes:**

**A. Database Connection Lost**
```bash
# Check PostgreSQL status
sudo service postgresql status

# Test connection
psql $DATABASE_URL

# If failed, check DATABASE_URL in .env
# Format: postgresql+asyncpg://user:password@host:port/database
```

**B. Telegram Bot Token Invalid**
```bash
# Verify token in .env
grep BOT_TOKEN .env

# Test with Telegram API
curl "https://api.telegram.org/bot[YOUR_TOKEN]/getMe"

# Should return:
# {"ok":true,"result":{"id":123456789,"is_bot":true,"first_name":"TeleTask",...}}
```

**C. Memory Exhaustion**
```bash
# Check memory
pm2 monit

# If RSS > 500MB, restart
pm2 restart hasontechtask

# Check for memory leaks in logs
pm2 logs hasontechtask | grep -i "memory"
```

**D. Event Loop Blocked**
```bash
# Check for sync operations in handlers
grep -r "time.sleep\|\.get()\|\.all()" handlers/

# All I/O must be async:
# ❌ WRONG: result = db.query(...).all()
# ✅ CORRECT: result = await session.execute(...); result.scalars().all()
```

---

### 2. Task Creation Fails / Wizard Hangs

**Symptoms:**
- `/taoviec` command starts but no response
- Wizard doesn't advance to next step
- Task created but not visible

**Diagnosis:**

**A. ConversationHandler State Issue**
```bash
# Check logs for state transition errors
pm2 logs hasontechtask | grep -i "state\|conversation"
```

**B. User Not Registered**
```python
# Verify user exists in database
psql $DATABASE_URL
SELECT * FROM users WHERE telegram_id = YOUR_ID;
```

If empty, user registration failed. Try `/start` command first.

**C. Database Transaction Failure**
```bash
# Check logs for transaction/commit errors
pm2 logs hasontechtask | grep -i "transaction\|commit\|rollback"

# If frequent, may indicate connection pool exhaustion
# Restart bot and reduce connection intensity
```

**Solutions:**

1. **Force restart conversation:**
   - Send `/cancel` to exit wizard
   - Send `/start` to re-register
   - Retry `/taoviec`

2. **Check database permissions:**
   ```bash
   psql $DATABASE_URL
   -- Check if user can insert
   INSERT INTO tasks (content) VALUES ('test');
   ROLLBACK;
   ```

3. **Verify async/await in handler:**
   - All database calls must use `await`
   - All message sends must use `await`
   - No blocking I/O in handlers

---

### 3. Reminders Not Sending

**Symptoms:**
- Set reminder with `/nhacviec` but don't receive notification
- Scheduler appears to be running
- No error messages

**Diagnosis:**

**A. User Notification Preference Disabled**
```bash
# Check user's notification settings
psql $DATABASE_URL
SELECT telegram_id, notify_all, notify_reminder, remind_1h
FROM users WHERE telegram_id = YOUR_ID;
```

Expected: All `true` for reminders to work.

**Fix:** User sends `/caidat` and enables notifications

**B. Reminder Query Issue**
```bash
# Check pending reminders
psql $DATABASE_URL
SELECT * FROM reminders
WHERE user_id = YOUR_ID
  AND is_sent = false
  AND remind_at <= NOW();
```

If empty, no pending reminders. Check deadline settings.

**C. Scheduler Not Running**
```bash
# Check APScheduler jobs in logs
pm2 logs hasontechtask | grep -i "apscheduler\|scheduler"

# Expected every 1 minute:
# "Processing reminders..." or similar
```

If not present, scheduler failed to initialize. Check `bot.py` startup logs:
```bash
pm2 logs hasontechtask | head -100 | grep -i "scheduler"
```

**D. Telegram API Failure**
```bash
# Check if send_message calls are failing
pm2 logs hasontechtask | grep -i "send_message\|failed.*notification"

# Common causes:
# - User blocked bot (can't fix)
# - User deleted their account (clean up DB)
# - Rate limiting (wait & retry)
```

**Solutions:**

1. **Test reminder manually:**
   ```python
   # From Python shell with bot context
   from services.notification import send_reminder_notification
   await send_reminder_notification(bot, user_id, task, "before_deadline")
   ```

2. **Force reminder send:**
   ```bash
   # Manually update reminder to past time
   psql $DATABASE_URL
   UPDATE reminders
   SET remind_at = NOW() - INTERVAL '5 minutes'
   WHERE id = REMINDER_ID;

   # Wait for next scheduler run (max 1 minute)
   ```

3. **Check timezone issue:**
   ```bash
   # Verify user's timezone
   psql $DATABASE_URL
   SELECT timezone FROM users WHERE telegram_id = YOUR_ID;

   # Deadline calculations use this timezone
   # If wrong, reminders won't trigger at expected time
   ```

---

### 4. Group Tasks Not Working

**Symptoms:**
- `/giaoviec` doesn't parse multiple assignees
- Group task created but members don't get notified
- Task appears as individual instead of group

**Diagnosis:**

**A. Group Not Registered**
```bash
# Check if group exists in database
psql $DATABASE_URL
SELECT * FROM groups WHERE telegram_id = CHAT_ID;
```

If empty, group registration failed.

**Solution:**
```python
# Run task creation again
# Handler calls get_or_create_group() automatically
await get_or_create_group(db, chat.id, chat.title)
```

**B. Mention Parsing Failure**
```bash
# Test mention extraction
# Send: /giaoviec @user1 @user2 task content
# Check logs for parsing errors

pm2 logs hasontechtask | grep -i "mention\|parse.*user"
```

**C. Permission Check Failure**
```bash
# Verify bot is group admin (for some operations)
psql $DATABASE_URL
SELECT * FROM group_members
WHERE group_id = GROUP_ID AND user_id = BOT_ID;
```

**D. Notification Preference**
```bash
# Check each assignee's preferences
psql $DATABASE_URL
SELECT telegram_id, notify_task_assigned
FROM users
WHERE telegram_id IN (ASSIGNEE1, ASSIGNEE2);
```

If `false`, members won't be notified of new tasks.

**Solutions:**

1. **Ensure group membership:**
   ```bash
   # Admin must have accepted bot invitation
   # Then members can receive task assignments
   ```

2. **Test mention format:**
   - Use `/giaoviec @username task` (direct mention)
   - Or reply with `/giaoviec task` (reply to user)
   - Or click user name in chat (text mention)

3. **Check group_members table:**
   ```bash
   psql $DATABASE_URL
   SELECT u.username, gm.role
   FROM group_members gm
   JOIN users u ON gm.user_id = u.id
   WHERE gm.group_id = GROUP_ID;
   ```

---

### 5. Reports Not Generating / Downloads Failing

**Symptoms:**
- `/export csv` command hangs or errors
- Report download links expire immediately
- Files not created on disk

**Diagnosis:**

**A. Export Directory Permissions**
```bash
# Check exports directory
ls -la /path/to/hasontechtask/exports/

# Should have rwx permissions
# If missing, create it:
mkdir -p /path/to/hasontechtask/exports
chmod 755 /path/to/hasontechtask/exports
```

**B. Disk Space**
```bash
# Check free space
df -h /

# If < 1GB, clean old reports:
find /path/to/hasontechtask/exports -mtime +3 -delete
```

**C. Report Generation Error**
```bash
# Check logs for specific format error
pm2 logs hasontechtask | grep -i "csv\|xlsx\|pdf\|report"

# Common issues:
# - matplotlib issue (PDF): missing font
# - openpyxl issue (XLSX): corrupted file
# - UTF-8 BOM issue (CSV): encoding error
```

**D. Download Link Expiration**
```bash
# Check database for expired reports
psql $DATABASE_URL
SELECT * FROM export_reports
WHERE created_at < NOW() - INTERVAL '72 hours';

# Cleanup task runs via scheduler:
# ReportScheduler.cleanup_expired_reports() (daily)
```

**Solutions:**

1. **Test report generation:**
   ```python
   from services.report_service import ReportService
   tasks = await TaskService.get_user_tasks(user_id)
   stats = await StatisticsService.calculate_user_stats(...)
   csv_bytes = await ReportService.generate_csv_report(tasks, stats)
   ```

2. **Fix encoding issues:**
   ```bash
   # For CSV with Vietnamese characters:
   # Must use UTF-8 with BOM
   # ReportService handles this automatically
   ```

3. **Manual cleanup:**
   ```bash
   psql $DATABASE_URL
   DELETE FROM export_reports
   WHERE created_at < NOW() - INTERVAL '72 hours';
   ```

---

### 6. Google Calendar Sync Not Working

**Symptoms:**
- `/lichgoogle` command doesn't show auth link
- OAuth callback fails
- Tasks not appearing in Google Calendar

**Diagnosis:**

**A. OAuth Callback Server Not Running**
```bash
# Check if oauth_callback.py is running
pm2 logs hasontechtask | grep -i "oauth"

# Should see: "OAuth server listening on port 8888" or similar
```

**B. Google API Credentials Invalid**
```bash
# Check if GOOGLE_CALENDAR_ENABLED is set
grep GOOGLE_CALENDAR_ENABLED .env

# If true, verify credentials exist:
ls config/google-credentials.json
```

**C. User Already Has Token**
```bash
# Check if user already connected
psql $DATABASE_URL
SELECT google_tokens, google_sync_enabled
FROM users WHERE telegram_id = YOUR_ID;
```

If tokens exist, user already authorized. Try disabling & reconnecting:
```python
# Set tokens to null
UPDATE users
SET google_tokens = null, google_sync_enabled = false
WHERE telegram_id = YOUR_ID;

# Then try /lichgoogle again
```

**D. Token Encryption Issue**
```bash
# Check if ENCRYPTION_KEY is set
grep ENCRYPTION_KEY .env

# Tokens must be encrypted/decrypted properly
# Missing key causes failures
```

**Solutions:**

1. **Enable Google Calendar:**
   ```bash
   # In .env:
   GOOGLE_CALENDAR_ENABLED=true
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REDIRECT_URI=https://your-domain.com/oauth/callback
   ENCRYPTION_KEY=your_secret_key_32_chars_minimum
   ```

2. **Restart bot after env changes:**
   ```bash
   pm2 restart hasontechtask
   ```

3. **Test OAuth callback:**
   ```bash
   # Should be accessible
   curl https://your-domain.com/oauth/callback?code=test
   ```

---

### 7. High Memory Usage / Bot Crashes

**Symptoms:**
- Bot uses > 500MB memory
- PM2 shows `exited with status 1`
- Out of memory errors in logs

**Diagnosis:**

**A. Connection Pool Leak**
```bash
# Check database connections
psql $DATABASE_URL
SELECT count(*) FROM pg_stat_activity;

# Should be < 8 (default max is 10)
# If maxed out, pool is leaking connections
```

**B. Task History Bloat**
```bash
# Check task_history table size
psql $DATABASE_URL
SELECT pg_size_pretty(pg_total_relation_size('task_history'));

# If > 100MB, consider archiving old records
DELETE FROM task_history
WHERE created_at < NOW() - INTERVAL '90 days';
```

**C. Soft Delete Undo Buffer**
```bash
# Check deleted_tasks_undo size
psql $DATABASE_URL
SELECT count(*) FROM deleted_tasks_undo;

# Should be small (< 100 records)
# Cleanup runs every 5 minutes
```

**D. Event Loop Blocked**
```bash
# Check for sync operations
grep -r "\.all()\|\.first()\|time.sleep" handlers/ services/

# All must be async:
# ❌ tasks = session.execute(...).all()
# ✅ result = await session.execute(...); tasks = result.scalars().all()
```

**Solutions:**

1. **Restart bot:**
   ```bash
   pm2 restart hasontechtask
   ```

2. **Increase memory limit (in ecosystem.config.js):**
   ```javascript
   env: {
       NODE_OPTIONS: "--max-old-space-size=512"  // 512MB
   }
   ```

3. **Archive old task_history:**
   ```bash
   psql $DATABASE_URL
   -- Create archive table
   CREATE TABLE task_history_archive AS
   SELECT * FROM task_history
   WHERE created_at < NOW() - INTERVAL '90 days';

   -- Delete from main table
   DELETE FROM task_history
   WHERE created_at < NOW() - INTERVAL '90 days';

   -- Vacuum to reclaim space
   VACUUM task_history;
   ```

4. **Enable memory monitoring:**
   ```bash
   pm2 monitor  # Opens monitoring dashboard
   ```

---

### 8. Database Migration Failures

**Symptoms:**
- Alembic migration errors on startup
- `ERROR: Could not find a migration context`
- New schema fields missing

**Diagnosis:**

```bash
# Check migration status
alembic current       # Current schema version
alembic heads         # Latest available version
alembic branches      # Any branched migrations

# If different, run pending migrations
alembic upgrade head
```

**Solutions:**

1. **Run pending migrations:**
   ```bash
   cd /path/to/hasontechtask
   alembic upgrade head
   pm2 restart hasontechtask
   ```

2. **Check migration file syntax:**
   ```bash
   # Look for Python syntax errors
   python3 -m py_compile database/migrations/versions/[MIGRATION].py
   ```

3. **Rollback if necessary:**
   ```bash
   # Revert to previous version
   alembic downgrade -1

   # Fix migration file
   # Then re-run upgrade
   alembic upgrade head
   ```

---

### 9. Slow Queries / Performance Issues

**Symptoms:**
- Commands take > 5 seconds to respond
- Database CPU high
- "slow query" warnings in logs

**Diagnosis:**

```bash
# Check slow query log
psql $DATABASE_URL
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Common Culprits:**

**A. Missing Indexes**
```bash
# Verify indexes exist
psql $DATABASE_URL
SELECT indexname FROM pg_indexes
WHERE tablename = 'tasks';

# Should include:
# - idx_tasks_assignee_status
# - idx_tasks_deadline
# - idx_tasks_creator
# - idx_tasks_group
```

**B. N+1 Queries**
```bash
# Check logs for repeated similar queries
pm2 logs hasontechtask | grep "SELECT.*FROM tasks" | sort | uniq -c

# If same query repeated many times, likely N+1 issue
# Use eager loading or batch queries
```

**C. Large Result Sets**
```bash
# Check if queries return too many rows
# Add LIMIT to list queries
# Use pagination (OFFSET/LIMIT)
```

**Solutions:**

1. **Enable query logging:**
   ```bash
   # In .env:
   LOG_LEVEL=DEBUG  # Logs all SQL queries

   pm2 restart hasontechtask
   ```

2. **Analyze slow query:**
   ```bash
   psql $DATABASE_URL
   EXPLAIN ANALYZE SELECT * FROM tasks WHERE assignee_id = 123;

   # Look for sequential scans on large tables
   # Add index if needed
   ```

3. **Optimize pagination:**
   ```python
   # WRONG: Get all then slice
   tasks = await get_all_tasks()
   tasks = tasks[0:10]

   # CORRECT: Paginate in database
   tasks = await get_user_tasks(user_id, limit=10, offset=0)
   ```

---

## System-Level Troubleshooting

### PostgreSQL Issues

**Service not starting:**
```bash
sudo service postgresql start
sudo service postgresql status
```

**Connection refused:**
```bash
# Check if PostgreSQL is listening
netstat -an | grep 5432

# Check connection string in .env
# Format: postgresql+asyncpg://user:password@host:port/db
```

**Disk space full:**
```bash
df -h /var/lib/postgresql
# Vacuum to reclaim space
psql $DATABASE_URL
VACUUM FULL;
```

### Telegram API Issues

**Bot token invalid:**
```bash
# Re-generate token from @BotFather
# Update .env BOT_TOKEN
pm2 restart hasontechtask
```

**Rate limited by Telegram:**
```bash
# Wait and retry (Telegram limits: 30 msg/sec)
# Check logs for rate limit errors
pm2 logs hasontechtask | grep -i "rate\|limit"
```

**Webhook not responding:**
```bash
# If using webhook mode (not polling):
curl https://your-domain.com/telegram  # Should return 200

# Check nginx config
sudo nginx -t
```

### SSL/HTTPS Issues

**Certificate expired:**
```bash
sudo certbot renew --dry-run
sudo certbot renew  # Actually renew
sudo systemctl restart nginx
```

**Certificate missing:**
```bash
sudo certbot certonly --standalone -d your-domain.com
```

---

## Health Check Interpretation

### Response Status

```json
{
  "status": "healthy"      // green - all systems OK
  "status": "degraded"     // yellow - some components offline
  "status": "down"         // red - critical failure
}
```

### Key Metrics

| Metric | Healthy | Degraded | Down |
|--------|---------|----------|------|
| Database | connected | - | disconnected |
| Uptime | > 1 hour | < 1 hour | N/A |
| Memory | < 300MB | 300-500MB | > 500MB |
| CPU | < 10% | 10-30% | > 30% |
| Tasks Today | any | any | N/A |

---

## Getting Help

**For reported issues:**
1. Gather logs: `pm2 logs hasontechtask > debug.log`
2. Run health check: `curl https://domain.com/health > health.json`
3. Check database: `psql $DATABASE_URL -c "SELECT VERSION();"`
4. Report with logs + health check output

**Common debug sequence:**
```bash
# 1. Check process
pm2 status

# 2. Check logs
pm2 logs hasontechtask --lines 100

# 3. Check database
psql $DATABASE_URL -c "SELECT 1;"

# 4. Check health endpoint
curl https://domain.com/health

# 5. Restart if needed
pm2 restart hasontechtask
```

---

**Last Updated:** 2025-12-20
**Version:** 1.0
**Status:** ACTIVE
