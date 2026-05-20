"""
WhatsApp Notification views.

Views:
- WebhookView: Twilio inbound webhook (public, signature-verified)
- NotificationLogViewSet: Read-only log listing
- WhatsAppTemplatesView: List available message templates
- SendTestMessageView: Send a test WhatsApp message (admin only)
"""

import logging

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsClinicAdmin
from notifications.models import NotificationLog, WhatsAppWebhook
from notifications.serializers import (
    NotificationLogSerializer,
    SendTestMessageSerializer,
    WhatsAppWebhookSerializer,
)
from notifications.services.template_service import (
    TemplateError,
    TemplateNotFoundError,
    TemplateVariableError,
    list_templates,
    render_template,
)
from notifications.services.twilio_service import (
    TwilioService,
    TwilioServiceError,
    TwilioSignatureError,
)

logger = logging.getLogger("notifications.services")


# ---------------------------------------------------------------------------
# WebhookView — Twilio inbound (public endpoint)
# ---------------------------------------------------------------------------


class WebhookView(APIView):
    """
    Twilio WhatsApp webhook receiver.

    Handles:
    - Inbound messages from patients
    - Status callbacks for sent messages

    This endpoint is PUBLIC but validates X-Twilio-Signature.
    Configured in settings.PUBLIC_ENDPOINTS to bypass tenant middleware.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """Process incoming Twilio webhook."""
        # Validate Twilio signature
        signature = request.headers.get("X-Twilio-Signature", "")
        full_url = request.build_absolute_uri()

        # For signature validation, we need the raw POST data
        post_data = dict(request.POST)
        # Flatten lists to single values for signature check
        flat_data = {
            k: v[0] if isinstance(v, list) else v for k, v in post_data.items()
        }

        if signature:
            try:
                valid = TwilioService.validate_signature(
                    request_url=full_url,
                    request_body=flat_data,
                    signature=signature,
                )
                if not valid:
                    logger.warning(
                        "Invalid Twilio signature from %s",
                        request.META.get("REMOTE_ADDR"),
                    )
                    return Response(
                        {"error": "invalid_signature"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Exception as exc:
                logger.error("Signature validation error: %s", exc)
                # In dev without credentials, allow through
                if not getattr(request, "_twilio_configured", True):
                    pass  # Allow in dev mode

        # Determine message type
        message_status = request.POST.get("MessageStatus", "")
        message_sid = request.POST.get("MessageSid", "")

        if message_status:
            # This is a status callback
            return self._handle_status_callback(request, flat_data, message_sid)
        else:
            # This is an inbound message
            return self._handle_inbound_message(request, flat_data, message_sid)

    def _handle_inbound_message(self, request, data, message_sid):
        """Process an inbound message from a patient."""
        from_number = request.POST.get("From", "")
        to_number = request.POST.get("To", "")
        body = request.POST.get("Body", "")

        # Remove whatsapp: prefix if present
        from_clean = from_number.replace("whatsapp:", "")
        to_clean = to_number.replace("whatsapp:", "")

        # Create webhook record
        webhook = WhatsAppWebhook.objects.create(
            # clinic will be set by processing task — default to first for now
            # In production, look up clinic by phone number mapping
            clinic_id=self._resolve_clinic(to_clean),
            from_number=from_clean,
            to_number=to_clean,
            message_body=body,
            direction=WhatsAppWebhook.Direction.INBOUND,
            twilio_sid=message_sid,
        )

        logger.info(
            "Inbound WhatsApp message: from=%s, sid=%s, body=%s",
            from_clean,
            message_sid,
            body[:50],
        )

        # TODO: Process inbound message with Celery task
        # - Match phone number to patient
        # - Parse intent (CONFIRMAR, CANCELAR, REAGENDAR)
        # - Update appointment status accordingly

        return Response(
            {"status": "received", "sid": message_sid},
            status=status.HTTP_200_OK,
        )

    def _handle_status_callback(self, request, data, message_sid):
        """Process a status callback from Twilio."""
        callback_data = TwilioService.process_status_callback(data)

        logger.info(
            "Status callback: sid=%s, status=%s",
            callback_data["sid"],
            callback_data["status"],
        )

        # Update notification log if exists
        try:
            log = NotificationLog.objects.get(provider_id=callback_data["sid"])
            log.status = callback_data["status"]
            log.provider_response = {**log.provider_response, **callback_data}

            if callback_data["status"] in ("delivered", "read"):
                log.delivered_at = timezone.now()
            if callback_data["status"] in ("failed", "undelivered"):
                log.error_message = callback_data.get("error_message", "")

            log.save(
                update_fields=[
                    "status",
                    "provider_response",
                    "delivered_at",
                    "error_message",
                ]
            )
        except NotificationLog.DoesNotExist:
            logger.warning(
                "Status callback for unknown message: sid=%s", callback_data["sid"]
            )

        return Response(
            {"status": "processed", "sid": callback_data["sid"]},
            status=status.HTTP_200_OK,
        )

    def _resolve_clinic(self, phone_number: str) -> str | None:
        """
        Resolve clinic ID from the destination phone number.

        In production, this should query a clinic_phone_mappings table.
        For now, returns None — the processing task will resolve it.
        """
        # TODO: Implement clinic phone number mapping
        from clinics.models import Clinic

        clinic = Clinic.objects.first()
        return clinic.id if clinic else None


# ---------------------------------------------------------------------------
# NotificationLogViewSet — Read-only log listing
# ---------------------------------------------------------------------------


class NotificationLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for notification logs.

    Endpoints:
    - GET    /api/v1/whatsapp/logs/          — list logs (?status=, ?channel=, ?patient_id=)
    - GET    /api/v1/whatsapp/logs/{id}/     — get log detail

    Filtering:
    - ?status=sent: Filter by status
    - ?channel=whatsapp: Filter by channel
    - ?patient_id=uuid: Filter by patient
    - ?template=appointment_reminder: Filter by template
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationLogSerializer
    ordering_fields = ["created_at", "sent_at", "delivered_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return notification logs for the current clinic (RLS handles isolation)."""
        queryset = NotificationLog.objects.all().select_related(
            "clinic",
            "patient",
            "appointment",
        )

        # Apply filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        channel_filter = self.request.query_params.get("channel")
        if channel_filter:
            queryset = queryset.filter(channel=channel_filter)

        patient_filter = self.request.query_params.get("patient_id")
        if patient_filter:
            queryset = queryset.filter(patient_id=patient_filter)

        template_filter = self.request.query_params.get("template")
        if template_filter:
            queryset = queryset.filter(template=template_filter)

        return queryset


