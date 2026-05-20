"""
NOM-024 Retention Policy Management Command.

Usage:
    python manage.py purge_expired_records [--years 5] [--dry-run]

NOM-024 requires clinical records retention for 5 years.
This command:
- Soft-deletes patients with no activity in 5+ years
- Anonymizes clinical notes older than 5 years
- Logs all actions via AuditLog for compliance
"""

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AuditLog
from patients.models import ClinicalNote, Patient


class Command(BaseCommand):
    help = "Purge or anonymize records beyond NOM-024 retention period (5 years)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--years",
            type=int,
            default=5,
            help="Retention period in years (default: 5 per NOM-024).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview affected records without making changes.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        years = options["years"]
        dry_run = options["dry_run"]
        cutoff_date = timezone.now() - timedelta(days=years * 365)

        self.stdout.write(self.style.WARNING(f"=== NOM-024 Retention Policy ==="))
        self.stdout.write(f"Retention period: {years} years")
        self.stdout.write(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write("")

        # ------------------------------------------------------------------
        # 1. Soft-delete inactive patients
        # ------------------------------------------------------------------
        self._purge_inactive_patients(cutoff_date, dry_run)

        # ------------------------------------------------------------------
        # 2. Anonymize old clinical notes
        # ------------------------------------------------------------------
        self._anonymize_old_notes(cutoff_date, dry_run)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Retention policy check complete ==="))

    # ------------------------------------------------------------------
    # Patients — soft-delete
    # ------------------------------------------------------------------

    def _purge_inactive_patients(self, cutoff_date, dry_run: bool) -> None:
        """
        Soft-delete patients with no activity (appointments) in the last N years.
        Uses Patient.all_objects to include already-soft-deleted patients
        so we don't double-process them.
        """
        self.stdout.write("--- Paso 1: Pacientes inactivos ---")

        # Find patients whose last appointment was before cutoff
        # (or who have never had any appointments and were created before cutoff)
        inactive_qs = Patient.all_objects.filter(
            is_deleted=False,
            created_at__lt=cutoff_date,
        ).exclude(appointments__date__gte=cutoff_date.date())

        count = inactive_qs.count()
        self.stdout.write(f"Pacientes inactivos encontrados: {count}")

        if count == 0:
            self.stdout.write("  Nada que procesar.")
            return

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"  [DRY RUN] Se marcarían {count} pacientes como eliminados."
                )
            )
            return

        # Process in batches of 100 to avoid memory issues
        processed = 0
        for patient in inactive_qs.iterator(chunk_size=100):
            patient_name = patient.full_name
            patient_id_str = str(patient.id)
            patient.delete()  # Soft delete

            # Log action
            try:
                AuditLog.objects.create(
                    clinic=patient.clinic,
                    user=None,
                    action="patients.patient.retention_purge",
                    resource_type="Patient",
                    resource_id=patient_id_str,
                    details={
                        "reason": "NOM-024 retention expired",
                        "patient_name": patient_name,
                        "cutoff_date": cutoff_date.isoformat(),
                    },
                    result="success",
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Auditoría no creada para paciente {patient_id_str}: {e}"
                    )
                )

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ {processed} pacientes eliminados (soft-delete).")
        )

    # ------------------------------------------------------------------
    # Clinical Notes — anonymize
    # ------------------------------------------------------------------

    def _anonymize_old_notes(self, cutoff_date, dry_run: bool) -> None:
        """
        Anonymize clinical notes older than the retention period.
        Replaces content with "[REDACTED - Retention period expired]".
        Only applies to unsigned notes — signed notes are immutable.
        """
        self.stdout.write("")
        self.stdout.write("--- Paso 2: Notas clínicas antiguas ---")

        old_notes_qs = ClinicalNote.objects.filter(
            created_at__lt=cutoff_date,
            is_signed=False,  # Signed notes are immutable
        ).exclude(content="[REDACTED - Retention period expired]")

        count = old_notes_qs.count()
        self.stdout.write(f"Notas clínicas para anonimizar: {count}")

        if count == 0:
            self.stdout.write("  Nada que procesar.")
            return

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"  [DRY RUN] Se anonimizarían {count} notas clínicas."
                )
            )
            return

        redacted_content = "[REDACTED - Retention period expired]"
        processed = 0

        for note in old_notes_qs.iterator(chunk_size=100):
            note_id_str = str(note.id)

            # Get patient and clinic for audit log
            try:
                clinic = note.patient.clinic
            except Patient.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Paciente no encontrado para nota {note_id_str}. Saltando."
                    )
                )
                continue

            note.content = redacted_content
            note.save(update_fields=["content", "updated_at"])

            # Log action
            try:
                AuditLog.objects.create(
                    clinic=clinic,
                    user=None,
                    action="patients.clinicalnote.retention_anonymized",
                    resource_type="ClinicalNote",
                    resource_id=note_id_str,
                    details={
                        "reason": "NOM-024 retention expired",
                        "note_title": note.title,
                        "patient_id": str(note.patient_id),
                        "cutoff_date": cutoff_date.isoformat(),
                    },
                    result="success",
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Auditoría no creada para nota {note_id_str}: {e}"
                    )
                )

            processed += 1

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ {processed} notas clínicas anonimizadas.")
        )
