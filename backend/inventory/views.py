"""
Inventory Tracking views.

ViewSets:
- InventoryItemViewSet: CRUD for inventory items + adjust action
- InventoryMovementViewSet: List movements (read-only)

Custom endpoints:
- InventoryAlertView: GET /api/v1/inventory/alerts/ — low stock + expiration alerts
- CategoriesView: GET /api/v1/inventory/categories/ — list available categories
"""

from datetime import date, timedelta
from decimal import Decimal

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import InventoryItem, InventoryMovement
from inventory.serializers import (
    AdjustmentSerializer,
    InventoryAlertSerializer,
    InventoryItemCreateSerializer,
    InventoryItemSerializer,
    InventoryMovementSerializer,
)
from inventory.services.stock_service import (
    adjust_stock,
    get_expiring_items,
    get_low_stock_items,
)


# ---------------------------------------------------------------------------
# InventoryItemViewSet
# ---------------------------------------------------------------------------


class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for inventory items.

    Endpoints:
    - GET    /api/v1/inventory/items/               — list items
    - POST   /api/v1/inventory/items/               — create item
    - GET    /api/v1/inventory/items/{id}/          — get item detail
    - PATCH  /api/v1/inventory/items/{id}/          — update item
    - DELETE /api/v1/inventory/items/{id}/          — delete item
    - POST   /api/v1/inventory/items/{id}/adjust/   — adjust stock

    Filtering:
    - ?category=material: Filter by category
    - ?is_low_stock=true: Filter low stock items
    - ?is_expired=true: Filter expired items
    - ?search=name: Search by name or barcode
    """

    permission_classes = [IsAuthenticated]
    ordering_fields = ["name", "stock_current", "expiration_date", "updated_at"]
    ordering = ["name"]
    search_fields = ["name", "barcode", "sku"]

    def get_queryset(self):
        """Return inventory items for the current clinic (RLS handles isolation)."""
        queryset = InventoryItem.objects.filter(is_active=True).select_related(
            "clinic", "created_by"
        )

        # Apply filters
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        is_low_stock = self.request.query_params.get("is_low_stock")
        if is_low_stock and is_low_stock.lower() == "true":
            queryset = queryset.filter(stock_current__lt=InventoryItem.stock_minimum)

        is_expired = self.request.query_params.get("is_expired")
        if is_expired and is_expired.lower() == "true":
            queryset = queryset.filter(is_expired=True)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return InventoryItemCreateSerializer
        return InventoryItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=True, methods=["post"], url_path="adjust")
    def adjust(self, request, *args, **kwargs):
        """
        Adjust stock for an inventory item.

        Body:
        - quantity: Decimal (positive = add, negative = remove)
        - note: Optional reason for adjustment

        Creates an InventoryMovement record for audit trail.
        """
        item = self.get_object()
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = Decimal(str(serializer.validated_data["quantity"]))
        note = serializer.validated_data.get("note", "")

        # Determine movement type based on quantity sign
        if quantity > 0:
            movement_type = InventoryMovement.MovementType.IN
        else:
            movement_type = InventoryMovement.MovementType.OUT

        try:
            movement = adjust_stock(
                item=item,
                quantity=quantity,
                movement_type=movement_type,
                note=note,
                user=request.user,
                reference_type="manual",
                reference_id="",
            )

            return Response(
                {
                    "item_id": str(item.id),
                    "previous_stock": str(movement.previous_stock),
                    "new_stock": str(movement.new_stock),
                    "movement_type": movement.movement_type,
                    "quantity": str(movement.quantity),
                    "note": movement.note,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response(
                {"error": "adjustment_failed", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# InventoryMovementViewSet
# ---------------------------------------------------------------------------


class InventoryMovementViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for inventory movements (read-only audit trail).

    Endpoints:
    - GET    /api/v1/inventory/movements/           — list movements
    - GET    /api/v1/inventory/movements/{id}/      — get movement detail

    Filtering:
    - ?item_id=uuid: Filter by item
    - ?movement_type=in: Filter by type
    - ?date_from=YYYY-MM-DD: Filter from date
    - ?date_to=YYYY-MM-DD: Filter to date
    """

    permission_classes = [IsAuthenticated]
    serializer_class = InventoryMovementSerializer
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return movements for the current clinic."""
        queryset = InventoryMovement.objects.all().select_related(
            "item", "clinic", "created_by"
        )

        # Apply filters
        item_id = self.request.query_params.get("item_id")
        if item_id:
            queryset = queryset.filter(item_id=item_id)

        movement_type = self.request.query_params.get("movement_type")
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset


# ---------------------------------------------------------------------------
# InventoryAlertView
# ---------------------------------------------------------------------------


class InventoryAlertView(APIView):
    """
    Custom endpoint for inventory alerts.

    GET /api/v1/inventory/alerts/?days=30

    Returns:
    - low_stock: Items below minimum threshold
    - expiring_soon: Items expiring within N days (default: 30)
    - expired: Items already expired
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        clinic_id = getattr(request, "clinic_id", None)

        if not clinic_id:
            return Response(
                {"error": "no_clinic", "message": "No se pudo determinar la clínica."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alerts = []

        # Low stock alerts
        low_stock_items = get_low_stock_items(clinic_id=str(clinic_id))
        for item in low_stock_items:
            alerts.append(
                {
                    "item_id": str(item.id),
                    "item_name": item.name,
                    "category": item.category,
                    "category_display": item.get_category_display(),
                    "stock_current": str(item.stock_current),
                    "stock_minimum": str(item.stock_minimum),
                    "is_low_stock": True,
                    "is_expired": item.is_expired,
                    "is_blocked": item.is_blocked,
                    "expiration_date": item.expiration_date,
                    "days_until_expiration": item.days_until_expiration,
                    "alert_type": "low_stock",
                }
            )

        # Expiring soon alerts
        expiring_items = get_expiring_items(clinic_id=str(clinic_id), days_ahead=days)
        for item in expiring_items:
            alerts.append(
                {
                    "item_id": str(item.id),
                    "item_name": item.name,
                    "category": item.category,
                    "category_display": item.get_category_display(),
                    "stock_current": str(item.stock_current),
                    "stock_minimum": str(item.stock_minimum),
                    "is_low_stock": item.is_low_stock,
                    "is_expired": item.is_expired,
                    "is_blocked": item.is_blocked,
                    "expiration_date": item.expiration_date,
                    "days_until_expiration": item.days_until_expiration,
                    "alert_type": "expiring_soon",
                }
            )

        # Already expired alerts
        today = date.today()
        expired_items = InventoryItem.objects.filter(
            clinic_id=clinic_id,
            is_active=True,
            is_expired=True,
        )
        for item in expired_items:
            alerts.append(
                {
                    "item_id": str(item.id),
                    "item_name": item.name,
                    "category": item.category,
                    "category_display": item.get_category_display(),
                    "stock_current": str(item.stock_current),
                    "stock_minimum": str(item.stock_minimum),
                    "is_low_stock": item.is_low_stock,
                    "is_expired": True,
                    "is_blocked": item.is_blocked,
                    "expiration_date": item.expiration_date,
                    "days_until_expiration": item.days_until_expiration,
                    "alert_type": "expired",
                }
            )

        return Response(
            {
                "alerts": alerts,
                "total_alerts": len(alerts),
                "days_ahead": days,
            }
        )


# ---------------------------------------------------------------------------
# CategoriesView
# ---------------------------------------------------------------------------


class CategoriesView(APIView):
    """
    Custom endpoint to list available inventory categories.

    GET /api/v1/inventory/categories/

    Returns the list of category choices with their display names.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = [
            {"value": choice[0], "label": choice[1]}
            for choice in InventoryItem.Category.choices
        ]
        return Response({"categories": categories})
