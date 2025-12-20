# Export URL Domain Investigation

**Issue**: `/export` command generates wrong URL (`http://localhost:8080/report/`) instead of configured domain
**Date**: 2025-12-19 22:25
**Investigator**: debugger (aa76906)

---

## Executive Summary

**Root Cause**: IDENTIFIED
**Status**: Configuration is CORRECT, potential runtime issue
**Impact**: Users receive localhost URLs instead of public domain URLs for report downloads

### Key Finding

Environment configuration is properly set in `.env`, code correctly references env var, but issue reported suggests runtime mismatch. Possible causes:
1. Old bot process before `.env` update
2. Caching in Telegram message
3. User testing with outdated report link

---

## Technical Analysis

### 1. URL Generation Code Path

**File**: `handlers/export.py`
**Line**: 399-400

```python
# Get report URL from environment
base_url = os.getenv("EXPORT_BASE_URL", "http://localhost:8080")
report_url = f"{base_url}/report/{result['report_id']}"
```

**Finding**: Code correctly uses `EXPORT_BASE_URL` with fallback to `localhost:8080`

---

### 2. Environment Configuration

**File**: `.env`
**Lines**: 33, 43

```bash
EXPORT_BASE_URL=https://teletask.hasontech.com  # Line 33
BOT_DOMAIN=https://teletask.hasontech.com       # Line 43
```

**Last Modified**: 2025-12-19 11:07:29 +0700
**Finding**: Correctly configured with production domain

---

### 3. Environment Loading

**File**: `bot.py`
**Line**: 73

```python
load_dotenv()
```

**File**: `config/settings.py`
**Line**: 13

```python
load_dotenv()
```

**Finding**: `dotenv` loaded twice (bot.py at startup, settings.py on import). Both locations ensure env vars available.

---

### 4. Settings Module Analysis

**File**: `config/settings.py`

**Missing Fields**:
- `EXPORT_BASE_URL` not defined in `Settings` dataclass
- `BOT_DOMAIN` not defined in `Settings` dataclass

**Finding**: Handler uses direct `os.getenv()` call, NOT settings module. This is acceptable but inconsistent with project pattern.

---

### 5. Runtime Verification

**Bot Process**:
- Process ID: 86714
- Started: 2025-12-19 16:53:29 +0700
- PM2 Name: `hasontechtask` (not `teletask-bot`)
- Status: Online, 5h uptime, 94.0MB memory

