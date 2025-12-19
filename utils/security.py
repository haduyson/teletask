"""
Security Utilities
Encryption/decryption for sensitive data like OAuth tokens
"""

import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TokenEncryption:
    """
    Encrypt/decrypt OAuth tokens using Fernet symmetric encryption.

    If ENCRYPTION_KEY is not set, tokens are stored in plaintext (backward compatible).
    This allows gradual migration without breaking existing functionality.
    """

    def __init__(self, key: Optional[str] = None):
        """
        Initialize encryption with optional key.

        Args:
            key: Fernet-compatible encryption key (base64 encoded 32 bytes)
        """
        self._fernet = None
        if key:
            try:
                from cryptography.fernet import Fernet
                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
                logger.info("Token encryption initialized")
            except ImportError:
                logger.warning("cryptography package not installed, tokens will be stored in plaintext")
            except Exception as e:
                logger.warning(f"Invalid encryption key, tokens will be stored in plaintext: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a token.

        Args:
            plaintext: Token to encrypt

        Returns:
            Encrypted token (base64) or original if encryption disabled
        """
        if not plaintext:
            return plaintext

        if not self._fernet:
            return plaintext

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            # Prefix with 'enc:' to identify encrypted values
            return f"enc:{encrypted.decode()}"
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a token.

        Args:
            ciphertext: Encrypted token or plaintext

        Returns:
            Decrypted token
        """
        if not ciphertext:
            return ciphertext

        # Check if value is encrypted (has 'enc:' prefix)
        if not ciphertext.startswith("enc:"):
            return ciphertext  # Return as-is (plaintext, backward compatible)

        if not self._fernet:
            logger.warning("Encrypted token found but encryption not enabled")
            return ciphertext

        try:
            encrypted_data = ciphertext[4:]  # Remove 'enc:' prefix
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            return ciphertext


# Singleton instance - lazy loaded
_token_encryption: Optional[TokenEncryption] = None


def get_token_encryption() -> TokenEncryption:
    """
    Get token encryption instance.

    Returns:
        TokenEncryption instance
    """
    global _token_encryption
    if _token_encryption is None:
        from config.settings import get_settings
        settings = get_settings()
        _token_encryption = TokenEncryption(settings.encryption_key)
    return _token_encryption


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using the global encryption instance.

    Args:
        token: Token to encrypt

    Returns:
        Encrypted token
    """
    return get_token_encryption().encrypt(token)


def decrypt_token(token: str) -> str:
    """
    Decrypt a token using the global encryption instance.

    Args:
        token: Encrypted token

    Returns:
        Decrypted token
    """
    return get_token_encryption().decrypt(token)


def is_encryption_enabled() -> bool:
    """Check if token encryption is enabled."""
    return get_token_encryption().is_enabled
