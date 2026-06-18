# Tasks: Facturación CFDI 4.0 — Phase 1 (MVP Fixes)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450-500 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (critical fixes ship together) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend critical fixes (CSD, XML, SOAP, retry, cadena) + migration | PR 1 | Base; tests included |
| 2 | Frontend wiring (hooks, form, filters, types) | PR 2 | Depends on PR 1 API contract |

## Phase 1: Backend Critical Fixes

- [x] 1.1 Add `xml_content` TextField to `Invoice` model in `backend/invoicing/models.py` (blank=True, default=""), update `mark_stamped()` to accept and save `xml_content` parameter
- [x] 1.2 Create migration for `xml_content` field: `python manage.py makemigrations invoicing`
- [x] 1.3 Fix `_decrypt_csd_password()` in `backend/invoicing/views.py`: decode `BinaryField` bytes → UTF-8 string, call `from patients.services.encryption_service import decrypt`, return `str` (not `bytes`), remove `b"placeholder"` fallback
- [x] 1.4 Fix `sign_cfdi()` call in `backend/invoicing/views.py`: change `key_password` param type from `bytes` to `str` (since `_decrypt_csd_password` now returns `str`), update `sign_cfdi` in `cfdi_builder.py` to accept `str` and `.encode("utf-8")` internally
- [x] 1.5 Fix `download_xml()` in `backend/invoicing/views.py`: return `HttpResponse(invoice.xml_content.encode(), content_type="application/xml")` with `Content-Disposition` header; keep 400 check for not-stamped
- [x] 1.6 Save `xml_content` during stamp in `backend/invoicing/views.py`: decode `result.xml` (base64 from Finkok) and pass to `mark_stamped()`
- [x] 1.7 Replace SOAP namespace parsing in `backend/invoicing/services/finkok_service.py`: add `NS_MAP` dict with `soap` and `sta` namespaces, use `ET.fromstring()` + `.find()` with namespace map in all three `_parse_*_response` methods instead of `str.replace()`
- [x] 1.8 Add `_NON_RETRYABLE_ERRORS` set in `backend/invoicing/services/finkok_service.py`: `{"CSD expirado", "XML mal formado", "certificado no válido", "UUID repetido"}`, update `_with_retry()` to check error keywords against this set
- [x] 1.9 Remove dead `cert_serial` param from `_build_cadena_original()` in `backend/invoicing/services/cfdi_builder.py`: remove param, update call site in `sign_cfdi()`

## Phase 2: Frontend

- [x] 2.1 Create `frontend/src/hooks/useInvoices.ts` with TanStack Query hooks: `useInvoices(params)`, `useInvoice(id)`, `useCreateInvoice()`, `useStampInvoice()`, `useCancelInvoice()` — each wired to `invoicesApi` methods
- [x] 2.2 Update `frontend/src/types/index.ts`: change `Invoice.status` union from `'pending'` to `'pending_stamp'`
- [x] 2.3 Fix `InvoicesPage.tsx` status filters: change `'pending'` → `'pending_stamp'` in filter button, `getStatusBadge()`, `getStatusLabel()`, and stamp action condition
- [x] 2.4 Wire create form in `InvoicesPage.tsx`: add `useState` for form fields, add `onSubmit` handler calling `useCreateInvoice()` mutation, wire all inputs to state

## Phase 3: Tests

- [x] 3.1 Fix `test_cfdi_builder.py`: update `_build_cadena_original` test to call without `cert_serial` param (was `_build_cadena_original(xml, "ABC123")` → `_build_cadena_original(xml)`)
- [x] 3.2 Fix `test_finkok_service.py`: update response parsing tests to use namespace-aware XML (add proper `xmlns:soap` and `xmlns:sta` declarations in test XML samples)
- [x] 3.3 Add retry whitelist test in `test_finkok_service.py`: verify `_with_retry` returns immediately for non-retryable errors ("CSD expirado", "XML mal formado") without sleeping
- [x] 3.4 Add test for `_decrypt_csd_password` in `backend/tests/unit/test_encryption_service.py` or new file: mock `FiscalConfig` with `csd_password_encrypted`, verify `decrypt()` is called with decoded string
- [x] 3.5 Add integration test for `download_xml` endpoint in `backend/tests/integration/test_invoice_viewset.py`: create stamped invoice with `xml_content`, GET `/xml/`, verify `Content-Type: application/xml` and body contains XML
