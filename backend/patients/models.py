"""
Patient Management models.

Models:
- Patient: Patient demographics, contact, medical history (encrypted fields)
- ClinicalNote: Clinical evolution notes (immutable once signed)
- PatientConsent: Consent records with signature tracking

All models enforce tenant isolation via clinic FK + RLS.
"""

import hashlib
import uuid
from typing import Any

from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Custom Manager for soft-delete
# ---------------------------------------------------------------------------


class PatientManager(models.Manager):
    """Default manager that excludes soft-deleted patients."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def get_by_natural_key(self, clinic_id, phone):
        return self.get(clinic_id=clinic_id, phone=phone, is_deleted=False)


class PatientAllManager(models.Manager):
    """Manager that includes soft-deleted patients (for admin/audit)."""

    pass


# ---------------------------------------------------------------------------
# Patient Model
# ---------------------------------------------------------------------------


class Patient(models.Model):
    """
    Patient record for a dental clinic.

    Sensitive medical fields (allergies, chronic_conditions, current_medications)
    are encrypted at rest using AES-256-GCM via the encryption service.
    """

    class Gender(models.TextChoices):
        MASCULINO = "M", "Masculino"
        FEMENINO = "F", "Femenino"
        OTRO = "O", "Otro"
        PREFIERE_NO_DECIR = "N", "Prefiere no decir"

    class BloodType(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="patients",
    )

    # Personal info
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    second_last_name = models.CharField(max_length=100, blank=True, default="")

    # Contact
    email = models.EmailField(blank=True, default="", db_index=True)
    phone = models.CharField(max_length=15, db_index=True)
    alternate_phone = models.CharField(max_length=15, blank=True, default="")

    # Identification
    curp = models.CharField(max_length=18, blank=True, default="", db_index=True)
    rfc = models.CharField(max_length=13, blank=True, default="")

    # Demographics
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        default=Gender.PREFIERE_NO_DECIR,
    )
    address = models.JSONField(default=dict, blank=True)
    occupation = models.CharField(max_length=100, blank=True, default="")

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=15, blank=True, default="")
    emergency_contact_relation = models.CharField(max_length=50, blank=True, default="")

    # Medical info
    blood_type = models.CharField(
        max_length=3,
        choices=BloodType.choices,
        blank=True,
        default="",
    )

    # Encrypted medical fields
    allergies = models.TextField(
        blank=True,
        default="",
        help_text="Encrypted: patient allergies",
    )
    chronic_conditions = models.TextField(
        blank=True,
        default="",
        help_text="Encrypted: chronic medical conditions",
    )
    current_medications = models.TextField(
        blank=True,
        default="",
        help_text="Encrypted: current medications",
    )

    # Insurance
    insurance_provider = models.CharField(max_length=200, blank=True, default="")
    insurance_policy_number = models.CharField(max_length=50, blank=True, default="")

    # Communication preferences
    whatsapp_opt_in = models.BooleanField(default=True)
    email_opt_in = models.BooleanField(default=True)

    # Consent tracking
    consent_signed = models.BooleanField(default=False)
    consent_signed_at = models.DateTimeField(blank=True, null=True)
    consent_version = models.CharField(max_length=20, blank=True, default="")

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_patients",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft delete
    is_deleted = models.BooleanField(default=False)

    # Managers
    objects = PatientManager()
    all_objects = PatientAllManager()

    class Meta:
        db_table = "patients"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(
                fields=["clinic", "last_name", "first_name"],
                name="idx_patients_name",
            ),
            models.Index(fields=["clinic", "phone"], name="idx_patients_phone"),
            models.Index(fields=["clinic", "email"], name="idx_patients_email"),
            models.Index(fields=["curp"], name="idx_patients_curp"),
            models.Index(fields=["clinic", "created_at"], name="idx_patients_created"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "phone"],
                name="uq_patient_clinic_phone",
                condition=models.Q(is_deleted=False),
            ),
        ]

    def __str__(self) -> str:
        full_name = self.full_name
        return f"{full_name} ({self.phone})"

    @property
    def full_name(self) -> str:
        """Return full name: first_name + last_name + second_last_name."""
        parts = [self.first_name, self.last_name]
        if self.second_last_name:
            parts.append(self.second_last_name)
        return " ".join(parts)

    def hard_delete(self) -> None:
        """Permanently delete the patient (bypasses soft-delete)."""
        super().delete()

    def delete(self, using=None, keep_parents=False):
        """Soft delete: mark as deleted instead of removing."""
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


# ---------------------------------------------------------------------------
# ClinicalNote Model
# ---------------------------------------------------------------------------


class ClinicalNote(models.Model):
    """
    Clinical evolution note (evolución clínica).

    Once signed (is_signed=True), the note becomes immutable.
    Immutability is enforced at:
    1. Serializer level (validation)
    2. Model level (save override)
    3. Database trigger (setup_rls command — Batch 5)

    The content field is encrypted at rest.
    """

    class NoteType(models.TextChoices):
        EVOLUTION = "evolution", "Evolución"
        DIAGNOSIS = "diagnosis", "Diagnóstico"
        TREATMENT = "treatment", "Tratamiento"
        OBSERVATION = "observation", "Observación"
        CONSENT = "consent", "Consentimiento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_notes",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinical_notes",
    )
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )

    note_type = models.CharField(
        max_length=30,
        choices=NoteType.choices,
        default=NoteType.EVOLUTION,
    )
    title = models.CharField(max_length=200)

    # Encrypted content
    content = models.TextField(
        help_text="Encrypted: clinical note content",
    )

    # Signature / immutability
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)
    signature_hash = models.CharField(max_length=64, blank=True, default="")

    # Attachments metadata
    attachments = models.JSONField(default=list, blank=True)

    # Dental odontogram fields (nullable — no behavior change for existing notes)
    tooth_fdi = models.IntegerField(
        null=True,
        blank=True,
        help_text="FDI tooth number (11-48 permanent, 51-85 primary)",
    )
    surface = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=[
            ("mesial", "Mesial"),
            ("distal", "Distal"),
            ("buccal", "Bucal"),
            ("lingual", "Lingual"),
            ("occlusal", "Oclusal"),
            ("root", "Raíz"),
        ],
        help_text="Tooth surface referenced in this note",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_notes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["patient", "created_at"], name="idx_notes_patient_date"
            ),
            models.Index(
                fields=["patient", "note_type"], name="idx_notes_patient_type"
            ),
            models.Index(fields=["appointment"], name="idx_notes_appointment"),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_note_type_display()}] {self.title} — {self.patient.full_name}"
        )

    def sign(self, user=None) -> None:
        """
        Sign the clinical note, making it immutable.

        Generates a SHA-256 hash of the content for integrity verification.
        """
        if self.is_signed:
            raise ValueError("Esta nota ya está firmada. No se puede modificar.")

        self.is_signed = True
        self.signed_at = timezone.now()

        # Generate signature hash from content + metadata
        hash_input = f"{self.content}|{self.title}|{self.note_type}|{self.author_id}"
        self.signature_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        self.save(
            update_fields=[
                "is_signed",
                "signed_at",
                "signature_hash",
                "updated_at",
            ]
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Prevent modification of signed notes."""
        if self.pk:
            try:
                existing = ClinicalNote.objects.get(pk=self.pk)
                if existing.is_signed:
                    raise ValueError(
                        "No se puede modificar una nota clínica firmada. "
                        "Cree una nueva nota con las correcciones."
                    )
            except ClinicalNote.DoesNotExist:
                pass  # New object, no existing record

        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# PatientConsent Model
