"""CFDI Invoicing URL routes — /api/v1/invoices/*"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from invoicing.views import InvoiceViewSet

router = DefaultRouter()
router.register(r"", InvoiceViewSet, basename="invoices")

urlpatterns = [
    path("", include(router.urls)),
]
