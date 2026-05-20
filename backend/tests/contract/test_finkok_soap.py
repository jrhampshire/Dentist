"""
Contract tests for Finkok SOAP (Task 12.12).

Tests:
- Stamp request/response schema
- Cancel request/response schema
- SOAP envelope structure validation
"""

import pytest
from unittest.mock import patch

from invoicing.services.finkok_service import (
    CancelResult,
    FinkokService,
    StampResult,
    StatusResult,
)


@pytest.mark.contract
class TestFinkokStampContract:
    """Test Finkok stamp request/response contract."""

    def test_stamp_request_has_correct_soap_action(self):
        """Verify the SOAP envelope structure matches Finkok spec."""
        service = FinkokService(username="demo", password="demo123")
        envelope = service._build_stamp_envelope("base64xml")

        # Must have proper XML declaration
        assert '<?xml version="1.0" encoding="UTF-8"?>' in envelope

        # Must have SOAP envelope with correct namespace
        assert 'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"' in envelope

        # Must have stamp namespace
        assert 'xmlns:sta="http://facturacion.finkok.com/stamp"' in envelope

        # Must have stamp operation
        assert "<sta:stamp>" in envelope
        assert "</sta:stamp>" in envelope

        # Must have credentials
        assert "<sta:username>demo</sta:username>" in envelope
        assert "<sta:password>demo123</sta:password>" in envelope

        # Must have XML payload
        assert "<sta:xml>base64xml</sta:xml>" in envelope

    def test_stamp_response_schema(self):
        """Verify response parsing matches expected schema."""
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <uuid>AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE</uuid>
      <xml>PD94bWwgdmVyc2lvbj0iMS4wIj8+</xml>
      <sat_certificate>20001000000300022815</sat_certificate>
      <stamp_date>2024-01-15T10:30:00</stamp_date>
    </stamp_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_stamp_response(response)

        assert isinstance(result, StampResult)
        assert result.success is True
        assert isinstance(result.uuid, str)
        assert isinstance(result.xml, str)
        assert isinstance(result.sat_certificate, str)
        assert isinstance(result.stamp_date, str)

    def test_stamp_error_response_schema(self):
        """Verify error response schema."""
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <error>El CSD proporcionado está expirado.</error>
    </stamp_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_stamp_response(response)

        assert isinstance(result, StampResult)
        assert result.success is False
        assert isinstance(result.error, str)
        assert result.uuid == ""


@pytest.mark.contract
class TestFinkokCancelContract:
    """Test Finkok cancel request/response contract."""

    def test_cancel_request_has_correct_soap_action(self):
        """Verify cancel SOAP envelope structure."""
        service = FinkokService(username="demo", password="demo123")
        envelope = service._build_cancel_envelope(
            uuid="TEST-UUID",
            rfc_emisor="XAXX010101000",
            reason="02",
            folio_sustitucion="",
        )

        assert '<?xml version="1.0" encoding="UTF-8"?>' in envelope
        assert 'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"' in envelope
        assert 'xmlns:sta="http://facturacion.finkok.com/cancel"' in envelope
        assert "<sta:cancel>" in envelope
        assert "<sta:uuid>TEST-UUID</sta:uuid>" in envelope
        assert "<sta:rfcEmisor>XAXX010101000</sta:rfcEmisor>" in envelope
        assert "<sta:motivo>02</sta:motivo>" in envelope

    def test_cancel_request_with_folio_sustitucion(self):
        """Verify cancel request includes folio when reason is 01."""
        service = FinkokService(username="demo", password="demo123")
        envelope = service._build_cancel_envelope(
            uuid="TEST-UUID",
            rfc_emisor="XAXX010101000",
            reason="01",
            folio_sustitucion="F-999",
        )

        assert "<sta:folioSustitucion>F-999</sta:folioSustitucion>" in envelope

    def test_cancel_response_schema(self):
        """Verify cancel response schema."""
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <cancel_result>
      <estatus>Cancelado</estatus>
    </cancel_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_cancel_response(response)

        assert isinstance(result, CancelResult)
        assert result.success is True
        assert isinstance(result.status, str)

    def test_cancel_error_response_schema(self):
        """Verify cancel error response schema."""
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <cancel_result>
      <error>UUID no encontrado en el sistema.</error>
    </cancel_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_cancel_response(response)

        assert isinstance(result, CancelResult)
        assert result.success is False
        assert isinstance(result.error, str)


@pytest.mark.contract
class TestFinkokStatusContract:
    """Test Finkok status check request/response contract."""

    def test_status_request_structure(self):
        """Verify status check SOAP envelope."""
        service = FinkokService(username="demo", password="demo123")
        envelope = service._build_status_envelope(
            uuid="TEST-UUID",
            rfc_emisor="XAXX010101000",
        )

        assert '<?xml version="1.0" encoding="UTF-8"?>' in envelope
        assert "<sta:obtenidosrelacionados>" in envelope
        assert "<sta:uuid>TEST-UUID</sta:uuid>" in envelope
        assert "<sta:rfcEmisor>XAXX010101000</sta:rfcEmisor>" in envelope

    def test_status_response_schema(self):
        """Verify status response schema."""
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <status_result>
      <estatus>Vigente</estatus>
      <uuid>TEST-UUID</uuid>
    </status_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_status_response(response)

        assert isinstance(result, StatusResult)
        assert result.success is True
        assert result.status == "Vigente"
        assert result.uuid == "TEST-UUID"


@pytest.mark.contract
class TestFinkokEndpoints:
    """Test endpoint URL contract."""

    def test_sandbox_urls_contain_demo(self):
        service = FinkokService(username="demo", password="demo123", sandbox=True)
        assert "demo-facturacion.finkok.com" in service._stamp_url
        assert "demo-facturacion.finkok.com" in service._cancel_url
        assert "demo-facturacion.finkok.com" in service._status_url

    def test_production_urls_no_demo(self):
        service = FinkokService(username="demo", password="demo123", sandbox=False)
        assert "demo-" not in service._stamp_url
        assert "demo-" not in service._cancel_url
        assert "demo-" not in service._status_url
        assert "facturacion.finkok.com" in service._stamp_url
