"""
Clinics app — Clinic (tenant) model and OnboardingStep tracking.

Clinic: Full tenant model with RFC, plan, subscription, email verification, and settings.
OnboardingStep: Tracks progress through the standard onboarding flow.
"""

import uuid

from django.db import models


class Clinic(models.Model):
    """
    Clinic (tenant) model for ClínicaSaaS.

    Each clinic is an isolated tenant with its own users, patients,
    appointments, inventory, and invoices.
    """

    class Plan(models.TextChoices):
        FREE = "free", "Free"
        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    rfc = models.CharField(max_length=13, unique=True, db_index=True)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.JSONField(default=dict, blank=True)
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=128, blank=True, null=True)
    email_verification_expires = models.DateTimeField(blank=True, null=True)
    subscription_start = models.DateField(blank=True, null=True)
    subscription_end = models.DateField(blank=True, null=True)
    onboarding_completed = models.BooleanField(default=False)
    settings = models.JSONField(default=dict, blank=True)
    # CFDI config stored as JSON (actual CSD files stored in S3/MinIO)
    cfdi_config = models.JSONField(default=dict, blank=True)
    stamps_remaining = models.PositiveIntegerField(default=50)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinics"
        indexes = [
            models.Index(fields=["rfc"], name="idx_clinics_rfc"),
            models.Index(fields=["status"], name="idx_clinics_status"),
            models.Index(fields=["plan"], name="idx_clinics_plan"),
            models.Index(fields=["email_verified"], name="idx_clinics_email_verified"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    @property
    def is_active(self) -> bool:
        """Check if the clinic is active and verified."""
        return self.status == self.Status.ACTIVE and self.email_verified

    def verify_email(self, token: str) -> bool:
        """Verify email with token. Returns True if successful."""
        if (
            self.email_verification_token == token
            and self.email_verification_expires
            and self.email_verification_expires > models.functions.Now()
        ):
            self.email_verified = True
            self.email_verification_token = ""
            self.email_verification_expires = None
            self.save(
                update_fields=[
                    "email_verified",
                    "email_verification_token",
                    "email_verification_expires",
                    "updated_at",
                ]
            )
            return True
        return False

    def generate_verification_token(self) -> str:
        """Generate a new email verification token with 24h expiry."""
        import secrets
        from django.utils import timezone

        self.email_verification_token = secrets.token_urlsafe(48)
        self.email_verification_expires = timezone.now() + timezone.timedelta(hours=24)
        self.save(
            update_fields=[
                "email_verification_token",
                "email_verification_expires",
                "updated_at",
            ]
        )
        return self.email_verification_token

    def complete_onboarding(self) -> None:
        """Mark onboarding as complete and activate the clinic."""
        self.onboarding_completed = True
        if self.email_verified and self.status == self.Status.PENDING:
            self.status = self.Status.ACTIVE
        self.save(update_fields=["onboarding_completed", "status", "updated_at"])


class OnboardingStep(models.Model):
    """
    Track onboarding progress for a clinic.

    Standard steps:
    - clinic_info: Basic clinic information
    - team_setup: Add team members
    - schedule_config: Configure working hours
    - patient_import: Import existing patients
    - fiscal_config: Set up CFDI fiscal data
    - whatsapp_config: Configure WhatsApp notifications
    """

    class StepName(models.TextChoices):
        CLINIC_INFO = "clinic_info", "Información de la clínica"
        TEAM_SETUP = "team_setup", "Configuración del equipo"
        SCHEDULE_CONFIG = "schedule_config", "Configuración de horarios"
        PATIENT_IMPORT = "patient_import", "Importación de pacientes"
        FISCAL_CONFIG = "fiscal_config", "Configuración fiscal"
        WHATSAPP_CONFIG = "whatsapp_config", "Configuración de WhatsApp"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name="onboarding_steps",
    )
    step_name = models.CharField(max_length=50, choices=StepName.choices)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "onboarding_steps"
        unique_together = ["clinic", "step_name"]
        ordering = ["created_at"]

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return f"{status} {self.clinic.name} — {self.step_name}"

    def mark_complete(self, metadata: dict | None = None) -> None:
        """Mark this step as completed."""
        from django.utils import timezone

        self.completed = True
        self.completed_at = timezone.now()
        if metadata:
            self.metadata = metadata
        self.save(update_fields=["completed", "completed_at", "metadata"])
