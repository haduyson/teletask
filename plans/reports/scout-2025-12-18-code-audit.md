# Codebase Scout Report: Utils, Config & Initialization Audit
**Date**: 2025-12-18  
**Scope**: `/utils/`, `/config/`, `bot.py` - Code quality, validation, configuration, initialization order

---

## Summary
Audited utils, configuration, and initialization layers. Found **11 issues** across 4 severity levels:
- **Critical**: 1
- **High**: 3  
- **Medium**: 4
- **Low**: 3

---

## Critical Issues

### 1. Hardcoded Timezone Disregards Config
**File**: `/home/botpanel/bots/hasontechtask/utils/formatters.py:32`  
**Severity**: CRITICAL  
**Issue**: `TZ = pytz.timezone("Asia/Ho_Chi_Minh")` is hardcoded - ignores config/settings TZ.
```python
# Line 32
TZ = pytz.timezone("Asia/Ho_Chi_Minh")
```
**Impact**: User timezone settings ignored; formatters always use Vietnam timezone even if config specifies different.  
**Affected Functions**:
- `format_datetime()` (lines 90-120)
- `get_status_icon()` (lines 57-87)
- All report formatting functions

**Fix**: Import from config and allow override:
```python
from config.settings import get_settings
settings = get_settings()
TZ = pytz.timezone(settings.timezone)
```

---

## High Priority Issues

### 2. Duplicate HTML Sanitization Functions
**Files**: 
- `/home/botpanel/bots/hasontechtask/utils/formatters.py:191` - `escape_html()`
- `/home/botpanel/bots/hasontechtask/utils/validators.py:199` - `sanitize_html()`
**Severity**: HIGH  
**Issue**: Two functions do same thing but with different implementation scope.

```python
# formatters.py line 191
def escape_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(text, quote=True)

# validators.py line 199
def sanitize_html(text: str) -> str:
    replacements = [("&", "&amp;"), ("<", "&lt;"), (">", "&gt;")]
    for old, new in replacements:
        text = text.replace(old, new)
    return text
```
**Impact**: 
- `escape_html()` is more complete (uses standard library)
- `sanitize_html()` incomplete (misses quotes, single quotes)
- Code duplication causes maintenance issues
- Inconsistent HTML escaping across codebase

**Fix**: Use only `escape_html()` from formatters; remove duplicate from validators.

### 3. Missing Input Validation Silently Defaults
**File**: `/home/botpanel/bots/hasontechtask/utils/validators.py:81, 115`  
**Severity**: HIGH  
**Issue**: Invalid inputs silently default instead of raising errors.

```python
# Line 50-81: validate_priority()
def validate_priority(priority: str) -> Tuple[bool, str]:
    priority = priority.lower().strip()
    if priority in priority_map:
        return True, priority_map[priority]
    return False, "normal"  # <-- SILENT DEFAULT!

# Line 84-115: validate_status()
def validate_status(status: str) -> Tuple[bool, str]:
    status = status.lower().strip()
    if status in status_map:
        return True, status_map[status]
    return False, "pending"  # <-- SILENT DEFAULT!
```
**Impact**:
- Callers can't distinguish invalid vs. default
- Users may not realize wrong priority/status was auto-corrected
- Tuple return `(False, default_value)` is confusing (False but returns value)

**Fix**: Raise ValueError or return Optional/Union type:
```python
def validate_priority(priority: str) -> str:
    if not priority or priority not in priority_map:
        raise ValueError(f"Invalid priority: {priority}")
    return priority_map[priority]
```

### 4. Validation Returns Silently Accept Invalid Progress
**File**: `/home/botpanel/bots/hasontechtask/utils/validators.py:118-137`  
**Severity**: HIGH  
**Issue**: `validate_progress()` accepts string conversion silently; no empty/None check.

```python
def validate_progress(progress: str) -> Tuple[bool, int]:
    progress = progress.replace("%", "").strip()
    try:
        value = int(progress)
        if 0 <= value <= 100:
            return True, value
        return False, 0
    except ValueError:
        return False, 0
```
**Issues**:
- No check for `None` input (would crash)
- Empty string returns `(False, 0)` - ambiguous if 0% is valid
- Returns `0` on both invalid format AND out-of-range

