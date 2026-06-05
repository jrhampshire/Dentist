# Tasks: Odontograma / Historia Clínica (Fase A)

## Change: `odontograma-historia-clinica`

## Review Workload Forecast

| Work Unit | Est. Lines | PR |
|-----------|-----------|-----|
| 1. Backend foundation (app, models, migrations, signals) | ~450 | PR #1 |
| 2. Backend API (views, serializers, urls) | ~500 | PR #2 |
| 3. Backend tests | ~400 | PR #2 (same PR, test follows code) |
| 4. Frontend foundation (types, API client, hooks) | ~250 | PR #3 |
| 5. Frontend UI — OdontogramSVG + tabs wire-up | ~350 | PR #4 |
| 6. Frontend UI — MedicalHistory + VitalSigns | ~300 | PR #5 |
| 7. Frontend UI — PatientImages gallery + viewer | ~350 | PR #6 |
| 8. Frontend UI — TreatmentPlan components | ~300 | PR #7 |
| **Total** | **~2900 lines** | **7 chained PRs** |

### Chained PR Strategy

```
PR #1: Backend foundation (models + migrations + signals)
  └── PR #2: Backend API + tests (views, serializers, urls, tests)
        └── PR #3: Frontend foundation (types, API client, hooks)
              └── PR #4: OdontogramSVG + tab wire-up
              └── PR #5: MedicalHistory + VitalSigns tabs
              └── PR #6: PatientImages gallery + viewer
              └── PR #7: TreatmentPlan components
```

**Dependency graph**: PR #1 → PR #2 → PR #3 → {PR #4, PR #5, PR #6, PR #7} (independent, merge order: 4, 5, 6, 7)

---

## Work Unit 1: Backend Foundation

### Task 1.1 — Create `dental_records` app skeleton ✅
**File**: `backend/dental_records/__init__.py` (empty)
**File**: `backend/dental_records/apps.py`
- [x] Create `DentalRecordsConfig` with `ready()` that imports `dental_records.signals`

**File**: `backend/dental_records/models.py`
- [x] All 12 models per design.md:
  - `VALID_FDI_CODES`, `SURFACE_CHOICES`, `CONDITION_CHOICES`, `validate_fdi()`
  - `DentalRecordEntry` (append-only, save/delete overrides)
  - `Tooth` (materialized, unique patient+tooth_fdi)
  - `ToothSurface` (materialized, unique tooth+surface)
  - `MedicalHistory` (versioned, is_active toggle)
  - `VitalSigns` (optional appointment FK)
  - `PatientImage` + `image_upload_path()`
  - `TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure`

**File**: `backend/dental_records/signals.py`
- [x] `materialize_tooth_state` post_save receiver on `DentalRecordEntry`

**File**: `backend/dental_records/choices.py`
- [x] ToothCondition, Surface, ImageType TextChoices

