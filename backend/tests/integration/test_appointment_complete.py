"""
Integration tests for the appointment complete endpoint (Slice A — inventario-consumo-automatico).

Tests:
- 4.1 Complete appointment with kit → stock deducted
- 4.2 Complete appointment without kit → no-op
- 4.3 Complete twice → idempotent (400)
- 4.4 Insufficient stock → 400 with details
- 4.5 Invalid status → 400
"""

from datetime import date, time

import pytest
from rest_framework.test import APIClient

from appointments.models import Appointment


# ---------------------------------------------------------------------------
# 4.1 Happy path — kit consumption deducts stock
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteAppointmentWithKit:
    """Test the complete endpoint with a non-empty inventory kit."""

    def test_complete_with_kit_deducts_stock(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_inventory_item,
        create_appointment,
        auth_headers,
    ):
        """POST /api/v1/appointments/{id}/complete/ → 200 + stock deducted."""
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        # Create inventory items
        gloves = create_inventory_item(
            clinic=clinic,
            name="Guantes de látex",
            stock_current=50,
            category="supply",
        )
        masks = create_inventory_item(
            clinic=clinic,
            name="Mascarillas",
            stock_current=30,
            category="supply",
        )

        # Create appointment type with kit
        kit = [
            {"item_id": str(gloves.id), "quantity": 2},
            {"item_id": str(masks.id), "quantity": 3},
        ]
        appt_type = create_appointment_type(clinic=clinic, inventory_kit=kit)

        # Create appointment in_progress
        patient = create_patient(clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, str(clinic.id)))

        response = client.post(f"/api/v1/appointments/{appt.id}/complete/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["inventory_consumed_at"] is not None
        assert data["inventory_items_consumed"] == 2

        # Verify stock was deducted
        gloves.refresh_from_db()
        masks.refresh_from_db()
        assert gloves.stock_current == 48  # 50 - 2
        assert masks.stock_current == 27  # 30 - 3

        # Verify appointment was updated
        appt.refresh_from_db()
        assert appt.status == Appointment.Status.COMPLETED
        assert appt.inventory_consumed_at is not None

        # Verify InventoryMovement records exist with correct reference
        from inventory.models import InventoryMovement

        movements = InventoryMovement.objects.filter(
            reference_type="appointment",
            reference_id=str(appt.id),
            movement_type=InventoryMovement.MovementType.CONSUMPTION,
        )
        assert movements.count() == 2


# ---------------------------------------------------------------------------
# 4.2 Complete without kit → no-op
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteAppointmentWithoutKit:
    """Test the complete endpoint with an empty inventory kit."""

    def test_complete_without_kit_succeeds(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
        auth_headers,
    ):
        """POST → 200 with inventory_items_consumed=0 when kit is empty."""
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        # Appointment type with empty kit
        appt_type = create_appointment_type(clinic=clinic, inventory_kit=[])

        patient = create_patient(clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, str(clinic.id)))

        response = client.post(f"/api/v1/appointments/{appt.id}/complete/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["inventory_consumed_at"] is not None
        assert data["inventory_items_consumed"] == 0

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.COMPLETED
        assert appt.inventory_consumed_at is not None


# ---------------------------------------------------------------------------
# 4.3 Idempotency — double completion returns 400
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteAppointmentIdempotency:
    """Test that completing the same appointment twice returns 400."""

    def test_complete_twice_returns_400(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
        auth_headers,
    ):
        """First complete → 200, second complete → 400."""
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        appt_type = create_appointment_type(clinic=clinic, inventory_kit=[])
        patient = create_patient(clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, str(clinic.id)))

        # First completion — should succeed
        response1 = client.post(f"/api/v1/appointments/{appt.id}/complete/")
        assert response1.status_code == 200

        # Second completion — should fail
        response2 = client.post(f"/api/v1/appointments/{appt.id}/complete/")
        assert response2.status_code == 400
        data = response2.json()
        assert data["error"] == "already_completed"


