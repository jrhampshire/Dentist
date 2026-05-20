"""
PDF generation service for CFDI invoices.

Generates a printable PDF representation of a CFDI invoice (representación impresa).
This is NOT the official CFDI — the XML is the legal document. The PDF is a
human-readable representation for the patient.

Post-MVP: Embed the CFDI XML as a PDF attachment (PDF/A-3a with XML embedded).

Dependencies: We use reportlab for PDF generation. If not installed, falls back
to a simple HTML template that can be converted with wkhtmltopdf.
"""

import logging
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)


def generate_invoice_pdf(invoice: Any, fiscal_config: Any) -> bytes:
    """
    Generate a PDF representation of a CFDI invoice.

    Args:
        invoice: Invoice model instance.
        fiscal_config: FiscalConfig model instance.

    Returns:
        PDF bytes.
    """
    try:
        return _generate_with_reportlab(invoice, fiscal_config)
    except ImportError:
        logger.warning("reportlab not installed. Falling back to HTML representation.")
        return _generate_html_fallback(invoice, fiscal_config)


def _generate_with_reportlab(invoice: Any, fiscal_config: Any) -> bytes:
    """Generate PDF using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import Letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=Letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(
        Paragraph(
            f"<b>FACTURA {invoice.folio}</b>",
            styles["Title"],
        )
    )
    elements.append(Spacer(1, 12))

    # CFDI info
    if invoice.cfdi_uuid:
        elements.append(
            Paragraph(
                f"<b>UUID:</b> {invoice.cfdi_uuid}<br/>"
                f"<b>Fecha de timbrado:</b> {invoice.cfdi_stamp_date.strftime('%Y-%m-%d %H:%M:%S') if invoice.cfdi_stamp_date else 'N/A'}<br/>"
                f"<b>Certificado SAT:</b> {invoice.cfdi_sat_certificate}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 12))

    # Emisor
    elements.append(Paragraph("<b>EMISOR</b>", styles["Heading2"]))
    elements.append(
        Paragraph(
            f"{fiscal_config.razon_social}<br/>"
            f"RFC: {fiscal_config.rfc}<br/>"
            f"Régimen: {fiscal_config.regimen_fiscal}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    # Receptor
    elements.append(Paragraph("<b>RECEPTOR</b>", styles["Heading2"]))
    elements.append(
        Paragraph(
            f"{invoice.nombre_receptor}<br/>"
            f"RFC: {invoice.rfc_receptor}<br/>"
            f"Uso CFDI: {invoice.get_uso_cfdi_display()}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    # Concepts table
    elements.append(Paragraph("<b>CONCEPTOS</b>", styles["Heading2"]))

    header_data = [
        ["Clave", "Descripción", "Cant.", "P.Unit.", "Importe"],
    ]
    row_data = []
    for c in invoice.concepts:
        row_data.append(
            [
                c.get("clave_sat", ""),
                c.get("descripcion", ""),
                str(c.get("cantidad", 1)),
                f"${c.get('valor_unitario', 0):.2f}",
                f"${c.get('importe', 0):.2f}",
            ]
        )

    table_data = header_data + row_data
    table = Table(
        table_data,
        colWidths=[0.8 * inch, 2.5 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Totals
    totals_data = [
        ["Subtotal:", f"${invoice.subtotal:.2f}"],
        ["IVA:", f"${invoice.iva:.2f}"],
        ["TOTAL:", f"${invoice.total:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[2 * inch, 1.5 * inch])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 2), (-1, 2), 2, colors.black),
            ]
        )
    )
    elements.append(totals_table)

    # Payment info
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(
            f"<b>Método de pago:</b> {invoice.get_metodo_pago_display()}<br/>"
            f"<b>Forma de pago:</b> {invoice.get_forma_pago_display()}<br/>"
            f"<b>Moneda:</b> {invoice.get_moneda_display()}",
            styles["Normal"],
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _generate_html_fallback(invoice: Any, fiscal_config: Any) -> bytes:
    """
    Generate a simple HTML representation as fallback.

    Returns HTML bytes that can be converted to PDF with wkhtmltopdf
    or viewed directly in a browser.
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Factura {invoice.folio}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #4A90D9; }}
        h2 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #4A90D9; color: white; padding: 8px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #eee; }}
        .totals {{ text-align: right; margin: 20px 0; }}
        .totals td {{ border: none; }}
        .uuid {{ color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>FACTURA {invoice.folio}</h1>
    {f'<p class="uuid">UUID: {invoice.cfdi_uuid}</p>' if invoice.cfdi_uuid else ""}

    <h2>EMISOR</h2>
    <p>
        {fiscal_config.razon_social}<br/>
        RFC: {fiscal_config.rfc}<br/>
        Régimen: {fiscal_config.regimen_fiscal}
    </p>

    <h2>RECEPTOR</h2>
    <p>
        {invoice.nombre_receptor}<br/>
        RFC: {invoice.rfc_receptor}<br/>
        Uso CFDI: {invoice.get_uso_cfdi_display()}
    </p>

    <h2>CONCEPTOS</h2>
    <table>
        <tr>
            <th>Clave SAT</th>
            <th>Descripción</th>
            <th>Cantidad</th>
            <th>Valor Unitario</th>
            <th>Importe</th>
        </tr>
        {
        "".join(
            f'''<tr>
            <td>{c.get("clave_sat", "")}</td>
            <td>{c.get("descripcion", "")}</td>
            <td>{c.get("cantidad", 1)}</td>
            <td>${c.get("valor_unitario", 0):.2f}</td>
            <td>${c.get("importe", 0):.2f}</td>
        </tr>'''
            for c in invoice.concepts
        )
    }
    </table>

    <div class="totals">
        <table>
            <tr><td>Subtotal:</td><td>${invoice.subtotal:.2f}</td></tr>
            <tr><td>IVA:</td><td>${invoice.iva:.2f}</td></tr>
            <tr><td><strong>TOTAL:</strong></td><td><strong>${
        invoice.total:.2f}</strong></td></tr>
        </table>
    </div>

    <p>
        <b>Método de pago:</b> {invoice.get_metodo_pago_display()}<br/>
        <b>Forma de pago:</b> {invoice.get_forma_pago_display()}<br/>
        <b>Moneda:</b> {invoice.get_moneda_display()}
    </p>
</body>
</html>"""
    return html.encode("utf-8")
