"""
Unit tests for model-level business logic.

Models tested:
- Appointment.save() — auto end_time calculation
- Patient.delete() / hard_delete() — soft delete
- InventoryItem.deduct_stock() — stock deduction with validation
- ClinicalNote.sign() — signature and immutability
- Invoice.cancel(), mark_cancelled(), mark_stamped(), mark_error(), calculate_totals()

Requires DB — uses @pytest.mark.django_db and conftest fixtures.
"""

from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


# ============================================================================
# Appointment.save() — auto-calculate end_time
# ============================================================================


@pytest.mark.django_db
class TestAppointmentSaveAutoEndTime:
    """Appointment.save() auto-calculates end_time from appointment_type.duration_minutes
    when end_time is not set. If end_time is already set, it is preserved."""

    def test_auto_calculates_end_time_when_not_set(
        self, create_appointment, create_appointment_type, create_clinic
    ):
        """When end_time is not explicitly set, it's calculated from duration_minutes."""
        clinic = create_clinic()
        appt_type = create_appointment_type(clinic=clinic, duration=60)
        appt = create_appointment(
            clinic=clinic,
            appt_type=appt_type,
            start=time(9, 0),
        )
        # Force end_time to None to trigger auto-calculation
        appt.end_time = None
        appt.save()

        appt.refresh_from_db()
        assert appt.end_time == time(10, 0)  # 9:00 + 60min

    def test_preserves_end_time_when_already_set(
        self, create_appointment, create_appointment_type, create_clinic
    ):
        """When end_time is already set, it is NOT recalculated."""
        clinic = create_clinic()
        appt_type = create_appointment_type(clinic=clinic, duration=60)
        appt = create_appointment(
            clinic=clinic,
            appt_type=appt_type,
            start=time(9, 0),
            end=time(10, 30),  # Explicit end_time, different from duration
        )

        appt.start_time = time(10, 0)
        appt.save()

        appt.refresh_from_db()
        # End_time should remain 10:30 (NOT recalculated from duration)
        assert appt.end_time == time(10, 30)

    def test_save_without_changes_preserves_values(
        self, create_appointment, create_appointment_type, create_clinic
    ):
        """Saving without changes preserves both start_time and end_time."""
        clinic = create_clinic()
        appt_type = create_appointment_type(clinic=clinic, duration=30)
        appt = create_appointment(
            clinic=clinic,
            appt_type=appt_type,
            start=time(9, 0),
            end=time(9, 30),
        )

        # Save without any changes
        appt.save()

        appt.refresh_from_db()
        assert appt.start_time == time(9, 0)
        assert appt.end_time == time(9, 30)


# ============================================================================
# Patient.delete() / hard_delete() — soft delete
# ============================================================================


@pytest.mark.django_db
class TestPatientSoftDelete:
    """Patient.delete() performs soft delete (is_deleted=True)."""

    def test_soft_delete_sets_is_deleted(self, create_patient):
        """delete() sets is_deleted=True without removing the DB row."""
        patient = create_patient()
        pk = patient.pk

        patient.delete()

        patient.refresh_from_db()
        assert patient.is_deleted is True
        assert patient.pk == pk  # Row still exists

    def test_soft_deleted_patient_not_found_by_default_manager(self, create_patient):
        """Default manager excludes soft-deleted patients."""
        patient = create_patient()
        pk = patient.pk
        patient.delete()

        from patients.models import Patient

        with pytest.raises(Patient.DoesNotExist):
            Patient.objects.get(pk=pk)

    def test_soft_deleted_patient_found_by_all_objects(self, create_patient):
        """all_objects manager includes soft-deleted patients."""
        patient = create_patient()
        pk = patient.pk
        patient.delete()

        from patients.models import Patient

        found = Patient.all_objects.get(pk=pk)
        assert found.pk == pk
        assert found.is_deleted is True

    def test_hard_delete_permanently_removes(self, create_patient):
        """hard_delete() permanently removes the database row."""
        patient = create_patient()
        pk = patient.pk

        patient.hard_delete()

        from patients.models import Patient

        with pytest.raises(Patient.DoesNotExist):
            Patient.all_objects.get(pk=pk)


# ============================================================================
# InventoryItem.deduct_stock()
# ============================================================================


