"""
Root URL configuration for ClínicaSaaS Dental MX.

Routes all API requests to their respective app routers.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from clinics.views import ClinicViewSet

# Router for clinics
clinics_router = DefaultRouter()
clinics_router.register(r"", ClinicViewSet, basename="clinics")


class HealthCheckView(APIView):
    """Liveness check — is the app running?"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessCheckView(APIView):
    """Readiness check — are all dependencies connected?"""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        checks = {}

        # Database check
        try:
            from django.db import connection

            connection.ensure_connection()
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "error"

        # Redis / Celery broker check
        try:
            from django.conf import settings as django_settings
            import redis

            redis_client = redis.from_url(django_settings.CELERY_BROKER_URL)
            redis_client.ping()
            checks["redis"] = "ok"
        except Exception:
            checks["redis"] = "error"

        # Celery worker check
        try:
            from config.celery import app

            insp = app.control.inspect(timeout=3)
            stats = insp.ping()
            checks["celery"] = "ok" if stats else "no_workers"
        except Exception:
            checks["celery"] = "error"

        all_ok = all(v in ("ok", "no_workers") for v in checks.values())
        status_code = 200 if all_ok else 503

        return Response(
            {"status": "ready" if all_ok else "degraded", "checks": checks},
            status=status_code,
        )


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health checks (public)
    path("api/v1/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/health/ready/", ReadinessCheckView.as_view(), name="readiness-check"),
    # App routers (auth required except public endpoints)
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/onboarding/", include("clinics.urls")),
    path("api/v1/clinics/", include(clinics_router.urls)),
    path("api/v1/patients/", include("patients.urls")),
    path("api/v1/appointments/", include("appointments.urls")),
    path("api/v1/invoices/", include("invoicing.urls")),
    path("api/v1/fiscal-config/", include("invoicing.urls_fiscal")),
    path("api/v1/whatsapp/", include("notifications.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),
    path("api/v1/inventory/", include("inventory.urls")),
]

# Serve media files in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
