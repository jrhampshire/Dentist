"""
Dental Records models for ClínicaSaaS Dental MX.

Models:
- DentalRecordEntry: Append-only odontogram entry (immutable once created)
- Tooth: Materialized current state per patient+tooth_fdi
- ToothSurface: Materialized current state per tooth+surface
- MedicalHistory: Versioned medical history with typed antecedents
- VitalSigns: Vital signs per patient, optionally linked to appointment
- PatientImage: Image upload (photos, X-rays) with thumbnail generation
- TreatmentPlan: Multi-phase treatment plan
- TreatmentPhase: Phase within a treatment plan
- TreatmentProcedure: Individual procedure within a phase

All models inherit tenant isolation via patient → clinic FK chain.
"""

import os
import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from dental_records.choices import ImageType, Surface, ToothCondition


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

# Valid FDI tooth numbers:
# Permanent: 11-48 (ISO 3950: upper right 11-18, upper left 21-28,
#                    lower left 31-38, lower right 41-48)
# Primary/deciduous: 51-85 (upper right 51-55, upper left 61-65,
#                           lower left 71-75, lower right 81-85)
VALID_FDI_CODES: set[int] = set(
    list(range(11, 19))  # upper right permanent
    + list(range(21, 29))  # upper left permanent
    + list(range(31, 39))  # lower left permanent
    + list(range(41, 49))  # lower right permanent
    + list(range(51, 56))  # upper right primary
    + list(range(61, 66))  # upper left primary
    + list(range(71, 76))  # lower left primary
    + list(range(81, 86))  # lower right primary
)


def validate_fdi(value: int) -> None:
    """Validate that an FDI tooth number is within the valid range (11-48 or 51-85)."""
    if value not in VALID_FDI_CODES:
        raise ValidationError(
            f"{value} no es un código FDI válido. "
            f"Debe estar entre 11-48 (permanentes) o 51-85 (primarios)."
        )


def sanitize_filename(filename: str) -> str:
    """Remove path separators and keep only safe characters."""
    return os.path.basename(filename).replace(" ", "_")


def get_image_path(instance: "PatientImage", filename: str) -> str:
    """Generate storage path: patients/{patient_id}/images/{image_type}/{uuid}_{sanitized_name}"""
    safe_name = sanitize_filename(filename)
    return f"patients/{instance.patient_id}/images/{instance.image_type}/{instance.id}_{safe_name}"


# ─────────────────────────────────────────────────────────────────────────
# 1. DentalRecordEntry — Append-only odontogram entry
# ─────────────────────────────────────────────────────────────────────────


