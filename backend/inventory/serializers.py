"""
Inventory Tracking serializers.

Serializers:
- InventoryItemSerializer: Full read serializer for inventory items
- InventoryItemCreateSerializer: Creation/update with clinic injection
- InventoryMovementSerializer: Movement audit trail (read-only)
- AdjustmentSerializer: Stock adjustment input
- InventoryAlertSerializer: Low stock / expiration alerts
"""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from inventory.models import InventoryItem, InventoryMovement


# ---------------------------------------------------------------------------
# InventoryItem Serializers
# ---------------------------------------------------------------------------


class InventoryItemSerializer(serializers.ModelSerializer):
    """Full serializer for reading inventory items."""

    category_display = serializers.SerializerMethodField()
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "clinic",
            "name",
            "description",
            "sku",
            "category",
            "category_display",
            "unit",
            "stock_current",
            "stock_minimum",
            "stock_maximum",
            "expiration_date",
            "batch_number",
            "is_expired",
            "is_blocked",
            "is_active",
            "is_low_stock",
            "is_out_of_stock",
            "days_until_expiration",
            "unit_price",
            "cost",
            "price",
            "supplier",
            "supplier_sku",
            "barcode",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "clinic",
            "is_expired",
            "created_at",
            "updated_at",
        ]

    def get_category_display(self, obj: InventoryItem) -> str:
        return obj.get_category_display()


class InventoryItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating inventory items."""

    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "description",
            "sku",
            "category",
            "unit",
            "stock_current",
            "stock_minimum",
            "stock_maximum",
            "expiration_date",
            "batch_number",
            "unit_price",
            "cost",
            "price",
            "supplier",
            "supplier_sku",
            "barcode",
            "is_blocked",
            "is_active",
        ]

    def validate_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es obligatorio.")
        return value.strip()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for stock levels."""
        stock_min = data.get("stock_minimum", 0)
        stock_max = data.get("stock_maximum", 0)

        if stock_max and stock_max < stock_min:
            raise serializers.ValidationError(
                {"stock_maximum": "El stock máximo debe ser mayor o igual al mínimo."}
            )

        return data

    def create(self, validated_data: dict[str, Any]) -> InventoryItem:
        """Create inventory item with clinic from JWT context."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError(
                "No se pudo determinar la clínica. Contacte al administrador."
            )

        from clinics.models import Clinic

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError("Clínica no encontrada.")

        validated_data["clinic"] = clinic
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        return super().create(validated_data)


# ---------------------------------------------------------------------------
# InventoryMovement Serializer
# ---------------------------------------------------------------------------


class InventoryMovementSerializer(serializers.ModelSerializer):
    """Read-only serializer for inventory movements."""

    movement_type_display = serializers.SerializerMethodField()
    item_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "item",
            "item_name",
            "clinic",
            "movement_type",
            "movement_type_display",
            "quantity",
            "previous_stock",
            "new_stock",
            "reference_type",
            "reference_id",
            "note",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_movement_type_display(self, obj: InventoryMovement) -> str:
        return obj.get_movement_type_display()

    def get_item_name(self, obj: InventoryMovement) -> str:
        return obj.item.name

    def get_created_by_name(self, obj: InventoryMovement) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


# ---------------------------------------------------------------------------
# Adjustment Serializer
# ---------------------------------------------------------------------------


class AdjustmentSerializer(serializers.Serializer):
    """
    Serializer for stock adjustments.

    Allows manual correction of stock levels with audit trail.
    """

    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Quantity to adjust (positive = add, negative = remove)",
    )
    note = serializers.CharField(
        max_length=500,
        required=False,
        default="",
        help_text="Reason for the adjustment",
    )

    def validate_quantity(self, value: Decimal) -> Decimal:
        """Quantity cannot be zero."""
        if value == 0:
            raise serializers.ValidationError(
                "La cantidad no puede ser cero. Use un valor positivo o negativo."
            )
        return value


# ---------------------------------------------------------------------------
# InventoryAlert Serializer
# ---------------------------------------------------------------------------


class InventoryAlertSerializer(serializers.Serializer):
    """Serializer for inventory alerts (low stock + expiration)."""

    item_id = serializers.UUIDField()
    item_name = serializers.CharField()
    category = serializers.CharField()
    category_display = serializers.CharField()
    stock_current = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock_minimum = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_low_stock = serializers.BooleanField()
    is_expired = serializers.BooleanField()
    is_blocked = serializers.BooleanField()
    expiration_date = serializers.DateField(allow_null=True)
    days_until_expiration = serializers.IntegerField(allow_null=True)
    alert_type = serializers.CharField(
        help_text="Type of alert: 'low_stock', 'expiring_soon', 'expired'"
    )
