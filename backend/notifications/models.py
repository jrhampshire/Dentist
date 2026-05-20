"""
WhatsApp Notification models.

Models:
- NotificationLog: Log of all outbound/inbound notification messages
- WhatsAppWebhook: Inbound webhook events from Twilio

All models enforce tenant isolation via clinic FK + RLS.
"""

import uuid

from django.db import models


# ---------------------------------------------------------------------------
# NotificationLog Model
# ---------------------------------------------------------------------------


class NotificationLog(models.Model):
    """
    Log of all notification messages sent via WhatsApp (or other channels).

    Tracks the full lifecycle: queued → sent → delivered → read/failed.
    Stores provider response for debugging and audit purposes.
    """

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        QUEUED = "queued", "En cola"
        SENT = "sent", "Enviado"
        DELIVERED = "delivered", "Entregado"
        READ = "read", "Leído"
        FAILED = "failed", "Fallido"
        UNDELIVERED = "undelivered", "No entregado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="notification_logs",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
    )

    # Message metadata
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.WHATSAPP,
    )
    template = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Template name used (e.g., appointment_reminder)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    recipient = models.CharField(
        max_length=50,
        help_text="Phone number or email of the recipient",
    )
    content = models.TextField(help_text="Rendered message content")

    # Provider tracking
    provider_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Twilio message SID or equivalent",
    )
    provider_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full provider API response",
    )
    error_message = models.TextField(blank=True, default="")

    # Timestamps
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["clinic", "status"], name="idx_notif_logs_clinic_status"
            ),
            models.Index(
                fields=["clinic", "channel"], name="idx_notif_logs_clinic_channel"
            ),
            models.Index(
                fields=["patient", "created_at"], name="idx_notif_logs_patient_date"
            ),
            models.Index(
                fields=["appointment", "created_at"],
                name="idx_notif_logs_appt_date",
            ),
            models.Index(fields=["provider_id"], name="idx_notif_logs_provider_id"),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(recipient=""),
                name="chk_notif_log_recipient_not_empty",
            ),
            models.CheckConstraint(
                check=~models.Q(content=""),
                name="chk_notif_log_content_not_empty",
            ),
        ]

    def __str__(self) -> str:
        patient_name = self.patient.full_name if self.patient else "N/A"
        return f"[{self.get_status_display()}] {self.channel} → {patient_name} ({self.recipient})"


# ---------------------------------------------------------------------------
# WhatsAppWebhook Model
# ---------------------------------------------------------------------------


class WhatsAppWebhook(models.Model):
    """
    Inbound webhook events from Twilio (WhatsApp).

    Stores every incoming message and status callback for audit and
    processing purposes. Each event has a unique Twilio SID.
    """

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Entrante"
        OUTBOUND = "outbound", "Saliente"
        STATUS = "status", "Status callback"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="whatsapp_webhooks",
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_webhooks",
    )

    # Message details
    from_number = models.CharField(max_length=50)
    to_number = models.CharField(max_length=50)
    message_body = models.TextField(blank=True, default="")
    direction = models.CharField(
        max_length=20,
        choices=Direction.choices,
        default=Direction.INBOUND,
    )

    # Twilio tracking
    twilio_sid = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique Twilio message/event SID",
    )

    # Processing status
    processed = models.BooleanField(
        default=False,
        help_text="Whether this webhook has been processed",
    )
    action_taken = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Description of action taken (e.g., 'appointment_confirmed')",
    )

    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "whatsapp_webhooks"
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["twilio_sid"], name="idx_webhooks_twilio_sid"
            ),
        ]
        indexes = [
            models.Index(
                fields=["clinic", "processed"], name="idx_webhooks_clinic_processed"
            ),
            models.Index(
                fields=["from_number", "received_at"],
                name="idx_webhooks_from_date",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_direction_display()}] {self.from_number} → {self.to_number} (SID: {self.twilio_sid[:12]}...)"
