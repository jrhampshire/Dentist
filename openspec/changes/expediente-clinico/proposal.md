# SDD Change Proposal — Expediente Clínico Digital (NOM-024)

**Change ID**: `expediente-clinico`  
**Phase**: Proposal  
**Date**: 2026-05-20  
**Artifact Store**: Hybrid (Engram + openspec filesystem)

---

## 1. Intent

Build a **NOM-024 compliant clinical records system** for Mexican dental practices by:

1. **Exposing existing backend capabilities** through a functional frontend UI (patient detail view, clinical notes panel, consent management)
2. **Fixing critical type mismatches** between frontend TypeScript enums and backend TextChoices that would cause silent API failures
3. **Addressing NOM-024 regulatory gaps** in audit coverage, data retention, and record portability

**Why this matters**: The backend API for clinical notes and consents is already well-implemented with encryption, immutability, and role-based access. The blocker is the missing frontend UI and type safety issues. This proposal focuses on delivering user value first (Slice A), then regulatory hardening (Slice B).

---

## 2. Scope

### In Scope (Slice A — Frontend Expediente UI)

| Component | Description |
|-----------|-------------|
| **Type Fixes** | Align `ClinicalNote.note_type` and `PatientConsent.consent_type` enums in `frontend/src/types/index.ts` with backend TextChoices |
| **Patient Detail Page** | New `PatientDetailPage.tsx` with tabs: Info, Clinical Notes, Consents, Audit Trail |
| **Clinical Notes Tab** | List, create, view, and sign clinical notes inline |
| **Consents Tab** | List, create, view, and sign patient consents |
| **Route Integration** | Add `/patients/:id` route; update `PatientsPage` to navigate to detail view |
| **API Client Fix** | Correct endpoint paths in `frontend/src/api/patients.ts` (currently `/clinical-notes/` but backend uses `/notes/`) |

### In Scope (Slice B — NOM-024 Compliance Layer)

| Component | Description |
|-----------|-------------|
| **Audit Coverage Fix** | Modify `_get_serializable_fields()` in `backend/core/signals.py` to hash/capture TextField content (clinical note changes) |
| **Data Retention** | Add `DataRetentionPolicy` model and Celery task for automatic archival |
| **Patient Export** | Add `/api/v1/patients/{id}/export/` endpoint (JSON/PDF) for expediente portability |
| **Backend Tests** | Full test coverage for `patients` app (models, serializers, views, permissions) |

### Out of Scope (This Change)

- Rewriting the backend API (already functional)
- Moving `signature_blob` from PostgreSQL BinaryField to S3/object storage (scale concern, but not blocking)
- Real-time collaboration on clinical notes
- Offline mode for clinical notes

---

## 3. Components

### Backend Changes

| File | Change | Reason |
|------|--------|--------|
| `backend/core/signals.py` | Fix `_get_serializable_fields()` to include hashed TextField content | NOM-024 audit trail must capture note content changes |
| `backend/patients/views.py` | Add `export` action to `PatientViewSet` | Expediente portability requirement |
| `backend/patients/models.py` | Add `DataRetentionPolicy` model (Slice B) | NOM-024 retention periods |
| `backend/patients/tests/` | Create test suite (Slice B) | Zero coverage currently; regression risk |

### Frontend Changes

| File | Change | Reason |
|------|--------|--------|
| `frontend/src/types/index.ts` | Fix `ClinicalNote.note_type` enum: `consultation` → `evolution`, add `diagnosis`, `observation`, `consent` | Backend uses: `evolution`, `diagnosis`, `treatment`, `observation`, `consent` |
| `frontend/src/types/index.ts` | Fix `PatientConsent.consent_type` enum: add `general`, `whatsapp` | Backend uses: `general`, `treatment`, `data_processing`, `whatsapp` |
| `frontend/src/api/patients.ts` | Fix endpoints: `/clinical-notes/` → `/notes/` | Backend URL patterns use `/notes/` |
| `frontend/src/pages/PatientDetailPage.tsx` | **NEW**: Patient detail with tabs | Core UI for expediente |
| `frontend/src/pages/PatientsPage.tsx` | Update "Ver" button to navigate to `/patients/:id` | Route integration |
| `frontend/src/App.tsx` | Add route for patient detail | Navigation |
| `frontend/src/hooks/usePatients.ts` | Add `useSignConsent` hook | Missing hook for consent signing |

