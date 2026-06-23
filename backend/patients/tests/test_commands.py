"""
Tests for NOM-024 retention management command (purge_expired_records).

Covers:
- --dry-run preview without modifications
- --years parameter controls cutoff
- Inactive patients are soft-deleted
- Old unsigned clinical notes are anonymized
- Signed notes are NOT anonymized
- Already-redacted notes are skipped
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from patients.models import ClinicalNote, Patient


@pytest.mark.django_db
class TestPurgeExpiredRecordsDryRun:
    """--dry-run should preview changes without modifying data."""

    def test_dry_run_does_not_modify_patients(self, create_clinic, create_patient):
        clinic = create_clinic(name="Retention Clinic")
        patient = create_patient(
            clinic=clinic,
            first_name="Old",
            last_name="Patient",
        )

        initial_count = Patient.objects.filter(clinic=clinic, is_deleted=False).count()

        out = StringIO()
        call_command("purge_expired_records", "--years=0", "--dry-run", stdout=out)

        output = out.getvalue()
        assert "DRY RUN" in output

        # Patient must NOT be deleted
        after_count = Patient.objects.filter(clinic=clinic, is_deleted=False).count()
        assert after_count == initial_count

    def test_dry_run_does_not_modify_notes(self, create_clinic, create_patient):
        clinic = create_clinic(name="Retention Clinic 2")
        patient = create_patient(clinic=clinic, first_name="Note", last_name="Owner")

        note = ClinicalNote.objects.create(
            patient=patient,
            clinic=clinic,
            title="Old Note",
            content="Original content",
            created_at=timezone.now() - timedelta(days=400),
        )

        original_content = note.content
        out = StringIO()
        call_command("purge_expired_records", "--years=1", "--dry-run", stdout=out)

        output = out.getvalue()
        assert "DRY RUN" in output

        note.refresh_from_db()
        assert note.content == original_content


@pytest.mark.django_db
class TestPurgeExpiredRecordsLive:
    """Live mode should actually modify data."""

    def test_soft_deletes_inactive_patients(
        self, create_clinic, create_patient, create_appointment
    ):
        clinic = create_clinic(name="Purge Clinic")
        patient = create_patient(
            clinic=clinic,
            first_name="Inactive",
            last_name="User",
        )

        out = StringIO()
        # --years=0 means cutoff is now, so any patient created before now
        # is eligible (but patients created in this test run at timezone.now()
        # will be microseconds later — safe for this test since the command uses
        # created_at__lt=cutoff_date, not created_at__lte).
        # We use --years=0 to force immediate eligibility.
        call_command("purge_expired_records", "--years=0", stdout=out)

        output = out.getvalue()
        assert "✓" in output

        # Patient should be soft-deleted
        patient.refresh_from_db()
        assert patient.is_deleted is True

    def test_anonymizes_old_unsigned_notes(self, create_clinic, create_patient):
        clinic = create_clinic(name="Anonymize Clinic")
        patient = create_patient(clinic=clinic, first_name="Note", last_name="Patient")

        note = ClinicalNote.objects.create(
            patient=patient,
            clinic=clinic,
            title="Old clinical note",
            content="Patient presents with tooth pain in lower right quadrant.",
            is_signed=False,
        )
        # Force created_at to be in the past
        note.created_at = timezone.now() - timedelta(days=400)
        note.save(update_fields=["created_at"])

        out = StringIO()
        call_command("purge_expired_records", "--years=1", stdout=out)

        output = out.getvalue()
        assert "✓" in output

        note.refresh_from_db()
        assert note.content == "[REDACTED - Retention period expired]"

    def test_preserves_signed_notes(self, create_clinic, create_patient, create_user):
        clinic = create_clinic(name="Signed Notes Clinic")
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(
            clinic=clinic, first_name="Signed", last_name="NoteOwner"
        )

        note = ClinicalNote.objects.create(
            patient=patient,
            clinic=clinic,
            title="Signed clinical note",
            content="Diagnosis: mild gingivitis. Treatment: scaling and polishing.",
            is_signed=True,
            signed_by=dentist,
        )
        # Force created_at to be in the past
        note.created_at = timezone.now() - timedelta(days=400)
        note.save(update_fields=["created_at"])

        out = StringIO()
        call_command("purge_expired_records", "--years=1", stdout=out)

        output = out.getvalue()
        assert "✓" in output

        note.refresh_from_db()
        assert note.content != "[REDACTED - Retention period expired]"
        assert "gingivitis" in note.content

    def test_skips_already_redacted_notes(self, create_clinic, create_patient):
        clinic = create_clinic(name="Skip Redacted Clinic")
        patient = create_patient(
            clinic=clinic, first_name="Already", last_name="Redacted"
        )

        note = ClinicalNote.objects.create(
            patient=patient,
            clinic=clinic,
            title="Already redacted",
            content="[REDACTED - Retention period expired]",
            is_signed=False,
        )
        note.created_at = timezone.now() - timedelta(days=400)
        note.save(update_fields=["created_at"])

        out = StringIO()
        call_command("purge_expired_records", "--years=1", stdout=out)

        output = out.getvalue()
        # Should report 0 notes to process, not re-anonymize
        assert "Notas clínicas para anonimizar: 0" in output


@pytest.mark.django_db
class TestPurgeExpiredRecordsCustomYears:
    """The --years parameter controls the retention window."""

    def test_custom_years_respects_cutoff(self, create_clinic, create_patient):
        clinic = create_clinic(name="Custom Years Clinic")
        patient = create_patient(clinic=clinic, first_name="Recent", last_name="One")

        # With --years=999, cutoff is ~1000 years ago — nothing should be deleted
        out = StringIO()
        call_command("purge_expired_records", "--years=999", stdout=out)

        output = out.getvalue()
        assert "Pacientes inactivos encontrados: 0" in output
        patient.refresh_from_db()
        assert patient.is_deleted is False
