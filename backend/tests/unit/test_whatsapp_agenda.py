"""
Unit tests for WhatsApp appointment agenda (agenda-whatsapp change).

Covers:
- _resolve_clinic lookup (task 3.4)
- Consent check in send_appointment_reminders (task 3.5)
- reset_whatsapp_on_reschedule signal (task 3.6)
- Webhook → task wiring integration (task 3.7)
"""

from unittest.mock import patch

import pytest


@pytest.mark.unit
@pytest.mark.django_db
class TestClinicResolution:
    """Test _resolve_clinic phone number → clinic ID resolution."""

    def test_matches_by_phone(self, create_clinic):
        """Clinic with matching phone number is found."""
        from notifications.views import WebhookView

        clinic = create_clinic()
        clinic.phone = "+525512345678"
        clinic.save(update_fields=["phone"])

        view = WebhookView()
        result = view._resolve_clinic("+525512345678")
        assert result == str(clinic.id)

    def test_matches_by_cfdi_config_phone(self, create_clinic):
        """Clinic with phone stored in cfdi_config is found."""
        from notifications.views import WebhookView

        clinic = create_clinic()
        clinic.phone = "+525511111111"
        clinic.cfdi_config = {"phone": "+525599999999"}
        clinic.save(update_fields=["phone", "cfdi_config"])

        view = WebhookView()
        result = view._resolve_clinic("+525599999999")
        assert result == str(clinic.id)

    def test_no_match_returns_none(self, create_clinic):
        """Non-matching phone returns None."""
        from notifications.views import WebhookView

        clinic = create_clinic()
        clinic.phone = "+525512345678"
        clinic.save(update_fields=["phone"])

        view = WebhookView()
        result = view._resolve_clinic("+525500000000")
        assert result is None

    def test_multiple_clinics_matches_first(self, create_clinic):
        """When multiple clinics exist, first match is returned."""
        from notifications.views import WebhookView

        clinic_a = create_clinic()
        clinic_a.name = "Clinic A"
        clinic_a.phone = "+525511111111"
        clinic_a.save(update_fields=["name", "phone"])

        clinic_b = create_clinic()
        clinic_b.name = "Clinic B"
        clinic_b.phone = "+525522222222"
        clinic_b.save(update_fields=["name", "phone"])

        view = WebhookView()
        result = view._resolve_clinic("+525522222222")
        assert result == str(clinic_b.id)