### Test Changes

| File | Change | Reason |
|------|--------|--------|
| `backend/patients/tests/test_models.py` | **NEW**: ClinicalNote immutability, PatientConsent signing | Model behavior validation |
| `backend/patients/tests/test_serializers.py` | **NEW**: Encryption/decryption, type validation | Serializer correctness |
| `backend/patients/tests/test_views.py` | **NEW**: CRUD operations, sign actions, permissions | API contract validation |
| `frontend/src/pages/__tests__/PatientDetailPage.test.tsx` | **NEW**: Tab navigation, note creation, signing | UI behavior validation |

---

## 4. Approach

### Phase 1: Slice A — Frontend Expediente UI (Recommended First PR)

**Goal**: Deliver functional UI for clinical notes and consents.

**Steps**:
1. Fix TypeScript enums in `types/index.ts` (blocking — API will fail without this)
2. Fix API endpoint paths in `api/patients.ts`
3. Create `PatientDetailPage.tsx` with tabs (Info, Notes, Consents)
4. Implement `ClinicalNotesTab` component (list, create, view, sign)
5. Implement `ConsentsTab` component (list, create, view, sign)
6. Add route `/patients/:id` in `App.tsx`
7. Update `PatientsPage.tsx` "Ver" button to navigate

**Estimated Effort**: 250–350 lines of frontend code  
**Review Focus**: Type alignment, UI usability, React Query integration

### Phase 2: Slice B — NOM-024 Compliance Layer (Follow-up PR)

**Goal**: Regulatory hardening for Mexican dental audits.

**Steps**:
1. Fix `_get_serializable_fields()` to hash TextField content (critical NOM-024 gap)
2. Add `DataRetentionPolicy` model with Celery task
3. Implement `/export/` endpoint for patient record portability
4. Write comprehensive backend tests for `patients` app

**Estimated Effort**: 350–550 lines across backend + tests  
**Review Focus**: Audit coverage, retention logic, test coverage

---

## 5. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Type Mismatch Breaks API** | 🔴 Critical | Fix enums in `types/index.ts` BEFORE any UI work. Backend valid values: `note_type` = `evolution|diagnosis|treatment|observation|consent`, `consent_type` = `general|treatment|data_processing|whatsapp` |
| **AuditLog Content Gap** | 🟠 High | Slice B must fix `_get_serializable_fields()` to hash TextField content. Current behavior: note content changes are invisible to audit trail. |
| **Zero Test Coverage** | 🟠 High | Slice B includes full test suite. Until then, manual QA required for Slice A. |
| **Patient Hard Delete Cascades Notes** | 🟡 Medium | `Patient.hard_delete()` will CASCADE to `ClinicalNote`. NOM-024 may require retention. Consider `SET_NULL` or soft-delete on notes (Slice B). |
| **Signature Blob in PostgreSQL** | 🟡 Medium | `PatientConsent.signature_blob` stores binary in DB. At scale, move to S3/MinIO. Not blocking for MVP. |
| **Role Name Mismatch** | 🟡 Medium | Backend uses Spanish roles (`dentista`, `recepcionista`), frontend types use English (`dentist`, `recepcionista`). Middleware must set `user_role` consistently. |

---

## 6. Key Decisions

### 6.1 Enum Mismatch Resolution

**Decision**: Update frontend TypeScript enums to match backend TextChoices exactly.

**Frontend (current, WRONG)**:
```typescript
note_type: 'consultation' | 'treatment' | 'follow_up' | 'other'
consent_type: 'treatment' | 'data_processing' | 'marketing'
```

