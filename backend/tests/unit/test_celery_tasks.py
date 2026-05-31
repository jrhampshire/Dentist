"""
Unit tests for Celery task — consume_inventory_kit (Task 4.7).

Tests that the task calls consume_kit() with the real appointment_id,
not a synthetic UUID.
"""

from unittest.mock import patch

import pytest

from appointments.models import Appointment


@pytest.mark.unit
@pytest.mark.django_db
class TestConsumeInventoryKitTask:
    """Test that the Celery task calls consume_kit() with correct arguments."""

    def test_task_calls_consume_kit_with_real_appointment_id(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """The task MUST pass appointment_id=str(appt.id) to consume_kit()."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(
            clinic=clinic,
            inventory_kit=[
                {"item_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}
            ],
        )
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        # Mock consume_kit
        with patch("inventory.services.stock_service.consume_kit") as mock_consume:
            mock_consume.return_value = []

            from celery_app.tasks import consume_inventory_kit

            result = consume_inventory_kit(str(appt.id))

            # Assert the task called consume_kit with the real appointment ID
            mock_consume.assert_called_once()
            _, kwargs = mock_consume.call_args
            assert kwargs["appointment_id"] == str(appt.id)
            assert kwargs["clinic_id"] == str(clinic.id)
            assert kwargs["kit"] == appt_type.inventory_kit

            assert result["status"] == "success"

    def test_task_skips_when_kit_is_empty(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """When inventory_kit is empty, the task returns 'skipped'."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic, inventory_kit=[])
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        with patch("inventory.services.stock_service.consume_kit") as mock_consume:
            from celery_app.tasks import consume_inventory_kit

            result = consume_inventory_kit(str(appt.id))

            mock_consume.assert_not_called()
            assert result["status"] == "skipped"
            assert result["reason"] == "no_kit"

    def test_task_handles_appointment_not_found(self):
        """When appointment doesn't exist, the task returns error."""
        from celery_app.tasks import consume_inventory_kit

        result = consume_inventory_kit("00000000-0000-0000-0000-000000000000")

        assert result["status"] == "error"
        assert result["reason"] == "appointment_not_found"

    def test_task_handles_value_error(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """ValueError from consume_kit is caught and returned as error."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)

        kit = [{"item_id": "00000000-0000-0000-0000-000000000001", "quantity": 5}]
        appt_type = create_appointment_type(clinic=clinic, inventory_kit=kit)
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="in_progress",
        )

        with patch(
            "inventory.services.stock_service.consume_kit",
            side_effect=ValueError(
                "Stock insuficiente para 'X': disponible=0, requerido=5"
            ),
        ):
            from celery_app.tasks import consume_inventory_kit

            result = consume_inventory_kit(str(appt.id))

            assert result["status"] == "error"
            assert "Stock insuficiente" in result["reason"]
