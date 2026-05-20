"""
TenantMiddleware — Multi-tenant isolation via PostgreSQL RLS.

Extracts clinic_id, user_id, and user_role from the JWT access token
and sets PostgreSQL session variables so that Row Level Security
automatically filters all queries by tenant.

Skips public endpoints (registration, webhooks, health checks).
"""

import logging
from typing import Callable

import jwt
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponse

logger = logging.getLogger(__name__)


class TenantMiddleware:
    """
    Middleware that injects tenant context into PostgreSQL session variables.

    Flow:
    1. Check if the request is for a public endpoint → skip if yes
    2. Extract JWT from Authorization header
    3. Decode and validate the token
    4. Set PostgreSQL session variables:
       - app.current_clinic_id
       - app.current_user_id
       - app.current_user_role
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Skip tenant injection for public endpoints
        if self._is_public_endpoint(request):
            return self.get_response(request)

        token = self._extract_token(request)
        if not token:
            return JsonResponse(
                {
                    "error": "missing_token",
                    "message": "Token de autenticación requerido.",
                },
                status=401,
            )

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {
                    "error": "token_expired",
                    "message": "Token expirado. Refresca tu sesión.",
                },
                status=401,
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid JWT token: %s", exc)
            return JsonResponse(
                {
                    "error": "invalid_token",
                    "message": "Token de autenticación inválido.",
                },
                status=401,
            )

        clinic_id = payload.get("clinic_id")
        user_id = payload.get("user_id")
        user_role = payload.get("role")

        if not clinic_id:
            return JsonResponse(
                {"error": "no_clinic", "message": "Token sin contexto de clínica."},
                status=403,
            )

        # Attach to request for use in views/serializers
        request.clinic_id = clinic_id  # type: ignore[attr-defined]
        request.user_id = user_id  # type: ignore[attr-defined]
        request.user_role = user_role  # type: ignore[attr-defined]

        # Set PostgreSQL session variables for RLS
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET app.current_clinic_id = %s", [str(clinic_id)])
                if user_id:
                    cursor.execute("SET app.current_user_id = %s", [str(user_id)])
                if user_role:
                    cursor.execute("SET app.current_user_role = %s", [user_role])
        except Exception as exc:
            logger.error("Failed to set PostgreSQL session variables: %s", exc)
            return JsonResponse(
                {
                    "error": "db_error",
                    "message": "Error de configuración de base de datos.",
                },
                status=500,
            )

        return self.get_response(request)

    @staticmethod
    def _is_public_endpoint(request: HttpRequest) -> bool:
        """Check if the request path matches a public endpoint."""
        path = request.path
        for endpoint in settings.PUBLIC_ENDPOINTS:
            if path.startswith(endpoint):
                return True
        return False

    @staticmethod
    def _extract_token(request: HttpRequest) -> str | None:
        """Extract JWT from Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        return None
