"""
Inventory models for ClínicaSaaS Dental MX.

Models:
- InventoryItem: Dental supplies and materials with stock tracking, expiration dates, and minimum stock alerts
- InventoryMovement: Audit trail for all stock changes (in/out/adjustment)

All models enforce tenant isolation via clinic FK + RLS.
"""

import uuid
from datetime import date, timedelta
from typing import Any

from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# InventoryItem Model
# ---------------------------------------------------------------------------


class InventoryItem(models.Model):
    """
    Dental inventory item (supplies, materials, equipment).

    Tracks stock levels, expiration dates, and minimum stock thresholds.
    Supports auto-consumption via inventory_kit on appointment completion.
    """

    class Category(models.TextChoices):
        MATERIAL = "material", "Material"
        SUPPLY = "supply", "Insumo"
        INSTRUMENT = "instrument", "Instrumento"
        MEDICATION = "medication", "Medicamento"
        LAB = "lab", "Laboratorio"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        LOW_STOCK = "low_stock", "Stock bajo"
        OUT_OF_STOCK = "out_of_stock", "Sin stock"
        EXPIRED = "expired", "Expirado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    sku = models.CharField(max_length=50, blank=True, default="", db_index=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SUPPLY,
        db_index=True,
    )

    # Unit of measure
    unit = models.CharField(
        max_length=20,
        default="pieza",
        help_text="Unit of measure (pieza, caja, ml, gr, etc.)",
    )

    # Stock levels
    stock_current = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current stock quantity",
    )
    stock_minimum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum stock level — triggers alert when below",
    )
    stock_maximum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Maximum stock level (optional reorder cap)",
    )

    # Expiration tracking
    expiration_date = models.DateField(blank=True, null=True, db_index=True)
    batch_number = models.CharField(max_length=100, blank=True, default="")
    is_expired = models.BooleanField(default=False, db_index=True)
    is_blocked = models.BooleanField(
        default=False,
        help_text="Blocked items cannot be used or consumed",
    )
    is_active = models.BooleanField(default=True)

    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Unit cost from supplier",
    )
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Supplier info
    supplier = models.CharField(max_length=200, blank=True, default="")
    supplier_sku = models.CharField(max_length=50, blank=True, default="")

    # Barcode
    barcode = models.CharField(max_length=100, blank=True, default="", db_index=True)

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_inventory_items",
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_items"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "category"], name="idx_inv_category"),
            models.Index(fields=["clinic", "is_active"], name="idx_inv_active"),
            models.Index(
                fields=["clinic", "stock_current", "stock_minimum"],
                name="idx_inv_stock_levels",
            ),
            models.Index(fields=["clinic", "is_expired"], name="idx_inv_expired"),
            models.Index(
                fields=["clinic", "expiration_date"],
                name="idx_inv_expiration",
            ),
        ]
        constraints = [
            # stock_current cannot be negative
            models.CheckConstraint(
                check=models.Q(stock_current__gte=0),
                name="chk_stock_current_non_negative",
            ),
            # stock_minimum must be >= 0
            models.CheckConstraint(
                check=models.Q(stock_minimum__gte=0),
                name="chk_stock_minimum_non_negative",
            ),
        ]

    def __str__(self) -> str:
        status = ""
        if self.is_blocked:
            status = "[BLOQUEADO] "
        elif self.is_expired:
            status = "[VENCIDO] "
        return f"{status}{self.name} ({self.stock_current} {self.unit})"

    @property
    def is_low_stock(self) -> bool:
        """Check if current stock is below minimum threshold."""
        return self.stock_current < self.stock_minimum

    @property
    def is_out_of_stock(self) -> bool:
        """Check if item is out of stock."""
        return self.stock_current == 0

    @property
    def days_until_expiration(self) -> int | None:
        """Return days until expiration, or None if no expiration date."""
        if not self.expiration_date:
            return None
        return (self.expiration_date - date.today()).days

    def mark_expired(self) -> None:
        """Mark this item as expired."""
        if self.expiration_date and self.expiration_date <= date.today():
            self.is_expired = True
            self.save(update_fields=["is_expired", "updated_at"])

    def deduct_stock(self, quantity, reason="") -> None:
        """Deduct stock quantity. Raises ValueError if insufficient stock."""
        from decimal import Decimal

        if self.is_blocked:
            raise ValueError(f"El item '{self.name}' está bloqueado y no puede usarse.")
        if self.is_expired:
            raise ValueError(f"El item '{self.name}' está expirado y no puede usarse.")
        if self.stock_current < Decimal(str(quantity)):
            raise ValueError(
                f"Stock insuficiente para '{self.name}': "
                f"disponible={self.stock_current}, requerido={quantity}"
            )

        previous = self.stock_current
        self.stock_current -= Decimal(str(quantity))
        self.save(update_fields=["stock_current", "updated_at"])

        # Log the movement
        InventoryMovement.objects.create(
            item=self,
            clinic=self.clinic,
            movement_type=InventoryMovement.MovementType.OUT,
            quantity=quantity,
            previous_stock=previous,
            new_stock=self.stock_current,
            note=reason or "Consumo por cita",
        )

    def add_stock(self, quantity, reason="") -> None:
        """Add stock quantity."""
        from decimal import Decimal

        previous = self.stock_current
        self.stock_current += Decimal(str(quantity))
        self.save(update_fields=["stock_current", "updated_at"])

        # Log the movement
        InventoryMovement.objects.create(
            item=self,
            clinic=self.clinic,
            movement_type=InventoryMovement.MovementType.IN,
            quantity=quantity,
            previous_stock=previous,
            new_stock=self.stock_current,
            note=reason or "Reabastecimiento",
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-update expiration flags on save."""
        # Check expiration
        if self.expiration_date and self.expiration_date <= date.today():
            self.is_expired = True
            self.is_blocked = True

        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# InventoryMovement Model
# ---------------------------------------------------------------------------


class InventoryMovement(models.Model):
    """
    Audit trail for inventory stock changes.

    Every stock change (in, out, adjustment, consumption) is logged here
    for traceability. Includes stock snapshots (previous/new) for auditing.
    """

    class MovementType(models.TextChoices):
        IN = "in", "Entrada"
        OUT = "out", "Salida"
        ADJUSTMENT = "adjustment", "Ajuste"
        CONSUMPTION = "consumption", "Consumo automático"
        RETURN = "return", "Devolución"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="inventory_movements",
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )

    # Movement details
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Signed quantity: positive for in, negative for out",
    )

    # Stock snapshot
    previous_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Stock before this movement",
    )
    new_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Stock after this movement",
    )

    # Reference (what triggered this movement)
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Type of reference (appointment, manual, purchase_order)",
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="ID of the reference object",
    )

    note = models.TextField(blank=True, default="")

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_inventory_movements",
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "item"], name="idx_mov_item"),
            models.Index(fields=["clinic", "movement_type"], name="idx_mov_type"),
            models.Index(
                fields=["clinic", "reference_type", "reference_id"],
                name="idx_mov_reference",
            ),
            models.Index(fields=["clinic", "created_at"], name="idx_mov_created"),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_movement_type_display()}] {self.item.name} — "
            f"{self.quantity:+.2f} ({self.previous_stock} → {self.new_stock})"
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensure quantity sign matches movement type."""
        from decimal import Decimal

        if self.movement_type in (
            self.MovementType.IN,
            self.MovementType.ADJUSTMENT,
            self.MovementType.RETURN,
        ):
            self.quantity = abs(Decimal(str(self.quantity)))
        elif self.movement_type in (
            self.MovementType.OUT,
            self.MovementType.CONSUMPTION,
        ):
            self.quantity = -abs(Decimal(str(self.quantity)))
        super().save(*args, **kwargs)
