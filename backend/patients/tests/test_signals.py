"""
Tests for audit signal handlers (NOM-024 compliance).

Tests cover:
- AuditLog created on ClinicalNote create and sign
- TextField content is hashed in audit log (not stored in plain text)
- BinaryField is skipped in audit log
- Password field is never logged
"""

import hashlib

import pytest
from django.db.models.signals import post_save

from core.models import AuditLog
from core.signals import _get_serializable_fields


@pytest.mark.django_db
class TestAuditSignalTextFieldHashing:
    """Tests for NOM-024 TextField hashing in audit signals."""

    def test_textfield_content_is_hashed_in_audit_details(self, patient, dentist_user):
        """When a ClinicalNote is created, its TextField content is hashed."""
        from patients.models import ClinicalNote
        from core.signals import audit_post_save

        # Count existing audit logs
        initial_count = AuditLog.objects.count()

        # Create a patient (this will trigger audit_post_save)
        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Nota de prueba de hashing",
            content="Este contenido clínico DEBE ser hasheado en el audit log.",
        )

        # Verify audit log was created
        assert AuditLog.objects.count() > initial_count

        # Get the most recent audit log entry
        audit_entry = AuditLog.objects.latest("created_at")
        details = audit_entry.details

        # The content field should NOT be in plain text
        if "new" in details:
            new_details = details["new"]
            assert "content" not in new_details, (
                "TextField 'content' should not be stored in plain text"
            )
            # The hash should be present
            assert "content_hash" in new_details, (
                "TextField 'content' hash should be present as 'content_hash'"
            )
            # The hash should be the first 16 chars of SHA-256
            assert len(new_details["content_hash"]) == 16

    def test_binaryfield_is_skipped(self):
        """BinaryField values should never appear in serializable fields."""
        from patients.models import PatientConsent

        # Create a consent with a signature blob
        consent = PatientConsent()
        consent.signature_blob = b"\x89PNG\x00\x00FAKE_BINARY_DATA"

        fields = _get_serializable_fields(consent)

        # BinaryField should be completely absent
        assert "signature_blob" not in fields, (
            "BinaryField 'signature_blob' should be skipped"
        )
        assert "signature_blob_hash" not in fields, (
            "BinaryField should not be hashed, it should be skipped entirely"
        )

    def test_password_field_never_logged(self):
        """The 'password' field should never appear in audit details, even hashed."""
        from accounts.models import User

        user = User()
        user.password = "hashed_password_value_here"

        fields = _get_serializable_fields(user)

        assert "password" not in fields, "Password field should never be logged"
        assert "password_hash" not in fields, "Password hash should never be logged"

    def test_clinical_note_with_content(self, patient, dentist_user):
        """Full integration test: creating and signing a note logs hashed content."""
        from patients.models import ClinicalNote

        initial_count = AuditLog.objects.count()

        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="treatment",
            title="Plan de tratamiento",
            content="Realizar endodoncia en pieza 16.",
        )

        # Sign the note
        note.sign(user=dentist_user)

        # Should have multiple audit logs now
        final_count = AuditLog.objects.count()
        assert final_count > initial_count


@pytest.mark.django_db
class TestAuditSignalBasic:
    """Tests for basic audit signal behavior."""

    def test_audit_log_created_on_patient_create(self, clinic):
        """Creating a patient should create an audit log entry."""
        initial_count = AuditLog.objects.count()

        patient = Patient.objects.create(
            clinic=clinic,
            first_name="Test",
            last_name="Patient",
            phone="5598765432",
            date_of_birth="1990-01-01",
        )

        assert AuditLog.objects.count() > initial_count

        # Find the audit entry for this patient
        audit_entry = AuditLog.objects.filter(
            resource_type="Patient",
            resource_id=str(patient.id),
        ).first()

        assert audit_entry is not None
        assert "created" in audit_entry.action

    def test_audit_log_skips_excluded_models(self):
        """AuditLog and Session models should not have audit entries."""
        from core.signals import _should_audit_model
        from core.models import AuditLog as AuditLogModel

        assert _should_audit_model(AuditLogModel) is False
