"""
Unit tests for core/authentication.py.

Tests JWTAuthentication.authenticate() with valid, expired, malformed,
and missing tokens. Matches ACTUAL code behavior (raises AuthenticationFailed
for invalid/expired tokens, returns None for missing header).
No DB required.
"""

from unittest.mock import Mock, patch

import jwt
import pytest
from rest_framework.exceptions import AuthenticationFailed

from core.authentication import JWTAuthentication

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_request(auth_header=None):
    """Build a DRF Request mock with an optional Authorization header."""
    request = Mock()
    request.headers = {"Authorization": auth_header} if auth_header else {}
    return request


# ---------------------------------------------------------------------------
# JWTAuthentication.authenticate()
# ---------------------------------------------------------------------------


class TestJWTAuthentication:
    """JWT authentication: valid, expired, malformed, and missing tokens."""

    @patch("core.authentication.User.objects.get")
    @patch("core.authentication.jwt.decode")
    def test_valid_token_returns_user_and_token(
        self, mock_jwt_decode, mock_user_get, mock_jwt_payload
    ):
        """Valid JWT → returns (user, token) tuple."""
        payload = mock_jwt_payload()
        mock_jwt_decode.return_value = payload

        mock_user = Mock()
        mock_user_get.return_value = mock_user

        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer valid.jwt.token")
        result = auth.authenticate(request)

        assert result is not None
        user, token = result
        assert user is mock_user
        assert token == "valid.jwt.token"
        mock_jwt_decode.assert_called_once()

    @patch("core.authentication.jwt.decode")
    def test_expired_token_raises_authentication_failed(self, mock_jwt_decode):
        """Expired JWT → raises AuthenticationFailed."""
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError()

        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer expired.token")

        with pytest.raises(AuthenticationFailed, match="expirado"):
            auth.authenticate(request)

    @patch("core.authentication.jwt.decode")
    def test_malformed_token_raises_authentication_failed(self, mock_jwt_decode):
        """Malformed/structurally invalid JWT → raises AuthenticationFailed."""
        mock_jwt_decode.side_effect = jwt.InvalidTokenError("Malformed token")

        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer malformed.token")

        with pytest.raises(AuthenticationFailed, match="inválido"):
            auth.authenticate(request)

    def test_missing_authorization_header_returns_none(self):
        """No Authorization header → returns None (no exception)."""
        auth = JWTAuthentication()
        request = make_mock_request(auth_header=None)

        result = auth.authenticate(request)
        assert result is None

    def test_non_bearer_header_returns_none(self):
        """Authorization header exists but isn't 'Bearer ...' → returns None."""
        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Basic dXNlcjpwYXNz")

        result = auth.authenticate(request)
        assert result is None

    def test_empty_bearer_token_returns_none(self):
        """Authorization header is 'Bearer ' with nothing after → returns None."""
        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer ")

        result = auth.authenticate(request)
        assert result is None

    @patch("core.authentication.jwt.decode")
    def test_token_missing_user_id_raises_authentication_failed(self, mock_jwt_decode):
        """JWT payload without 'user_id' → raises AuthenticationFailed."""
        mock_jwt_decode.return_value = {"role": "admin", "clinic_id": "c1"}

        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer no.user.id.token")

        with pytest.raises(AuthenticationFailed, match="sin user_id"):
            auth.authenticate(request)

    @patch("core.authentication.User.objects.get")
    @patch("core.authentication.jwt.decode")
    def test_user_not_found_raises_authentication_failed(
        self, mock_jwt_decode, mock_user_get, mock_jwt_payload
    ):
        """Valid token but user deleted/inactive → raises AuthenticationFailed."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        mock_jwt_decode.return_value = mock_jwt_payload()
        mock_user_get.side_effect = User.DoesNotExist("User does not exist")

        auth = JWTAuthentication()
        request = make_mock_request(auth_header="Bearer valid.but.deleted.user")

        with pytest.raises(AuthenticationFailed, match="no encontrado"):
            auth.authenticate(request)
