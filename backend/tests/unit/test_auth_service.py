"""
Unit tests for auth_service.py (Task 12.1).

Tests:
- Password verification
- JWT generation
- Account lockout
- Token rotation
- Token revocation
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from accounts.services.auth_service import AuthService


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthServiceAuthenticate:
    """Test the authenticate method."""

    def test_successful_authentication(self, create_user):
        user = create_user(email="test@test.com", password="correctpass")
        result = AuthService.authenticate("test@test.com", "correctpass")
        assert result == user
        assert result.failed_login_attempts == 0

    def test_wrong_password_raises(self, create_user):
        create_user(email="test@test.com", password="correctpass")
        with pytest.raises(ValueError, match="Email o contraseña incorrectos"):
            AuthService.authenticate("test@test.com", "wrongpass")

    def test_nonexistent_user_raises_generic(self):
        with pytest.raises(ValueError, match="Email o contraseña incorrectos"):
            AuthService.authenticate("nonexistent@test.com", "anypass")

    def test_inactive_user_raises(self, create_user):
        create_user(email="inactive@test.com", password="pass", is_active=False)
        with pytest.raises(ValueError, match="desactivada"):
            AuthService.authenticate("inactive@test.com", "pass")

    def test_locked_account_raises(self, create_user):
        user = create_user(email="locked@test.com", password="pass")
        # Manually lock the account
        user.failed_login_attempts = 5
        user.locked_until = timezone.now() + timedelta(minutes=10)
        user.save()

        with pytest.raises(ValueError, match="bloqueada"):
            AuthService.authenticate("locked@test.com", "pass")

    def test_failed_attempts_reset_on_success(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        user.failed_login_attempts = 3
        user.save()

        AuthService.authenticate("test@test.com", "pass")
        user.refresh_from_db()
        assert user.failed_login_attempts == 0

    def test_account_locks_after_max_attempts(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        from accounts.services.auth_service import MAX_FAILED_ATTEMPTS

        for _ in range(MAX_FAILED_ATTEMPTS):
            with pytest.raises(ValueError):
                AuthService.authenticate("test@test.com", "wrong")

        user.refresh_from_db()
        assert user.is_locked() is True


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthServiceGenerateTokens:
    """Test token generation."""

    def test_generate_tokens_returns_expected_keys(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        result = AuthService.generate_tokens(user)

        assert "access_token" in result
        assert "refresh_token" in result
        assert "expires_in" in result
        assert result["user"] == user
        assert result["expires_in"] == 900  # 15 minutes

    def test_access_token_is_valid_jwt(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        result = AuthService.generate_tokens(user)

        payload = AuthService.validate_access_token(result["access_token"])
        assert payload["user_id"] == str(user.pk)
        assert payload["role"] == user.role

    def test_refresh_token_stored_in_db(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        result = AuthService.generate_tokens(user)

        from accounts.models import RefreshToken

        db_token = RefreshToken.objects.get(token=result["refresh_token"])
        assert db_token.user == user
        assert db_token.revoked is False


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthServiceRefreshToken:
    """Test token refresh/rotation."""

    def test_refresh_returns_new_tokens(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)
        old_refresh = tokens["refresh_token"]

        new_tokens = AuthService.refresh_access_token(old_refresh)
        # New tokens are returned
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # Refresh token is rotated (new token generated)
        assert len(new_tokens["refresh_token"]) > 0
        assert new_tokens["refresh_token"] != old_refresh

    def test_refresh_revokes_old_token(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        AuthService.refresh_access_token(tokens["refresh_token"])

        from accounts.models import RefreshToken

        old = RefreshToken.objects.get(token=tokens["refresh_token"])
        assert old.revoked is True

    def test_refresh_expired_token_raises(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        # Make the token expired
        from accounts.models import RefreshToken

        RefreshToken.objects.filter(token=tokens["refresh_token"]).update(
            expires_at=timezone.now() - timedelta(days=1)
        )

        with pytest.raises(ValueError, match="expirado"):
            AuthService.refresh_access_token(tokens["refresh_token"])

    def test_refresh_revoked_token_raises(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        # Revoke it first
        AuthService.revoke_token(tokens["refresh_token"])

        with pytest.raises(ValueError, match="inválido"):
            AuthService.refresh_access_token(tokens["refresh_token"])


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthServiceRevokeToken:
    """Test token revocation (logout)."""

    def test_revoke_token_returns_true(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        assert AuthService.revoke_token(tokens["refresh_token"]) is True

    def test_revoke_nonexistent_token_returns_false(self):
        assert AuthService.revoke_token("nonexistent") is False

    def test_revoke_all_user_tokens(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        AuthService.generate_tokens(user)
        AuthService.generate_tokens(user)

        count = AuthService.revoke_all_user_tokens(user)
        assert count == 2


@pytest.mark.unit
@pytest.mark.django_db
class TestAuthServiceValidateToken:
    """Test access token validation."""

    def test_valid_token_returns_payload(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        payload = AuthService.validate_access_token(tokens["access_token"])
        assert payload["user_id"] == str(user.pk)
        assert payload["role"] == user.role

    def test_expired_token_raises(self, create_user):
        user = create_user(email="test@test.com", password="pass")
        tokens = AuthService.generate_tokens(user)

        # Decode, modify exp, re-encode
        import jwt
        from django.conf import settings

        payload = jwt.decode(
            tokens["access_token"], settings.SECRET_KEY, algorithms=["HS256"]
        )
        payload["exp"] = timezone.now() - timedelta(hours=1)
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        with pytest.raises(ValueError, match="expirado"):
            AuthService.validate_access_token(expired_token)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="inválido"):
            AuthService.validate_access_token("invalid.token.here")
