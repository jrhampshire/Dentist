"""
Finkok SOAP client service for CFDI 4.0 stamping.

Handles communication with Finkok PAC (Proveedor Autorizado de Certificación)
for stamping, cancellation, and status checking of CFDI invoices.

SOAP Endpoints (sandbox/production):
- Stamping: https://demo-facturacion.finkok.com/servicios/soap/stamp
- Cancellation: https://demo-facturacion.finkok.com/servicios/soap/cancel
- Status: https://demo-facturacion.finkok.com/servicios/soap/obtenidosrelacionados

Timeouts: 30s connect, 60s read
Retry: Exponential backoff with 5 retries
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

logger = logging.getLogger(__name__)

# Finkok API endpoints
FINKOK_STAMP_URL = "https://demo-facturacion.finkok.com/servicios/soap/stamp"
FINKOK_CANCEL_URL = "https://demo-facturacion.finkok.com/servicios/soap/cancel"
FINKOK_STATUS_URL = (
    "https://demo-facturacion.finkok.com/servicios/soap/obtenidosrelacionados"
)

# Timeouts (connect, read)
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 60

# Retry configuration
MAX_RETRIES = 5
BASE_BACKOFF = 1.0  # seconds


@dataclass
class StampResult:
    """Result of a successful CFDI stamp."""

    success: bool
    uuid: str = ""
    xml: str = ""  # Base64-encoded signed XML
    sat_certificate: str = ""
    stamp_date: str = ""  # ISO 8601 timestamp
    error: str = ""


@dataclass
class CancelResult:
    """Result of a CFDI cancellation request."""

    success: bool
    status: str = ""  # SAT cancellation status
    error: str = ""


@dataclass
class StatusResult:
    """Result of a CFDI status check."""

    success: bool
    status: str = ""  # Vigente, Cancelado, etc.
    uuid: str = ""
    error: str = ""


class FinkokService:
    """
    SOAP client for Finkok PAC services.

    Usage:
        service = FinkokService(username="demo", password="demo123")
        result = service.stamp(cfdi_xml_base64="...")
        if result.success:
            print(f"Stamped: {result.uuid}")
    """

    def __init__(
        self,
        username: str,
        password: str,
        sandbox: bool = True,
    ):
        self.username = username
        self.password = password
        self.sandbox = sandbox
        self._stamp_url = (
            FINKOK_STAMP_URL if sandbox else FINKOK_STAMP_URL.replace("demo-", "")
        )
        self._cancel_url = (
            FINKOK_CANCEL_URL if sandbox else FINKOK_CANCEL_URL.replace("demo-", "")
        )
        self._status_url = (
            FINKOK_STATUS_URL if sandbox else FINKOK_STATUS_URL.replace("demo-", "")
        )

    # -----------------------------------------------------------------------
    # Stamp (register/timbrar)
    # -----------------------------------------------------------------------

    def stamp(self, cfdi_xml_base64: str) -> StampResult:
        """
        Stamp a CFDI XML via Finkok.

        Args:
            cfdi_xml_base64: The CFDI 4.0 XML encoded as base64 string.

        Returns:
            StampResult with UUID, XML, and certificate info on success.
        """
        soap_body = self._build_stamp_envelope(cfdi_xml_base64)

        return self._with_retry(
            self._do_stamp_request,
            soap_body,
        )

    def _do_stamp_request(self, soap_body: str) -> StampResult:
        """Execute a single stamp request."""
        try:
            response = requests.post(
                self._stamp_url,
                data=soap_body.encode("utf-8"),
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": "http://facturacion.finkok.com/stamp",
                },
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            response.raise_for_status()
        except Timeout:
            logger.error("Finkok stamp request timed out")
            return StampResult(
                success=False, error="Timeout al conectar con Finkok (timbrado)."
            )
        except RequestsConnectionError as e:
            logger.error("Finkok connection error: %s", e)
            return StampResult(success=False, error="Error de conexión con Finkok.")
        except Exception as e:
            logger.error("Finkok stamp unexpected error: %s", e)
            return StampResult(success=False, error=f"Error inesperado: {str(e)}")

        return self._parse_stamp_response(response.text)

    def _build_stamp_envelope(self, cfdi_xml_base64: str) -> str:
        """Build SOAP envelope for stamp request."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:sta="http://facturacion.finkok.com/stamp">
  <soap:Header/>
  <soap:Body>
    <sta:stamp>
      <sta:username>{self.username}</sta:username>
      <sta:password>{self.password}</sta:password>
      <sta:xml>{cfdi_xml_base64}</sta:xml>
    </sta:stamp>
  </soap:Body>
