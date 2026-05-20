"""
Inventory stock management service.

Functions:
- adjust_stock: Manual stock adjustment with audit trail
- consume_kit: Auto-consume inventory kit from appointment type
- get_low_stock_items: Detect items below minimum threshold
- get_expiring_items: Detect items approaching expiration
- get_expired_items: Detect already expired items
- mark_expired_items: Mark expired items and block them
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

from inventory.models import InventoryItem, InventoryMovement

logger = logging.getLogger("invoicing.services")


# ---------------------------------------------------------------------------
# Stock Adjustment
# ---------------------------------------------------------------------------


def adjust_stock(
    item: InventoryItem,
    quantity,
    movement_type: str = InventoryMovement.MovementType.ADJUSTMENT,
    note: str = "",
    user=None,
    reference_type: str = "",
    reference_id: str = "",
) -> InventoryMovement:
    """
    Adjust stock for an inventory item.

    Args:
        item: The InventoryItem to adjust
        quantity: Signed quantity (positive = add, negative = remove)
        movement_type: Type of movement (adjustment, in, out, consumption, return)
        note: Reason for the adjustment
        user: User performing the adjustment
        reference_type: What triggered this (e.g., 'appointment', 'manual')
        reference_id: ID of the triggering object

    Returns:
        The created InventoryMovement record

    Raises:
        ValueError: If item is blocked/expired or insufficient stock
    """
    if item.is_blocked:
        raise ValueError(f"El item '{item.name}' está bloqueado.")
    if item.is_expired and Decimal(str(quantity)) < 0:
        raise ValueError(f"El item '{item.name}' está expirado.")

    new_stock = item.stock_current + Decimal(str(quantity))

    if new_stock < 0:
        raise ValueError(
            f"Stock insuficiente para '{item.name}': "
            f"disponible={item.stock_current}, requerido={abs(quantity)}"
        )

    with transaction.atomic():
        previous_stock = item.stock_current
        item.stock_current = new_stock
        item.save(update_fields=["stock_current", "updated_at"])

        movement = InventoryMovement.objects.create(
            item=item,
            clinic=item.clinic,
            movement_type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            note=note,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=user,
        )

    return movement


# ---------------------------------------------------------------------------
# Auto-Consumption from Appointment Kits
# ---------------------------------------------------------------------------


def consume_kit(
    clinic_id: str,
    kit: list[dict[str, Any]],
    appointment_id: str,
    user=None,
) -> list[InventoryMovement]:
    """
    Auto-consume inventory items from an appointment type's inventory_kit.

    The kit format is: [{"item_id": "uuid", "quantity": 2}, ...]

    Args:
        clinic_id: Clinic UUID for tenant isolation
        kit: List of {item_id, quantity} dicts
        appointment_id: The appointment that triggered consumption
        user: User performing the consumption

    Returns:
        List of created InventoryMovement records

    Raises:
        ValueError: If any item is unavailable, blocked, or expired
    """
    movements = []

    with transaction.atomic():
        for kit_item in kit:
            item_id = kit_item.get("item_id")
            quantity = Decimal(str(kit_item.get("quantity", 0)))

            if not item_id or quantity <= 0:
                continue

            try:
                item = InventoryItem.objects.select_for_update().get(
                    id=item_id, clinic_id=clinic_id, is_active=True
                )
            except InventoryItem.DoesNotExist:
                raise ValueError(f"Item de inventario no encontrado: {item_id}")

            if item.is_blocked:
                raise ValueError(
                    f"El item '{item.name}' está bloqueado y no puede consumirse."
                )

            if item.is_expired:
                raise ValueError(
                    f"El item '{item.name}' está expirado y no puede consumirse."
                )

            if item.stock_current < quantity:
                raise ValueError(
                    f"Stock insuficiente para '{item.name}': "
                    f"disponible={item.stock_current}, requerido={quantity}"
                )

            movement = adjust_stock(
                item=item,
                quantity=-quantity,  # Negative for consumption
                movement_type=InventoryMovement.MovementType.CONSUMPTION,
                note=f"Consumo automático por cita {appointment_id}",
                user=user,
                reference_type="appointment",
                reference_id=str(appointment_id),
            )
            movements.append(movement)

    logger.info(
        f"Consumed inventory kit for clinic {clinic_id}: "
        f"{len(movements)} items for appointment {appointment_id}"
    )
    return movements


# ---------------------------------------------------------------------------
# Low Stock Detection
# ---------------------------------------------------------------------------


def get_low_stock_items(clinic_id: str):
    """
    Get all items where current stock is below minimum threshold.

    Args:
        clinic_id: Clinic UUID for tenant isolation

    Returns:
        QuerySet of InventoryItem objects with low stock
    """
    return InventoryItem.objects.filter(
        clinic_id=clinic_id,
        is_active=True,
        stock_current__lt=F("stock_minimum"),
    ).order_by("stock_current")


# ---------------------------------------------------------------------------
# Expiration Detection
# ---------------------------------------------------------------------------


def get_expiring_items(clinic_id: str, days_ahead: int = 30):
    """
    Get items expiring within the next N days.

    Args:
        clinic_id: Clinic UUID for tenant isolation
        days_ahead: Number of days to look ahead (default: 30)

    Returns:
        QuerySet of InventoryItem objects expiring soon
    """
    today = date.today()
    threshold = today + timedelta(days=days_ahead)

    return InventoryItem.objects.filter(
        clinic_id=clinic_id,
        is_active=True,
        is_expired=False,
        expiration_date__isnull=False,
        expiration_date__lte=threshold,
        expiration_date__gte=today,
    ).order_by("expiration_date")


def get_expired_items(clinic_id: str):
    """
    Get items that are already expired but not yet marked.

    Args:
        clinic_id: Clinic UUID for tenant isolation

    Returns:
        QuerySet of expired InventoryItem objects not yet marked
    """
    return InventoryItem.objects.filter(
        clinic_id=clinic_id,
        is_active=True,
        expiration_date__isnull=False,
        expiration_date__lt=date.today(),
        is_expired=False,
    ).order_by("expiration_date")


def _mark_expired_items(clinic_id: str) -> int:
    """
    Mark all expired items as expired and blocked for a specific clinic.

    Args:
        clinic_id: Clinic UUID for tenant isolation

    Returns:
        Number of items marked as expired
    """
    count = InventoryItem.objects.filter(
        clinic_id=clinic_id,
        is_active=True,
        expiration_date__isnull=False,
        expiration_date__lte=date.today(),
        is_expired=False,
    ).update(is_expired=True, is_blocked=True, updated_at=timezone.now())

    if count:
        logger.info(f"Marked {count} inventory items as expired for clinic {clinic_id}")

    return count


# ---------------------------------------------------------------------------
# Wrapper functions for Celery tasks (clinic-agnostic)
# ---------------------------------------------------------------------------


def get_items_expiring_within(days: int = 30, clinic=None):
    """
    Find inventory items expiring within the given number of days.

    Args:
        days: Number of days to look ahead
        clinic: Optional Clinic instance for filtering

    Returns:
        QuerySet of InventoryItem instances
    """
    if clinic:
        return get_expiring_items(clinic_id=str(clinic.id))
    # Without clinic filter, return for all clinics (admin use)
    today = date.today()
    threshold = today + timedelta(days=days)
    return (
        InventoryItem.objects.filter(
            is_active=True,
            is_expired=False,
            expiration_date__isnull=False,
            expiration_date__lte=threshold,
            expiration_date__gte=today,
        )
        .order_by("expiration_date")
        .select_related("clinic")
    )


def get_items_below_minimum(clinic=None):
    """
    Find inventory items with stock below their minimum threshold.

    Args:
        clinic: Optional Clinic instance for filtering

    Returns:
        QuerySet of InventoryItem instances
    """
    if clinic:
        return get_low_stock_items(clinic_id=str(clinic.id))
    return (
        InventoryItem.objects.filter(
            is_active=True,
            stock_current__lt=F("stock_minimum"),
        )
        .order_by("stock_current")
        .select_related("clinic")
    )


def mark_expired_items(clinic=None) -> int:
    """
    Mark items past their expiration date as expired and blocked.

    Args:
        clinic: Optional Clinic instance for filtering

    Returns:
        Number of items marked as expired
    """
    if clinic:
        return _mark_expired_items(str(clinic.id))
    # Mark for all clinics
    count = InventoryItem.objects.filter(
        is_active=True,
        expiration_date__isnull=False,
        expiration_date__lte=date.today(),
        is_expired=False,
    ).update(is_expired=True, is_blocked=True, updated_at=timezone.now())

    if count:
        logger.info(f"Marked {count} inventory items as expired (all clinics)")

    return count


def consume_inventory_kit(kit: list[dict], clinic_id: str, reason: str = "") -> bool:
    """
    Consume all items in an inventory kit (wrapper for Celery tasks).

    Args:
        kit: List of {"item_id": uuid, "quantity": int} dicts
        clinic_id: Clinic UUID for tenant isolation
        reason: Reason for consumption

    Returns:
        True if all items were consumed

    Raises:
        ValueError if any item has insufficient stock or is blocked
    """
    # We need an appointment_id for the reference — use a synthetic one
    from uuid import uuid4

    appointment_id = str(uuid4())
    movements = consume_kit(
        clinic_id=clinic_id,
        kit=kit,
        appointment_id=appointment_id,
        user=None,
    )
    return len(movements) > 0 or len(kit) == 0