**File**: `backend/dental_records/urls.py`
- [x] Placeholder urlpatterns (will be filled in PR#2)

**File**: `backend/dental_records/tests/__init__.py`
**File**: `backend/dental_records/tests/test_models.py`
- [x] Tests for all 12 models, append-only constraint, signal materialization, tenant isolation, versioning, FDI validation, image path format, procedure appointment linking

### Task 1.2 — Register app in settings ✅
**File**: `backend/config/settings/base.py`
- [x] Add `"dental_records"` to `LOCAL_APPS` list (after dashboard, before invoicing)

**File**: `backend/config/urls.py`
- [x] Add `path("api/v1/dental-records/", include("dental_records.urls"))`

**File**: `backend/requirements.txt`
- [x] Add Pillow>=10.0 and django-storages>=1.14

### Task 1.3 — Create initial migration ✅
**Action**: `python manage.py makemigrations dental_records`
- [x] Single migration `0001_initial.py` creating all 12 models + indexes/constraints
- Depends on `patients` (Patient model), `appointments` (Appointment model)

### Task 1.4 — Extend ClinicalNote with dental fields ✅
**File**: `backend/patients/models.py`
- [x] Add `tooth_fdi` (IntegerField, null, blank) to `ClinicalNote`
- [x] Add `surface` (CharField, null, blank, choices=SURFACE_CHOICES) to `ClinicalNote`

**Migration**: `backend/patients/migrations/0002_add_clinical_note_dental_fields.py`
- [x] Migration adds nullable fields, no data loss

---

## Work Unit 2: Backend API + Tests

### Task 2.1 — Serializers ✅
**File**: `backend/dental_records/serializers.py`
- [x] `DentalRecordEntrySerializer` (read+create, includes created_by_name, idempotent check, FDI/surface validation)
- [x] `ToothStateSerializer` + `ToothSurfaceStateSerializer` (read-only nested state)
- [x] `MedicalHistorySerializer` (read+versioned upsert, creates new version on PUT)
- [x] `VitalSignsSerializer` (read+create, BP validation, at-least-one-field check)
- [x] `PatientImageListSerializer` (list, proxy URLs), `PatientImageUploadSerializer` (multipart, thumbnail gen), `PatientImageSerializer` (detail)
- [x] `TreatmentPlanDetailSerializer` (nested phases→procedures), `TreatmentPlanListSerializer`
- [x] `TreatmentPhaseSerializer` (nested procedures)
- [x] `TreatmentProcedureSerializer` (FDI validation, cost >= 0)

### Task 2.2 — Views / ViewSets ✅
**File**: `backend/dental_records/views.py`
- [x] `DentalRecordEntryViewSet`: list + create + retrieve, 405 on PUT/PATCH/DELETE
- [x] `ToothStateViewSet`: read-only list → GET `/patients/{id}/teeth/state/`
- [x] `MedicalHistoryViewSet`: list (active), create, retrieve, PUT (versioned upsert), list_versions action
- [x] `VitalSignsViewSet`: list, create, retrieve, date range filter, appointment filter
- [x] `PatientImageViewSet`: create, list, retrieve, serve_file, serve_thumbnail, destroy
- [x] `TreatmentPlanViewSet`: full CRUD
- [x] `TreatmentPhaseViewSet`: CRUD nested under plan
- [x] `TreatmentProcedureViewSet`: CRUD nested under phase

### Task 2.3 — URL routing ✅
**File**: `backend/dental_records/urls.py`
- [x] Manual path() patterns for all ViewSets with patient_id/{plan_id}/{phase_id} nesting
- [x] config/urls.py already has the include (set up in PR#1)

### Task 2.4 — Image serving helper ✅
**File**: `backend/dental_records/services.py`
- [x] `generate_thumbnail(image_file, max_size=(300, 300))` → returns InMemoryUploadedFile or None (for PDFs)
- [x] `get_image_path(instance, filename)` → returns storage path

### Task 2.5 — Backend Tests ✅
**File**: `backend/dental_records/tests/test_api.py` (consolidated all API tests)
- [x] DentalRecordEntry: create, idempotent, list, filter by tooth_fdi, invalid FDI→400, invalid surface→400, DELETE/PUT/PATCH→405
- [x] ToothState: entry→state reflected, empty patient, multiple surfaces, state overwrites
- [x] MedicalHistory: create v1, get active, 404 on none, PUT creates v2, list versions, preserves antecedents
- [x] VitalSigns: create, list, date range filter, BP validation, at-least-one-field, retrieve
- [x] PatientImage: upload JPEG→thumbnail, upload PDF→no thumbnail, list, filter by type, serve_file, serve_thumbnail, delete, wrong type→400
- [x] TreatmentPlan: create, list, detail with nested phases, create phase, create procedure, cascade delete, invalid FDI, negative cost
- [x] Tenant isolation: cross-clinic access → 404/empty for entries, medical history, vital signs, images, plans
- [x] Unauthenticated: all endpoints → 401

(Note: test_models.py was already completed in PR#1 with model-level tests. Clinical note dental fields tests deferred to PR#3 with frontend.)

---

## Work Unit 3: Frontend Foundation

### Task 3.1 — TypeScript types ✅
**File**: `frontend/src/types/dental-records.ts`
- [x] `ToothCondition` enum type
- [x] `SurfaceName` type
- [x] `ToothSurface` interface
- [x] `Tooth` interface
- [x] `DentalRecordEntry` interface
- [x] `MedicalHistory` interface
- [x] `VitalSigns` interface
- [x] `PatientImage` interface
- [x] `TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure` interfaces
- [x] `CONDITION_COLORS` constant map
- [x] `IMAGE_TYPE_LABELS` constant map
- [x] `PLAN_STATUS_LABELS`, `PHASE_STATUS_LABELS`, `PROC_STATUS_LABELS`

### Task 3.2 — API client ✅
**File**: `frontend/src/api/dental-records.ts`
- [x] `dentalRecordsApi` object with all endpoints:
  - [x] `getOdontogram(patientId)`, `listDentalRecords(patientId)`, `createDentalRecord(patientId, data)`
  - [x] `getMedicalHistory(patientId)`, `upsertMedicalHistory(patientId, data)`, `listMedicalHistoryVersions(patientId)`
  - [x] `listVitalSigns(patientId, params?)`, `createVitalSigns(patientId, data)`, `getVitalSigns(patientId, recordId)`
  - [x] `listImages(patientId, params?)`, `createImage(patientId, formData)`, `getImage(patientId, imageId)`, `serveFile(patientId, imageId)`, `serveThumbnail(patientId, imageId)`, `deleteImage(patientId, imageId)`
  - [x] `listTreatmentPlans(patientId)`, `createTreatmentPlan(patientId, data)`, `getTreatmentPlan(patientId, planId)`, `updateTreatmentPlan(...)`, `deleteTreatmentPlan(...)`
  - [x] `createPhase(patientId, planId, data)`, `updatePhase(...)`, `deletePhase(...)`
  - [x] `createProcedure(patientId, planId, phaseId, data)`, `updateProcedure(...)`, `deleteProcedure(...)`

### Task 3.3 — React Query hooks ✅
**File**: `frontend/src/hooks/useDentalRecords.ts`
- [x] `useOdontogram(patientId)`, `useDentalRecords(patientId)`, `useCreateDentalRecord()`

**File**: `frontend/src/hooks/useMedicalHistory.ts`
- [x] `useMedicalHistory(patientId)`, `useMedicalHistoryVersions(patientId)`, `useUpsertMedicalHistory()`

**File**: `frontend/src/hooks/useVitalSigns.ts`
- [x] `useVitalSigns(patientId, params?)`, `useCreateVitalSigns()`

**File**: `frontend/src/hooks/usePatientImages.ts`
- [x] `usePatientImages(patientId, params?)`, `useCreatePatientImage()`, `useDeletePatientImage()`

**File**: `frontend/src/hooks/useTreatmentPlans.ts`
- [x] `useTreatmentPlans(patientId)`, `useTreatmentPlan(patientId, planId)`, `useCreateTreatmentPlan()`, `useUpdateTreatmentPlan()`, `useDeleteTreatmentPlan()`
- [x] `useCreatePhase()`, `useUpdatePhase()`, `useDeletePhase()`
- [x] `useCreateProcedure()`, `useUpdateProcedure()`, `useDeleteProcedure()`

---

## Work Unit 4: Frontend UI — Odontogram

### Task 4.1 — OdontogramSVG component ✅
**File**: `frontend/src/components/odontogram/OdontogramSVG.tsx`
- [x] SVG with viewBox `0 0 800 500`
- [x] Two arches: maxillary (upper) and mandibular (lower)
- [x] 32 permanent teeth (11-18, 21-28, 31-38, 41-48) + 20 primary (51-55, 61-65, 71-75, 81-85)
- [x] Each permanent tooth: 5 polygons (mesial, distal, buccal, lingual, occlusal)
- [x] Each primary tooth: 4 polygons (no occlusal)
- [x] Color mapping from `CONDITION_COLORS`
- [x] Props: `teeth: Tooth[]`, `onSurfaceClick(toothFdi, surfaceName)`
- [x] FDI labels rendered as `<text>` elements

### Task 4.2 — SurfaceConditionModal ✅
**File**: `frontend/src/components/odontogram/SurfaceConditionModal.tsx`
- [x] Dialog/modal with condition dropdown (14 options with color swatches)
- [x] Notes textarea
- [x] Submit button → calls `onSubmit` callback
- [x] Shadcn/ui Dialog + native select + textarea components

### Task 4.3 — LegendPanel ✅
**File**: `frontend/src/components/odontogram/LegendPanel.tsx`
- [x] Color legend showing all 14 conditions with their colors
- [x] Compact 2-column grid layout

### Task 4.4 — OdontogramTab ✅
**File**: `frontend/src/components/odontogram/OdontogramTab.tsx`
- [x] Composes OdontogramSVG + SurfaceConditionModal + LegendPanel
- [x] Fetches odontogram data via `useOdontogram`
- [x] Handles surface click → modal → create entry → query invalidation
- [x] Loading/error/empty states

### Task 4.5 — Wire Odontogram tab into PatientDetailPage ✅
**File**: `frontend/src/pages/Patients/PatientDetailPage.tsx`
- [x] Add new TabsTrigger: "Odontograma" (value="odontogram")
- [x] Add TabsContent wrapping `<OdontogramTab patientId={patient.id} />`
- [x] Import `OdontogramTab`

---

## Work Unit 5: Frontend UI — MedicalHistory + VitalSigns

### Task 5.1 — MedicalHistoryForm ✅
**File**: `frontend/src/components/medical-history/MedicalHistoryForm.tsx`
- [x] Form with 5 antecedent sections (patológicos, quirúrgicos, alérgicos, farmacológicos, familiares) with add/remove items
- [x] Textareas for motivo_consulta + enfermedad_actual
- [x] Submit → `upsertMedicalHistory`
- [x] Pre-fills with existing active record data

### Task 5.2 — MedicalHistoryTab ✅
**File**: `frontend/src/components/medical-history/MedicalHistoryTab.tsx`
- [x] Shows active record (read-only view) + edit button
- [x] Edit mode shows MedicalHistoryForm
- [x] Version history toggle (collapsible list of past versions)
- [x] Uses `useMedicalHistory` + `useMedicalHistoryVersions`
- [x] Loading/error/empty states

### Task 5.3 — VitalSignsForm ✅
**File**: `frontend/src/components/vital-signs/VitalSignsForm.tsx`
- [x] Form with fields: BP systolic/diastolic, heart rate, temperature, weight, height, notes
- [x] Validation: min/max ranges on number inputs
- [x] Shadcn/ui Input + textarea
- [x] Submit → `createVitalSigns`

### Task 5.4 — VitalSignsHistory ✅
**File**: `frontend/src/components/vital-signs/VitalSignsHistory.tsx`
- [x] Table of past vital signs records
- [x] Sorted by recorded_at desc (handled in parent)
- [x] Shows BP as "120/80", HR, temp, weight, height
- [x] Empty state

### Task 5.5 — VitalSignsTab ✅
**File**: `frontend/src/components/vital-signs/VitalSignsTab.tsx`
- [x] Composes VitalSignsForm + VitalSignsHistory
- [x] Uses `useVitalSigns` + `useCreateVitalSigns`
- [x] Loading/error/empty states

### Task 5.6 — Wire MedicalHistory + VitalSigns tabs into PatientDetailPage ✅
**File**: `frontend/src/pages/Patients/PatientDetailPage.tsx`
- [x] Add TabsTrigger: "Historia Médica" (value="medical-history", Heart icon)
- [x] Add TabsTrigger: "Signos Vitales" (value="vital-signs", Activity icon)
- [x] Add corresponding TabsContent with `<MedicalHistoryTab>` and `<VitalSignsTab>`

---

## Work Unit 6: Frontend UI — PatientImages

### Task 6.1 — ImageUploader
**File**: `frontend/src/components/patient-images/ImageUploader.tsx`
- Drag & drop zone (react-dropzone or native HTML5)
- File type validation (JPEG, PNG, PDF)
- File size validation (20MB max)
- Metadata form: image_type select, tooth_fdi optional, description
- Upload progress indicator
- Submit → `createImage` with FormData (multipart)

### Task 6.2 — ImageGallery
**File**: `frontend/src/components/patient-images/ImageGallery.tsx`
- CSS Grid (3-4 columns responsive)
- Thumbnail previews (served via `serveThumbnail` endpoint)
- Filter chips by image_type
- Filter by tooth_fdi (dropdown)
- Click thumbnail → opens ImageViewer modal
- Loading skeleton, empty state

### Task 6.3 — ImageViewer
**File**: `frontend/src/components/patient-images/ImageViewer.tsx`
- Modal overlay (Shadcn/ui Dialog)
- `<img>` with original image (served via `serveFile` endpoint)
- Keyboard navigation (← → for prev/next, Esc to close)
- Zoom via CSS transform + mouse wheel
- Metadata panel: type, tooth, date, uploader, description
- Delete button (admin only)

### Task 6.4 — PatientImagesTab
**File**: `frontend/src/components/patient-images/PatientImagesTab.tsx`
- Composes ImageUploader + ImageGallery + ImageViewer
- Uses `usePatientImages` + `useCreatePatientImage` + `useDeletePatientImage`
- Upload modal trigger button

### Task 6.5 — Wire PatientImages tab into PatientDetailPage
**File**: `frontend/src/pages/Patients/PatientDetailPage.tsx`
- Add TabsTrigger: "Imágenes" (value="images")
- Add TabsContent with `<PatientImagesTab patientId={patient.id} />`

---

## Work Unit 7: Frontend UI — TreatmentPlan

### Task 7.1 — TreatmentPlanForm ✅
**File**: `frontend/src/components/treatment-plan/TreatmentPlanForm.tsx`
- [x] Form: name, description, status select
- [x] Create/edit mode via Dialog
- [x] Submit → `createTreatmentPlan` or `updateTreatmentPlan`

### Task 7.2 — PhaseList + PhaseForm ✅
**File**: `frontend/src/components/treatment-plan/PhaseList.tsx`
- [x] Accordion-style expandable cards per phase (chevron toggle, no Shadcn Accordion available)
- [x] Shows phase name, order, status, description
- [x] "Add procedure" button per phase
- [x] Edit/delete phase buttons

**File**: `frontend/src/components/treatment-plan/PhaseForm.tsx`
- [x] Inline form for creating/editing phases
- [x] Fields: name, order, description, status

### Task 7.3 — ProcedureList + ProcedureForm ✅
**File**: `frontend/src/components/treatment-plan/ProcedureList.tsx`
- [x] Table of procedures within a phase (Shadcn/ui Table)
- [x] Columns: description, tooth_fdi, cost, status, actions (no appointment column — field in backend but not wired)
- [x] Inline edit/delete buttons

**File**: `frontend/src/components/treatment-plan/ProcedureForm.tsx`
- [x] Inline form for creating/editing procedures
- [x] Fields: description (required), tooth_fdi (optional), cost (optional), status, notes (optional textarea)

### Task 7.4 — TreatmentPlanDetail ✅
**File**: `frontend/src/components/treatment-plan/TreatmentPlanDetail.tsx`
- [x] Shows plan header (name, status, description)
- [x] PhaseList nested inside
- [x] Edit plan button (opens TreatmentPlanForm dialog)
- [x] Delete plan button (with inline confirmation)

### Task 7.5 — TreatmentPlanList ✅
**File**: `frontend/src/components/treatment-plan/TreatmentPlanList.tsx`
- [x] List of plans for patient (cards with name, status badge, phases_count, date)
- [x] "Create new plan" button
- [x] Click plan → onSelectPlan callback

### Task 7.6 — TreatmentPlanTab ✅
**File**: `frontend/src/components/treatment-plan/TreatmentPlanTab.tsx`
- [x] Two-panel layout: left list, right detail
- [x] Composes TreatmentPlanList + TreatmentPlanDetail + TreatmentPlanForm dialog
- [x] Uses all hooks from useTreatmentPlans
- [x] Loading/error/empty/selection states

### Task 7.7 — Wire TreatmentPlan tab into PatientDetailPage ✅
**File**: `frontend/src/pages/Patients/PatientDetailPage.tsx`
- [x] Add TabsTrigger: "Plan de Tratamiento" (value="treatment-plan", ClipboardList icon)
- [x] Add TabsContent with `<TreatmentPlanTab patientId={patient.id} />`

---

## Task Ordering & Dependencies

```
Phase 1: Backend Foundation
  ├── 1.1 Create dental_records app (models + signals)
  ├── 1.2 Register app in settings
  ├── 1.3 Create initial migration
  └── 1.4 Extend ClinicalNote (patients app migration)

Phase 2: Backend API + Tests
  ├── 2.1 Serializers
  ├── 2.2 Views/ViewSets
  ├── 2.3 URL routing
  ├── 2.4 Image serving helper
  └── 2.5 Backend tests (all test files)

Phase 3: Frontend Foundation
  ├── 3.1 TypeScript types
  ├── 3.2 API client
  └── 3.3 React Query hooks

Phase 4: Odontogram UI
  ├── 4.1 OdontogramSVG
  ├── 4.2 SurfaceConditionModal
  ├── 4.3 LegendPanel
  ├── 4.4 OdontogramTab
  └── 4.5 Wire into PatientDetailPage

Phase 5: MedicalHistory + VitalSigns UI
  ├── 5.1 MedicalHistoryForm
  ├── 5.2 MedicalHistoryTab
  ├── 5.3 VitalSignsForm
  ├── 5.4 VitalSignsHistory
  ├── 5.5 VitalSignsTab
  └── 5.6 Wire into PatientDetailPage

Phase 6: PatientImages UI
  ├── 6.1 ImageUploader
  ├── 6.2 ImageGallery
  ├── 6.3 ImageViewer
  ├── 6.4 PatientImagesTab
  └── 6.5 Wire into PatientDetailPage

Phase 7: TreatmentPlan UI
  ├── 7.1 TreatmentPlanForm
  ├── 7.2 PhaseList + PhaseForm
  ├── 7.3 ProcedureList + ProcedureForm
  ├── 7.4 TreatmentPlanDetail
  ├── 7.5 TreatmentPlanList
  ├── 7.6 TreatmentPlanTab
  └── 7.7 Wire into PatientDetailPage
```

## Notes

- **All ViewSets** must scope querysets by `patient_id` from URL kwargs and verify patient belongs to user's clinic (404 if not).
- **Image serving endpoints** (`serve_file`, `serve_thumbnail`) must stream file content, not redirect to S3.
- **OdontogramSVG geometry**: permanent teeth ~24×32px, primary ~18×24px. Oclusal = center rect, mesial/distal = side rects, buccal/lingual = top/bottom rects.
- **MedicalHistory upsert**: PUT → find active record, set `is_active=False`, create new with `version = max_version + 1`.
- **DentalRecordEntry idempotency**: if tooth+surface+condition exists, return 200 with existing entry instead of creating duplicate.
- **Pillow dependency**: add to `requirements.txt` if not already present (needed for thumbnail generation).
- **django-storages**: add to `requirements.txt` for production S3 support (dev uses FileSystemStorage).