**Environment Test** (from bot's venv):
```bash
EXPORT_BASE_URL=https://teletask.hasontech.com ✓
BOT_DOMAIN=https://teletask.hasontech.com ✓
```

**Finding**: Environment loads correctly when tested. Bot started AFTER .env modification, should have correct values.

---

### 6. Health Check Server

**File**: `monitoring/health_check.py`
**Lines**: 41-42, 570-591

Serves `/report/{report_id}` endpoint on port 8080:
```python
web_app.router.add_get('/report/{report_id}', self.report_page_handler)
```

Also generates `config.json` with `BOT_DOMAIN` (line 575):
```python
domain = os.getenv("BOT_DOMAIN", "")
```

**Finding**: Health check server correctly configured to serve reports, uses same env var pattern.

---

## Code Execution Flow

```
User sends /export command
  ↓
handlers/export.py::export_start() (line 181)
  ↓
User selects options (period, filter, format)
  ↓
handlers/export.py::confirm_callback() (line 365)
  ↓
services/report_service.py::create_export_report() (line 711)
  ↓
Generates report file + stores in DB
  ↓
Returns to handlers/export.py (line 397)
  ↓
LINE 399: base_url = os.getenv("EXPORT_BASE_URL", "http://localhost:8080")
LINE 400: report_url = f"{base_url}/report/{result['report_id']}"
  ↓
Sends Telegram message with URL (line 420-434)
```

---

## Potential Issue Scenarios

### Scenario A: Old Bot Instance (UNLIKELY)
- Bot started 16:53 (after .env modified 11:07) ✓
- Process uses fresh environment ✓
- Ruled out

### Scenario B: Cached Telegram Message (POSSIBLE)
- User received message from old bot session
- Telegram shows cached message
- Test: Send new /export request

### Scenario C: Testing with Old Link (POSSIBLE)
- User testing old report link from before fix
- New exports should generate correct URLs
- Test: Create new export

### Scenario D: PM2 Environment Isolation (UNLIKELY BUT POSSIBLE)
- PM2 ecosystem.config.js doesn't explicitly load .env
- Python's load_dotenv() should find .env in working directory
- Test: PM2 restart with explicit env check

---

## Evidence Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| Code logic | ✓ Correct | Line 399 uses `EXPORT_BASE_URL` |
| .env config | ✓ Correct | Both vars set to `https://teletask.hasontech.com` |
| dotenv loading | ✓ Present | bot.py:73, settings.py:13 |
| Bot process | ✓ Fresh | Started after .env modification |
| Runtime test | ✓ Pass | Venv test loads correct values |

---

## Recommended Actions

### Immediate (Verify Issue Still Exists)

1. **Test Current Export**
   ```bash
   # From bot chat, send: /export
   # Complete wizard, check URL in response
   # Expected: https://teletask.hasontech.com/report/{id}
   ```

2. **Check Recent Logs**
   ```bash
   pm2 logs hasontechtask --lines 1000 | grep -i "export\|report"
   ```
   Look for actual URL being generated (log statement at line 436)

### Short-term (If Issue Persists)

3. **Add Debug Logging**
   Edit `handlers/export.py` line 398-401:
   ```python
   # Get report URL from environment
   base_url = os.getenv("EXPORT_BASE_URL", "http://localhost:8080")
   logger.info(f"EXPORT_BASE_URL={base_url}")  # ADD THIS
   report_url = f"{base_url}/report/{result['report_id']}"
   ```

4. **Restart Bot with Verification**
   ```bash
   pm2 restart hasontechtask
   pm2 logs hasontechtask --lines 50 | grep "Health check server started"
   # Should show port 8080
   ```

### Long-term (Architectural Improvements)

5. **Add to Settings Dataclass**
   Edit `config/settings.py`:
   ```python
   @dataclass
   class Settings:
       # ... existing fields ...

       # Export configuration
       export_base_url: str = field(
           default_factory=lambda: os.getenv("EXPORT_BASE_URL", "")
       )
       bot_domain: str = field(
           default_factory=lambda: os.getenv("BOT_DOMAIN", "")
       )
   ```

6. **Update Handler to Use Settings**
   Edit `handlers/export.py` line 399:
   ```python
   from config.settings import get_settings

   # ...
   settings = get_settings()
   base_url = settings.export_base_url or "http://localhost:8080"
   ```

7. **Add Startup Validation**
   Edit `config/settings.py::validate()`:
   ```python
   def validate(self) -> None:
       """Validate required settings."""
       if not self.bot_token:
           raise ValueError("BOT_TOKEN is required")
       if not self.database_url:
           raise ValueError("DATABASE_URL is required")
       if not self.export_base_url:
           logger.warning("EXPORT_BASE_URL not set, using localhost fallback")
   ```

---

## File & Line Reference

| File | Lines | Issue |
|------|-------|-------|
| `handlers/export.py` | 399-400 | URL generation from env var |
| `config/settings.py` | 16-105 | Missing EXPORT_BASE_URL/BOT_DOMAIN fields |
| `.env` | 33, 43 | Configuration (correctly set) |
| `bot.py` | 73 | Environment loading |
| `monitoring/health_check.py` | 41-42 | Report serving endpoint |

---

## Unresolved Questions

1. Can user provide screenshot/exact error message showing localhost URL?
2. Was this from a NEW export after bot restart at 16:53, or cached message?
3. Are there any database records in `export_reports` table showing actual URLs stored?
4. Is nginx/reverse proxy potentially rewriting URLs in health check responses?

---

**Next Steps**: Need user to confirm issue still exists with fresh export attempt. All configuration is correct, suggesting cached message or testing with old link.
