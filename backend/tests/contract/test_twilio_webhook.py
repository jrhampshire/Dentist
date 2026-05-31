"""
Contract tests for Twilio webhook (Task 12.11).

Tests:
- Mock Twilio signature validation
- Inbound message parsing
- Webhook endpoint behavior
"""

import base64
import hashlib
import hmac
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from notifications.services.twilio_service import TwilioService


@pytest.mark.contract
class TestTwilioSignatureValidation:
    """Test Twilio signature validation logic."""

    def _compute_signature(self, url, params, auth_token):
        """Compute Twilio signature for testing."""
        sorted_params = sorted(params.items())
        data = url
        for key, value in sorted_params:
            data += key + value

        digest = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        return base64.b64encode(digest).decode("utf-8")

    def test_valid_signature_accepted(self, settings):
        settings.TWILIO_AUTH_TOKEN = "test_auth_token_123"

        url = "https://example.com/webhook"
        params = {
            "MessageSid": "SM123",
            "From": "whatsapp:+5215512345678",
            "Body": "CONFIRMAR",
        }

        signature = self._compute_signature(url, params, "test_auth_token_123")

        assert TwilioService.validate_signature(url, params, signature) is True

    def test_invalid_signature_rejected(self, settings):
        settings.TWILIO_AUTH_TOKEN = "test_auth_token_123"

        url = "https://example.com/webhook"
        params = {
            "MessageSid": "SM123",
            "From": "whatsapp:+5215512345678",
            "Body": "CONFIRMAR",
        }

        # Wrong signature
        assert TwilioService.validate_signature(url, params, "wrong_signature") is False

    def test_tampered_params_rejected(self, settings):
        settings.TWILIO_AUTH_TOKEN = "test_auth_token_123"

        url = "https://example.com/webhook"
        original_params = {
            "MessageSid": "SM123",
            "From": "whatsapp:+5215512345678",
            "Body": "CONFIRMAR",
        }

        signature = self._compute_signature(url, original_params, "test_auth_token_123")

        # Tamper with the body
        tampered_params = dict(original_params)
        tampered_params["Body"] = "BAJA"

        assert (
            TwilioService.validate_signature(url, tampered_params, signature) is False
        )

    def test_no_auth_token_returns_false(self, settings):
        settings.TWILIO_AUTH_TOKEN = ""

        result = TwilioService.validate_signature("url", {}, "sig")
        assert result is False


@pytest.mark.contract
class TestTwilioMessageParsing:
    """Test inbound message parsing."""

    def test_parse_confirmar(self):
        assert TwilioService.parse_response("CONFIRMAR") == "confirmar"
        assert TwilioService.parse_response("confirmo") == "confirmar"
        assert TwilioService.parse_response("si") == "confirmar"
        assert TwilioService.parse_response("sí") == "confirmar"
        assert TwilioService.parse_response("yes") == "confirmar"

    def test_parse_cancelar(self):
        assert TwilioService.parse_response("CANCELAR") == "cancelar"
        assert TwilioService.parse_response("cancelo") == "cancelar"
        assert TwilioService.parse_response("no") == "cancelar"
        assert TwilioService.parse_response("cancel") == "cancelar"

    def test_parse_baja(self):
        assert TwilioService.parse_response("BAJA") == "baja"
        assert TwilioService.parse_response("opt-out") == "baja"
        assert TwilioService.parse_response("desuscribir") == "baja"
        assert TwilioService.parse_response("no quiero") == "baja"

    def test_parse_unrecognized_returns_none(self):
        assert TwilioService.parse_response("Hola, ¿cómo estás?") is None
        assert TwilioService.parse_response("") is None
        assert TwilioService.parse_response(None) is None

    def test_parse_case_insensitive(self):
        assert TwilioService.parse_response("  Confirmar  ") == "confirmar"
        assert TwilioService.parse_response("  BAJA  ") == "baja"

    def test_baja_takes_priority(self):
        """If message contains both baja and confirmar keywords, baja wins."""
        assert TwilioService.parse_response("no quiero confirmar") == "baja"


@pytest.mark.contract
class TestTwilioStatusCallback:
    """Test status callback processing."""

    def test_process_sent_status(self):
        result = TwilioService.process_status_callback(
            {
                "MessageSid": "SM123",
                "MessageStatus": "sent",
                "To": "whatsapp:+5215512345678",
                "From": "whatsapp:+14155238886",
            }
        )

        assert result["sid"] == "SM123"
        assert result["status"] == "sent"

    def test_process_delivered_status(self):
        result = TwilioService.process_status_callback(
            {
                "MessageSid": "SM123",
                "MessageStatus": "delivered",
            }
        )

        assert result["status"] == "delivered"

    def test_process_failed_status(self):
        result = TwilioService.process_status_callback(
            {
                "MessageSid": "SM123",
                "MessageStatus": "failed",
                "ErrorCode": "30008",
                "ErrorMessage": "Unknown error",
            }
        )

        assert result["status"] == "failed"
        assert result["error_code"] == "30008"
        assert result["error_message"] == "Unknown error"

    def test_process_unknown_status_defaults_to_failed(self):
        result = TwilioService.process_status_callback(
            {
                "MessageSid": "SM123",
                "MessageStatus": "weird_status",
            }
        )

        assert result["status"] == "failed"

    def test_status_mapping(self):
        """Test all status mappings."""
        mappings = {
            "queued": "queued",
            "sending": "queued",
            "sent": "sent",
            "delivered": "delivered",
            "read": "read",
            "undelivered": "undelivered",
            "failed": "failed",
        }

        for twilio_status, expected in mappings.items():
            result = TwilioService.process_status_callback(
                {
                    "MessageStatus": twilio_status,
                }
            )
            assert result["status"] == expected, f"Failed for {twilio_status}"
