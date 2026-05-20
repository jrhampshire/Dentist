"""Inventory Tracking URL routes — /api/v1/inventory/*"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory.views import (
    CategoriesView,
    InventoryAlertView,
    InventoryItemViewSet,
    InventoryMovementViewSet,
)

# Router for inventory resources
router = DefaultRouter()
router.register(r"items", InventoryItemViewSet, basename="inventory-items")
router.register(r"movements", InventoryMovementViewSet, basename="inventory-movements")

urlpatterns = [
    path("", include(router.urls)),
    path("alerts/", InventoryAlertView.as_view(), name="inventory-alerts"),
    path("categories/", CategoriesView.as_view(), name="inventory-categories"),
]
