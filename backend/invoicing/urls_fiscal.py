"""CFDI Fiscal Config URL routes — /api/v1/fiscal-config/*"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from invoicing.views import FiscalConfigViewSet

router = DefaultRouter()
router.register(r"", FiscalConfigViewSet, basename="fiscal-config")

urlpatterns = [
    path("", include(router.urls)),
]
