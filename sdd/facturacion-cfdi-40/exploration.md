# Exploration: Facturación CFDI 4.0 (Finkok)

## Current State

### Backend — What Works
- **Models**: Well-structured `Invoice` and `FiscalConfig` with proper indexes, constraints, and a complete status state machine (`draft` → `pending_stamp` → `stamped` → `sent` → `paid`, plus cancellation path).
- **Serializers**: `InvoiceCreateSerializer` has robust validation for concepts, RFC format, patient/appointment resolution, auto-calculates totals, and generates per-clinic sequential folios (`FAC-000001`).
- **Views**: `InvoiceViewSet` exposes all required actions (`stamp`, `cancel`, `download_pdf`, `download_xml`) with proper permission checks and status guards.
- **Finkok SOAP client**: `FinkokService` implements stamp, cancel, and status check with retry logic (exponential backoff, 5 retries) and timeout handling.
- **CFDI XML builder**: Generates structurally correct CFDI 4.0 XML with `Comprobante`, `Emisor`, `Receptor`, `Conceptos`, and `Impuestos` elements.
- **PDF generation**: Dual-path service (ReportLab primary, HTML fallback) generates human-readable invoice PDFs.
- **Settings**: Environment-aware Finkok config (`docker.py` sandbox, `production.py` live, `staging.py` sandbox).
- **URLs**: Both `/api/v1/invoices/` and `/api/v1/fiscal-config/` are wired into root `urls.py`.

### Backend — What's Broken / Problematic

| Issue | Severity | Location |
|-------|----------|----------|
| **CSD password decryption is a PLACEHOLDER** | 🔴 Critical | `views.py:_decrypt_csd_password()` returns `b"placeholder"`. Real stamping will fail because the CSD key cannot be loaded. |
| **`download_xml` is a stub** | 🔴 Critical | `views.py:download_xml()` returns JSON message instead of actual XML bytes. Legal requirement not met. |
| **Fragile SOAP response parsing** | 🔴 High | `finkok_service.py` strips namespaces with `.replace("soap:", "").replace(":", "_")`. Any nested namespace or attribute with colons will break parsing. |
| **Retries on validation errors** | 🟡 Medium | `_with_retry()` retries 5× even on validation errors (e.g., "CSD expirado"). Wastes time and Finkok quota. |
| **Simplified cadena original** | 🟡 Medium | `cfdi_builder.py:_build_cadena_original()` is hand-rolled pipe-separated string. SAT requires official XSLT transformation; this may fail validation. |
| **XML signing uses string replacement** | 🟡 Medium | `sign_cfdi()` injects attributes via `xml_string.replace("<cfdi:Comprobante ", ...)` — fragile if attribute order changes. |
| **Hardcoded demo URL transformation** | 🟡 Medium | Production URLs derived via `replace("demo-", "")` — breaks if Finkok changes subdomain scheme. |
| **3 pre-existing failing cfdi_builder tests** | 🟡 Medium | Likely XML declaration handling in `_build_cadena_original` or global `ET.register_namespace` side effects. |
| **4 pre-existing failing finkok_service tests** | 🟡 Medium | Likely response parsing or retry-logic fragility. |
| **Missing audit signals** | 🟢 Low | User mentioned signals for audit logging, but `invoicing/signals.py` does not exist. |

### Frontend Gaps

| Gap | Impact |
|-----|--------|
| **`useInvoices.ts` does NOT exist** | User claimed it exists, but it's missing from `frontend/src/hooks/` and not exported from `hooks/index.ts`. |
| **Create invoice form is non-functional** | `InvoicesPage.tsx` dialog has inputs but no `onSubmit`, no React state for form fields, and no concept line-item management. |
| **Status filter mismatch** | Frontend filters by `pending`, but backend status is `pending_stamp`. Filter will never match. |
| **Cancel reason not bound** | Cancel dialog has a `<select>` for SAT reason but does not read its value; the `cancelReason` state is bound to a notes text field instead. |
| **No fiscal config UI** | No frontend page to configure RFC, CSD upload, or validation. |
| **No patient autocomplete** | Create form requires raw patient ID instead of searchable patient selector. |
| **No invoice detail page** | Only list view exists; no detail/edit view for drafts. |
| **Weak error handling** | Stamp/cancel mutations show no user-facing error states (only `alert()` on download failure). |
| **XML download will break** | Frontend expects `blob` from `/xml/`, but backend returns JSON. |

### Test Coverage Gaps

