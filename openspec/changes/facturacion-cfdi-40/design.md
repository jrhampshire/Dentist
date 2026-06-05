# Design: Facturación CFDI 4.0 — Phase 1 (MVP Fixes)

## Technical Approach

Five targeted backend fixes to unblock end-to-end CFDI stamping (CSD decryption, XML download, SOAP parsing, retry logic, cadena original) plus frontend wiring (useInvoices hook, create form binding, status filter alignment). Each fix is isolated to its own file. No new external dependencies. No S3 storage.

---

## Architecture Decisions

### Decision: CSD Password Decryption

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Call `encryption_service.decrypt()` directly | Need to decode `BinaryField` bytes → str first | **Chosen** |
| Add a dedicated `decrypt_csd_password` model method | Cleaner but adds model logic | Not needed, one call site |
| Keep `b"placeholder"` | Blocks stamping entirely | Rejected |

**Rationale**: The existing `core.encryption.decrypt()` expects a base64-encoded string. `csd_password_encrypted` is a Django `BinaryField` (raw bytes of the base64 string). Decode to UTF-8 first, then call `decrypt()`. Remove the `b"placeholder"` fallback.

### Decision: download_xml Serving Strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add `xml_content` `TextField` to Invoice model, populate during stamp | Requires migration, stores signed XML | **Chosen for MVP** |
| Regenerate XML from invoice data on-the-fly | Loses Finkok signature/validity | Rejected |
| Fetch from Finkok on every request | Extra API call, latency | Rejected |

**Rationale**: The Finkok `stamp()` response includes the signed XML (base64-encoded in `result.xml`). Currently `mark_stamped()` ignores it. Add an `xml_content` `TextField` to store the decoded signed XML, populate it in the stamp action, and serve it from `download_xml` with `Content-Type: application/xml`.

### Decision: SOAP Parsing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `xml.etree.ElementTree` with namespace map | Robust, no deps | **Chosen** |
| `defusedxml` | Security benefit | Not needed for pre-validated SOAP responses |
| zeep/soap library | Heavy dep for 3 endpoints | Overkill |

**Rationale**: Replace `str.replace("soap:", "").replace(":", "_")` with proper namespace-aware parsing using `ET.fromstring()` + namespace map `{'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'sta': '...'}`. Normalize element names in all three `_parse_*_response` methods.

### Decision: Retry Whitelist

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Whitelist non-retryable errors by keyword | Simple, covers known cases | **Chosen for MVP** |
| HTTP status-based | Finkok always returns 200 | Rejected |
| Parse structured error codes from SOAP | More precise but heavier | Not needed yet |

**Rationale**: Current retry only checks `"parseando"`. Add a `_NON_RETRYABLE_ERRORS` set with known validation errors: `"CSD expirado"`, `"XML mal formado"`, `"certificado no válido"`, `"UUID repetido"`. All other errors → retry. Network/connection errors are already caught by exception handlers.

### Decision: Cadena Original Fix (Phase 1)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Use official SAT XSLT 4.0 | Correct but needs XSLT file + lxml | **Phase 2** |
| Fix current `_build_cadena_original` | Quick, unblocks | **Chosen for Phase 1** |
| Remove cert_serial dead param | Minor cleanup | Included |

**Rationale**: Phase 1 scope is to fix any structural issues causing existing test failures. The `_build_cadena_original` function has a dead `cert_serial` parameter (not used in the output). Remove it. Verify all existing tests pass. Full SAT XSLT is Phase 2.

---

## Data Flow

```
                    STAMP FLOW (fixed)
                    ==================

Invoice.create → status=draft
       │
       ▼
[POST /stamp/] ──→ _decrypt_csd_password() ──→ encryption_service.decrypt()
       │              (was: b"placeholder")         (returns plaintext str)
       │
       ▼
build_cfdi_xml() ──→ sign_cfdi() ──→ encode_for_finkok()
       │
       ▼
FinkokService.stamp() ──→ POST SOAP ──→ _parse_stamp_response()
       │                      │             (namespace-aware ET)
       │                      ▼
       │              retry? ←─── whitelist check
       │                      │
       │                      ▼ (not retryable → return)
       │
       ▼
mark_stamped(uuid, xml, ...)
  ──→ store xml_content (NEW — decoded from result.xml base64)
  ──→ serve via [GET /xml/] with Content-Type: application/xml
```

