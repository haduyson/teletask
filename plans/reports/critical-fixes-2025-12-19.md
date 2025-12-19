# Critical Issues Fixed - 2025-12-19

## Summary

Fixed all 8 critical security and data integrity issues identified in the codebase review.

## Changes Made

### 1. Transaction Context Manager (connection.py)
**Issue**: Connection pool leak on exceptions
**Fix**: Added proper async context manager with auto commit/rollback

```python
@asynccontextmanager
async def transaction(self) -> AsyncGenerator[Connection, None]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
```

### 2. OAuth Token Encryption (new: utils/security.py)
**Issue**: Plaintext OAuth tokens in database
**Fix**: Created token encryption module using Fernet (AES-256)

- Added `ENCRYPTION_KEY` to settings.py
- Created `utils/security.py` with `encrypt_token()` and `decrypt_token()`
- Updated `calendar_service.py` to encrypt/decrypt tokens
- Backward compatible: handles both encrypted and plaintext tokens

### 3. Input Validation (new: services/task_validation.py)
**Issue**: No validation on task mutations
**Fix**: Created validation module with:

- `validate_content()` - 2-500 chars
- `validate_priority()` - low/normal/high/urgent
- `validate_status()` - pending/in_progress/completed
- `validate_progress()` - 0-100
- `ValidationError` exception class
- Applied to `create_task()`, `update_task_status()`

### 4. Permission Checks (new: services/task_permissions.py)
**Issue**: No permission checks before mutations
**Fix**: Created permission module with:

- `can_view_task()`, `can_modify_task()`, `can_delete_task()`
- `check_modify_permission()`, `check_delete_permission()`
- `PermissionError` exception class
- Applied to `update_task_status()`, `soft_delete_task()`

### 5. Foreign Key CASCADE (models.py)
**Issue**: 10 FKs missing ondelete behavior
**Fix**: Added CASCADE/SET NULL to all foreign keys:

| Model | Column | Behavior |
|-------|--------|----------|
| Task | creator_id | SET NULL |
| Task | assignee_id | SET NULL |
| Task | group_id | CASCADE |
| Task | parent_recurring_id | SET NULL |
| Task | deleted_by | SET NULL |
| Reminder | user_id | CASCADE |
| TaskHistory | user_id | SET NULL |
| UserStatistics | user_id | CASCADE |
| UserStatistics | group_id | CASCADE |
| DeletedTaskUndo | deleted_by | SET NULL |

### 6. Dependencies (requirements.txt)
Added `cryptography>=42.0.0` for token encryption

## Files Modified

| File | Changes |
|------|---------|
| database/connection.py | Fixed transaction() context manager |
| database/models.py | Added CASCADE/SET NULL to 10 FKs |
| config/settings.py | Added encryption_key setting |
| services/calendar_service.py | Added token encryption/decryption |
| services/task_service.py | Added validation + permission imports & checks |
| requirements.txt | Added cryptography package |

## New Files Created

| File | Purpose |
|------|---------|
| utils/security.py | Token encryption/decryption utilities |
| services/task_validation.py | Input validation functions |
| services/task_permissions.py | Permission check functions |

## Next Steps

1. **Generate encryption key**:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. **Add to .env**:
   ```
   ENCRYPTION_KEY=your_generated_key_here
   ```

3. **Install new dependency**:
   ```bash
   pip install cryptography>=42.0.0
   ```

4. **Run Alembic migration** (recommended for FK changes):
   ```bash
   alembic revision --autogenerate -m "add_fk_cascade_behavior"
   alembic upgrade head
   ```

5. **Migrate existing OAuth tokens** (if any exist):
   - Existing plaintext tokens will continue to work
   - New tokens will be encrypted automatically
   - Optional: Create migration script to encrypt existing tokens

## Unresolved Questions

1. Should we create a migration to encrypt existing OAuth tokens?
2. Database backup before running FK cascade migration?
3. Need to update error handlers in callbacks.py to catch new ValidationError/PermissionError?
