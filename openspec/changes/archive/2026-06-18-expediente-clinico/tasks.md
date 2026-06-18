# Tasks: Expediente Clínico Digital — Slice A (Frontend UI + Type Fixes)

## Phase 1: Foundation (Type Fixes + API)

- [x] **T1. Fix TypeScript enums in `frontend/src/types/index.ts`** — Update `ClinicalNote.note_type` union from `'consultation' | 'treatment' | 'follow_up' | 'other'` to `'evolution' | 'diagnosis' | 'treatment' | 'observation' | 'consent'`. Update `PatientConsent.consent_type` union from `'treatment' | 'data_processing' | 'marketing'` to `'general' | 'treatment' | 'data_processing' | 'whatsapp'`.

- [x] **T2. Fix API endpoint paths in `frontend/src/api/patients.ts`** — Change `listNotes`, `createNote`, `signNote` base path from `/clinical-notes/` to `/notes/`. Add `signConsent` method: `POST /patients/:id/consents/:pk/sign/` with optional `signature_blob` parameter.

- [x] **T3. Add `useSignConsent` hook in `frontend/src/hooks/usePatients.ts`** — Create mutation hook following existing pattern (`useSignClinicalNote`): calls `patientsApi.signConsent`, invalidates `['consents', patientId]` query on success.

- [x] **T4. Create shadcn UI components** — Generate `tabs.tsx` and `badge.tsx` via shadcn CLI (or manually create minimal versions matching project's existing UI component patterns in `frontend/src/components/ui/`).

## Phase 2: Core UI

- [x] **T5. Create `frontend/src/pages/PatientDetailPage.tsx`** — Build tabbed page with shadcn Tabs: "Información" (PatientInfoCard read-only), "Notas Clínicas" (ClinicalNotesTab), "Consentimientos" (ConsentsTab). Include PageHeader with patient name + back button. Handle loading/error states. Use `usePatient(id)` for header data.

- [x] **T6. Create `frontend/src/pages/PatientDetail/ClinicalNotesTab.tsx`** — Table listing notes with columns: type badge, title, author, date, status badge ("Firmada"/"Pendiente"). Include "Nueva Nota" dialog with form fields (note_type select, title, content textarea). Sign button per row (disabled + lock icon if already signed). Use `useClinicalNotes`, `useCreateClinicalNote`, `useSignClinicalNote`.

- [x] **T7. Create `frontend/src/pages/PatientDetail/ConsentsTab.tsx`** — Table listing consents with columns: type badge, version, signed status, signed_at. Include "Nuevo Consentimiento" dialog (consent_type select, content textarea). Sign button per row with confirmation dialog. Disabled + lock icon for signed consents. Use `useConsents`, `useCreateConsent`, `useSignConsent`.

- [x] **T8. Add route in `frontend/src/App.tsx`** — Import `PatientDetailPage`, add route `/patients/:id` inside ProtectedRoute wrapper, placed after `/patients` route.

## Phase 3: Navigation + Polish

- [x] **T9. Wire navigation in `frontend/src/pages/PatientsPage.tsx`** — Import `useNavigate`, update Eye button's onClick to `navigate(`/patients/${patient.id}`)`.

- [x] **T10. Handle empty states** — ClinicalNotesTab: show "Sin notas clínicas" message when empty. ConsentsTab: show "Sin consentimientos" message when empty. Both with subtle illustration or icon.

- [x] **T11. Add type badge labels** — Create `NOTE_TYPE_LABELS` and `CONSENT_TYPE_LABELS` maps in `frontend/src/types/index.ts` for Spanish display labels (e.g., `'evolution': 'Evolución'`, `'general': 'General'`).

## Testing

- [x] **T12. Test `frontend/src/pages/Patients/__tests__/PatientDetailPage.test.tsx`** — Verify tabs render correct content when selected. Verify loading state shows spinner. Verify error state shows error message. Mock React Query data for patient, notes, consents.

- [x] **T13. Test `frontend/src/pages/Patients/__tests__/ClinicalNotesTab.test.tsx`** — Verify note list renders with correct data. Verify signed notes show disabled state + lock icon. Verify sign action calls mutation with correct patientId + noteId. Verify create note dialog submits correctly.

- [x] **T14. Test `frontend/src/pages/Patients/__tests__/ConsentsTab.test.tsx`** — Verify consent list renders. Verify signed consents show read-only state. Verify sign consent calls correct API. Verify empty state message displays.

---

# Tasks: Expediente Clínico Digital — Slice B (NOM-024 Compliance)

**Slice**: B — NOM-024 Compliance Layer
**Chain Strategy**: stacked-to-main (auto-chain)

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Estimated lines | ~550 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Backend + API, ~200), PR 2 (Frontend tab, ~200), PR 3 (Compliance + tests, ~150) |