# ---------------------------------------------------------------------------
# 4.4 Insufficient stock → 400 with details
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteAppointmentInsufficientStock:
    """Test that insufficient stock returns 400 with per-item details."""

    def test_insufficient_stock_returns_400(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_inventory_item,
        create_appointment,
        auth_headers,
    ):
        """Complete with insufficient stock → 400 with error details."""
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        # Create item with stock_current = 0
        item = create_inventory_item(
            clinic=clinic,
            name="Guantes de látex",
            stock_current=0,
            category="supply",
        )

        # Kit requires 2 but available stock is 0
        kit = [{"item_id": str(item.id), "quantity": 2}]
        appt_type = create_appointment_type(clinic=clinic, inventory_kit=kit)

        patient = create_patient(clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, str(clinic.id)))

        response = client.post(f"/api/v1/appointments/{appt.id}/complete/")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "stock_insufficient"
        assert "details" in data
        assert len(data["details"]) == 1
        detail = data["details"][0]
        assert detail["item_name"] == "Guantes de látex"
        assert detail["available"] == 0
        assert detail["required"] == 2


# ---------------------------------------------------------------------------
# 4.5 Invalid status → 400
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestCompleteAppointmentInvalidStatus:
    """Test that completing an appointment with invalid status returns 400."""

    def test_complete_cancelled_appointment_returns_400(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
        auth_headers,
    ):
        """Complete a cancelled appointment → 400."""
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        appt_type = create_appointment_type(clinic=clinic, inventory_kit=[])
        patient = create_patient(clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="cancelled",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, str(clinic.id)))

        response = client.post(f"/api/v1/appointments/{appt.id}/complete/")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_status"


# ---------------------------------------------------------------------------
# 4.6 Serializer validation — invalid kit items
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.django_db
class TestAppointmentTypeSerializerKitValidation:
    """Test validate_inventory_kit() on AppointmentTypeSerializer."""

    def test_valid_kit_passes(
        self,
        create_clinic,
        create_inventory_item,
    ):
        """A kit with valid item_id and quantity passes validation."""
        clinic = create_clinic()
        item = create_inventory_item(clinic=clinic)

        from appointments.serializers import AppointmentTypeSerializer

        kit = [{"item_id": str(item.id), "quantity": 3}]
        request = type("Req", (), {"clinic_id": str(clinic.id)})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        validated_kit = serializer.validate_inventory_kit(kit)
        assert validated_kit == kit

    def test_missing_item_id_raises_error(self, create_clinic):
        """Kit item without item_id raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        with pytest.raises(serializers.ValidationError, match="item_id"):
            serializer.validate_inventory_kit([{"quantity": 5}])

    def test_invalid_uuid_raises_error(self, create_clinic):
        """Kit item with invalid UUID raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        with pytest.raises(serializers.ValidationError, match="UUID"):
            serializer.validate_inventory_kit(
                [{"item_id": "not-a-uuid", "quantity": 1}]
            )

    def test_negative_quantity_raises_error(self, create_clinic):
        """Kit item with negative quantity raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        item_id = "00000000-0000-0000-0000-000000000001"
        with pytest.raises(serializers.ValidationError, match="positivo"):
            serializer.validate_inventory_kit([{"item_id": item_id, "quantity": -1}])

    def test_zero_quantity_raises_error(self, create_clinic):
        """Kit item with zero quantity raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        item_id = "00000000-0000-0000-0000-000000000001"
        with pytest.raises(serializers.ValidationError, match="positivo"):
            serializer.validate_inventory_kit([{"item_id": item_id, "quantity": 0}])

    def test_nonexistent_item_id_raises_error(self, create_clinic):
        """Kit item with non-existent item_id raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic = create_clinic()
        request = type("Req", (), {"clinic_id": str(clinic.id)})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        item_id = "00000000-0000-0000-0000-000000000099"
        with pytest.raises(serializers.ValidationError, match="no encontrado"):
            serializer.validate_inventory_kit([{"item_id": item_id, "quantity": 1}])

    def test_empty_kit_returns_value(self, create_clinic):
        """Empty kit list passes validation."""
        from appointments.serializers import AppointmentTypeSerializer

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        result = serializer.validate_inventory_kit([])
        assert result == []

    def test_none_kit_returns_value(self, create_clinic):
        """None kit passes validation."""
        from appointments.serializers import AppointmentTypeSerializer

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        result = serializer.validate_inventory_kit(None)
        assert result is None

    def test_non_dict_entry_raises_error(self, create_clinic):
        """Kit with non-dict entries raises ValidationError."""
        from appointments.serializers import AppointmentTypeSerializer
        from rest_framework import serializers

        clinic_id = "00000000-0000-0000-0000-000000000001"
        request = type("Req", (), {"clinic_id": clinic_id})()
        serializer = AppointmentTypeSerializer(context={"request": request})
        with pytest.raises(serializers.ValidationError, match="diccionario"):
            serializer.validate_inventory_kit(["not_a_dict"])
