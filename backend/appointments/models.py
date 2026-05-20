"""
Appointment Scheduling models.

Models:
- AppointmentType: Types of appointments (consulta, limpieza, extracción) with duration, price, color
- Appointment: Individual scheduled appointments with status tracking
- ScheduleSlot: Recurring weekly availability configuration (e.g., Monday 9-5)

All models enforce tenant isolation via clinic FK + RLS.
"""

import uuid
from datetime import datetime, time, timedelta
from typing import Any

from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# AppointmentType Model
# ---------------------------------------------------------------------------


class AppointmentType(models.Model):
    """
    Type of dental appointment.

    Defines the duration, price, and visual color for calendar UI.
    Also includes an inventory_kit for auto-consumption on completion.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="appointment_types",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    duration_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    color = models.CharField(
        max_length=7,
        default="#4A90D9",
        help_text="Hex color for calendar UI (e.g., #4A90D9)",
    )
    inventory_kit = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {item_id, quantity} for auto-consumption",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointment_types"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["clinic", "is_active"], name="idx_appt_types_active"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.duration_minutes}min)"


# ---------------------------------------------------------------------------
# Appointment Model
# ---------------------------------------------------------------------------


class Appointment(models.Model):
    """
    Individual scheduled appointment.

    Status flow: scheduled → confirmed → in_progress → completed
    Alternative: scheduled → cancelled, scheduled → no_show
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Programada"
        CONFIRMED = "confirmed", "Confirmada"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Completada"
        CANCELLED = "cancelled", "Cancelada"
        NO_SHOW = "no_show", "No asistió"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    appointment_type = models.ForeignKey(
        AppointmentType,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    dentist = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="dentist_appointments",
        limit_choices_to={"role__in": ["dentista", "admin"]},
    )

    # Date and time
    date = models.DateField(db_index=True)
    start_time = models.TimeField(db_index=True)
    end_time = models.TimeField()

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    # Cancellation
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="cancelled_appointments",
        blank=True,
    )
    cancelled_at = models.DateTimeField(blank=True, null=True)

    # WhatsApp tracking
    whatsapp_sent = models.BooleanField(default=False)
    whatsapp_sent_at = models.DateTimeField(blank=True, null=True)
    whatsapp_response = models.CharField(
        max_length=20, blank=True, default="", null=True
    )

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_appointments",
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointments"
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["clinic", "date"], name="idx_appts_clinic_date"),
            models.Index(fields=["clinic", "status"], name="idx_appts_status"),
            models.Index(fields=["patient", "date"], name="idx_appts_patient_date"),
            models.Index(fields=["dentist", "date"], name="idx_appts_dentist_date"),
            models.Index(
                fields=["clinic", "date", "status"], name="idx_appts_date_status"
            ),
        ]
        constraints = [
            # Prevent double-booking same dentist at same time
            # Only applies to active statuses (not cancelled/no_show)
            models.UniqueConstraint(
                fields=["dentist", "date", "start_time"],
                name="uq_dentist_time_slot",
                condition=models.Q(
                    status__in=["scheduled", "confirmed", "in_progress"]
                ),
            ),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_status_display()}] {self.patient.full_name} — "
            f"{self.date} {self.start_time} ({self.dentist.get_full_name()})"
        )

    @property
    def patient_name(self) -> str:
        """Return the patient's full name."""
        return self.patient.full_name

    @property
    def dentist_name(self) -> str:
        """Return the dentist's full name."""
        return self.dentist.get_full_name()

    def cancel(self, reason: str = "", user=None) -> None:
        """Cancel this appointment."""
        if self.status in (self.Status.COMPLETED, self.Status.CANCELLED):
            raise ValueError("No se puede cancelar una cita ya completada o cancelada.")

        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.cancelled_by = user
        self.cancelled_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "cancellation_reason",
                "cancelled_by",
                "cancelled_at",
                "updated_at",
            ]
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-calculate end_time from appointment type duration if not set."""
        if not self.end_time and self.appointment_type_id:
            # We need the duration — fetch if not already loaded
            if hasattr(self, "appointment_type") and self.appointment_type:
                duration = self.appointment_type.duration_minutes
            else:
                # Fetch from DB
                try:
                    appt_type = AppointmentType.objects.get(id=self.appointment_type_id)
                    duration = appt_type.duration_minutes
                except AppointmentType.DoesNotExist:
                    duration = 30  # fallback

            start_dt = datetime.combine(self.date, self.start_time)
            end_dt = start_dt + timedelta(minutes=duration)
            self.end_time = end_dt.time()

        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ScheduleSlot Model
# ---------------------------------------------------------------------------


class ScheduleSlot(models.Model):
    """
    Recurring weekly availability configuration.

    Represents a dentist's (or clinic-wide) working hours for a specific
    day of the week. E.g., "Monday 9:00-17:00 for Dr. Pérez".

    These are NOT individual appointments — they define when slots can be booked.
    """

    class DayOfWeek(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="schedule_slots",
    )
    dentist = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="schedule_slots",
        null=True,
        blank=True,
        help_text="Null = applies to all dentists (clinic-wide schedule)",
    )
    day_of_week = models.PositiveIntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    # Optional date range for temporary schedules
    valid_from = models.DateField(blank=True, null=True)
    valid_until = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "schedule_slots"
        ordering = ["day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["clinic", "day_of_week"], name="idx_schedule_day"),
        ]

    def __str__(self) -> str:
        dentist_name = self.dentist.get_full_name() if self.dentist else "Todos"
        day_name = self.get_day_of_week_display()
        return (
            f"[{day_name}] {dentist_name} — "
            f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
        )

    def clean(self) -> None:
        """Validate that end_time is after start_time."""
        if self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio.")
