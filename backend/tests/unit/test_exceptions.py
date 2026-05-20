"""
Unit tests for core/exceptions.py — unified_exception_handler.

Tests all DRF exception types through the unified error handler.
Uses APIRequestFactory to create mock request objects.

Important: The actual code returns responses with fields:
  {"error": ..., "message": ..., "details": ..., "request_id": ...}

The spec mentions "code" and "error_code" fields, but the ACTUAL code
uses "error" and "request_id". Tests match ACTUAL code behavior.
"""

import pytest
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.test import APIRequestFactory

from core.exceptions import unified_exception_handler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

factory = APIRequestFactory()


def _make_context(method="GET", path="/api/test/"):
    """Create a DRF exception handler context dict with a mock request."""
    request = factory.get(path) if method == "GET" else factory.post(path)
    # request_id is only set by middleware; mock requests won't have it
    return {"request": request}


def _call_handler(exc, context=None):
    """Call unified_exception_handler and return the response."""
    if context is None:
        context = _make_context()
    return unified_exception_handler(exc, context)


# ---------------------------------------------------------------------------
# ValidationError → 400
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidationError:
    """ValidationError must return HTTP 400 with structured error."""

    def test_validation_error_returns_400(self):
        """ValidationError → HTTP 400 with validation_error code."""
        exc = ValidationError({"email": ["Este campo es requerido."]})
        response = _call_handler(exc)

        assert response.status_code == 400
        assert response.data["error"] == "validation_error"

    def test_validation_error_includes_message(self):
        """ValidationError includes a Spanish message."""
        exc = ValidationError({"phone": ["Número inválido."]})
        response = _call_handler(exc)

        assert "message" in response.data
        assert isinstance(response.data["message"], str)
        assert len(response.data["message"]) > 0

    def test_validation_error_includes_details(self):
        """ValidationError includes field-level details."""
        exc = ValidationError({"email": ["Este campo es requerido."]})
        response = _call_handler(exc)

        assert "details" in response.data
        assert "email" in response.data["details"]

    def test_validation_error_includes_request_id(self):
        """ValidationError response includes request_id field."""
        exc = ValidationError({"name": ["Requerido."]})
        response = _call_handler(exc)

        assert "request_id" in response.data
        # request_id is None when no middleware sets it
        assert response.data["request_id"] is None

    def test_validation_error_with_list_detail(self):
        """ValidationError with list-style detail is formatted correctly."""
        exc = ValidationError(["Error general en los datos."])
        response = _call_handler(exc)

        assert response.status_code == 400
        assert response.data["error"] == "validation_error"


# ---------------------------------------------------------------------------
# NotAuthenticated → 401
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNotAuthenticated:
    """NotAuthenticated must return HTTP 401."""

    def test_not_authenticated_returns_401(self):
        """NotAuthenticated → HTTP 401 with not_authenticated error."""
        exc = NotAuthenticated()
        response = _call_handler(exc)

        assert response.status_code == 401
        assert response.data["error"] == "not_authenticated"

    def test_not_authenticated_has_empty_details(self):
        """NotAuthenticated has empty details dict."""
        exc = NotAuthenticated()
        response = _call_handler(exc)

        assert response.data["details"] == {}

    def test_not_authenticated_includes_message(self):
        """NotAuthenticated includes a Spanish login message."""
        exc = NotAuthenticated()
        response = _call_handler(exc)

        assert "message" in response.data
        assert "iniciar sesión" in response.data["message"].lower()


# ---------------------------------------------------------------------------
# AuthenticationFailed → 401
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuthenticationFailed:
    """AuthenticationFailed (expired/invalid credentials) → HTTP 401."""

    def test_authentication_failed_returns_401(self):
        """AuthenticationFailed → HTTP 401 with authentication_failed error."""
        exc = AuthenticationFailed()
        response = _call_handler(exc)

        assert response.status_code == 401
        assert response.data["error"] == "authentication_failed"

    def test_authentication_failed_includes_message(self):
        """AuthenticationFailed message comes from exc.detail."""
        exc = AuthenticationFailed("Token expirado.")
        response = _call_handler(exc)

        assert response.data["message"] == "Token expirado."


# ---------------------------------------------------------------------------
# PermissionDenied → 403
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPermissionDenied:
    """PermissionDenied must return HTTP 403."""

    def test_permission_denied_returns_403(self):
        """PermissionDenied → HTTP 403 with permission_denied error."""
        exc = PermissionDenied()
        response = _call_handler(exc)

        assert response.status_code == 403
        assert response.data["error"] == "permission_denied"

    def test_permission_denied_has_empty_details(self):
        """PermissionDenied has empty details dict."""
        exc = PermissionDenied()
        response = _call_handler(exc)

        assert response.data["details"] == {}

    def test_permission_denied_includes_message(self):
        """PermissionDenied includes a Spanish no-permissions message."""
        exc = PermissionDenied()
        response = _call_handler(exc)

        assert "message" in response.data
        assert "permisos" in response.data["message"].lower()


# ---------------------------------------------------------------------------
# NotFound → 404
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNotFound:
    """NotFound must return HTTP 404."""

    def test_not_found_returns_404(self):
        """NotFound → HTTP 404 with not_found error code."""
        exc = NotFound()
        response = _call_handler(exc)

        assert response.status_code == 404
        # NotFound is an APIException with default_code="not_found"
        assert response.data["error"] == "not_found"

    def test_not_found_includes_message(self):
        """NotFound includes the exception detail message."""
        exc = NotFound("Paciente no encontrado.")
        response = _call_handler(exc)

        assert response.data["message"] == "Paciente no encontrado."

    def test_not_found_has_empty_details(self):
        """NotFound has empty details dict."""
        exc = NotFound()
        response = _call_handler(exc)

        assert response.data["details"] == {}


# ---------------------------------------------------------------------------
# Unexpected Exception → 500
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnexpectedException:
    """Non-DRF exceptions must return HTTP 500 without leaking details."""

    def test_unexpected_exception_returns_500(self):
        """Non-DRF exception → HTTP 500 with internal_server_error."""
        exc = Exception("Something went wrong internally")
        response = _call_handler(exc)

        assert response.status_code == 500
        assert response.data["error"] == "internal_server_error"

    def test_unexpected_exception_does_not_leak_details(self):
        """Exception message must NOT appear in the response."""
        exc = Exception("SECRET: database password is hunter2")
        response = _call_handler(exc)

        data_str = str(response.data)
        assert "hunter2" not in data_str
        assert "SECRET" not in data_str
        # The internal message should be generic
        assert "Error interno" in response.data["message"]

    def test_unexpected_exception_has_empty_details(self):
        """Unexpected exception has empty details dict."""
        exc = Exception("boom")
        response = _call_handler(exc)

        assert response.data["details"] == {}

    def test_unexpected_exception_includes_request_id_field(self):
        """Response includes request_id field (None when no middleware)."""
        exc = Exception("test")
        response = _call_handler(exc)

        assert "request_id" in response.data
