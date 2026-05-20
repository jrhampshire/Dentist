"""
Unit tests for stock_service.py (Task 12.6).

Tests:
- Stock adjustment logic
- Low stock detection
- Expiration detection
- Kit consumption
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from inventory.models import InventoryItem, InventoryMovement
from inventory.services.stock_service import (
    adjust_stock,
    consume_kit,
    get_expired_items,
    get_expiring_items,
    get_low_stock_items,
    mark_expired_items,
)


@pytest.mark.integration
@pytest.mark.django_db
class TestAdjustStock:
    """Test stock adjustment."""

    def test_increase_stock(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("100.00"))

        movement = adjust_stock(item, Decimal("50.00"), note="Reabastecimiento")

        item.refresh_from_db()
        assert item.stock_current == Decimal("150.00")
        assert movement.quantity == Decimal("50.00")
        assert movement.previous_stock == Decimal("100.00")
        assert movement.new_stock == Decimal("150.00")

    def test_decrease_stock(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("100.00"))

        movement = adjust_stock(item, Decimal("-30.00"), note="Salida")

        item.refresh_from_db()
        assert item.stock_current == Decimal("70.00")
        assert movement.quantity == Decimal("-30.00")

    def test_insufficient_stock_raises(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("10.00"))

        with pytest.raises(ValueError, match="Stock insuficiente"):
            adjust_stock(item, Decimal("-20.00"))

    def test_blocked_item_raises(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, is_active=True)
        item.is_blocked = True
        item.save()

        with pytest.raises(ValueError, match="bloqueado"):
            adjust_stock(item, Decimal("10.00"))

    def test_expired_item_cannot_decrease(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("50.00"))
        item.is_expired = True
        item.save()

        with pytest.raises(ValueError, match="expirado"):
            adjust_stock(item, Decimal("-10.00"))

    def test_expired_item_can_increase(self, create_clinic, create_inventory_item):
        """Expired items can still receive stock (e.g., correction)."""
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("50.00"))
        item.is_expired = True
        item.save()

        movement = adjust_stock(item, Decimal("10.00"), note="Correction")
        item.refresh_from_db()
        assert item.stock_current == Decimal("60.00")

    def test_creates_movement_record(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("100.00"))

        adjust_stock(
            item,
            Decimal("25.00"),
            movement_type=InventoryMovement.MovementType.IN,
            note="Compra",
            reference_type="purchase_order",
            reference_id="PO-001",
        )

        movement = InventoryMovement.objects.get(item=item)
        assert movement.movement_type == InventoryMovement.MovementType.IN
        assert movement.note == "Compra"
        assert movement.reference_type == "purchase_order"
        assert movement.reference_id == "PO-001"


@pytest.mark.integration
@pytest.mark.django_db
class TestConsumeKit:
    """Test kit consumption."""

    def test_consume_kit_deducts_stock(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        item1 = create_inventory_item(
            clinic=clinic, name="Guantes", stock_current=Decimal("100.00")
        )
        item2 = create_inventory_item(
            clinic=clinic, name="Mascarillas", stock_current=Decimal("200.00")
        )

        kit = [
            {"item_id": str(item1.pk), "quantity": 2},
            {"item_id": str(item2.pk), "quantity": 5},
        ]

        movements = consume_kit(
            clinic_id=str(clinic.pk),
            kit=kit,
            appointment_id="appt-001",
        )

        assert len(movements) == 2

        item1.refresh_from_db()
        assert item1.stock_current == Decimal("98.00")

        item2.refresh_from_db()
        assert item2.stock_current == Decimal("195.00")

    def test_consume_kit_insufficient_stock_raises(
        self, create_clinic, create_inventory_item
    ):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("1.00"))

        kit = [{"item_id": str(item.pk), "quantity": 5}]

        with pytest.raises(ValueError, match="Stock insuficiente"):
            consume_kit(clinic_id=str(clinic.pk), kit=kit, appointment_id="appt-001")

    def test_consume_kit_blocked_item_raises(
        self, create_clinic, create_inventory_item
    ):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("100.00"))
        item.is_blocked = True
        item.save()

        kit = [{"item_id": str(item.pk), "quantity": 1}]

        with pytest.raises(ValueError, match="bloqueado"):
            consume_kit(clinic_id=str(clinic.pk), kit=kit, appointment_id="appt-001")

    def test_consume_kit_expired_item_raises(
        self, create_clinic, create_inventory_item
    ):
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic, stock_current=Decimal("100.00"))
        item.is_expired = True
        item.save()

        kit = [{"item_id": str(item.pk), "quantity": 1}]

        with pytest.raises(ValueError, match="expirado"):
            consume_kit(clinic_id=str(clinic.pk), kit=kit, appointment_id="appt-001")


@pytest.mark.integration
@pytest.mark.django_db
class TestLowStockDetection:
    """Test low stock alerts."""

    def test_finds_items_below_minimum(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        low_item = create_inventory_item(
            clinic=clinic,
            name="Low Stock Item",
            stock_current=Decimal("5.00"),
            stock_minimum=Decimal("20.00"),
        )
        ok_item = create_inventory_item(
            clinic=clinic,
            name="OK Item",
            stock_current=Decimal("100.00"),
            stock_minimum=Decimal("20.00"),
        )

        low_stock = get_low_stock_items(str(clinic.pk))

        assert low_item in low_stock
        assert ok_item not in low_stock

    def test_empty_when_no_low_stock(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        create_inventory_item(
            clinic=clinic,
            stock_current=Decimal("100.00"),
            stock_minimum=Decimal("20.00"),
        )

        assert get_low_stock_items(str(clinic.pk)).count() == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestExpirationDetection:
    """Test expiration alerts."""

    def test_finds_expiring_items(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        expiring_soon = create_inventory_item(
            clinic=clinic,
            name="Expiring Soon",
            expiration_date=date.today() + timedelta(days=15),
        )
        not_expiring = create_inventory_item(
            clinic=clinic,
            name="Not Expiring",
            expiration_date=date.today() + timedelta(days=90),
        )

        expiring = get_expiring_items(str(clinic.pk), days_ahead=30)

        assert expiring_soon in expiring
        assert not_expiring not in expiring

    def test_finds_expired_items(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        expired = create_inventory_item(
            clinic=clinic,
            name="Already Expired",
            expiration_date=date.today() - timedelta(days=5),
        )

        expired_items = get_expired_items(str(clinic.pk))

        assert expired in expired_items

    def test_does_not_return_already_marked_expired(
        self, create_clinic, create_inventory_item
    ):
        clinic = create_clinic()
        item = create_inventory_item(
            clinic=clinic,
            expiration_date=date.today() - timedelta(days=5),
        )
        item.is_expired = True
        item.save()

        assert get_expired_items(str(clinic.pk)).count() == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestMarkExpiredItems:
    """Test marking expired items."""

    def test_marks_expired_items(self, create_clinic, create_inventory_item):
        clinic = create_clinic()
        expired_item = create_inventory_item(
            clinic=clinic,
            name="Expired",
            expiration_date=date.today() - timedelta(days=1),
        )
        valid_item = create_inventory_item(
            clinic=clinic,
            name="Valid",
            expiration_date=date.today() + timedelta(days=30),
        )

        count = mark_expired_items(clinic=clinic)

        assert count == 1
        expired_item.refresh_from_db()
        assert expired_item.is_expired is True
        assert expired_item.is_blocked is True

        valid_item.refresh_from_db()
        assert valid_item.is_expired is False

    def test_returns_zero_when_nothing_to_mark(
        self, create_clinic, create_inventory_item
    ):
        clinic = create_clinic()
        create_inventory_item(
            clinic=clinic,
            expiration_date=date.today() + timedelta(days=30),
        )

        count = mark_expired_items(clinic=clinic)
        assert count == 0
