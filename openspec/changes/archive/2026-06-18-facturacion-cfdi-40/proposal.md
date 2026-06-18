# Proposal: Facturación CFDI 4.0

## Intent

Fix critical blockers in CFDI 4.0 invoicing integration with Finkok PAC to enable end-to-end invoice stamping and frontend invoice management. Current implementation has non-functional stubs, incorrect parsing, and missing frontend wiring that prevent production use.

## Scope

### In Scope
- Fix `_decrypt_csd_password()` placeholder (currently returns `b"placeholder"`)
- Fix `download_xml` stub (returns JSON instead of XML bytes)
- Fix SOAP namespace parsing (replace fragile string replacement with proper XML parsing)
- Fix retry logic (exclude validation errors like "CSD expirado" from retries)
- Fix `_build_cadena_original` (use official SAT XSLT or proper structure)
- Wire frontend invoice creation form (add onSubmit, state binding)
- Create `useInvoices` hook (missing despite being in project docs)
- Fix status filter values (frontend uses `pending`, backend uses `pending_stamp`)

### Out of Scope
- S3 storage for signed XML/PDF (post-MVP)
- Fiscal config management UI (post-MVP)
- DOM-based XML signing with `xmldom-kosz` (post-MVP)

## Capabilities

### New Capabilities
- `invoice-management`: Frontend invoice CRUD operations with proper state management
- `cfdi-stamping`: Backend CFDI 4.0 stamping with Finkok SOAP integration

### Modified Capabilities
- None (no existing specs in `openspec/specs/`)

## Approach

**Phase 1 (MVP fixes)**: Critical backend fixes for stamping to work end-to-end:
1. Implement actual CSD password decryption using Django settings
2. Return actual XML bytes from `download_xml` endpoint
3. Use `xml.etree.ElementTree` for SOAP response parsing
4. Filter retry logic to exclude validation errors
5. Wire frontend form and create missing hook

**Phase 2 (Hardening)**: 
1. Implement official SAT XSLT for cadena original
2. Add comprehensive integration tests
3. Add audit signals for invoice events

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `invoicing/services/finkok_service.py` | Modified | Fix `_decrypt_csd_password`, SOAP parsing, retry logic |
| `invoicing/views.py` | Modified | Fix `download_xml` endpoint to return XML bytes |
| `invoicing/services/cfdi_builder.py` | Modified | Fix `_build_cadena_original` structure |
| `frontend/src/hooks/useInvoices.ts` | New | Create missing hook for invoice operations |
| `frontend/src/pages/InvoicesPage.tsx` | Modified | Wire create form, fix status filter values |
| `frontend/src/api/invoices.ts` | Modified | Add missing API methods for hook |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CSD password decryption fails in production | High | Test with actual CSD certificate, validate against Finkok sandbox |
| SAT XSLT validation rejects cadena original | Medium | Use official SAT XSLT 3.2, test with known-good invoices |
| SOAP parsing breaks on Finkok response variations | Medium | Add contract tests with sample responses, use robust XML parser |
| Frontend form submission fails silently | Low | Add error boundaries, toast notifications, logging |

## Rollback Plan

1. Revert backend changes: `git revert` on `finkok_service.py`, `views.py`, `cfdi_builder.py`
2. Revert frontend changes: `git revert` on `InvoicesPage.tsx`, `useInvoices.ts`, `invoices.ts`
3. Restore previous deployment from staging backup
4. Disable invoice creation feature flag if available

## Dependencies

- Finkok sandbox credentials for testing
- Valid CSD certificate (production or staging)
- Django settings for CSD password encryption key

## Success Criteria

- [ ] Invoice stamping completes end-to-end in Finkok sandbox
- [ ] `download_xml` returns valid XML bytes (not JSON)
- [ ] Frontend can create invoices via form submission
- [ ] Status filter correctly shows invoices by `pending_stamp`, `stamped`, `cancelled`
- [ ] Validation errors (e.g., "CSD expirado") do not trigger retry loops
- [ ] All 7 previously failing tests pass (3 cfdi_builder + 4 finkok_service)
