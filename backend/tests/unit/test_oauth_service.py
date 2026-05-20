"""
Unit tests for accounts/services/oauth_service.py.

Tests Google/Apple OAuth2 token exchange, ID token verification,
and handle_oauth_login with mocked external dependencies.
No DB required.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from accounts.services.oauth_service import (
    AppleOAuthService,
    GoogleOAuthService,
    handle_oauth_login,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# GoogleOAuthService.exchange_code
# ---------------------------------------------------------------------------


class TestGoogleExchangeCode:
    """Google token exchange: success, failure, and edge cases."""

    @patch("accounts.services.oauth_service.requests.post")
    @patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
        },
    )
    def test_successful_exchange(self, mock_post, mocked_google_oauth_response):
        """Exchange a valid authorization code and receive tokens."""
        mock_post.return_value = mocked_google_oauth_response

        result = GoogleOAuthService.exchange_code(
            code="valid_code",
            code_verifier="valid_verifier",
            redirect_uri="https://example.com/callback",
        )

        assert result["access_token"] == "mock_access_token"
        assert result["id_token"] == "mock_id_token"
        assert result["expires_in"] == 3600

    @patch("accounts.services.oauth_service.requests.post")
    @patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
        },
    )
    def test_http_error_raises_value_error(self, mock_post):
        """Token exchange HTTP failure raises ValueError."""
        mock_resp = Mock(spec=requests.Response)
        mock_resp.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="No se pudo completar"):
            GoogleOAuthService.exchange_code(
                code="invalid_code",
                code_verifier="verifier",
                redirect_uri="https://example.com/callback",
            )

    @patch("accounts.services.oauth_service.requests.post")
    @patch.dict(
        "os.environ",
        {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret",
        },
    )
    def test_connection_error_raises_value_error(self, mock_post):
        """Network failure raises ValueError."""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(ValueError, match="No se pudo completar"):
            GoogleOAuthService.exchange_code(
                code="code",
                code_verifier="verifier",
                redirect_uri="https://example.com/callback",
            )

    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""})
    def test_missing_config_raises_value_error(self):
        """Missing client credentials raises ValueError."""
        with pytest.raises(ValueError, match="no está configurado"):
            GoogleOAuthService.exchange_code(
                code="code",
                code_verifier="verifier",
                redirect_uri="https://example.com/callback",
            )


# ---------------------------------------------------------------------------
# GoogleOAuthService.verify_id_token
# ---------------------------------------------------------------------------


class TestGoogleVerifyIdToken:
    """Google ID token verification."""

    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test-client-id"})
    def test_successful_verification(self, mocked_google_verify_id_token):
        """Valid ID token returns claims with email and sub."""
        claims = GoogleOAuthService.verify_id_token("valid_id_token")

        assert claims["email"] == "user@gmail.com"
        assert claims["name"] == "Google User"
        assert claims["sub"] == "12345"
        assert claims["email_verified"] is True

    @patch("google.oauth2.id_token.verify_oauth2_token")
    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "test-client-id"})
    def test_verification_failure_raises_value_error(self, mock_verify_token):
        """Failed verification raises ValueError."""
        mock_verify_token.side_effect = Exception("Invalid token")

        with pytest.raises(ValueError, match="Token de Google inválido"):
            GoogleOAuthService.verify_id_token("bad_token")

    @patch.dict("os.environ", {"GOOGLE_CLIENT_ID": ""})
    def test_missing_client_id_raises_value_error(self):
        """Missing client_id raises ValueError.

        Note: the ValueError is caught by the outer except clause in
        verify_id_token() and re-raised as 'Token de Google inválido.'
        """
        with pytest.raises(ValueError, match="Token de Google inválido"):
            GoogleOAuthService.verify_id_token("some_token")


# ---------------------------------------------------------------------------
# AppleOAuthService.exchange_code
# ---------------------------------------------------------------------------


class TestAppleExchangeCode:
    """Apple token exchange: success and failure."""

    @patch("accounts.services.oauth_service.requests.post")
    @patch.object(
        AppleOAuthService, "_generate_client_secret", return_value="mock_jwt_secret"
    )
    @patch.dict("os.environ", {"APPLE_CLIENT_ID": "test-apple-client-id"})
    def test_successful_exchange(self, mock_gen_secret, mock_post):
        """Exchange a valid Apple authorization code and receive tokens."""
        mock_resp = Mock(spec=requests.Response)
        mock_resp.json.return_value = {
            "access_token": "apple_access_token",
            "id_token": "apple_id_token",
            "refresh_token": "apple_refresh_token",
        }
        mock_resp.ok = True
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        result = AppleOAuthService.exchange_code(
            code="valid_apple_code",
            code_verifier="valid_verifier",
            redirect_uri="https://example.com/callback",
        )

        assert result["access_token"] == "apple_access_token"
        assert result["id_token"] == "apple_id_token"
        assert result["refresh_token"] == "apple_refresh_token"

    @patch("accounts.services.oauth_service.requests.post")
    @patch.object(
        AppleOAuthService, "_generate_client_secret", return_value="mock_jwt_secret"
    )
    @patch.dict("os.environ", {"APPLE_CLIENT_ID": "test-apple-client-id"})
    def test_http_error_raises_value_error(self, mock_gen_secret, mock_post):
        """Apple token exchange failure raises ValueError."""
        mock_resp = Mock(spec=requests.Response)
        mock_resp.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        mock_post.return_value = mock_resp

        with pytest.raises(ValueError, match="No se pudo completar"):
            AppleOAuthService.exchange_code(
                code="bad_code",
                code_verifier="verifier",
                redirect_uri="https://example.com/callback",
            )

    @patch.dict("os.environ", {"APPLE_CLIENT_ID": ""})
    def test_missing_client_id_raises_value_error(self):
        """Missing Apple client ID raises ValueError."""
        with pytest.raises(ValueError, match="no está configurado"):
            AppleOAuthService.exchange_code(
                code="code",
                code_verifier="verifier",
                redirect_uri="https://example.com/callback",
            )


# ---------------------------------------------------------------------------
# handle_oauth_login
# ---------------------------------------------------------------------------


class TestHandleOAuthLogin:
    """OAuth login: user lookup, creation, and linking."""

    @patch("accounts.services.oauth_service.AuthService.generate_tokens")
    @patch("accounts.services.oauth_service.User.objects")
    def test_existing_oauth_user(self, mock_user_objects, mock_generate_tokens):
        """Find existing user by OAuth provider + ID."""
        mock_user = Mock()
        mock_user.is_active = True
        mock_user_objects.filter.return_value.first.return_value = mock_user
        mock_generate_tokens.return_value = {
            "access": "access_token",
            "refresh": "refresh_token",
        }

        result = handle_oauth_login(
            provider="google",
            email="user@gmail.com",
            oauth_id="12345",
            first_name="Google",
            last_name="User",
        )

        assert result["access"] == "access_token"
        assert result["refresh"] == "refresh_token"

    @patch("accounts.services.oauth_service.AuthService.generate_tokens")
    @patch("accounts.services.oauth_service.User.objects")
    def test_link_by_email(self, mock_user_objects, mock_generate_tokens):
        """Link OAuth credentials to existing user found by email."""
        mock_user = Mock()
        mock_user.is_active = True

        # First filter (oauth_provider + oauth_id) returns None
        # Second filter (email) returns the user
        mock_user_objects.filter.return_value.first.side_effect = [
            None,  # oauth lookup → no match
            mock_user,  # email lookup → found
        ]
        mock_generate_tokens.return_value = {"access": "a", "refresh": "r"}

        result = handle_oauth_login(
            provider="google",
            email="existing@test.com",
            oauth_id="new_oauth_id",
        )

        # Verify OAuth credentials were linked
        assert mock_user.oauth_provider == "google"
        assert mock_user.oauth_id == "new_oauth_id"
        mock_user.save.assert_called()
        assert result["access"] == "a"

    @patch("accounts.services.oauth_service.AuthService.generate_tokens")
    @patch("accounts.services.oauth_service.User.objects")
    def test_create_new_user(self, mock_user_objects, mock_generate_tokens):
        """Create a new user when no existing match is found."""
        mock_user_objects.filter.return_value.first.return_value = None
        mock_new_user = Mock()
        mock_new_user.is_active = True
        mock_user_objects.create.return_value = mock_new_user
        mock_generate_tokens.return_value = {"access": "a", "refresh": "r"}

        result = handle_oauth_login(
            provider="apple",
            email="new@test.com",
            oauth_id="apple_123",
            first_name="Apple",
            last_name="User",
        )

        mock_user_objects.create.assert_called_once()
        assert result["access"] == "a"

    @patch("accounts.services.oauth_service.User.objects")
    def test_inactive_user_raises_value_error(self, mock_user_objects):
        """Inactive user raises ValueError."""
        mock_user = Mock()
        mock_user.is_active = False
        mock_user_objects.filter.return_value.first.return_value = mock_user

        with pytest.raises(ValueError, match="desactivada"):
            handle_oauth_login(
                provider="google",
                email="inactive@test.com",
                oauth_id="12345",
            )


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


class TestPKCE:
    """PKCE code_verifier / code_challenge generation."""

    def test_generate_pkce_pair_returns_strings(self):
        """PKCE pair generation returns two non-empty strings."""
        from accounts.services.oauth_service import generate_pkce_pair

        verifier, challenge = generate_pkce_pair()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_generate_state_returns_string(self):
        """State generation returns a non-empty string."""
        from accounts.services.oauth_service import generate_state

        state = generate_state()
        assert isinstance(state, str)
        assert len(state) > 0