---

## Phase 1: Backend — AuditLog Fix + Audit Trail API

### Task B1.1: Fix `_get_serializable_fields` to hash TextField content
**File**: `backend/core/signals.py`
**Action**: Replace the `TextField` skip in `_get_serializable_fields()` (line 135) with a SHA-256 hash. When a field is `TextField`, store `{field_name}_hash` instead of skipping entirely. Add `import hashlib` at top of file. This ensures clinical note content changes are captured in audit details without DB bloat.

- [x] B1.1 Done

### Task B1.2: Create AuditTrailViewSet
**File**: `backend/core/views.py` (new)
**Action**: Create a read-only `AuditTrailViewSet` (ListModelMixin + GenericViewSet) that filters `AuditLog` entries by query params `resource_type` and `resource_id`. Returns paginated list ordered by `-created_at`. Permissions: `IsAuthenticated`. Serializer: inline `AuditLogSerializer` with fields `id`, `action`, `resource_type`, `resource_id`, `user`, `details`, `result`, `ip_address`, `created_at`.

- [x] B1.2 Done

### Task B1.3: Wire audit trail URL route
**File**: `backend/core/urls.py` (new) or root `backend/config/urls.py`
**Action**: Register `AuditTrailViewSet` at `/api/v1/audit-trail/`. Ensure it's accessible with standard list action. If `core/urls.py` doesn't exist, add route in the root URL config.

- [x] B1.3 Done

### Task B1.4: Add audit trail API client method
**File**: `frontend/src/api/patients.ts`
**Action**: Add `getAuditTrail` method: `(resourceType: string, resourceId: string, params?: { page?: number }) => apiClient.get('/audit-trail/', { params: { resource_type: resourceType, resource_id: resourceId, ...params } })`. Add `AuditLog` type to `frontend/src/types/index.ts` if not present.

- [x] B1.4 Done

---

## Phase 2: Frontend — Audit Trail Tab

### Task B2.1: Create `useAuditTrail` hook
**File**: `frontend/src/hooks/useAuditTrail.ts` (new)
**Action**: Add React Query hook `useAuditTrail(resourceType, resourceId, params?)` that calls `patientsApi.getAuditTrail(resourceType, resourceId, params)`. Returns paginated audit entries with loading/error states. Query key: `['audit-trail', resourceType, resourceId, params]`.

- [x] B2.1 Done

### Task B2.2: Add `AuditLog` type
**File**: `frontend/src/types/index.ts`
**Action**: Add `AuditLog` interface: `{ id: string, action: string, resource_type: string, resource_id: string, user?: string, details: Record<string, unknown>, result: string, ip_address?: string, created_at: string }`.

- [x] B2.2 Done

### Task B2.3: Create `AuditTrailTab` component
**File**: `frontend/src/pages/Patients/AuditTrailTab.tsx` (new)
**Action**: Tab component that displays audit log entries in a table using shadcn `Table`. Columns: `action` (dot-notation), `user` (name or "Sistema"), `created_at` (formatted date), `result` (badge: success=green, failure=red), `details` (expandable JSON). Show hash fields (`*_hash`) with a "verified" Shield icon. Handle loading/empty states.

- [x] B2.3 Done

### Task B2.4: Wire Audit Trail tab into PatientDetailPage
**File**: `frontend/src/pages/Patients/PatientDetailPage.tsx`
**Action**: Add 4th tab "Auditoría" (Shield icon from lucide-react) to the `TabsList`. Add `TabsContent` for `value="audit"` rendering `<AuditTrailTab patientId={patient.id} />`. Pass `resource_type="Patient"` to the tab component.