# ---------------------------------------------------------------------------


class PatientConsent(models.Model):
    """
    Patient consent record.

    Tracks consent for:
    - General treatment
    - Specific treatments
    - Data processing (privacy)
    - WhatsApp communications

    Includes signature blob (binary) and hash for verification.
    """

    class ConsentType(models.TextChoices):
        GENERAL = "general", "Consentimiento General"
        TREATMENT = "treatment", "Consentimiento de Tratamiento"
        DATA_PROCESSING = "data_processing", "Consentimiento de Datos"
        WHATSAPP = "whatsapp", "Consentimiento WhatsApp"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(
        max_length=50,
        choices=ConsentType.choices,
    )
    version = models.CharField(max_length=20, default="1.0")
    content = models.TextField(
        help_text="Consent template content at time of signing",
    )

    # Signature
    signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)
    signature_blob = models.BinaryField(blank=True, null=True)
    signature_hash = models.CharField(max_length=64, blank=True, default="")
    signed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_consents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["patient", "consent_type"], name="idx_consents_patient_type"
            ),
        ]

    def __str__(self) -> str:
        status = "Firmado" if self.signed else "Pendiente"
        return (
            f"[{self.get_consent_type_display()}] {self.patient.full_name} — {status}"
        )

    def sign(
        self,
        signature_blob: bytes | None = None,
        ip_address: str | None = None,
        user=None,
    ) -> None:
        """Mark consent as signed with signature data."""
        self.signed = True
        self.signed_at = timezone.now()
        if signature_blob:
            self.signature_blob = signature_blob
        if ip_address:
            self.ip_address = ip_address

        # Generate hash from content + metadata
        hash_input = (
            f"{self.content}|{self.consent_type}|{self.version}|{self.patient_id}"
        )
        self.signature_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        self.save(
            update_fields=[
                "signed",
                "signed_at",
                "signature_blob",
                "signature_hash",
                "ip_address",
            ]
        )
