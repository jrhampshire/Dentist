## Exploration: Expediente Clínico Digital (NOM-024)

### Current State

The backend for Clinical Notes and Patient Consent is **already largely implemented** — contrary to the initial assumption that no API layer existed.

**What EXISTS (Backend):**
- `ClinicalNote` model with encrypted content, `sign()` method, immutability enforcement at model + serializer levels, SHA-256 signature hash, and FK to `Patient` and `Appointment`.
- `PatientConsent` model with signature blob, hash, IP tracking, and `sign()` method.
- `ClinicalNoteViewSet` (List, Retrieve, Create, Sign action) nested under `/api/v1/patients/{id}/notes/`.
- `PatientConsentViewSet` (List, Retrieve, Create, Sign action) nested under `/api/v1/patients/{id}/consents/`.
- Serializers with automatic encryption/decryption via `encryption_service`.
- Role-based permissions: `IsDentist` for notes, `IsAuthenticated` for consents.
- `AuditLog` append-only model with `post_save`/`post_delete` signal-based auto-logging.
- `AuditMiddleware` capturing IP, user agent, request ID, and clinic context per request.
- `Patient` model includes top-level `consent_signed`, `consent_signed_at`, and `consent_version` fields.

**What EXISTS (Frontend):**
- `patientsApi` module already defines endpoints for notes and consents.
- React Query hooks (`useClinicalNotes`, `useCreateClinicalNote`, `useSignClinicalNote`, `useConsents`, `useCreateConsent`) already exist.
- `PatientsPage.tsx` provides a basic patient list with CRUD dialog.

**What is MISSING:**
- **Frontend UI**: No patient detail view, no clinical notes panel, no consent management UI, no sign-note flow. The `PatientsPage` is just a searchable table with create/edit dialogs.
- **Type Safety**: Frontend TypeScript types have **wrong enum values** that do not match backend choices. This will cause silent runtime failures.
- **Audit Coverage**: `AuditLog` signal handler (`_get_serializable_fields`) skips `TextField` values, meaning **clinical note content changes are not captured in audit details** — a potential NOM-024 gap.
- **Data Retention**: No enforcement of NOM-024 retention periods or automatic archival policies.
- **Tests**: Zero tests exist for the `patients` app.
- **Update/Delete on Notes/Consents**: ViewSets intentionally lack Update/Delete mixins (by design for immutability), but unsigned notes cannot be corrected without creating a new record.
- **NOM-024 Export**: No endpoint to export a complete patient record (expediente clínico completo) as required for portability.

### Affected Areas

| File | Why Affected |
|------|-------------|
| `backend/patients/models.py` | Core domain; may need retention fields or cascade adjustments |
| `backend/patients/views.py` | Already functional; may need export/report actions |
| `backend/patients/serializers.py` | Type enum alignment; audit detail gaps |
| `backend/core/signals.py` | `_get_serializable_fields` skips `TextField` — hides note content from audit |
| `backend/core/models.py` | `AuditLog` may need retention tagging or NOM-024-specific action types |
| `frontend/src/types/index.ts` | **Critical mismatch** in `note_type` and `consent_type` enums |
| `frontend/src/pages/PatientsPage.tsx` | Needs expansion into patient detail + clinical notes + consents |
| `frontend/src/hooks/usePatients.ts` | Hooks exist but are not consumed by any UI |
| `frontend/src/api/patients.ts` | Already complete; may need export endpoint |

### NOM-024 Requirements Mapping

| Requirement | Status | Gap |
|-------------|--------|-----|
| Identity of creator/modifier | ✅ | `created_by`, `author`, `signed_by`, `user` on AuditLog |
| Immutable audit trail | ⚠️ | Append-only `AuditLog`, but **note content changes are omitted** from details |
| Patient consent management | ⚠️ | Models exist, API exists, **no frontend UI** |
| Data retention periods | ❌ | Not implemented |
| Physical/electronic security | ✅ | AES-256-GCM encryption, RLS, soft delete |
| Record integrity (hash) | ✅ | SHA-256 on `ClinicalNote` and `PatientConsent` |
| Access control | ✅ | `IsDentist`, `IsClinicAdmin`, `IsOwnerOrAdmin` |
| Expediente portability | ❌ | No export endpoint |

