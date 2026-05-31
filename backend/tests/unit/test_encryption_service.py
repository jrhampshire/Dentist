"""
Unit tests for encryption_service.py (Task 12.2).

Tests:
- AES-256 encrypt/decrypt round-trip
- Empty string handling
- Key validation
- Tampered ciphertext detection
"""

import base64
import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.core.exceptions import ImproperlyConfigured

from patients.services.encryption_service import (
    decrypt,
    encrypt,
    reset_key,
)


@pytest.mark.unit
class TestEncryptionRoundTrip:
    """Test encrypt/decrypt round-trip."""

    def test_encrypt_decrypt_round_trip(self, settings):
        """Basic round-trip: encrypt then decrypt returns original."""
        plaintext = "Alergia a la penicilina"
        ciphertext = encrypt(plaintext)
        assert ciphertext != plaintext
        assert ciphertext  # Not empty

        decrypted = decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_decrypt_unicode(self, settings):
        """Round-trip with unicode characters."""
        plaintext = "Ñoño con café y corazón ❤️"
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_decrypt_long_text(self, settings):
        """Round-trip with long clinical note."""
        plaintext = "Paciente de 45 años con diabetes tipo 2. " * 100
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_empty_string_returns_empty(self, settings):
        """Empty string should return empty string."""
        assert encrypt("") == ""

    def test_decrypt_empty_string_returns_empty(self, settings):
        """Empty string should return empty string."""
        assert decrypt("") == ""


@pytest.mark.unit
class TestEncryptionProperties:
    """Test encryption properties."""

    def test_same_plaintext_different_ciphertext(self, settings):
        """Each encryption should produce different ciphertext (random IV)."""
        plaintext = "same text"
        ct1 = encrypt(plaintext)
        ct2 = encrypt(plaintext)
        assert ct1 != ct2

    def test_ciphertext_is_base64(self, settings):
        """Ciphertext should be valid base64."""
        ciphertext = encrypt("test")
        # Should not raise
        decoded = base64.b64decode(ciphertext)
        assert len(decoded) > 0

    def test_ciphertext_contains_nonce(self, settings):
        """Ciphertext blob should be nonce (12) + ciphertext + tag (16)."""
        ciphertext = encrypt("test")
        blob = base64.b64decode(ciphertext)
        # Minimum: 12 byte nonce + 16 byte tag = 28 bytes
        assert len(blob) >= 28


@pytest.mark.unit
class TestDecryptionErrors:
    """Test decryption error handling."""

    def test_tampered_ciphertext_raises(self, settings):
        """Tampered ciphertext should raise InvalidTag."""
        plaintext = "secret"
        ciphertext = encrypt(plaintext)

        # Tamper with the ciphertext
        blob = base64.b64decode(ciphertext)
        tampered = blob[:-1] + bytes([blob[-1] ^ 0xFF])
        tampered_b64 = base64.b64encode(tampered).decode()

        from cryptography.exceptions import InvalidTag

        with pytest.raises(InvalidTag):
            decrypt(tampered_b64)

    def test_invalid_base64_raises(self, settings):
        """Invalid base64 should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid base64"):
            decrypt("not-valid-base64!!!")

    def test_too_short_ciphertext_raises(self, settings):
        """Ciphertext shorter than nonce + tag should raise ValueError."""
        # Encode a blob that's too short
        short_blob = b"tooshort"
        short_b64 = base64.b64encode(short_blob).decode()

        with pytest.raises(ValueError, match="too short"):
            decrypt(short_b64)


@pytest.mark.unit
class TestKeyManagement:
    """Test encryption key management."""

    def test_key_caching(self, settings):
        """Key should be cached after first use."""
        from patients.services.encryption_service import _get_key, _key

        reset_key()
        key1 = _get_key()
        key2 = _get_key()
        assert key1 is key2

    def test_reset_key_clears_cache(self, settings):
        """reset_key should clear the cache."""
        from patients.services.encryption_service import _get_key

        reset_key()
        key1 = _get_key()
        reset_key()
        key2 = _get_key()
        # After reset, a new key instance is created
        assert key1 is not key2

    def test_invalid_base64_key_raises(self, settings):
        """Invalid base64 key should raise ImproperlyConfigured."""
        settings.ENCRYPTION_KEY = "not-valid-base64!!!"
        reset_key()

        with pytest.raises(ImproperlyConfigured, match="base64-encoded"):
            encrypt("test")

    def test_wrong_length_key_raises(self, settings):
        """Key that's not 32 bytes should raise ImproperlyConfigured."""
        wrong_key = base64.b64encode(b"short").decode()
        settings.ENCRYPTION_KEY = wrong_key
        reset_key()

        with pytest.raises(ImproperlyConfigured, match="32 bytes"):
            encrypt("test")

    def test_missing_key_generates_random(self, settings, caplog):
        """Missing key should generate a random key with a warning."""
        settings.ENCRYPTION_KEY = ""
        reset_key()

        # Should still work (with random key)
        ciphertext = encrypt("test")
        decrypted = decrypt(ciphertext)
        assert decrypted == "test"

        # Should have logged a warning
        assert "ENCRYPTION_KEY not set" in caplog.text


@pytest.mark.unit
class TestCSDPasswordDecryption:
    """Test _decrypt_csd_password in invoicing/views.py."""

    def test_decrypts_from_binaryfield(self, settings):
        """Verify _decrypt_csd_password decrypts encrypted CSD password."""
        from unittest.mock import MagicMock
        from invoicing.views import _decrypt_csd_password
        from patients.services.encryption_service import encrypt

        # Encrypt a test password
        plaintext = "mi_password_csd"
        encrypted = encrypt(plaintext)

        # Mock FiscalConfig with encrypted password as bytes
        fiscal_config = MagicMock()
        fiscal_config.csd_password_encrypted = encrypted.encode("utf-8")

        result = _decrypt_csd_password(fiscal_config)

        assert result == plaintext
        assert isinstance(result, str)

    def test_returns_placeholder_on_decrypt_failure(self, settings, caplog):
        """If decryption fails, return placeholder and log warning."""
        from unittest.mock import MagicMock
        from invoicing.views import _decrypt_csd_password

        fiscal_config = MagicMock()
        # Corrupted data that will fail decryption
        fiscal_config.csd_password_encrypted = b"not-valid-encrypted-data!!!"

        result = _decrypt_csd_password(fiscal_config)

        assert result == "placeholder"
        assert isinstance(result, str)

    def test_raises_on_empty_password(self):
        """Empty/unset CSD password should raise ValueError."""
        import pytest as pytest_mod
        from unittest.mock import MagicMock
        from invoicing.views import _decrypt_csd_password

        fiscal_config = MagicMock()
        fiscal_config.csd_password_encrypted = None

        with pytest_mod.raises(ValueError, match="CSD password not configured"):
            _decrypt_csd_password(fiscal_config)
