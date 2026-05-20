"""
WhatsApp Notification serializers.

Serializers:
- NotificationLogSerializer: Read-only log entries
- WhatsAppWebhookSerializer: Read-only webhook entries
- SendTestMessageSerializer: Input for sending test messages
"""

from rest_framework import serializers

from notifications.models import NotificationLog, WhatsAppWebhook


# ---------------------------------------------------------------------------
# NotificationLog Serializers
# ---------------------------------------------------------------------------


class NotificationLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for notification log entries."""

    patient_name = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    channel_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "clinic",
            "patient",
            "patient_name",
            "appointment",
            "channel",
            "channel_display",
            "template",
            "status",
            "status_display",
            "recipient",
            "content",
            "provider_id",
            "error_message",
            "sent_at",
            "delivered_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_patient_name(self, obj: NotificationLog) -> str | None:
        if obj.patient:
            return obj.patient.full_name
        return None

    def get_status_display(self, obj: NotificationLog) -> str:
        return obj.get_status_display()

    def get_channel_display(self, obj: NotificationLog) -> str:
        return obj.get_channel_display()


# ---------------------------------------------------------------------------
# WhatsAppWebhook Serializers
# ---------------------------------------------------------------------------


class WhatsAppWebhookSerializer(serializers.ModelSerializer):
    """Read-only serializer for webhook entries."""

    direction_display = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppWebhook
        fields = [
            "id",
            "clinic",
            "patient",
            "patient_name",
            "from_number",
            "to_number",
            "message_body",
            "direction",
            "direction_display",
            "twilio_sid",
            "processed",
            "action_taken",
            "received_at",
            "processed_at",
        ]
        read_only_fields = fields

    def get_direction_display(self, obj: WhatsAppWebhook) -> str:
        return obj.get_direction_display()

    def get_patient_name(self, obj: WhatsAppWebhook) -> str | None:
        if obj.patient:
            return obj.patient.full_name
        return None


# ---------------------------------------------------------------------------
# Send Test Message Serializer
# ---------------------------------------------------------------------------


class SendTestMessageSerializer(serializers.Serializer):
    """Serializer for sending a test WhatsApp message."""

    recipient = serializers.CharField(
        max_length=50,
        help_text="Phone number in E.164 format (e.g., +5215512345678)",
    )
    template = serializers.CharField(
        max_length=100,
        default="test_message",
        help_text="Template name to use",
    )
    variables = serializers.JSONField(
        default=dict,
        required=False,
        help_text="Template variables as key-value pairs",
    )

    def validate_recipient(self, value: str) -> str:
        """Validate phone number format."""
        value = value.strip()
        if not value.startswith("+"):
            raise serializers.ValidationError(
                "El número debe estar en formato E.164 (e.g., +5215512345678)."
            )
        if len(value) < 8:
            raise serializers.ValidationError(
                "El número de teléfono es demasiado corto."
            )
        return value
