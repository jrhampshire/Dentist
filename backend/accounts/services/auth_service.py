"""
Authentication service for ClínicaSaaS.

Handles:
- JWT generation (access + refresh tokens)
- JWT validation
- Token rotation (single-use refresh tokens)
- Password verification with account lockout
- User authentication flow
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import RefreshToken

logger = logging.getLogger(__name__)

User = get_user_model()

# Token lifetimes
ACCESS_TOKEN_LIFETIME_MINUTES = 15
REFRESH_TOKEN_LIFETIME_DAYS = 7

# Account lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def authenticate(email: str, password: str) -> User:
        """
        Authenticate a user by email and password.

        Raises:
            User.DoesNotExist: if user not found
            ValueError: if account is locked, inactive, or password is wrong
        """
        try:
            user = User.objects.get(email=email, is_deleted=False)
        except User.DoesNotExist:
            # Don't reveal whether email exists
            raise ValueError("Email o contraseña incorrectos.")

        # Check if account is locked
        if user.is_locked():
            remaining = user.locked_until - timezone.now()
            minutes = int(remaining.total_seconds() / 60) + 1
            raise ValueError(
                f"Cuenta bloqueada. Intenta de nuevo en {minutes} minutos."
            )

        # Check if account is active
        if not user.is_active:
            raise ValueError("Tu cuenta está desactivada. Contacta al administrador.")

        # Verify password
        if not user.check_password(password):
            user.record_failed_attempt()
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                logger.warning(
                    "Account locked after %d failed attempts: %s",
                    MAX_FAILED_ATTEMPTS,
                    email,
                )
            raise ValueError("Email o contraseña incorrectos.")

        # Successful login — reset failed attempts
        user.reset_failed_attempts()
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return user

    @staticmethod
    def generate_tokens(user: User) -> dict[str, Any]:
        """
        Generate access and refresh tokens for a user.

        Returns dict with:
        - access_token: JWT string
        - refresh_token: DB token string
        - expires_in: seconds until access token expires
        - user: User instance
        """
        now = timezone.now()
        access_exp = now + timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES)
        refresh_exp = now + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)

        # Build access token payload
        access_payload = {
            "user_id": str(user.pk),
            "clinic_id": str(user.clinic_id) if user.clinic_id else None,
            "role": user.role,
            "exp": access_exp,
            "iat": now,
        }

        # Sign access token
        access_token = jwt.encode(
            access_payload,
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        # Create refresh token in DB
        import secrets

        refresh_token_str = secrets.token_urlsafe(64)
        RefreshToken.objects.create(
            user=user,
            token=refresh_token_str,
            expires_at=refresh_exp,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "expires_in": int(ACCESS_TOKEN_LIFETIME_MINUTES * 60),
            "user": user,
        }

    @staticmethod
    def refresh_access_token(
        refresh_token_str: str, ip: str | None = None, user_agent: str | None = None
    ) -> dict[str, Any]:
        """
        Rotate refresh token: revoke old, issue new pair.

        Single-use: the old refresh token is immediately revoked.

        Raises:
            ValueError: if token is invalid, expired, or revoked
        """
        try:
            db_token = RefreshToken.objects.select_related("user").get(
                token=refresh_token_str,
                revoked=False,
            )
        except RefreshToken.DoesNotExist:
            raise ValueError("Token de refresco inválido.")

        # Check expiration
        if db_token.is_expired():
            db_token.revoke()
            raise ValueError("Token de refresco expirado.")

        # Check user is still active
        user = db_token.user
        if not user.is_active or user.is_deleted:
            db_token.revoke()
            raise ValueError("Usuario desactivado.")

        # Revoke old token (single-use)
        db_token.revoke()

        # Generate new token pair
        return AuthService.generate_tokens(user)

    @staticmethod
    def revoke_token(refresh_token_str: str) -> bool:
        """
        Revoke a refresh token (logout).

        Returns True if token was found and revoked, False otherwise.
        """
        try:
            db_token = RefreshToken.objects.get(
                token=refresh_token_str,
                revoked=False,
            )
            db_token.revoke()
            logger.info("Token revoked for user: %s", db_token.user.email)
            return True
        except RefreshToken.DoesNotExist:
            return False

    @staticmethod
    def validate_access_token(token: str) -> dict[str, Any]:
        """
        Validate and decode an access token.

        Returns the decoded payload.

        Raises:
            ValueError: if token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expirado.")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Token inválido: {exc}")

    @staticmethod
    def get_user_by_id(user_id: str) -> User | None:
        """Get an active, non-deleted user by ID."""
        try:
            return User.objects.get(pk=user_id, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return None

    @staticmethod
    def revoke_all_user_tokens(user: User) -> int:
        """
        Revoke all active refresh tokens for a user.

        Returns the number of tokens revoked.
        """
        count = RefreshToken.objects.filter(
            user=user,
            revoked=False,
        ).update(revoked=True)
        logger.info("Revoked %d tokens for user: %s", count, user.email)
        return count