class DentalRecordEntry(models.Model):
    """
    Immutable odontogram entry recording a condition for a tooth+surface.

    Once created, entries CANNOT be updated or deleted (append-only audit trail
    for NOM-004 compliance). The post_save signal materializes current state
    into Tooth and ToothSurface models.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="dental_records",
    )
    tooth_fdi = models.IntegerField(validators=[validate_fdi])
    surface = models.CharField(max_length=20, choices=Surface.choices)
    condition = models.CharField(max_length=20, choices=ToothCondition.choices)
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dental_records_entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "tooth_fdi"], name="idx_dre_patient_tooth"),
            models.Index(fields=["patient", "created_at"], name="idx_dre_patient_date"),
        ]

    def __str__(self) -> str:
        return (
            f"Diente {self.tooth_fdi} {self.get_surface_display()} "
            f"— {self.get_condition_display()} ({self.patient_id})"
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Prevent updates to existing entries (append-only).

        Uses the same pattern as AuditLog: only block saves when the row
        already exists in the database, allowing force_insert for new rows.
        """
        if self.pk and not kwargs.get("force_insert"):
            try:
                DentalRecordEntry.objects.get(pk=self.pk)
                raise ValidationError(
                    "Las entradas del odontograma son inmutables. "
                    "No se pueden modificar registros existentes."
                )
            except DentalRecordEntry.DoesNotExist:
                pass  # New object with explicit pk — allow create
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Prevent deletion of odontogram entries (append-only)."""
        raise ValidationError(
            "Las entradas del odontograma son inmutables. "
            "No se pueden eliminar registros existentes."
        )


# ─────────────────────────────────────────────────────────────────────────
# 2. Tooth — Materialized current state per patient+tooth_fdi
# ─────────────────────────────────────────────────────────────────────────


class Tooth(models.Model):
    """
    Materialized current state of a tooth for a patient.

    Updated automatically by DentalRecordEntry post_save signal.
    Represents the LATEST condition recorded for this tooth.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="teeth",
    )
    tooth_fdi = models.IntegerField(validators=[validate_fdi])
    condition = models.CharField(max_length=20, choices=ToothCondition.choices)
    last_entry = models.ForeignKey(
        DentalRecordEntry,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dental_records_teeth"
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "tooth_fdi"],
                name="uq_tooth_patient_fdi",
            ),
        ]
        indexes = [
            models.Index(
                fields=["patient", "condition"], name="idx_tooth_patient_cond"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Diente {self.tooth_fdi} — {self.get_condition_display()} "
            f"({self.patient_id})"
        )


# ─────────────────────────────────────────────────────────────────────────
# 3. ToothSurface — Materialized current state per tooth+surface
# ─────────────────────────────────────────────────────────────────────────


class ToothSurface(models.Model):
    """
    Materialized current state of a tooth surface.

    Updated automatically by DentalRecordEntry post_save signal.
    Each tooth can have up to 5 surface entries (permanent: mesial,
    distal, buccal, lingual, occlusal; primary: no occlusal).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tooth = models.ForeignKey(
        Tooth,
        on_delete=models.CASCADE,
        related_name="surfaces",
    )
    surface = models.CharField(max_length=20, choices=Surface.choices)
    condition = models.CharField(max_length=20, choices=ToothCondition.choices)
    last_entry = models.ForeignKey(
        DentalRecordEntry,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dental_records_tooth_surfaces"
        constraints = [
            models.UniqueConstraint(
                fields=["tooth", "surface"],
                name="uq_tooth_surface",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.tooth} — {self.get_surface_display()}: "
            f"{self.get_condition_display()}"
        )


# ─────────────────────────────────────────────────────────────────────────
# 4. MedicalHistory — Versioned medical history
# ─────────────────────────────────────────────────────────────────────────


class MedicalHistory(models.Model):
    """
    Versioned medical history per patient.

    Each patient has one active record (is_active=True) and a version
    chain of previous records. Upsert creates a new version with
    version = max_existing_version + 1 and deactivates the previous one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_histories",
    )
    version = models.IntegerField(default=1)

    # Five typed antecedents per NOM-004-SSA3-2012
    antecedentes_patologicos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de { "enfermedad": str, "notas": str }',
    )
    antecedentes_quirurgicos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de { "procedimiento": str, "fecha": str, "notas": str }',
    )
    antecedentes_alergicos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de { "alergeno": str, "reaccion": str, "notas": str }',
    )
    antecedentes_farmacologicos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de { "medicamento": str, "dosis": str, "notas": str }',
    )
    antecedentes_familiares = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de { "parentesco": str, "enfermedad": str, "notas": str }',
    )

    # Chief complaint and current illness
    motivo_consulta = models.TextField(
        blank=True,
        default="",
        verbose_name="Motivo de consulta",
    )
    enfermedad_actual = models.TextField(
        blank=True,
        default="",
        verbose_name="Enfermedad actual",
    )

    # Active flag for version tracking
    is_active = models.BooleanField(default=True)

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_medical_histories",
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_medical_histories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dental_records_medical_histories"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "version"],
                name="uq_medical_history_patient_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=["patient", "is_active"],
                name="idx_mh_patient_active",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Historia Médica v{self.version} — "
            f"{self.patient_id} "
            f"({'Activo' if self.is_active else 'Histórico'})"
        )


# ─────────────────────────────────────────────────────────────────────────
# 5. VitalSigns — Vital signs recording
# ─────────────────────────────────────────────────────────────────────────


