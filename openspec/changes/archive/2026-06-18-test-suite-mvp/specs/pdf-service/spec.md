# pdf-service — Test Spec

## Purpose

Unit tests for `invoicing/services/pdf_service.py`: `generate_invoice_pdf`, `_generate_with_reportlab`, `_generate_html_fallback`.

## Requirements

### Requirement: generate_invoice_pdf MUST produce a PDF using ReportLab or HTML fallback

The system SHALL generate a PDF invoice. If ReportLab is unavailable, the system SHALL fall back to HTML-to-PDF conversion.

#### Scenario: ReportLab generation succeeds

- GIVEN a valid Invoice object with line items and tax data
- WHEN `generate_invoice_pdf(invoice)` is called
- THEN the system SHALL return a bytes object containing a valid PDF, and the PDF SHALL include clinic name, invoice number, line items, subtotal, tax, and total

#### Scenario: ReportLab raises an error, HTML fallback succeeds

- GIVEN a valid Invoice object and ReportLab raising an import or rendering error
- WHEN `generate_invoice_pdf(invoice)` is called
- THEN the system SHALL fall back to `_generate_html_fallback`, produce a PDF, and return it without raising to the caller

#### Scenario: Both ReportLab and HTML fallback fail

- GIVEN a valid Invoice object and both rendering paths fail
- WHEN `generate_invoice_pdf(invoice)` is called
- THEN the system SHALL raise `PDFGenerationError` with a descriptive message

#### Scenario: Invoice with zero line items

- GIVEN an Invoice with no line items
- WHEN `generate_invoice_pdf(invoice)` is called
- THEN the system SHALL produce a PDF with zero line items rendered and total at `0.00`