@pytest.mark.django_db
class TestInventoryItemDeductStock:
    """InventoryItem.deduct_stock() deducts stock with validation."""

    def test_sufficient_stock_deducts_correctly(self, create_inventory_item):
        """Deducting from sufficient stock reduces the quantity."""
        item = create_inventory_item(stock_current=Decimal("100.00"))

        item.deduct_stock(Decimal("30.00"))

        item.refresh_from_db()
        assert item.stock_current == Decimal("70.00")

    def test_insufficient_stock_raises_valueerror(self, create_inventory_item):
        """Deducting more than available raises ValueError."""
        item = create_inventory_item(stock_current=Decimal("10.00"))

        with pytest.raises(ValueError, match="Stock insuficiente"):
            item.deduct_stock(Decimal("30.00"))

        # Quantity remains unchanged
        item.refresh_from_db()
        assert item.stock_current == Decimal("10.00")

    def test_zero_stock_deduction_makes_zero(self, create_inventory_item):
        """Deducting exactly the full quantity results in zero."""
        item = create_inventory_item(stock_current=Decimal("30.00"))

        item.deduct_stock(Decimal("30.00"))

        item.refresh_from_db()
        assert item.stock_current == Decimal("0.00")

    def test_blocked_item_raises_valueerror(self, create_inventory_item):
        """Blocked items cannot be deducted."""
        item = create_inventory_item(stock_current=Decimal("100.00"))
        item.is_blocked = True
        item.save()

        with pytest.raises(ValueError, match="bloqueado"):
            item.deduct_stock(Decimal("10.00"))

        item.refresh_from_db()
        assert item.stock_current == Decimal("100.00")

    def test_expired_item_raises_valueerror(self, create_inventory_item):
        """Expired items cannot be deducted."""
        item = create_inventory_item(stock_current=Decimal("50.00"))
        item.is_expired = True
        item.save()

        with pytest.raises(ValueError, match="expirado"):
            item.deduct_stock(Decimal("10.00"))

    def test_creates_movement_record(self, create_inventory_item):
        """Deducting stock creates an InventoryMovement record."""
        item = create_inventory_item(stock_current=Decimal("50.00"))

        item.deduct_stock(Decimal("15.00"), reason="Consumo por cita")

        from inventory.models import InventoryMovement

        movement = InventoryMovement.objects.filter(item=item).first()
        assert movement is not None
        assert movement.movement_type == InventoryMovement.MovementType.OUT
        assert movement.quantity == Decimal("-15.00")
        assert movement.previous_stock == Decimal("50.00")
        assert movement.new_stock == Decimal("35.00")
        assert "Consumo por cita" in movement.note


# ============================================================================
# ClinicalNote.sign()
# ============================================================================


@pytest.mark.django_db
class TestClinicalNoteSign:
    """ClinicalNote.sign() signs the note and makes it immutable."""

    def test_sign_sets_is_signed_and_generates_hash(self, create_clinic, create_user):
        """Signing sets is_signed=True and generates a signature_hash."""
        clinic = create_clinic()
        author = create_user(role="dentista", clinic=clinic)

        from patients.models import ClinicalNote, Patient

        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            phone="5512345678",
        )

        note = ClinicalNote.objects.create(
            patient=patient,
            author=author,
            note_type="evolution",
            title="Consulta de seguimiento",
            content="Paciente muestra mejoría.",
        )

        assert note.is_signed is False
        assert note.signature_hash == ""

        note.sign()

        note.refresh_from_db()
        assert note.is_signed is True
        assert note.signed_at is not None
        assert len(note.signature_hash) == 64  # SHA-256 hex digest
        assert note.signature_hash != ""

    def test_sign_already_signed_raises_valueerror(self, create_clinic, create_user):
        """Signing an already signed note raises ValueError."""
        clinic = create_clinic()
        author = create_user(role="dentista", clinic=clinic)

        from patients.models import ClinicalNote, Patient

        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            phone="5512345679",
        )

        note = ClinicalNote.objects.create(
            patient=patient,
            author=author,
            note_type="diagnosis",
            title="Diagnóstico inicial",
            content="Caries en molar 16.",
        )
        note.sign()  # First sign succeeds

        with pytest.raises(ValueError, match="ya está firmada"):
            note.sign()  # Second sign fails


# ============================================================================
# Invoice methods
# ============================================================================


@pytest.mark.django_db
class TestInvoiceCancel:
    """Invoice.cancel() requests cancellation (SAT flow)."""

    def test_cancel_stamped_invoice_sets_cancellation_requested(self, create_invoice):
        """Cancelling a stamped invoice sets status to cancellation_requested."""
        invoice = create_invoice(status="stamped", cfdi_uuid="uuid-123")

        invoice.cancel(reason="02")  # Error without relation

        invoice.refresh_from_db()
        assert invoice.status == "cancellation_requested"
        assert invoice.cancellation_reason == "02"

    def test_cancel_non_stamped_raises_valueerror(self, create_invoice):
        """Cancelling a draft invoice raises ValueError."""
        invoice = create_invoice(status="draft")

        with pytest.raises(ValueError, match="Solo se pueden cancelar"):
            invoice.cancel()

    def test_cancel_pending_stamp_raises_valueerror(self, create_invoice):
        """Cancelling a pending_stamp invoice raises ValueError."""
        invoice = create_invoice(status="pending_stamp")

        with pytest.raises(ValueError, match="Solo se pueden cancelar"):
            invoice.cancel()


