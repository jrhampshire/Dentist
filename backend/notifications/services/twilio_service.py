"""
Twilio WhatsApp service.

Handles:
- Sending WhatsApp messages via Twilio REST API
- X-Twilio-Signature header validation
- Status callback processing
- Exponential backoff retries (3 attempts)
- Timeout: 10s connect / 30s read
"""

import hashlib
import hmac
import logging
import time
from base64 import b64decode
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("notifications.services")

# Twilio API base URL
TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"

# Timeout tuple: (connect_timeout, read_timeout)
TIMEOUT = (10, 30)

# Retry configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0  # 1s, 2s, 4s


class TwilioServiceError(Exception):
    """Base exception for Twilio service errors."""

    pass


class TwilioSignatureError(TwilioServiceError):
    """Raised when Twilio signature validation fails."""

    pass


class TwilioService:
    """
    Service for interacting with Twilio WhatsApp API.

    Usage:
        service = TwilioService()
        result = service.send_message("+5215512345678", "Hola, tu cita es mañana...")
    """

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        whatsapp_number: str | None = None,
    ):
        self.account_sid = account_sid or getattr(settings, "TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token or getattr(settings, "TWILIO_AUTH_TOKEN", "")
        self.whatsapp_number = whatsapp_number or getattr(
            settings, "TWILIO_WHATSAPP_NUMBER", ""
        )

        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured")

    def send_message(
        self,
        to_number: str,
        body: str,
        status_callback_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp message via Twilio REST API.

        Args:
            to_number: Recipient phone in E.164 format with whatsapp: prefix
            body: Message text content
            status_callback_url: Optional webhook URL for status updates

        Returns:
            Dict with Twilio response data including 'sid', 'status', etc.

        Raises:
            TwilioServiceError: If the API call fails after retries
        """
        if not self.account_sid or not self.auth_token:
            raise TwilioServiceError("Twilio credentials not configured")

        url = f"{TWILIO_API_BASE}/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": f"whatsapp:{self.whatsapp_number}",
            "To": f"whatsapp:{to_number}",
            "Body": body,
        }

        if status_callback_url:
            data["StatusCallback"] = status_callback_url

        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    timeout=TIMEOUT,
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "Twilio message sent: sid=%s, status=%s",
                    result.get("sid"),
                    result.get("status"),
                )
                return result

            except requests.exceptions.Timeout as exc:
                last_error = exc
                logger.warning(
                    "Twilio request timeout (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                )

            except requests.exceptions.HTTPError as exc:
                # Client errors (4xx) should not be retried
                if exc.response is not None and exc.response.status_code < 500:
                    error_body = ""
                    try:
                        error_body = exc.response.text
                    except Exception:
                        pass
                    logger.error(
                        "Twilio client error (not retried): %s — %s",
                        exc.response.status_code,
                        error_body,
                    )
                    raise TwilioServiceError(
                        f"Twilio API error {exc.response.status_code}: {error_body}"
                    ) from exc

                last_error = exc
                logger.warning(
                    "Twilio server error (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                )

            except requests.exceptions.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Twilio request failed (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    exc,
                )

            # Exponential backoff before next retry
            if attempt < MAX_RETRIES - 1:
                backoff = BACKOFF_FACTOR * (2**attempt)
                logger.debug("Backing off %.1fs before retry...", backoff)
                time.sleep(backoff)

        raise TwilioServiceError(
            f"Failed to send message after {MAX_RETRIES} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def validate_signature(
        request_url: str,
        request_body: dict[str, str],
        signature: str,
        auth_token: str | None = None,
    ) -> bool:
        """
        Validate X-Twilio-Signature header.

        Twilio signs requests by:
        1. Sorting all POST parameters alphabetically
        2. Concatenating URL + sorted params
        3. HMAC-SHA1 with auth token
        4. Base64 encoding

        Args:
            request_url: Full URL that received the request
            request_body: POST parameters as dict
            signature: X-Twilio-Signature header value
            auth_token: Twilio auth token (defaults to settings)

        Returns:
            True if signature is valid
        """
        token = auth_token or getattr(settings, "TWILIO_AUTH_TOKEN", "")
        if not token:
            logger.warning("Cannot validate signature: no auth token configured")
            return False

        # Sort parameters and build the data string
        sorted_params = sorted(request_body.items())
        data = request_url
        for key, value in sorted_params:
            data += key + value

        # Compute HMAC-SHA1
        expected = hmac.new(
            token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        expected_b64 = b64decode(expected)
        provided_b64 = b64decode(signature)

        return hmac.compare_digest(expected_b64, provided_b64)

    @staticmethod
    def parse_response(body: str) -> str | None:
        """
        Parse an inbound WhatsApp message for known commands.

        Args:
            body: Raw message text from patient

        Returns:
            One of: "confirmar", "cancelar", "baja", or None if unrecognized
        """
        if not body:
            return None

        text = body.strip().lower()

        # Normalize common variations
        confirmar_keywords = ["confirmar", "confirmo", "si", "sí", "confirm", "yes"]
        cancelar_keywords = ["cancelar", "cancelo", "no", "cancel"]
        baja_keywords = ["baja", "opt-out", "optout", "desuscribir", "no quiero"]

        if any(kw in text for kw in baja_keywords):
            return "baja"
        if any(kw in text for kw in confirmar_keywords):
            return "confirmar"
        if any(kw in text for kw in cancelar_keywords):
            return "cancelar"

        return None

    @staticmethod
    def process_status_callback(callback_data: dict[str, str]) -> dict[str, Any]:
        """
        Process a Twilio status callback.

        Args:
            callback_data: POST data from Twilio status webhook

        Returns:
            Dict with normalized status info:
            - sid: Message SID
            - status: Normalized status (sent, delivered, failed, etc.)
            - error_code: Twilio error code if any
            - error_message: Human-readable error if any
        """
        twilio_status = callback_data.get("MessageStatus", "unknown")
        status_map = {
            "queued": "queued",
            "sending": "queued",
            "sent": "sent",
            "delivered": "delivered",
            "read": "read",
            "undelivered": "undelivered",
            "failed": "failed",
        }

        return {
            "sid": callback_data.get("MessageSid", ""),
            "status": status_map.get(twilio_status, "failed"),
            "twilio_status": twilio_status,
            "error_code": callback_data.get("ErrorCode", ""),
            "error_message": callback_data.get("ErrorMessage", ""),
            "to": callback_data.get("To", ""),
            "from": callback_data.get("From", ""),
        }
