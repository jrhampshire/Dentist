"""
AES-256-GCM field-level encryption service for NOM-024 compliance.

Encrypts sensitive patient fields:
- allergies, chronic_conditions, current_medications
- clinical_note.content
- patient_consent.content

Uses AES-256-GCM with random IV (nonce) and authentication tag.
Storage format: base64(nonce + ciphertext + tag)
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# AES-GCM nonce size (12 bytes = 96 bits, recommended for GCM)
_NONCE_SIZE = 12
# AES-GCM tag size (16 bytes = 128 bits)
_TAG_SIZE = 16

# Cached key instance
_key: Optional[AESGCM] = None


def _get_key() -> AESGCM:
    """Get or create the AESGCM key instance from settings."""
    global _key
    if _key is not None:
        return _key

    key_bytes = _load_key()
    _key = AESGCM(key_bytes)
    return _key


def _load_key() -> bytes:
    """
    Load the 256-bit encryption key from settings.

    The ENCRYPTION_KEY setting should be a base64-encoded 32-byte key.
    If empty, generates a random key (WARNING: data will be lost on restart).
    """
    raw = getattr(settings, "ENCRYPTION_KEY", "")

    if not raw:
        # In development, generate a random key and warn
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            "ENCRYPTION_KEY not set. Using random key — encrypted data will be "
            "unreadable after restart. Set ENCRYPTION_KEY in your .env file."
        )
        return AESGCM.generate_key(bit_length=256)

    try:
        key_bytes = base64.b64decode(raw)
    except Exception as e:
        raise ImproperlyConfigured(
            f"ENCRYPTION_KEY must be base64-encoded. Decoding failed: {e}"
        )

    if len(key_bytes) != 32:
        raise ImproperlyConfigured(
            f"ENCRYPTION_KEY must be 32 bytes (256 bits), got {len(key_bytes)} bytes. "
            f'Generate one with: python -c "import base64, os; '
            f'print(base64.b64encode(os.urandom(32)).decode())"'
        )

    return key_bytes


def encrypt(plaintext: str) -> str:
    """
    Encrypt a string using AES-256-GCM.

    Args:
        plaintext: The text to encrypt.

    Returns:
        Base64-encoded string of nonce + ciphertext + tag.
    """
    if not plaintext:
        return ""

    aesgcm = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Store: nonce + ciphertext_and_tag (ciphertext + 16-byte tag appended)
    blob = nonce + ciphertext_and_tag
    return base64.b64encode(blob).decode("ascii")


def decrypt(ciphertext_b64: str) -> str:
    """
    Decrypt a base64-encoded AES-256-GCM ciphertext.

    Args:
        ciphertext_b64: Base64-encoded string of nonce + ciphertext + tag.

    Returns:
        Decrypted plaintext string.

    Raises:
        cryptography.exceptions.InvalidTag: If decryption fails (wrong key or corrupted data).
    """
    if not ciphertext_b64:
        return ""

    aesgcm = _get_key()

    try:
        blob = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 ciphertext: {e}")

    if len(blob) < _NONCE_SIZE + _TAG_SIZE:
        raise ValueError(
            f"Ciphertext too short: expected at least {_NONCE_SIZE + _TAG_SIZE} bytes, "
            f"got {len(blob)}"
        )

    nonce = blob[:_NONCE_SIZE]
    ciphertext_and_tag = blob[_NONCE_SIZE:]

    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
    return plaintext_bytes.decode("utf-8")


def reset_key() -> None:
    """Reset the cached key (useful for testing)."""
    global _key
    _key = None
