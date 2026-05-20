"""
Unified exception handler for DRF.

Converts all exceptions into a consistent JSON format:
{
    "error": "error_code",
    "message": "Human-readable message in Spanish",
    "details": {...},
    "request_id": "uuid"
}
"""

import logging
from typing import Any

from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def unified_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """
    Unified exception handler that normalizes all API errors.

    Maps Django/DRF exceptions to a consistent error response format
    with error code, Spanish message, optional details, and request_id.
    """
    # Call DRF's default handler first to get the response
    response = drf_exception_handler(exc, context)

    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None

    if response is None:
        # Unhandled exception — log it and return 500
        logger.exception("Unhandled exception in API request")
        return Response(
            {
                "error": "internal_server_error",
                "message": "Error interno del servidor. Por favor intenta de nuevo más tarde.",
                "details": {},
                "request_id": request_id,
            },
            status=500,
        )

    # Build the unified error response
    error_data = _build_error_data(exc, response, request_id)
    response.data = error_data

    return response


def _build_error_data(
    exc: Exception,
    response: Response,
    request_id: str | None,
) -> dict[str, Any]:
    """Build the unified error data dict."""
    if isinstance(exc, ValidationError):
        return {
            "error": "validation_error",
            "message": "Error de validación en los datos enviados.",
            "details": _format_validation_details(exc.detail),
            "request_id": request_id,
        }

    if isinstance(exc, NotAuthenticated):
        return {
            "error": "not_authenticated",
            "message": "Debes iniciar sesión para acceder a este recurso.",
            "details": {},
            "request_id": request_id,
        }

    if isinstance(exc, AuthenticationFailed):
        return {
            "error": "authentication_failed",
            "message": str(exc.detail)
            if hasattr(exc, "detail")
            else "Credenciales inválidas.",
            "details": {},
            "request_id": request_id,
        }

    if isinstance(exc, PermissionDenied):
        return {
            "error": "permission_denied",
            "message": "No tienes permisos para realizar esta acción.",
            "details": {},
            "request_id": request_id,
        }

    if isinstance(exc, APIException):
        error_code = getattr(exc, "default_code", "api_error")
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        return {
            "error": error_code,
            "message": message,
            "details": {},
            "request_id": request_id,
        }

    # Generic server error
    return {
        "error": "internal_server_error",
        "message": "Error interno del servidor.",
        "details": {},
        "request_id": request_id,
    }


def _format_validation_details(detail: Any) -> dict | list:
    """Format DRF validation details into a clean structure."""
    if isinstance(detail, dict):
        formatted = {}
        for field, errors in detail.items():
            if isinstance(errors, list):
                formatted[field] = [str(e) for e in errors]
            elif isinstance(errors, dict):
                formatted[field] = _format_validation_details(errors)
            else:
                formatted[field] = [str(errors)]
        return formatted
    if isinstance(detail, list):
        return [str(e) for e in detail]
    return {"non_field_errors": [str(detail)]}