@pytest.mark.django_db
class TestInvoiceMarkCancelled:
    """Invoice.mark_cancelled() confirms cancellation (after SAT approval)."""

    def test_mark_cancelled_from_requested(self, create_invoice):
        """Marking cancellation_requested invoice as cancelled."""
        invoice = create_invoice(status="cancellation_requested")

        invoice.mark_cancelled()

        invoice.refresh_from_db()
        assert invoice.status == "cancelled"
        assert invoice.cancelled_at is not None

    def test_mark_cancelled_from_non_requested_raises(self, create_invoice):
        """Cannot mark as cancelled unless currently cancellation_requested."""
        invoice = create_invoice(status="draft")

        with pytest.raises(ValueError, match="cancellation_requested"):
            invoice.mark_cancelled()


@pytest.mark.django_db
class TestInvoiceMarkStamped:
    """Invoice.mark_stamped() records successful SAT stamping."""

    def test_mark_stamped_sets_uuid_and_status(self, create_invoice):
        """Marking as stamped sets cfdi_uuid, status, and certificate."""
        invoice = create_invoice(status="pending_stamp")

        invoice.mark_stamped(
            uuid="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            sat_certificate="00001000000512345678",
            stamp_date=timezone.now(),
            xml_url="https://finkok.com/xml/123",
            pdf_url="https://finkok.com/pdf/123",
        )

        invoice.refresh_from_db()
        assert invoice.status == "stamped"
        assert invoice.cfdi_uuid == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert invoice.cfdi_sat_certificate == "00001000000512345678"
        assert invoice.cfdi_stamp_date is not None
        assert invoice.xml_url == "https://finkok.com/xml/123"
        assert invoice.pdf_url == "https://finkok.com/pdf/123"
        assert invoice.error_message == ""


@pytest.mark.django_db
class TestInvoiceMarkError:
    """Invoice.mark_error() records a stamping failure."""

    def test_mark_error_sets_status_and_message(self, create_invoice):
        """Marking error sets status to error and stores the message."""
        invoice = create_invoice(status="pending_stamp")

        invoice.mark_error("Finkok timeout: error 503")

        invoice.refresh_from_db()
        assert invoice.status == "error"
        assert invoice.error_message == "Finkok timeout: error 503"


@pytest.mark.django_db
class TestInvoiceCalculateTotals:
    """Invoice.calculate_totals() recalculates amounts from concepts."""

    def test_calculate_totals_single_concept(self, create_invoice):
        """Subtotal, IVA, and total are recalculated from concept."""
        invoice = create_invoice(
            concepts=[
                {
                    "clave_sat": "84111506",
                    "descripcion": "Limpieza dental",
                    "cantidad": 1,
                    "valor_unitario": 800.00,
                    "importe": 800.00,
                    "iva_rate": 0.16,
                }
            ],
            subtotal=Decimal("0"),
            iva=Decimal("0"),
            total=Decimal("0"),
        )

        invoice.calculate_totals()

        assert invoice.subtotal == Decimal("800.00")
        # iva = 800 * 0.16 = 128.00
        assert invoice.iva == Decimal("128.00")
        assert invoice.total == Decimal("928.00")

    def test_calculate_totals_multiple_concepts(self, create_invoice):
        """Multiple concepts are summed correctly."""
        invoice = create_invoice(
            concepts=[
                {
                    "clave_sat": "84111506",
                    "descripcion": "Limpieza",
                    "cantidad": 1,
                    "valor_unitario": 800.00,
                    "importe": 800.00,
                    "iva_rate": 0.16,
                },
                {
                    "clave_sat": "85121600",
                    "descripcion": "Radiografía",
                    "cantidad": 1,
                    "valor_unitario": 300.00,
                    "importe": 300.00,
                    "iva_rate": 0.16,
                },
            ],
            subtotal=Decimal("0"),
            iva=Decimal("0"),
            total=Decimal("0"),
        )

        invoice.calculate_totals()

        assert invoice.subtotal == Decimal("1100.00")  # 800 + 300
        assert invoice.iva == Decimal("176.00")  # (800+300) * 0.16
        assert invoice.total == Decimal("1276.00")

    def test_calculate_totals_zero_concepts(self, create_invoice):
        """Empty concepts result in zero amounts."""
        invoice = create_invoice(
            concepts=[],
            subtotal=Decimal("0"),
            iva=Decimal("0"),
            total=Decimal("0"),
        )

        invoice.calculate_totals()

        assert invoice.subtotal == Decimal("0.00")
        assert invoice.iva == Decimal("0.00")
        assert invoice.total == Decimal("0.00")
