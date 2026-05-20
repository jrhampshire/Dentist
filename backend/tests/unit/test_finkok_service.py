"""
Unit tests for finkok_service.py (Task 12.4).

Tests:
- SOAP request building
- Response parsing
- Error handling (mock responses)
- Retry logic
"""

from unittest.mock import patch

import pytest

from invoicing.services.finkok_service import (
    CancelResult,
    FinkokService,
    StampResult,
    StatusResult,
)


@pytest.mark.unit
class TestFinkokServiceInit:
    """Test service initialization."""

    def test_sandbox_urls(self):
        service = FinkokService(username="demo", password="demo123", sandbox=True)
        assert "demo-facturacion" in service._stamp_url
        assert "demo-facturacion" in service._cancel_url

    def test_production_urls(self):
        service = FinkokService(username="demo", password="demo123", sandbox=False)
        assert "demo-facturacion" not in service._stamp_url
        assert "demo-facturacion" not in service._cancel_url


@pytest.mark.unit
class TestStampEnvelope:
    """Test SOAP envelope building for stamp."""

    def test_build_stamp_envelope(self):
        service = FinkokService(username="testuser", password="testpass")
        envelope = service._build_stamp_envelope("base64xml")

        assert '<?xml version="1.0"' in envelope
        assert "<sta:username>testuser</sta:username>" in envelope
        assert "<sta:password>testpass</sta:password>" in envelope
        assert "<sta:xml>base64xml</sta:xml>" in envelope
        assert "soap:Envelope" in envelope
        assert "sta:stamp" in envelope


@pytest.mark.unit
class TestStampResponseParsing:
    """Test parsing of stamp responses."""

    def test_parse_successful_stamp_response(self):
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <uuid>ABC12345-1234-5678-9ABC-123456789012</uuid>
      <xml>base64signedxml</xml>
      <sat_certificate>SAT123</sat_certificate>
      <stamp_date>2024-01-15T10:30:00</stamp_date>
    </stamp_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_stamp_response(response)

        assert result.success is True
        assert result.uuid == "ABC12345-1234-5678-9ABC-123456789012"
        assert result.xml == "base64signedxml"
        assert result.sat_certificate == "SAT123"
        assert result.stamp_date == "2024-01-15T10:30:00"

    def test_parse_error_response(self):
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <error>CSD expirado</error>
    </stamp_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_stamp_response(response)

        assert result.success is False
        assert "CSD expirado" in result.error

    def test_parse_missing_uuid(self):
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <uuid></uuid>
    </stamp_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_stamp_response(response)

        assert result.success is False
        assert "UUID" in result.error

    def test_parse_malformed_xml(self):
        service = FinkokService(username="demo", password="demo123")

        result = service._parse_stamp_response("not xml at all")

        assert result.success is False
        assert "parseando" in result.error


@pytest.mark.unit
class TestCancelEnvelope:
    """Test SOAP envelope building for cancel."""

    def test_build_cancel_envelope_without_folio(self):
        service = FinkokService(username="testuser", password="testpass")
        envelope = service._build_cancel_envelope(
            uuid="ABC-123",
            rfc_emisor="XAXX010101000",
            reason="02",
            folio_sustitucion="",
        )

        assert "<sta:uuid>ABC-123</sta:uuid>" in envelope
        assert "<sta:rfcEmisor>XAXX010101000</sta:rfcEmisor>" in envelope
        assert "<sta:motivo>02</sta:motivo>" in envelope
        assert "folioSustitucion" not in envelope

    def test_build_cancel_envelope_with_folio(self):
        service = FinkokService(username="testuser", password="testpass")
        envelope = service._build_cancel_envelope(
            uuid="ABC-123",
            rfc_emisor="XAXX010101000",
            reason="01",
            folio_sustitucion="F-999",
        )

        assert "<sta:folioSustitucion>F-999</sta:folioSustitucion>" in envelope


@pytest.mark.unit
class TestCancelResponseParsing:
    """Test parsing of cancel responses."""

    def test_parse_successful_cancel(self):
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

        assert result.success is True
        assert result.status == "Cancelado"

    def test_parse_cancel_error(self):
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <cancel_result>
      <error>UUID no encontrado</error>
    </cancel_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_cancel_response(response)

        assert result.success is False
        assert "UUID" in result.error


@pytest.mark.unit
class TestStatusResponseParsing:
    """Test parsing of status check responses."""

    def test_parse_status_response(self):
        service = FinkokService(username="demo", password="demo123")

        response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <status_result>
      <estatus>Vigente</estatus>
      <uuid>ABC-123</uuid>
    </status_result>
  </soap:Body>
</soap:Envelope>"""

        result = service._parse_status_response(response)

        assert result.success is True
        assert result.status == "Vigente"
        assert result.uuid == "ABC-123"


@pytest.mark.unit
class TestStampWithMock:
    """Test stamp method with mocked HTTP."""

    @patch("invoicing.services.finkok_service.requests.post")
    def test_stamp_success(self, mock_post):
        mock_response = type(
            "MockResponse",
            (),
            {
                "text": """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <stamp_result>
      <uuid>TEST-UUID-123</uuid>
      <xml>base64xml</xml>
      <sat_certificate>SAT-CERT</sat_certificate>
      <stamp_date>2024-01-15T10:00:00</stamp_date>
    </stamp_result>
  </soap:Body>
</soap:Envelope>""",
                "raise_for_status": lambda: None,
            },
        )()
        mock_post.return_value = mock_response

        service = FinkokService(username="demo", password="demo123")
        result = service.stamp("base64cfdi")

        assert result.success is True
        assert result.uuid == "TEST-UUID-123"
        mock_post.assert_called_once()

    @patch("invoicing.services.finkok_service.requests.post")
    def test_stamp_timeout(self, mock_post):
        from requests.exceptions import Timeout

        mock_post.side_effect = Timeout()

        service = FinkokService(username="demo", password="demo123")
        # Disable retries for this test
        service._with_retry = lambda func, *args, **kwargs: func(*args, **kwargs)
        result = service.stamp("base64cfdi")

        assert result.success is False
        assert "Timeout" in result.error

    @patch("invoicing.services.finkok_service.requests.post")
    def test_stamp_connection_error(self, mock_post):
        from requests.exceptions import ConnectionError as RequestsConnectionError

        mock_post.side_effect = RequestsConnectionError("Connection refused")

        service = FinkokService(username="demo", password="demo123")
        service._with_retry = lambda func, *args, **kwargs: func(*args, **kwargs)
        result = service.stamp("base64cfdi")

        assert result.success is False
        assert "conexión" in result.error