### Approaches

#### 1. Frontend-First Approach (Minimum Viable)
Build the missing UI components, fix type mismatches, and wire existing APIs.

- **Pros**: Fastest path to user value; leverages existing solid backend.
- **Cons**: Leaves NOM-024 gaps (retention, audit detail coverage, export) unaddressed.
- **Effort**: Medium (~250–350 frontend lines).

#### 2. Full NOM-024 Compliance Approach
Frontend UI + backend enhancements for full regulatory compliance.

- **Frontend**: Patient Detail page with tabs (Info, Clinical Notes, Consents), note creation/signing, consent capture, audit trail viewer.
- **Backend**: Fix audit detail capture for encrypted fields, add data retention model/scheduler, add patient record export endpoint (PDF/JSON).
- **Pros**: Production-ready for Mexican regulatory audits.
- **Cons**: Significantly larger scope; requires background job infrastructure (Celery) for retention policies.
- **Effort**: High (~600–900 lines across both stacks).

#### 3. Incremental Approach (Recommended)
Slice into two deliverable chunks:

1. **Slice A — Frontend Expediente UI + Type Fixes** (reviewable PR < 400 lines)
   - Fix `ClinicalNote` and `PatientConsent` TypeScript types.
   - Create `PatientDetailPage` with tabs.
   - `ClinicalNotesTab`: list, create, view, sign.
   - `ConsentsTab`: list, create, view, sign.
   - Add route for patient detail.

2. **Slice B — NOM-024 Compliance Layer**
   - Fix `_get_serializable_fields` to hash/capture note content for audit.
   - Add `DataRetentionPolicy` model and Celery task.
   - Add `/api/v1/patients/{id}/export/` endpoint.
   - Add backend tests for the entire `patients` app.

- **Pros**: Protects review focus, delivers value early, reduces risk.
- **Cons**: Requires two PRs instead of one.
- **Effort**: Slice A = Medium, Slice B = Medium-High.

### Recommendation

**Go with Approach 3 (Incremental)**. The backend API is already functional and well-designed. The immediate blocker is the missing frontend UI and the type mismatches. Ship Slice A first to unlock the feature, then follow with Slice B for regulatory hardening.

### Risks

1. **Type Mismatch Silently Breaks API Calls**: Frontend sends `note_type: 'consultation'` which the backend rejects (valid: `evolution`, `diagnosis`, `treatment`, `observation`, `consent`). This must be fixed before any UI goes live.
2. **AuditLog Content Gap**: NOM-024 auditors may require proof that clinical note content was not altered. The current signal handler skips `TextField`, so content changes are invisible to the audit trail.
3. **Zero Test Coverage**: The `patients` app has no tests. Changes to serializers or views carry regression risk.
4. **Patient Soft Delete vs Note Hard Delete**: While `Patient.delete()` is a soft delete, `Patient.hard_delete()` (or admin action) will cascade-delete `ClinicalNote` records due to `on_delete=models.CASCADE`. NOM-024 may require retention even after patient deletion.
5. **Signature Blob Storage**: `PatientConsent.signature_blob` stores binary data in PostgreSQL. At scale, this should move to object storage (S3/MinIO) with a reference in the DB.
6. **Role Mismatch in Permissions**: `IsDentist` checks for `user_role in ("dentista", "admin")`, but the frontend `User.role` type only includes `'admin' | 'dentist' | 'recepcionista'`. The backend uses Spanish role names (`dentista`, `recepcionista`) while the frontend uses English (`dentist`, `recepcionista`). Ensure middleware sets `user_role` consistently.

### Ready for Proposal

**Yes** — with a recommendation to scope the initial proposal around **Slice A (Frontend Expediente UI + Type Fixes)**. The backend foundation is strong; the proposal should focus on the frontend gap and explicitly note that NOM-024 hardening (Slice B) will be a follow-up change.
