"""
Unit tests for pdf_service.py — generate_invoice_pdf.

Tests:
- ReportLab generation → returns PDF bytes starting with %PDF-
- ImportError fallback → returns HTML bytes
- Both paths fail → exception propagates
- Invoice with zero line items → produces PDF

Note: The actual generate_invoice_pdf signature takes TWO args:
  generate_invoice_pdf(invoice, fiscal_config)
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from invoicing.services.pdf_service import generate_invoice_pdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_invoice(concepts=None, **overrides):
    """Create a mock Invoice with minimal attributes for PDF generation."""
    defaults = {
        "folio": "F-001",
        "cfdi_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "cfdi_stamp_date": datetime(2025, 5, 20, 10, 30, 0),
        "cfdi_sat_certificate": "00001000000512345678",
        "nombre_receptor": "Público General",
        "rfc_receptor": "XAXX010101000",
        "subtotal": 1000.00,
        "iva": 160.00,
        "total": 1160.00,
        "concepts": concepts
        if concepts is not None
        else [
            {
                "clave_sat": "84111506",
                "descripcion": "Consulta dental",
                "cantidad": 1,
                "valor_unitario": 1000.00,
                "importe": 1000.00,
            }
        ],
    }
    defaults.update(overrides)
    invoice = MagicMock(**defaults)
    invoice.get_uso_cfdi_display.return_value = "Gastos en general"
    invoice.get_metodo_pago_display.return_value = "Pago en una sola exhibición"
    invoice.get_forma_pago_display.return_value = "Efectivo"
    invoice.get_moneda_display.return_value = "Peso Mexicano"
    return invoice


def _make_mock_fiscal_config(**overrides):
    """Create a mock FiscalConfig."""
    defaults = {
        "razon_social": "Test Clinic SA de CV",
        "rfc": "XAXX010101000",
        "regimen_fiscal": "601",
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateInvoicePdfReportLab:
    """Tests where ReportLab is available and works."""

    def test_generates_pdf_with_magic_bytes(self):
        """ReportLab generation succeeds → returns bytes starting with %PDF-."""
        invoice = _make_mock_invoice()
        fiscal_config = _make_mock_fiscal_config()

        result = generate_invoice_pdf(invoice, fiscal_config)

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-")

    def test_pdf_includes_folio_in_header(self):
        """PDF content includes the invoice folio."""
        invoice = _make_mock_invoice(folio="F-999")
        fiscal_config = _make_mock_fiscal_config()

        result = generate_invoice_pdf(invoice, fiscal_config)

        # PDF streams may be compressed; check for the raw string
        assert b"F-999" in result

    def test_pdf_includes_clinic_info(self):
        """PDF includes fiscal config data (razon_social, rfc)."""
        invoice = _make_mock_invoice()
        fiscal_config = _make_mock_fiscal_config(
            razon_social="Dental Pro SA de CV", rfc="DEN123456ABC"
        )

        result = generate_invoice_pdf(invoice, fiscal_config)

        assert b"Dental Pro SA de CV" in result or b"Dental" in result

    def test_pdf_with_zero_line_items(self):
        """Invoice with zero line items → produces PDF with total at 0.00."""
        invoice = _make_mock_invoice(
            concepts=[],
            subtotal=0.00,
            iva=0.00,
            total=0.00,
        )
        fiscal_config = _make_mock_fiscal_config()

        result = generate_invoice_pdf(invoice, fiscal_config)

        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-")
        assert b"0.00" in result


@pytest.mark.unit
class TestGenerateInvoicePdfFallback:
    """Tests where ReportLab is unavailable (ImportError) and HTML fallback is used."""

    def test_fallback_produces_html_when_reportlab_unavailable(self):
        """ReportLab ImportError → fallback returns HTML bytes."""
        invoice = _make_mock_invoice()
        fiscal_config = _make_mock_fiscal_config()

        with patch(
            "invoicing.services.pdf_service._generate_with_reportlab",
            side_effect=ImportError("No module named 'reportlab'"),
        ):
            result = generate_invoice_pdf(invoice, fiscal_config)

        assert isinstance(result, bytes)
        # HTML fallback produces UTF-8 encoded HTML
        assert b"<!DOCTYPE html>" in result or b"<html" in result
        assert b"F-001" in result

    def test_fallback_html_contains_patient_data(self):
        """HTML fallback includes receptor information."""
        invoice = _make_mock_invoice(
            nombre_receptor="Juan Pérez",
            rfc_receptor="JUPR900101ABC",
        )
        fiscal_config = _make_mock_fiscal_config()

        with patch(
            "invoicing.services.pdf_service._generate_with_reportlab",
            side_effect=ImportError("No module named 'reportlab'"),
        ):
            result = generate_invoice_pdf(invoice, fiscal_config)

        html = result.decode("utf-8")
        assert "Juan Pérez" in html
        assert "JUPR900101ABC" in html

    def test_fallback_includes_total(self):
        """HTML fallback includes the total amount."""
        invoice = _make_mock_invoice(total=1499.99, subtotal=1293.09, iva=206.90)
        fiscal_config = _make_mock_fiscal_config()

        with patch(
            "invoicing.services.pdf_service._generate_with_reportlab",
            side_effect=ImportError("No module named 'reportlab'"),
        ):
            result = generate_invoice_pdf(invoice, fiscal_config)

        html = result.decode("utf-8")
        assert "1499.99" in html


@pytest.mark.unit
class TestGenerateInvoicePdfBothFail:
    """Tests where both ReportLab and HTML fallback fail."""

    def test_exception_propagates_when_both_fail(self):
        """When both paths fail, the error from the fallback propagates.

        Note: The actual code does not define PDFGenerationError.
        generate_invoice_pdf catches ImportError only from ReportLab;
        if _generate_html_fallback also raises, that exception propagates.
        """
        invoice = _make_mock_invoice()
        fiscal_config = _make_mock_fiscal_config()

        with (
            patch(
                "invoicing.services.pdf_service._generate_with_reportlab",
                side_effect=ImportError("No module named 'reportlab'"),
            ),
            patch(
                "invoicing.services.pdf_service._generate_html_fallback",
                side_effect=RuntimeError("wkhtmltopdf not found"),
            ),
        ):
            with pytest.raises(RuntimeError, match="wkhtmltopdf"):
                generate_invoice_pdf(invoice, fiscal_config)