class VitalSigns(models.Model):
    """
    Vital signs recorded for a patient, optionally linked to an appointment.

    BP validation: systolic must be > diastolic (enforced in clean()).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="vital_signs",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vital_signs",
    )

    # Blood pressure (mmHg)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)

    # Heart rate (bpm)
    heart_rate = models.IntegerField(null=True, blank=True)

    # Temperature (°C)
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )

    # Weight (kg)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Height (m)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    recorded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dental_records_vital_signs"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["patient", "recorded_at"], name="idx_vs_patient_date"),
        ]

    def __str__(self) -> str:
        bp = ""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            bp = f"TA {self.blood_pressure_systolic}/{self.blood_pressure_diastolic} "
        return (
            f"Signos Vitales {bp}— {self.patient_id} "
            f"({self.recorded_at.strftime('%Y-%m-%d %H:%M')})"
        )

    def clean(self) -> None:
        """Validate blood pressure: systolic must be > diastolic."""
        super().clean()
        if (
            self.blood_pressure_systolic is not None
            and self.blood_pressure_diastolic is not None
            and self.blood_pressure_systolic <= self.blood_pressure_diastolic
        ):
            raise ValidationError(
                "La presión sistólica debe ser mayor que la diastólica."
            )


# ─────────────────────────────────────────────────────────────────────────
# 6. PatientImage — Image upload with metadata
# ─────────────────────────────────────────────────────────────────────────


class PatientImage(models.Model):
    """
    Patient image (photo, X-ray, document) stored via django-storages.

    Thumbnail is auto-generated on save via Pillow (for images; skipped for PDFs).
    Images are served through Django proxy views for tenant enforcement,
    never via direct S3 URLs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="images",
    )
    tooth_fdi = models.IntegerField(
        null=True,
        blank=True,
        validators=[validate_fdi],
        help_text="Optional link to a specific tooth",
    )
    image_type = models.CharField(
        max_length=30,
        choices=ImageType.choices,
        default=ImageType.PHOTO,
    )
    image = models.ImageField(upload_to=get_image_path)
    thumbnail = models.ImageField(
        upload_to=get_image_path,
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True, default="")
    file_size = models.IntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes",
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="MIME type of the uploaded file",
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dental_records_patient_images"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["patient", "image_type"], name="idx_pi_patient_type"),
            models.Index(fields=["patient", "tooth_fdi"], name="idx_pi_patient_tooth"),
        ]

    def __str__(self) -> str:
        tooth_label = f"Diente {self.tooth_fdi}" if self.tooth_fdi else "Sin diente"
        return (
            f"[{self.get_image_type_display()}] {tooth_label} "
            f"— {self.patient_id} ({self.uploaded_at.strftime('%Y-%m-%d')})"
        )


# ─────────────────────────────────────────────────────────────────────────
# 7. TreatmentPlan — Multi-phase treatment plan
# ─────────────────────────────────────────────────────────────────────────


class TreatmentPlan(models.Model):
    """
    Multi-phase treatment plan for a patient.

    Contains one or more TreatmentPhases, each with their own procedures.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="treatment_plans",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dental_records_treatment_plans"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Plan: {self.name} [{self.get_status_display()}] — {self.patient_id}"


# ─────────────────────────────────────────────────────────────────────────
# 8. TreatmentPhase — Phase within a treatment plan
# ─────────────────────────────────────────────────────────────────────────


class TreatmentPhase(models.Model):
    """
    A phase within a treatment plan, executed in order.

    Each phase contains one or more TreatmentProcedures.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Completado"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        TreatmentPlan,
        on_delete=models.CASCADE,
        related_name="phases",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    order = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:
        db_table = "dental_records_treatment_phases"
        ordering = ["order"]

    def __str__(self) -> str:
        return (
            f"Fase {self.order}: {self.name} [{self.get_status_display()}] "
            f"— Plan {self.plan_id}"
        )


# ─────────────────────────────────────────────────────────────────────────
# 9. TreatmentProcedure — Procedure within a phase
# ─────────────────────────────────────────────────────────────────────────


class TreatmentProcedure(models.Model):
    """
    An individual procedure within a treatment phase.

    Can be optionally linked to a specific tooth_fdi and/or an appointment.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", "Planeado"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Realizado"
        CANCELLED = "cancelled", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phase = models.ForeignKey(
        TreatmentPhase,
        on_delete=models.CASCADE,
        related_name="procedures",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="treatment_procedures",
    )
    tooth_fdi = models.IntegerField(
        null=True,
        blank=True,
        validators=[validate_fdi],
    )
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "dental_records_treatment_procedures"
        ordering = ["phase__order", "id"]

    def __str__(self) -> str:
        tooth_label = f"Diente {self.tooth_fdi}" if self.tooth_fdi else "Genérico"
        return f"[{self.get_status_display()}] {tooth_label} — {self.description[:60]}"
