"""
Tests for Patient Management models.

Tests cover:
- ClinicalNote.sign() — immutability and signature hash
- ClinicalNote.soft_delete cascading (via patient)
- PatientConsent.sign() — signature with/without blob
- Patient.delete() soft delete
"""

import pytest
from django.utils import timezone

from accounts.models import User
from clinics.models import Clinic
from patients.models import ClinicalNote, Patient, PatientConsent


@pytest.mark.django_db
class TestClinicalNote:
    """Tests for ClinicalNote model."""

    def test_sign_successfully(self, clinic: Clinic, dentist_user: User):
        """Signing a note sets is_signed, signed_at, and signature_hash."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Juan",
            last_name="Pérez",
            phone="5550000001",
            date_of_birth="1990-01-01",
        )
        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Nota de evolución",
            content="Paciente estable",
        )

        assert note.is_signed is False
        assert note.signed_at is None
        assert note.signature_hash == ""

        note.sign(user=dentist_user)

        assert note.is_signed is True
        assert note.signed_at is not None
        assert note.signature_hash != ""
        assert len(note.signature_hash) == 64  # SHA-256 hex

    def test_sign_raises_value_error_on_resign(
        self, clinic: Clinic, dentist_user: User
    ):
        """Signing an already-signed note raises ValueError."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="María",
            last_name="García",
            phone="5550000002",
            date_of_birth="1985-06-15",
        )
        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="diagnosis",
            title="Diagnóstico inicial",
            content="Caries profunda en molar 16",
        )
        note.sign(user=dentist_user)

        with pytest.raises(ValueError, match="ya está firmada"):
            note.sign(user=dentist_user)

    def test_soft_delete_cascading(self, clinic: Clinic):
        """ClinicalNote should be cascade-deleted when patient is hard-deleted."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Carlos",
            last_name="López",
            phone="5550000003",
            date_of_birth="1978-03-22",
        )
        note = ClinicalNote.objects.create(
            patient=patient,
            note_type="observation",
            title="Observación",
            content="Sin novedades",
        )

        # Soft delete shouldn't cascade (CASCADE is Django-level, not affected by soft-delete)
        patient.delete()  # Soft delete
        # The note still exists
        assert ClinicalNote.objects.filter(id=note.id).exists()

        # Hard delete DOES cascade
        patient.hard_delete()
        assert not ClinicalNote.objects.filter(id=note.id).exists()


@pytest.mark.django_db
class TestPatientConsent:
    """Tests for PatientConsent model."""

    def test_sign_successfully(self, clinic: Clinic, dentist_user: User):
        """Signing a consent sets signed=True, signed_at, signature_hash."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Ana",
            last_name="Martínez",
            phone="5550000004",
            date_of_birth="1992-11-08",
        )
        consent = PatientConsent.objects.create(
            patient=patient,
            consent_type="treatment",
            version="1.0",
            content="Consentimiento para tratamiento de conducto",
        )

        assert consent.signed is False

        consent.sign(user=dentist_user)

        assert consent.signed is True
        assert consent.signed_at is not None
        assert consent.signature_hash != ""
        assert consent.signature_blob is None

    def test_sign_with_blob(self, clinic: Clinic, dentist_user: User):
        """Signing with signature_blob stores the binary data."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Luis",
            last_name="Hernández",
            phone="5550000005",
            date_of_birth="1988-07-14",
        )
        consent = PatientConsent.objects.create(
            patient=patient,
            consent_type="general",
            version="2.0",
            content="Consentimiento general dental",
        )

        signature_bytes = b"\x89PNG\x00\x00FAKE_SIGNATURE_DATA"
        consent.sign(signature_blob=signature_bytes, user=dentist_user)

        assert consent.signature_blob == signature_bytes
        assert consent.signed is True

    def test_sign_stores_ip_address(self, clinic: Clinic, dentist_user: User):
        """Signing should store the provided IP address."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Pedro",
            last_name="Díaz",
            phone="5550000006",
            date_of_birth="1995-09-30",
        )
        consent = PatientConsent.objects.create(
            patient=patient,
            consent_type="data_processing",
            version="1.0",
            content="Aviso de privacidad",
        )

        consent.sign(
            user=dentist_user,
            ip_address="192.168.1.100",
        )

        assert consent.ip_address == "192.168.1.100"


@pytest.mark.django_db
class TestPatient:
    """Tests for Patient model."""

    def test_delete_soft_delete(self, clinic: Clinic):
        """delete() should soft-delete (set is_deleted=True)."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Sofía",
            last_name="Ramírez",
            phone="5550000007",
            date_of_birth="2000-04-12",
        )

        assert patient.is_deleted is False

        patient.delete()

        patient.refresh_from_db()
        assert patient.is_deleted is True

        # Should NOT appear in default manager
        assert not Patient.objects.filter(id=patient.id).exists()

        # Should appear in all_objects manager
        assert Patient.all_objects.filter(id=patient.id).exists()

    def test_full_name_property(self, clinic: Clinic):
        """full_name should combine first_name, last_name, and second_last_name."""
        patient = Patient.objects.create(
            clinic=clinic,
            first_name="José",
            last_name="Álvarez",
            second_last_name="Muñoz",
            phone="5550000008",
            date_of_birth="1982-01-20",
        )

        assert patient.full_name == "José Álvarez Muñoz"