**Backend (correct)**:
```python
# ClinicalNote.NoteType
EVOLUTION = "evolution"
DIAGNOSIS = "diagnosis"
TREATMENT = "treatment"
OBSERVATION = "observation"
CONSENT = "consent"

# PatientConsent.ConsentType
GENERAL = "general"
TREATMENT = "treatment"
DATA_PROCESSING = "data_processing"
WHATSAPP = "whatsapp"
```

**Rationale**: Backend is the source of truth for API contracts. Frontend must align.

---

### 6.2 Signature Blob Storage

**Decision**: Keep `signature_blob` in PostgreSQL BinaryField for MVP; document as technical debt.

**Rationale**:
- Moving to S3 requires infrastructure setup (bucket, IAM, CDN)
- Adds complexity to consent signing flow (upload → get URL → store reference)
- PostgreSQL BinaryField is acceptable for <10K patients
- Can migrate later with background job

**Tradeoff**: Simpler MVP vs. scalability. Revisit at 5K+ patients.

---

### 6.3 AuditLog TextField Capture

**Decision**: Hash TextField content instead of storing plain text in audit details.

**Implementation**:
```python
def _get_serializable_fields(instance: Any) -> dict:
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.attname, None)
        if field.get_internal_type() == "TextField":
            # Hash instead of storing plain content
            data[f"{field.name}_hash"] = hashlib.sha256(value.encode()).hexdigest()
        elif field.get_internal_type() != "BinaryField":
            data[field.name] = str(value) if not isinstance(value, (str, int, float, bool, dict, list)) else value
    return data
```

**Rationale**:
- NOM-024 requires proof of content integrity
- Storing full TextField content in audit log would bloat DB
- Hash allows verification: "content matched at time of audit entry"

---

### 6.4 Frontend Architecture: Inline vs Separate Page

**Decision**: Separate `PatientDetailPage` with tabs (not inline in `PatientsPage`).

**Rationale**:
- Clinical notes and consents are complex workflows (create, view, sign, audit)
- Inline would make `PatientsPage` unwieldy (>500 lines)
- Tabbed detail page scales better for future features (treatment plans, invoices, appointments)
- Follows React Router best practices for master-detail patterns

---

## 7. Success Criteria

### Slice A (Frontend UI)

- ✅ User can navigate from patient list to patient detail view
- ✅ User can create, view, and sign clinical notes
- ✅ User can create, view, and sign consents
- ✅ No TypeScript type errors or runtime API failures due to enum mismatches
- ✅ PR size < 400 lines (focused review)

### Slice B (NOM-024 Compliance)

- ✅ AuditLog captures hashed content of TextField changes
- ✅ DataRetentionPolicy model exists with Celery task
- ✅ `/export/` endpoint returns complete patient record (JSON)
- ✅ Backend test coverage > 80% for `patients` app
- ✅ All NOM-024 requirements mapped and validated

---

## 8. Recommendation

**Proceed with Slice A first**. The backend is solid; the immediate blocker is the missing frontend UI and type mismatches. Ship Slice A to unlock user value, then follow with Slice B for regulatory hardening.

**Next Step**: If approved, move to **Design Phase** to create detailed technical design for Slice A (component hierarchy, state management, API integration patterns).

---

## Appendix: NOM-024 Requirements Mapping

| Requirement | Status | Component |
|-------------|--------|-----------|
| Identity of creator/modifier | ✅ Existing | `created_by`, `author`, `signed_by`, `user` on AuditLog |
| Immutable audit trail | ⚠️ Slice B | Append-only `AuditLog`, but TextField content not captured |
| Patient consent management | ⚠️ Slice A | Models + API exist; missing frontend UI |
| Data retention periods | ❌ Slice B | Not implemented |
| Physical/electronic security | ✅ Existing | AES-256-GCM encryption, RLS, soft delete |
| Record integrity (hash) | ✅ Existing | SHA-256 on `ClinicalNote` and `PatientConsent` |
| Access control | ✅ Existing | `IsDentist`, `IsClinicAdmin`, `IsOwnerOrAdmin` |
| Expediente portability | ❌ Slice B | No export endpoint |