```
                    FRONTEND FLOW (fixed)
                    =====================

InvoicesPage
  ├── useInvoices() hook ──→ TanStack Query: ['invoices', filters]
  ├── useInvoice(id)       ──→ TanStack Query: ['invoices', id]
  ├── useCreateInvoice()   ──→ mutation → invalidate ['invoices']
  ├── useStampInvoice()    ──→ mutation → invalidate ['invoices']
  └── useCancelInvoice()   ──→ mutation → invalidate ['invoices']

Status filter: 'pending' → 'pending_stamp' (match backend)
Form submit: wire state → invoicesApi.create()
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/invoicing/models.py` | Modify | Add `xml_content` `TextField` for storing signed XML |
| `backend/invoicing/views.py` | Modify | Fix `_decrypt_csd_password()` to call `encryption_service.decrypt()`; fix `download_xml` to return XML bytes; save `xml_content` during stamp |
| `backend/invoicing/services/finkok_service.py` | Modify | Replace `str.replace` SOAP parsing with `ET` namespace maps; add `_NON_RETRYABLE_ERRORS` whitelist |
| `backend/invoicing/services/cfdi_builder.py` | Modify | Remove dead `cert_serial` param from `_build_cadena_original` |
| `frontend/src/hooks/useInvoices.ts` | **Create** | TanStack Query hooks: `useInvoices`, `useInvoice`, `useCreateInvoice`, `useStampInvoice`, `useCancelInvoice` |
| `frontend/src/pages/InvoicesPage.tsx` | Modify | Wire create form onSubmit; change filter `'pending'` → `'pending_stamp'` |
| `frontend/src/types/index.ts` | Modify | `Invoice.status`: `'pending'` → `'pending_stamp'` |

---

## Interfaces / Contracts

### Encryption integration

```python
# Before (views.py)
def _decrypt_csd_password(fiscal_config) -> bytes:
    return b"placeholder"

# After
def _decrypt_csd_password(fiscal_config) -> str:
    from core.encryption import decrypt
    encrypted_bytes = fiscal_config.csd_password_encrypted  # BinaryField → bytes
    encrypted_str = encrypted_bytes.decode("utf-8")          # base64 string
    return decrypt(encrypted_str)                            # returns plaintext str
```

### XML download endpoint

```
GET /api/v1/invoices/{id}/xml/

Response 200:
  Content-Type: application/xml
  Content-Disposition: attachment; filename="factura_{folio}.xml"
  Body: <cfdi:Comprobante ...> ... </cfdi:Comprobante>

Response 400 (not stamped):
  { "error": "not_stamped", "message": "La factura no ha sido timbrada." }
```

### useInvoices hook API

```typescript
// frontend/src/hooks/useInvoices.ts
function useInvoices(params?: { page?: number; status?: string }): {
  data: PaginatedResponse<Invoice> | undefined
  isLoading: boolean
  error: Error | null
}

function useInvoice(id: string): {
  data: Invoice | undefined
  isLoading: boolean
}

function useCreateInvoice(): {
  mutate: (data: CreateInvoicePayload) => void
  isPending: boolean
  error: Error | null
}

function useStampInvoice(): {
  mutate: (id: string) => void
  isPending: boolean
}
```

### Status type alignment

```typescript
// Before
status: 'draft' | 'pending' | 'stamped' | 'cancelled' | 'error'

// After
status: 'draft' | 'pending_stamp' | 'stamped' | 'cancelled' | 'error'
```

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_decrypt_csd_password` with mock encryption | Verify correct call chain |
| Unit | SOAP parsing with sample Finkok XML responses | Verify namespace-aware extraction |
| Unit | Retry whitelist behavior | Verify non-retryable errors return immediately |
| Unit | `_build_cadena_original` (existing tests) | Verify all 3 pass after cleanup |
| Integration | `download_xml` endpoint | Verify Content-Type and body bytes |
| Integration | Full stamp flow with mock Finkok | Verify xml_content is stored and served |
| E2E | Create invoice → stamp → download XML | Browser test with sandbox Finkok |

## Migration / Rollout

One migration to add `xml_content` field. Rollout: deploy backend first (non-breaking — new field is empty string by default), then frontend. No feature flags needed.

## Open Questions

- None for Phase 1 scope.