@pytest.mark.unit
@pytest.mark.django_db
class TestConsentCheck:
    """Test consent filtering in send_appointment_reminders."""

    def test_skips_when_whatsapp_opt_in_false(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """Reminder is skipped when patient.whatsapp_opt_in is False."""
        from celery_app.tasks import send_appointment_reminders

        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        patient.phone = "+525512345678"
        patient.whatsapp_opt_in = False
        patient.save(update_fields=["phone", "whatsapp_opt_in"])

        appt_type = create_appointment_type(clinic=clinic)
        create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="scheduled",
        )

        with patch(
            "notifications.services.twilio_service.TwilioService"
        ) as mock_twilio_class:
            mock_twilio = mock_twilio_class.return_value
            mock_twilio.send_message.return_value = {"sid": "SM123", "status": "queued"}

            result = send_appointment_reminders()

            # Should not send — consent not confirmed
            assert result["sent"] == 0
            assert result["failed"] == 0

    def test_skips_when_no_signed_consent_record(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """Reminder is skipped when PatientConsent WhatsApp signed record is missing."""
        from celery_app.tasks import send_appointment_reminders

        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        patient.phone = "+525512345678"
        patient.whatsapp_opt_in = True
        patient.save(update_fields=["phone", "whatsapp_opt_in"])

        appt_type = create_appointment_type(clinic=clinic)
        create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="scheduled",
        )

        with patch(
            "notifications.services.twilio_service.TwilioService"
        ) as mock_twilio_class:
            mock_twilio = mock_twilio_class.return_value
            mock_twilio.send_message.return_value = {"sid": "SM123", "status": "queued"}

            result = send_appointment_reminders()

            assert result["sent"] == 0
            assert result["failed"] == 0

    def test_sends_when_consent_is_complete(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """Reminder IS sent when both opt_in and PatientConsent are satisfied."""
        from celery_app.tasks import send_appointment_reminders
        from patients.models import PatientConsent

        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        patient.phone = "+525512345678"
        patient.whatsapp_opt_in = True
        patient.save(update_fields=["phone", "whatsapp_opt_in"])

        # Create signed WhatsApp consent
        PatientConsent.objects.create(
            patient=patient,
            consent_type="whatsapp",
            signed=True,
            content="Consent for WhatsApp messaging",
        )

        appt_type = create_appointment_type(clinic=clinic)
        create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="scheduled",
        )

        with patch(
            "notifications.services.twilio_service.TwilioService"
        ) as mock_twilio_class:
            mock_twilio = mock_twilio_class.return_value
            mock_twilio.send_message.return_value = {"sid": "SM123", "status": "queued"}

            result = send_appointment_reminders()

            assert result["sent"] == 1
            assert result["failed"] == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestWhatsAppSignal:
    """Test reset_whatsapp_on_reschedule post_save signal."""

    def test_resets_whatsapp_sent_on_reschedule(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """Completed → scheduled transition resets whatsapp_sent to False."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)

        appt_type = create_appointment_type(clinic=clinic)
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="completed",
        )
        # Set whatsapp_sent flag
        appt.whatsapp_sent = True
        appt.save(update_fields=["whatsapp_sent"])

        # Reschedule: change status to scheduled
        appt.status = "scheduled"
        appt.save(update_fields=["status"])

        appt.refresh_from_db()
        assert appt.whatsapp_sent is False

    def test_does_not_reset_on_normal_status_change(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """Scheduled → confirmed transition does NOT reset whatsapp_sent."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)

        appt_type = create_appointment_type(clinic=clinic)
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="scheduled",
        )
        appt.whatsapp_sent = True
        appt.save(update_fields=["whatsapp_sent"])

        # Normal transition: mark as confirmed
        appt.status = "confirmed"
        appt.save(update_fields=["status"])

        appt.refresh_from_db()
        assert appt.whatsapp_sent is True  # Should NOT have been reset

    def test_does_not_reset_on_new_appointment(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
    ):
        """New appointments (created) do not trigger reset logic."""
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)

        appt_type = create_appointment_type(clinic=clinic)

        # Create a brand-new appointment — signal should not crash
        appt = create_appointment(
            clinic=clinic,
            patient=patient,
            dentist=dentist,
            appt_type=appt_type,
            status="scheduled",
        )
        assert (
            appt.whatsapp_sent is False
        )  # Default is False, signal shouldn't override


@pytest.mark.integration
@pytest.mark.django_db
class TestWebhookTaskWiring:
    """Integration test: webhook POST → WhatsAppWebhook created → task called."""

    def test_webhook_creates_record_and_dispatches_task(self, settings, create_clinic):
        """POST to webhook creates WhatsAppWebhook and calls process_whatsapp_response."""
        import base64
        import hashlib
        import hmac

        from rest_framework.test import APIClient

        from notifications.models import WhatsAppWebhook

        clinic = create_clinic()
        clinic.phone = "+525500000000"  # Match the To number
        clinic.save(update_fields=["phone"])

        settings.TWILIO_AUTH_TOKEN = "test_token"

        client = APIClient()

        url = "http://testserver/api/v1/whatsapp/webhook/"
        params = {
            "MessageSid": "SM-WIRING-TEST",
            "From": "whatsapp:+525511111111",
            "To": "whatsapp:+525500000000",
            "Body": "CONFIRMAR",
            "AccountSid": "AC-test",
        }

        # Compute valid signature
        sorted_params = sorted(params.items())
        data = url
        for key, value in sorted_params:
            data += key + value

        digest = hmac.new(
            "test_token".encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(digest).decode("utf-8")

        with patch("celery_app.tasks.process_whatsapp_response.delay") as mock_delay:
            response = client.post(
                url,
                data=params,
                format="multipart",
                HTTP_X_TWILIO_SIGNATURE=signature,
            )

            assert response.status_code == 200

            # Webhook record must exist
            webhook = WhatsAppWebhook.objects.filter(
                twilio_sid="SM-WIRING-TEST"
            ).first()
            assert webhook is not None
            assert webhook.from_number == "+525511111111"
            assert webhook.message_body == "CONFIRMAR"

            # Celery task must have been dispatched with the webhook ID
            mock_delay.assert_called_once_with(str(webhook.id))
