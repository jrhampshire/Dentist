"""
AuditMiddleware — Captures request context for audit logging.

Stores user, IP, user agent, and request path in thread-local storage
so that post_save signals can access this context when creating
AuditLog entries.
"""

import logging
import threading
from typing import Callable

from django.http.request import HttpRequest
from django.http.response import HttpResponse

logger = logging.getLogger(__name__)

# Thread-local storage for audit context
_audit_context = threading.local()


def get_audit_context() -> dict:
    """Retrieve the current audit context from thread-local storage."""
    return getattr(_audit_context, "data", {})


def set_audit_context(data: dict) -> None:
    """Set the audit context in thread-local storage."""
    _audit_context.data = data


def clear_audit_context() -> None:
    """Clear the audit context from thread-local storage."""
    _audit_context.data = {}


class AuditMiddleware:
    """
    Middleware that captures request context for audit logging.

    Stores context in thread-local storage accessible via:
        from core.middleware.audit import get_audit_context
        ctx = get_audit_context()
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Build audit context from request
        user_id = getattr(request, "user_id", None)
        if request.user and request.user.is_authenticated:
            user_id = str(request.user.pk)

        clinic_id = getattr(request, "clinic_id", None)
        if clinic_id:
            clinic_id = str(clinic_id)

        # Get request_id from RequestIDMiddleware
        request_id = getattr(request, "request_id", None)

        context = {
            "user_id": user_id,
            "clinic_id": clinic_id,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", ""),
            "request_id": request_id,
            "path": request.path,
            "method": request.method,
        }

        set_audit_context(context)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Clear context after response to avoid leakage
            clear_audit_context()

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP, respecting proxy headers."""
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # First IP is the real client IP
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