- [x] B2.4 Done

---

## Phase 3: Compliance Features

### Task B3.1: Create retention policy management command
**File**: `backend/patients/management/commands/purge_expired_records.py` (new, with `__init__.py` files)
**Action**: Django management command that soft-deletes inactive patients and anonymizes old clinical notes (NOM-024 5-year retention). Supports `--years` and `--dry-run` flags.

- [x] B3.1 Done

### Task B3.2: Create patient export endpoint
**File**: `backend/patients/views.py`
**Action**: Add `@action(detail=True, methods=["get"], url_path="export")` `export_patient_data` method on `PatientViewSet`. Returns JSON response with: patient demographics (decrypted), all clinical notes (decrypted content), all consents, related appointments, related invoices. Response headers: `Content-Disposition: attachment`.

- [x] B3.2 Done

### Task B3.3: Add export API client + button
**File**: `frontend/src/api/patients.ts` + `frontend/src/pages/Patients/PatientDetailPage.tsx`
**Action**: Add `exportPatientData: (id: string) => apiClient.get(...)` to API client. Add "Exportar Expediente" button (Download icon) in PatientDetailPage header. On click, triggers browser download of JSON file.

- [x] B3.3 Done

---

## Phase 4: Tests

### Task B4.1: Create test infrastructure
**File**: `backend/patients/tests/__init__.py`, `backend/patients/tests/conftest.py` (new)
**Action**: Create test package with pytest fixtures: `patient`, `clinical_note`, `consent`, `dentist_user`, `clinic`, `admin_user`, `receptionist_user`, `signed_note`, `signed_consent`.

- [x] B4.1 Done

### Task B4.2: Model tests
**File**: `backend/patients/tests/test_models.py` (new)
**Action**: Test `ClinicalNote.sign()` immutability (raises ValueError on re-sign), `PatientConsent.sign()` flow (sets signed_at, signature_hash, with/without blob, IP), `Patient.soft_delete()` vs `hard_delete()`, `full_name` property.

- [x] B4.2 Done

### Task B4.3: Serializer tests
**File**: `backend/patients/tests/test_serializers.py` (new)
**Action**: Test `ClinicalNoteSerializer` valid data + decryption, `ClinicalNoteCreateSerializer` valid/invalid/required-fields, `PatientConsentSerializer` valid data + create flow, `PatientSerializer` decrypted output.

- [x] B4.3 Done

### Task B4.4: View tests
**File**: `backend/patients/tests/test_views.py` (new)
**Action**: Test `ClinicalNoteViewSet` list/create/sign/409 conflicts, `PatientConsentViewSet` list/create/sign, `AuditTrailViewSet` list/filter/auth-required, export endpoint.

- [x] B4.4 Done

### Task B4.5: Audit signal tests
**File**: `backend/patients/tests/test_signals.py` (new)
**Action**: Test TextField content hashed in audit details (not plain text), BinaryField skipped entirely, password field never logged (even hashed), audit log created on create/sign.

- [x] B4.5 Done

### Task B4.6: Frontend AuditTrailTab test
**File**: `frontend/src/pages/Patients/__tests__/AuditTrailTab.test.tsx` (new)
**Action**: Test renders audit entries, shows loading spinner, handles empty state ("No hay registros de auditoría"), expandable details toggle, success/failure icons, error state.

- [x] B4.6 Done

---

## Suggested PR Split

| PR | Scope | Est. Lines | Review Focus |
|----|-------|------------|--------------|
| **PR 1** | Phase 1: AuditLog hash fix + AuditTrailViewSet + API route + API client method | ~200 | Signal correctness, view permissions, API contract |
| **PR 2** | Phase 2: AuditTrailTab component + hook + PatientDetailPage integration + AuditLog type | ~200 | Tab rendering, React Query integration, UI consistency |
| **PR 3** | Phase 3 + 4: Retention command, export endpoint, full test suite (backend + frontend) | ~150 | Export completeness, test coverage, command safety |