**Fix**: 
```python
def validate_progress(progress: Optional[str]) -> int:
    if not progress:
        raise ValueError("Progress cannot be empty")
    progress = progress.replace("%", "").strip()
    try:
        value = int(progress)
        if 0 <= value <= 100:
            return value
        raise ValueError(f"Progress must be 0-100, got {value}")
    except ValueError:
        raise ValueError(f"Invalid progress format: {progress}")
```

---

## Medium Priority Issues

### 5. Hardcoded Values in bot.py Should Be Config
**File**: `/home/botpanel/bots/hasontechtask/bot.py`  
**Severity**: MEDIUM  
**Issues**:

**5a. Default health port hardcoded**  
Line 186:
```python
health_port = int(os.getenv('HEALTH_PORT', 8080))
```
Should be in config/settings.py

**5b. Log level loaded twice**  
Lines 30-31:
```python
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# ... but also in config.settings
```
Should use `get_settings().log_level`

**5c. Timezone logged but from os.getenv**  
Line 130:
```python
logger.info(f"Timezone: {os.getenv('TZ', 'UTC')}")
```
Should use `get_settings().timezone`

**Impact**: Config scattered between bot.py and config/settings.py; no single source of truth.

### 6. Admin IDs Parsed in Multiple Places
**File**: `/home/botpanel/bots/hasontechtask/bot.py:170-176` vs `config/settings.py:73-79`  
**Severity**: MEDIUM  
**Issue**: Admin IDs parsed in bot.py when already done in config.

