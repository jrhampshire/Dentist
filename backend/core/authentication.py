"""
Custom JWT Authentication for DRF.

Validates the JWT access token from the Authorization header,
extracts claims (user_id, clinic_id, role), and sets them on
the request for downstream middleware and views.
"""

import logging
from typing import Any, Tuple

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT authentication that validates the access token
    and resolves the Django User object.

    The token must contain: user_id, clinic_id, role
    """

    www_authenticate_realm = "api"

    def authenticate(self, request: Any) -> Tuple[Any, Any] | None:
        """
        Returns a (user, token) tuple if authentication succeeds,
        or None if no token is provided.
        Raises AuthenticationFailed if the token is invalid.
        """
        token = self._get_token_from_header(request)
        if token is None:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed(_("Token expirado. Refresca tu sesión."))
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed(
                _("Token inválido: %(error)s") % {"error": str(exc)}
            )

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed(_("Token sin user_id."))

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed(_("Usuario no encontrado o desactivado."))

        return user, token

    def authenticate_header(self, request: Any) -> str:
        """Return the WWW-Authenticate header value."""
        return f'{self.www_authenticate_realm} realm="{self.www_authenticate_realm}"'

    @staticmethod
    def _get_token_from_header(request: Any) -> str | None:
        """Extract JWT from the Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:].strip() or None