</soap:Envelope>"""

    def _parse_stamp_response(self, xml_response: str) -> StampResult:
        """Parse Finkok stamp SOAP response."""
        try:
            # Finkok returns XML with stamp_result element
            # Extract key fields from the response
            import xml.etree.ElementTree as ET

            # Remove namespaces for easier parsing
            cleaned = xml_response.replace("soap:", "").replace(":", "_")
            root = ET.fromstring(cleaned)

            # Look for stamp_result in the body
            error_elem = root.find(".//error")
            if error_elem is not None and error_elem.text:
                return StampResult(success=False, error=error_elem.text.strip())

            uuid_elem = root.find(".//uuid")
            xml_elem = root.find(".//xml")
            sat_cert_elem = root.find(".//sat_certificate")
            stamp_date_elem = root.find(".//stamp_date")

            uuid = uuid_elem.text.strip() if uuid_elem is not None else ""
            xml_data = xml_elem.text.strip() if xml_elem is not None else ""
            sat_cert = sat_cert_elem.text.strip() if sat_cert_elem is not None else ""
            stamp_date = (
                stamp_date_elem.text.strip() if stamp_date_elem is not None else ""
            )

            if not uuid:
                return StampResult(
                    success=False,
                    error="No se recibió UUID del timbrado.",
                )

            return StampResult(
                success=True,
                uuid=uuid,
                xml=xml_data,
                sat_certificate=sat_cert,
                stamp_date=stamp_date,
            )

        except ET.ParseError as e:
            logger.error("Failed to parse Finkok stamp response: %s", e)
            return StampResult(
                success=False,
                error=f"Error parseando respuesta de Finkok: {str(e)}",
            )

    # -----------------------------------------------------------------------
    # Cancel
    # -----------------------------------------------------------------------

    def cancel(
        self,
        uuid: str,
        rfc_emisor: str,
        reason: str = "02",
        folio_sustitucion: str = "",
    ) -> CancelResult:
        """
        Request cancellation of a CFDI.

        Args:
            uuid: CFDI UUID to cancel.
            rfc_emisor: RFC of the issuer.
            reason: SAT cancellation reason (01, 02, 03, 04).
            folio_sustitucion: Substitute folio (required for reason 01).

        Returns:
            CancelResult with SAT status.
        """
        soap_body = self._build_cancel_envelope(
            uuid, rfc_emisor, reason, folio_sustitucion
        )

        return self._with_retry(
            self._do_cancel_request,
            soap_body,
        )

    def _do_cancel_request(self, soap_body: str) -> CancelResult:
        """Execute a single cancel request."""
        try:
            response = requests.post(
                self._cancel_url,
                data=soap_body.encode("utf-8"),
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": "http://facturacion.finkok.com/cancel",
                },
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            response.raise_for_status()
        except Timeout:
            logger.error("Finkok cancel request timed out")
            return CancelResult(
                success=False, error="Timeout al conectar con Finkok (cancelación)."
            )
        except RequestsConnectionError as e:
            logger.error("Finkok connection error: %s", e)
            return CancelResult(success=False, error="Error de conexión con Finkok.")
        except Exception as e:
            logger.error("Finkok cancel unexpected error: %s", e)
            return CancelResult(success=False, error=f"Error inesperado: {str(e)}")

        return self._parse_cancel_response(response.text)

    def _build_cancel_envelope(
        self,
        uuid: str,
        rfc_emisor: str,
        reason: str,
        folio_sustitucion: str,
    ) -> str:
        """Build SOAP envelope for cancel request."""
        folio_tag = (
            f"<sta:folioSustitucion>{folio_sustitucion}</sta:folioSustitucion>"
            if folio_sustitucion
            else ""
        )
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:sta="http://facturacion.finkok.com/cancel">
  <soap:Header/>
  <soap:Body>
    <sta:cancel>
      <sta:username>{self.username}</sta:username>
      <sta:password>{self.password}</sta:password>
      <sta:uuid>{uuid}</sta:uuid>
      <sta:rfcEmisor>{rfc_emisor}</sta:rfcEmisor>
      <sta:motivo>{reason}</sta:motivo>
      {folio_tag}
    </sta:cancel>
  </soap:Body>
</soap:Envelope>"""

    def _parse_cancel_response(self, xml_response: str) -> CancelResult:
        """Parse Finkok cancel SOAP response."""
        try:
            import xml.etree.ElementTree as ET

            cleaned = xml_response.replace("soap:", "").replace(":", "_")
            root = ET.fromstring(cleaned)

            error_elem = root.find(".//error")
            if error_elem is not None and error_elem.text:
                return CancelResult(success=False, error=error_elem.text.strip())

            status_elem = root.find(".//estatus")
            status = status_elem.text.strip() if status_elem is not None else ""

            return CancelResult(success=True, status=status)

        except ET.ParseError as e:
            logger.error("Failed to parse Finkok cancel response: %s", e)
            return CancelResult(
                success=False,
                error=f"Error parseando respuesta de cancelación: {str(e)}",
            )

    # -----------------------------------------------------------------------
    # Check Status (get_related / obtener relacionados)
    # -----------------------------------------------------------------------

    def check_status(self, uuid: str, rfc_emisor: str) -> StatusResult:
        """
        Check the SAT status of a CFDI.

        Args:
            uuid: CFDI UUID to check.
            rfc_emisor: RFC of the issuer.

        Returns:
            StatusResult with SAT status (Vigente, Cancelado, etc.)
        """
        soap_body = self._build_status_envelope(uuid, rfc_emisor)

        return self._with_retry(
            self._do_status_request,
            soap_body,
        )

    def _do_status_request(self, soap_body: str) -> StatusResult:
        """Execute a single status check request."""
        try:
            response = requests.post(
                self._status_url,
                data=soap_body.encode("utf-8"),
                headers={
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "SOAPAction": "http://facturacion.finkok.com/obtenidosrelacionados",
                },
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
            response.raise_for_status()
        except Timeout:
            logger.error("Finkok status request timed out")
            return StatusResult(
                success=False, error="Timeout al conectar con Finkok (estado)."
            )
        except RequestsConnectionError as e:
            logger.error("Finkok connection error: %s", e)
            return StatusResult(success=False, error="Error de conexión con Finkok.")
        except Exception as e:
            logger.error("Finkok status unexpected error: %s", e)
            return StatusResult(success=False, error=f"Error inesperado: {str(e)}")

        return self._parse_status_response(response.text)

    def _build_status_envelope(self, uuid: str, rfc_emisor: str) -> str:
        """Build SOAP envelope for status check."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:sta="http://facturacion.finkok.com/obtenidosrelacionados">
  <soap:Header/>
  <soap:Body>
    <sta:obtenidosrelacionados>
      <sta:username>{self.username}</sta:username>
      <sta:password>{self.password}</sta:password>
      <sta:uuid>{uuid}</sta:uuid>
      <sta:rfcEmisor>{rfc_emisor}</sta:rfcEmisor>
    </sta:obtenidosrelacionados>
  </soap:Body>
</soap:Envelope>"""

    def _parse_status_response(self, xml_response: str) -> StatusResult:
        """Parse Finkok status SOAP response."""
        try:
            import xml.etree.ElementTree as ET

            cleaned = xml_response.replace("soap:", "").replace(":", "_")
            root = ET.fromstring(cleaned)

            error_elem = root.find(".//error")
            if error_elem is not None and error_elem.text:
                return StatusResult(success=False, error=error_elem.text.strip())

            status_elem = root.find(".//estatus")
            status = status_elem.text.strip() if status_elem is not None else ""
            uuid_elem = root.find(".//uuid")
            uuid = uuid_elem.text.strip() if uuid_elem is not None else ""

            return StatusResult(success=True, status=status, uuid=uuid)

        except ET.ParseError as e:
            logger.error("Failed to parse Finkok status response: %s", e)
            return StatusResult(
                success=False,
                error=f"Error parseando respuesta de estado: {str(e)}",
            )

    # -----------------------------------------------------------------------
    # Retry with exponential backoff
    # -----------------------------------------------------------------------

    def _with_retry(self, func, *args, **kwargs):
        """
        Execute a request with exponential backoff retry.

        Retries up to MAX_RETRIES times with backoff: 1s, 2s, 4s, 8s, 16s.
        """
        last_result = None
        for attempt in range(MAX_RETRIES):
            result = func(*args, **kwargs)
            last_result = result

            if result.success:
                return result

            # Don't retry on parse errors or validation errors
            if "parseando" in result.error or "parse" in result.error.lower():
                return result

            if attempt < MAX_RETRIES - 1:
                backoff = BASE_BACKOFF * (2**attempt)
                logger.warning(
                    "Finkok request failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    MAX_RETRIES,
                    result.error,
                    backoff,
                )
                time.sleep(backoff)

        return last_result