```python
# bot.py lines 170-176 (DUPLICATE)
admin_ids_str = os.getenv('ADMIN_IDS', '')
admin_ids = []
for x in admin_ids_str.split(','):
    x = x.strip()
    if x.lstrip('-').isdigit() and x:
        admin_ids.append(int(x))

# config/settings.py lines 73-79 (ORIGINAL)
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    self.admin_ids = [
        int(id_.strip())
        for id_ in admin_ids_str.split(",")
        if id_.strip().isdigit()
    ]
```
**Impact**:
- Logic duplication
- Parsing differences (bot.py handles negative IDs, settings doesn't)
- Hard to maintain

**Fix**: Use `get_settings().admin_ids` in bot.py.

### 7. Missing Validation in extract_mentions()
**File**: `/home/botpanel/bots/hasontechtask/utils/validators.py:10-23`  
**Severity**: MEDIUM  
**Issue**: No validation of extracted mentions format; accepts any alphanumeric.

```python
def extract_mentions(text: str) -> Tuple[List[str], str]:
    mentions = re.findall(r"@(\w+)", text)  # <-- No validation
    remaining = re.sub(r"@\w+", "", text).strip()
    remaining = re.sub(r"\s+", " ", remaining)
    return mentions, remaining
```
**Issues**:
- Regex `\w+` accepts numbers-only (invalid usernames like `@123`)
- No length limits on mentions
- No check for reserved usernames

**Impact**: Invalid Telegram usernames could be extracted, leading to failed API calls later.

### 8. Configuration Not Validated on Load
**File**: `/home/botpanel/bots/hasontechtask/config/settings.py:93-98`  
**Severity**: MEDIUM  
**Issue**: `get_settings()` caches but validation only called once; could fail silently on hot-reload.

```python
@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()  # <-- Only called on first access
    return settings
```
**Impact**:
- If env vars change mid-runtime, invalid state not detected
- `.validate()` only checks BOT_TOKEN and DATABASE_URL (missing others)

---

## Low Priority Issues

### 9. Keyboard Callbacks Use String-Only Parsing
**File**: `/home/botpanel/bots/hasontechtask/utils/keyboards.py:137, 149`  
**Severity**: LOW  
**Issue**: Callback data constructed with string concat; no delimiter escaping.

```python
# Line 137
callback_data=f"{prefix}:page:{page - 1}:{extra_data}"
```
**Impact**: If `extra_data` contains `:`, parsing breaks (though Telegram limits to 64 chars, so low risk).

### 10. Timezone Localization Could Fail on Naive Datetimes
**File**: `/home/botpanel/bots/hasontechtask/utils/formatters.py:68-73`  
**Severity**: LOW  
**Issue**: Assumes deadline is aware; could raise exception if naive + has different offset.

```python
if deadline.tzinfo is None:
    deadline = TZ.localize(deadline)  # <-- Could fail if already localized
else:
    deadline = deadline.astimezone(TZ)
```
**Risk**: Very low (only if datetime created incorrectly), but could crash formatter.

### 11. escape_markdown() Iterates Over String
**File**: `/home/botpanel/bots/hasontechtask/utils/formatters.py:253-269`  
**Severity**: LOW  
**Issue**: Inefficient; iterates 18+ times for each character.

```python
special_chars = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
result = text
for char in special_chars:
    result = result.replace(char, f'\\{char}')  # <-- O(n*m) complexity
```
**Better**: Use `str.translate()` or regex:
```python
import re
pattern = r'([\\\_\*\[\]\(\)~`>#\+\-=|{}\.!])'
return re.sub(pattern, r'\\\1', text)
```

---

## Initialization Order Issues

### Issue 1: Settings Loaded After Environment
**File**: `/home/botpanel/bots/hasontechtask/bot.py:26-27`
```python
load_dotenv()  # Line 27
# ... but config/settings also does this at line 13
```
- `load_dotenv()` called twice (once in bot.py, once in config/settings.py)
- Timing: settings.py loads AFTER bot.py imports config module

### Issue 2: Database Connection Happens Before Handlers Register
**File**: `/home/botpanel/bots/hasontechtask/bot.py:134-149`
```python
# Line 136: DB connects first
await init_database(database_url)
# Line 149: Handlers register after
register_handlers(application)
```
**Impact**: If handler imports fail, bot already connected to DB (resource leak on error).

### Issue 3: Missing Graceful Shutdown for Scheduler
**File**: `/home/botpanel/bots/hasontechtask/bot.py:252-257`
```python
stop_scheduler()  # <-- No await, but scheduler might be async
await application.updater.stop()
```
**Issue**: `stop_scheduler()` might not be awaited; could leave background tasks running.

---

## Summary Table

| ID | File | Line | Issue | Severity |
|----|------|------|-------|----------|
| 1 | formatters.py | 32 | Hardcoded TZ | **CRITICAL** |
| 2 | formatters.py, validators.py | 191, 199 | Duplicate escape_html | **HIGH** |
| 3 | validators.py | 81, 115 | Silent defaults | **HIGH** |
| 4 | validators.py | 118 | Progress validation weak | **HIGH** |
| 5 | bot.py | 186, 30, 130 | Config scattered | **MEDIUM** |
| 6 | bot.py, settings.py | 170, 73 | Admin IDs parsed twice | **MEDIUM** |
| 7 | validators.py | 10 | extract_mentions unvalidated | **MEDIUM** |
| 8 | settings.py | 93 | Config not re-validated | **MEDIUM** |
| 9 | keyboards.py | 137 | Callback data parsing fragile | **LOW** |
| 10 | formatters.py | 68 | Timezone localization risky | **LOW** |
| 11 | formatters.py | 263 | escape_markdown inefficient | **LOW** |

---

## Recommendations

### Immediate (Critical/High)
1. Move TZ to config; inject into formatters
2. Remove duplicate `sanitize_html()` from validators
3. Change priority/status validators to raise errors
4. Add None/empty checks to `validate_progress()`

### Short-term (Medium)
5. Consolidate config loading into config/settings.py
6. Remove duplicate admin_ids parsing from bot.py
7. Add username regex validation to `extract_mentions()`
8. Implement config re-validation or hot-reload checks

### Nice-to-have (Low)
9. Use structured callback data (JSON or fixed delimiters)
10. Add try-except for timezone edge cases
11. Optimize `escape_markdown()` with regex

---

## Files Analyzed
- `/home/botpanel/bots/hasontechtask/bot.py`
- `/home/botpanel/bots/hasontechtask/config/settings.py`
- `/home/botpanel/bots/hasontechtask/utils/formatters.py`
- `/home/botpanel/bots/hasontechtask/utils/validators.py`
- `/home/botpanel/bots/hasontechtask/utils/keyboards.py`
- `/home/botpanel/bots/hasontechtask/utils/messages.py`
- `/home/botpanel/bots/hasontechtask/utils/db_utils.py`
- `/home/botpanel/bots/hasontechtask/utils/__init__.py`

