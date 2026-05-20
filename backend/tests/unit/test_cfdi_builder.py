"""
Unit tests for cfdi_builder.py (Task 12.5).

Tests:
- XML structure validation
- CFDI element building
- Decimal formatting
- Receptor regime detection
- Cadena original building

Note: CSD signing tests require actual certificate files,
so we test the XML building separately from signing.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from invoicing.services.cfdi_builder import (
    _build_cadena_original,
    _fmt_decimal,
    _format_cert_serial,
    _get_receptor_regimen,
    build_cfdi_xml,
    encode_for_finkok,
)


@pytest.mark.unit
class TestFmtDecimal:
    """Test decimal formatting."""

    def test_formats_integer(self):
        assert _fmt_decimal(1000) == "1000.00"

    def test_formats_decimal(self):
        assert _fmt_decimal(Decimal("1234.56")) == "1234.56"

    def test_formats_float(self):
        assert _fmt_decimal(100.5) == "100.50"

    def test_formats_string(self):
        assert _fmt_decimal("500") == "500.00"

    def test_formats_zero(self):
        assert _fmt_decimal(0) == "0.00"


@pytest.mark.unit
class TestFormatCertSerial:
    """Test certificate serial number formatting."""

    def test_formats_as_20_char_hex(self):
        result = _format_cert_serial(12345)
        assert result == "00000000000000003039"
        assert len(result) == 20

    def test_formats_large_number(self):
        result = _format_cert_serial(0xFFFFFFFFFFFFFFFFFFFF)
        assert len(result) == 20


@pytest.mark.unit
class TestGetReceptorRegimen:
    """Test receptor fiscal regime detection."""

    def test_persona_moral_12_chars(self):
        # 12 chars = persona moral
        assert _get_receptor_regimen("XAXX01010100") == "601"

    def test_persona_fisica_13_chars(self):
        # 13 characters = persona física
        assert _get_receptor_regimen("AAAA010101ABC") == "605"


@pytest.mark.unit
class TestBuildCFDIXml:
    """Test CFDI XML building."""

    def _make_mock_invoice(self):
        invoice = MagicMock()
        invoice.folio = "F-001"
        invoice.forma_pago = "01"
        invoice.metodo_pago = "PUE"
        invoice.moneda = "MXN"
        invoice.subtotal = Decimal("1000.00")
        invoice.iva = Decimal("160.00")
        invoice.total = Decimal("1160.00")
        invoice.rfc_receptor = "XAXX010101000"
        invoice.nombre_receptor = "Público General"
        invoice.uso_cfdi = "G03"
        invoice.concepts = [
            {
                "clave_sat": "84111506",
                "descripcion": "Consulta dental",
                "cantidad": 1,
                "valor_unitario": 1000.00,
                "importe": 1000.00,
                "iva_rate": 0.16,
            }
        ]
        return invoice

    def _make_mock_fiscal_config(self):
        config = MagicMock()
        config.rfc = "XAXX010101000"
        config.razon_social = "Test Clinic SA de CV"
        config.regimen_fiscal = "601"
        config.fiscal_address = {"codigo_postal": "06300"}
        return config

    def test_xml_has_comprobante_root(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert "cfdi:Comprobante" in xml
        assert 'Version="4.0"' in xml

    def test_xml_has_emisor(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert "cfdi:Emisor" in xml
        assert 'Rfc="XAXX010101000"' in xml
        assert "Test Clinic SA de CV" in xml
        assert 'RegimenFiscal="601"' in xml

    def test_xml_has_receptor(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert "cfdi:Receptor" in xml
        assert 'Rfc="XAXX010101000"' in xml
        assert "Público General" in xml
        assert 'UsoCFDI="G03"' in xml

    def test_xml_has_conceptos(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert "cfdi:Conceptos" in xml
        assert "cfdi:Concepto" in xml
        assert "Consulta dental" in xml
        assert 'ValorUnitario="1000.00"' in xml

    def test_xml_has_impuestos(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert "cfdi:Impuestos" in xml
        assert "cfdi:Traslados" in xml
        assert "cfdi:Traslado" in xml
        assert 'Impuesto="002"' in xml  # IVA
        assert "160.00" in xml

    def test_xml_has_declaration(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml

    def test_xml_has_tipo_de_comprobante(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert 'TipoDeComprobante="I"' in xml  # Ingreso

    def test_xml_has_lugar_expedicion(self):
        invoice = self._make_mock_invoice()
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        assert 'LugarExpedicion="06300"' in xml

    def test_multiple_concepts(self):
        invoice = self._make_mock_invoice()
        invoice.concepts = [
            {
                "clave_sat": "84111506",
                "descripcion": "Consulta",
                "cantidad": 1,
                "valor_unitario": 500.00,
                "importe": 500.00,
                "iva_rate": 0.16,
            },
            {
                "clave_sat": "84111506",
                "descripcion": "Limpieza",
                "cantidad": 1,
                "valor_unitario": 300.00,
                "importe": 300.00,
                "iva_rate": 0.16,
            },
        ]
        config = self._make_mock_fiscal_config()

        xml = build_cfdi_xml(invoice, config)

        # Both concepts should be present (count opening tags only)
        assert xml.count("<cfdi:Concepto") == 2
        assert "Consulta" in xml
        assert "Limpieza" in xml


@pytest.mark.unit
class TestCadenaOriginal:
    """Test cadena original building for signing."""

    def test_builds_cadena_with_pipe_separators(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0"
    Serie="A" Folio="F-001" Fecha="2024-01-15T10:00:00"
    FormaPago="01" SubTotal="1000.00" Descuento="0.00" Moneda="MXN"
    Total="1160.00" TipoDeComprobante="I" MetodoPago="PUE"
    LugarExpedicion="06300">
  <cfdi:Emisor Rfc="XAXX010101000" Nombre="Test Clinic" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="AAAA010101ABC" Nombre="Juan Pérez" UsoCFDI="G03"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" Cantidad="1" ClaveUnidad="ACT"
        Descripcion="Consulta" ValorUnitario="1000.00" Importe="1000.00"/>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
    <cfdi:Traslados>
      <cfdi:Traslado Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="160.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
</cfdi:Comprobante>"""

        cadena = _build_cadena_original(xml, "ABC123")

        assert cadena.startswith("||4.0|")
        assert cadena.endswith("||")
        assert "160.00" in cadena


@pytest.mark.unit
class TestEncodeForFinkok:
    """Test base64 encoding for Finkok submission."""

    def test_encodes_xml_to_base64(self):
        xml = '<?xml version="1.0"?><test>hello</test>'
        encoded = encode_for_finkok(xml)

        import base64

        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == xml

    def test_handles_unicode(self):
        xml = '<?xml version="1.0"?><test>Ñoño café</test>'
        encoded = encode_for_finkok(xml)

        import base64

        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == xml