| Area | Coverage | Gap |
|------|----------|-----|
| `cfdi_builder.py` | 16 tests, 3 failing | No tests for `sign_cfdi()` (requires real CSD files). No tests for `_get_expedition_place` with missing CP. |
| `finkok_service.py` | 17 tests, 4 failing | No tests for actual SOAP network failures during retry. No tests for XML injection in credentials. |
| `pdf_service.py` | 4 tests | Only mocked ReportLab; no visual/structural PDF assertions. No tests for unstamped invoice PDF. |
| `views.py` | 7 integration tests | No tests for `download_pdf`, `download_xml`, or `validate-csd`. No tests for non-admin cancellation denial. |
| `serializers.py` | 0 dedicated tests | No unit tests for `InvoiceCreateSerializer` validation edge cases (duplicate folio, invalid concept structure). |
| `models.py` | 7 tests (passing) | No tests for `calculate_totals` or `mark_stamped` with invalid data. |
| **Frontend** | 0 tests | No component tests, no hook tests, no API client tests. |
| **E2E / Contract** | 1 Finkok contract test | No live sandbox integration test (only mocked responses). |

### Finkok API Integration Assessment
- **Sandbox vs Production**: Properly separated via settings + `FinkokService.sandbox` flag. URLs switch correctly.
- **Credential config**: Reads from env vars (`FINKOK_USERNAME`, `FINKOK_PASSWORD`, `FINKOK_SANDBOX`), but code has hardcoded fallbacks (`demo` / `demo123`) which could leak into production if env vars are empty.
- **SOAP envelope structure**: Correctly follows Finkok stamp/cancel/obtenidosrelacionados specs.
- **Timeout/retry**: 30s connect, 60s read, 5 retries with exponential backoff — reasonable for SOAP.

## Recommended Approach

1. **Fix critical blockers first**:
   - Implement `_decrypt_csd_password()` using the existing `core.encryption` service.
   - Make `download_xml()` return actual XML bytes (store signed XML from Finkok response in DB or S3).
   - Fix SOAP response parsing to use proper namespace-aware XML parsing (e.g., `xml.etree.ElementTree` with namespace map, or `lxml`).

2. **Stabilize retry logic**:
   - Add non-retryable error whitelist (validation errors, auth errors) to `_with_retry()`.

3. **Fix pre-existing test failures**:
   - Debug and fix the 7 failing tests (3 cfdi_builder + 4 finkok_service).

4. **Frontend — make invoice creation real**:
   - Create `useInvoices.ts` hook with TanStack Query wrappers.
   - Bind the create form to React state and wire `onSubmit` to `invoicesApi.create()`.
   - Add concept line-item management (add/remove rows with clave SAT, descripción, cantidad, valor unitario).
   - Fix status filter values to match backend (`pending_stamp` instead of `pending`).
   - Fix cancel dialog to read the `<select>` value for SAT reason.
   - Add proper error toast handling for stamp/cancel failures.

5. **Add missing tests**:
   - Unit tests for `_decrypt_csd_password`, `download_pdf`, `download_xml` views.
   - Frontend hook/component tests (React Testing Library + MSW).
   - One live sandbox contract test to validate actual Finkok connectivity.

6. **Polish / Hardening**:
   - Replace string-replacement XML signing with proper DOM mutation.
   - Evaluate migrating cadena original to SAT official XSLT (post-MVP).
   - Add XML injection protection in SOAP envelope building (escape credentials).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **CSD password placeholder breaks stamping in prod** | Certain | 🔴 Critical | Fix `_decrypt_csd_password` before any production deploy. |
| **SOAP parser breaks on real Finkok responses** | High | 🔴 Critical | Replace namespace-stripping hack with proper XML parsing; test against real sandbox. |
| **Simplified cadena original rejected by SAT** | Medium | 🟡 High | Plan XSLT migration; test with Finkok sandbox validation. |
| **No XML download = legal non-compliance** | Certain | 🔴 Critical | Store signed XML from Finkok and serve it via `download_xml`. |
| **Frontend create form doesn't work** | Certain | 🟡 Medium | Wire form state and API call; blocks user acceptance. |
| **Hardcoded fallback credentials leak to prod** | Low | 🟡 Medium | Remove fallbacks from code; enforce env vars in production settings. |
| **Retry storm on validation errors** | High | 🟢 Low | Whitelist non-retryable errors. |

## Ready for Proposal

**Yes** — with the following clarifications needed from the user/orchestrator:
1. Is the `core.encryption` service ready to use for CSD password decryption, or does it need implementation too?
2. Should XML/PDF files be stored locally, on S3, or served directly from Finkok URLs?
3. Should the frontend invoice creation form auto-populate concepts from a selected appointment/treatment?
