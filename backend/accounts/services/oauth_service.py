"""
OAuth2 service for Google and Apple sign-in with PKCE.

Handles:
- PKCE code_verifier/code_challenge generation
- OAuth2 code exchange for Google and Apple
- User info retrieval and matching
- User creation/linking on first OAuth login
- JWT token issuance after successful OAuth auth
"""

import hashlib
import base64
import logging
import os
import secrets
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.services.auth_service import AuthService

logger = logging.getLogger(__name__)

User = get_user_model()

# OAuth provider configuration
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"

# Request timeouts (seconds)
OAUTH_TIMEOUT = 10


def generate_pkce_pair() -> tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge.

    Returns:
        (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(64)
    # code_challenge = BASE64URL(SHA256(code_verifier))
    sha256 = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(sha256).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def generate_state() -> str:
    """Generate a cryptographically secure state parameter for CSRF protection."""
    return secrets.token_urlsafe(32)


class GoogleOAuthService:
    """Google OAuth2 with PKCE flow."""

    @staticmethod
    def exchange_code(
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for Google tokens.

        Args:
            code: Authorization code from Google
            code_verifier: PKCE code verifier
            redirect_uri: Must match the one used in auth request

        Returns:
            dict with id_token, access_token, etc.

        Raises:
            ValueError: if code exchange fails
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            raise ValueError("Google OAuth no está configurado.")

        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        }

        try:
            resp = requests.post(
                GOOGLE_TOKEN_URL,
                data=data,
                timeout=OAUTH_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("Google token exchange failed: %s", exc)
            raise ValueError("No se pudo completar la autenticación con Google.")

    @staticmethod
    def get_user_info(access_token: str) -> dict[str, Any]:
        """
        Get user profile from Google using access token.

        Returns:
            dict with email, name, picture, sub (Google user ID)

        Raises:
            ValueError: if userinfo request fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            resp = requests.get(
                GOOGLE_USERINFO_URL,
                headers=headers,
                timeout=OAUTH_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("Google userinfo request failed: %s", exc)
            raise ValueError("No se pudo obtener la información del usuario de Google.")

    @staticmethod
    def verify_id_token(id_token: str) -> dict[str, Any]:
        """
        Verify Google ID token and extract claims.

        Uses google-auth library for proper JWT verification.

        Returns:
            dict with email, email_verified, name, sub, etc.

        Raises:
            ValueError: if token verification fails
        """
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            client_id = os.getenv("GOOGLE_CLIENT_ID", "")
            if not client_id:
                raise ValueError("Google OAuth no está configurado.")

            # Verify the ID token
            claims = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                client_id,
            )

            if not claims.get("email_verified"):
                raise ValueError("El email de Google no está verificado.")

            return claims

        except ImportError:
            # Fallback: decode without verification (not recommended for prod)
            import jwt

            payload = jwt.decode(id_token, options={"verify_signature": False})
            return payload

        except Exception as exc:
            logger.error("Google ID token verification failed: %s", exc)
            raise ValueError("Token de Google inválido.")


class AppleOAuthService:
    """Apple Sign-In with PKCE flow."""

    @staticmethod
    def exchange_code(
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for Apple tokens.

        Apple requires a client_secret (JWT signed with private key).

        Args:
            code: Authorization code from Apple
            code_verifier: PKCE code verifier
            redirect_uri: Must match the one used in auth request

        Returns:
            dict with id_token, access_token, refresh_token, etc.

        Raises:
            ValueError: if code exchange fails
        """
        client_id = os.getenv("APPLE_CLIENT_ID", "")
        client_secret = AppleOAuthService._generate_client_secret()

        if not client_id:
            raise ValueError("Apple OAuth no está configurado.")

        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }

        try:
            resp = requests.post(
                APPLE_TOKEN_URL,
                data=data,
                timeout=OAUTH_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.error("Apple token exchange failed: %s", exc)
            raise ValueError("No se pudo completar la autenticación con Apple.")

    @staticmethod
    def decode_id_token(id_token: str) -> dict[str, Any]:
        """
        Decode Apple ID token to extract user claims.

        Apple ID tokens contain: email, email_verified, sub (Apple user ID), etc.

        Returns:
            dict with email, sub, etc.

        Raises:
            ValueError: if token is invalid
        """
        import jwt

        try:
            # Apple public keys are at https://appleid.apple.com/auth/keys
            # For now, decode without verification (add verification in production)
            payload = jwt.decode(id_token, options={"verify_signature": False})
            return payload
        except Exception as exc:
            logger.error("Apple ID token decode failed: %s", exc)
            raise ValueError("Token de Apple inválido.")

    @staticmethod
    def _generate_client_secret() -> str:
        """
        Generate Apple client_secret (JWT signed with ES256 private key).

        In production, this uses the Apple private key from the developer portal.
        For now, reads from environment.
        """
        client_secret_jwt = os.getenv("APPLE_CLIENT_SECRET_JWT", "")
        if not client_secret_jwt:
            raise ValueError("Apple client_secret JWT no está configurado.")
        return client_secret_jwt


def handle_oauth_login(
    provider: str,
    email: str,
    oauth_id: str,
    first_name: str = "",
    last_name: str = "",
) -> dict[str, Any]:
    """
    Handle OAuth login: find or create user, issue JWT tokens.

    Args:
        provider: 'google' or 'apple'
        email: User's email from provider
        oauth_id: Provider's user ID (sub)
        first_name: User's first name (optional)
        last_name: User's last name (optional)

    Returns:
        Token dict from AuthService.generate_tokens()

    Raises:
        ValueError: if user cannot be found or created
    """
    # Try to find existing user by OAuth credentials
    user = User.objects.filter(
        oauth_provider=provider,
        oauth_id=oauth_id,
        is_deleted=False,
    ).first()

    # If not found by OAuth, try to find by email and link
    if not user:
        user = User.objects.filter(
            email=email,
            is_deleted=False,
        ).first()

        if user:
            # Link OAuth credentials to existing user
            user.oauth_provider = provider
            user.oauth_id = oauth_id
            user.save(update_fields=["oauth_provider", "oauth_id", "updated_at"])
            logger.info("Linked %s OAuth to existing user: %s", provider, email)
        else:
            # Create new user via OAuth
            # Note: OAuth users may not have a clinic yet (onboarding flow)
            user = User.objects.create(
                email=email,
                first_name=first_name or email.split("@")[0],
                last_name=last_name or "",
                role=User.Role.RECEPCIONISTA,  # Default role, can be changed later
                oauth_provider=provider,
                oauth_id=oauth_id,
                is_verified=True,  # OAuth emails are pre-verified
            )
            logger.info("Created new user via %s OAuth: %s", provider, email)

    if not user.is_active:
        raise ValueError("Tu cuenta está desactivada. Contacta al administrador.")

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])

    # Generate JWT tokens
    return AuthService.generate_tokens(user)
