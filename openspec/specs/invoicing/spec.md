# invoicing — CFDI 4.0 Invoicing Specification

## Purpose

CFDI 4.0 electronic invoicing with SAT (Finkok PAC) stamping, fiscal configuration per clinic, invoice lifecycle management, PDF generation, and cancellation workflow.

## Requirements

### Requirement: FiscalConfig MUST be unique per clinic

The system SHALL store one fiscal configuration per clinic containing RFC, razón social, régimen fiscal, and CSD certificate credentials for SAT stamping.

#### Scenario: CSD password is encrypted at rest

- GIVEN a clinic configures its CSD with password `"secret123"`
- WHEN the `FiscalConfig` is saved
- THEN the `csd_password_encrypted` column SHALL contain AES-256-GCM encrypted bytes
- AND the plaintext password SHALL NOT be stored in the database

#### Scenario: CSD password is decrypted for stamping

- GIVEN a `FiscalConfig` with encrypted CSD password
- WHEN the CFDI builder service needs the password for stamping
- THEN the decryption service SHALL return the original plaintext password
- AND the decrypted value SHALL be used only in-memory during the stamping call

### Requirement: Invoice MUST calculate totals from concepts

The system SHALL automatically compute `subtotal`, `iva`, and `total` from the `concepts` array when `calculate_totals()` is called or on save.

#### Scenario: Totals calculated correctly

- GIVEN `concepts=[{importe: 1000, iva_rate: 0.16}, {importe: 500, iva_rate: 0.16}]`
- WHEN `invoice.calculate_totals()` is called
- THEN `subtotal` SHALL be `1500.00`
- AND `iva` SHALL be `240.00`
- AND `total` SHALL be `1680.00`

#### Scenario: Folio is unique per clinic

- GIVEN clinic A has invoice folio `F-001`
- WHEN a new invoice with folio `F-001` is created for clinic A
- THEN the system SHALL reject it with a unique constraint violation
- AND clinic B MAY still create its own `F-001`

### Requirement: Invoice lifecycle MUST follow CFDI status flow

The system SHALL enforce the invoice status flow: `draft → pending_stamp → stamped → sent → paid`, with cancellation path `stamped → cancellation_requested → cancelled`.

#### Scenario: Stamped invoice receives SAT UUID

- GIVEN an invoice with status `pending_stamp`
- WHEN Finkok successfully stamps the CFDI and returns UUID `"abc-123"`
- THEN `invoice.mark_stamped(uuid="abc-123", ...)` SHALL set status to `stamped`
- AND `cfdi_uuid`, `cfdi_sat_certificate`, `cfdi_stamp_date`, `xml_content` SHALL be populated
- AND `error_message` SHALL be cleared

#### Scenario: Stamping error is recorded

- GIVEN an invoice with status `pending_stamp`
- WHEN Finkok returns an error during stamping
- THEN `invoice.mark_error("Error message")` SHALL set status to `error`
- AND `error_message` SHALL contain the Finkok error details

#### Scenario: Non-retryable errors block automatic retry

- GIVEN the Finkok service returns an error containing "UUID repetido", "RFC emisor no vigente", "Certificado revocado", "CSD vencido", or "Sello mal formado"
- WHEN the stamping task processes the error
- THEN the system SHALL NOT retry the stamping
- AND the invoice SHALL remain in `error` status

#### Scenario: Stamps remaining at zero blocks stamping

- GIVEN a clinic that has consumed all its Finkok stamp credits
- WHEN a user attempts to stamp a new invoice
- THEN the system SHALL reject the stamping attempt
- AND SHALL return an error indicating no stamps remaining

#### Scenario: Cancellation follows SAT flow

- GIVEN a `stamped` invoice
- WHEN `invoice.cancel(reason="02")` is called
- THEN status SHALL change to `cancellation_requested`
- AND `cancellation_reason` SHALL be set
- AND the Finkok service SHALL be called to request cancellation with the SAT

### Requirement: Revenue reporting MUST exclude draft and cancelled invoices

The system SHALL count only `stamped`, `sent`, and `paid` invoices toward revenue metrics. Draft, cancelled, `pending_stamp`, `cancellation_requested`, and `error` invoices SHALL be excluded.

#### Scenario: Revenue excludes non-final statuses

- GIVEN invoices with statuses: draft ($1000), cancelled ($500), stamped ($300), sent ($200), paid ($100)
- WHEN the dashboard revenue metric is queried
- THEN the system SHALL return total revenue of $600 ($300 + $200 + $100)

### Requirement: PDF generation MUST produce CBB representation

The system SHALL generate a PDF (CBB — Comprobante Digital Simplificado) for any stamped invoice.

#### Scenario: PDF includes all required fields

- GIVEN a stamped invoice with CFDI UUID, RFCs, concepts, and totals
- WHEN the PDF is generated
- THEN the PDF SHALL include the SAT UUID, QR code, emisor/receptor data, concepts table, and totals
- AND the PDF SHALL be compliant with CFDI 4.0 representation format