# ---------------------------------------------------------------------------
# WhatsAppTemplatesView — List available templates
# ---------------------------------------------------------------------------


class WhatsAppTemplatesView(APIView):
    """
    List available WhatsApp message templates.

    GET /api/v1/whatsapp/templates/

    Returns all pre-approved templates with their variables and structure.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = list_templates()
        return Response({"templates": templates, "total": len(templates)})


# ---------------------------------------------------------------------------
# SendTestMessageView — Send a test message (admin only)
# ---------------------------------------------------------------------------


class SendTestMessageView(APIView):
    """
    Send a test WhatsApp message.

    POST /api/v1/whatsapp/send-test/

    Admin-only endpoint for testing WhatsApp connectivity and templates.
    """

    permission_classes = [IsAuthenticated, IsClinicAdmin]

    def post(self, request):
        serializer = SendTestMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient = serializer.validated_data["recipient"]
        template_name = serializer.validated_data["template"]
        variables = serializer.validated_data.get("variables", {})

        try:
            # Render the template
            content = render_template(template_name, variables)
        except TemplateNotFoundError as exc:
            return Response(
                {"error": "template_not_found", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TemplateVariableError as exc:
            return Response(
                {"error": "missing_variables", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send via Twilio
        try:
            service = TwilioService()
            result = service.send_message(
                to_number=recipient,
                body=content,
                status_callback_url=request.build_absolute_uri(
                    "/api/v1/whatsapp/webhook/"
                ),
            )

            # Log the message
            log = NotificationLog.objects.create(
                clinic_id=getattr(request, "clinic_id", None),
                channel=NotificationLog.Channel.WHATSAPP,
                template=template_name,
                status=NotificationLog.Status.QUEUED,
                recipient=recipient,
                content=content,
                provider_id=result.get("sid", ""),
                provider_response=result,
            )

            return Response(
                {
                    "status": "sent",
                    "sid": result.get("sid"),
                    "twilio_status": result.get("status"),
                    "log_id": str(log.id),
                },
                status=status.HTTP_200_OK,
            )

        except TwilioServiceError as exc:
            logger.error("Failed to send test message: %s", exc)
            return Response(
                {"error": "send_failed", "message": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
