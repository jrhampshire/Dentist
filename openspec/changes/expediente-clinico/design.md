# Design: Expediente Clínico Digital — Slice A (Frontend UI + Type Fixes)

## Technical Approach

Slice A delivers the missing frontend UI for clinical notes and consents while fixing critical type/enum mismatches. The backend API is already functional — this is purely a frontend change + type alignment. Strategy: fix types first (blocking), then build the patient detail page with tabbed UI consuming existing React Query hooks.

## Architecture Decisions

### Decision: API endpoint paths

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep `/clinical-notes/` | Will 404 against backend — backend uses `/notes/` | **Fix to `/notes/`** |
| Keep current paths | Silent API failures | **Add missing `signConsent` endpoint** |

### Decision: State management for tabs

| Option | Tradeoff | Decision |
|--------|----------|----------|
| useState + manual fetch | Breaks existing pattern | **TanStack Query** — all pages use it |
| Local state for dialogs | Only for open/closed | **useState for UI state** (dialog open, selected item) |

### Decision: Read-only signed state

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Disable all inputs | Confusing UX | **Show lock icon + gray background**, form fields disabled |
| Hide action buttons | User can't see what exists | **Show but disable** edit/delete buttons |

### Decision: Page organization

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Single file | >400 lines, hard to review | **Split into page + 3 tab components** |
| Shared patient info component | Reuse from PatientsPage | **Inline in first tab** — simple read-only display |

## Data Flow

```
PatientsPage ──(Link to /patients/:id)──→ PatientDetailPage
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                              InfoTab   ClinicalNotesTab  ConsentsTab
                                    │          │              │
                                    ▼          ▼              ▼
                              usePatient  useClinicalNotes  useConsents
                                    │          │              │
                                    ▼          ▼              ▼
                              patientsApi.get  patientsApi.listNotes  patientsApi.listConsents
```

Sign flows:
```
ClinicalNotesTab ──→ useSignClinicalNote ──→ patientsApi.signNote ──→ POST /patients/:id/notes/:pk/sign/
ConsentsTab      ──→ useSignConsent      ──→ patientsApi.signConsent ──→ POST /patients/:id/consents/:pk/sign/
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/types/index.ts` | Modify | Fix `note_type` union: `'evolution'\|'diagnosis'\|'treatment'\|'observation'\|'consent'`. Fix `consent_type` union: `'general'\|'treatment'\|'data_processing'\|'whatsapp'` |
| `frontend/src/api/patients.ts` | Modify | Fix `listNotes`/`createNote`/`signNote` paths: `/clinical-notes/` → `/notes/`. Add `signConsent` endpoint |
| `frontend/src/hooks/usePatients.ts` | Modify | Add `useSignConsent` hook |
| `frontend/src/pages/PatientDetailPage.tsx` | Create | Tabbed page: patient info, clinical notes, consents |
| `frontend/src/pages/PatientsPage.tsx` | Modify | Wire Eye button to navigate to `/patients/:id` |
| `frontend/src/App.tsx` | Modify | Add route `/patients/:id` → `PatientDetailPage` |

## Interfaces / Contracts

```typescript
// Fixed enums (matching backend TextChoices)
note_type: 'evolution' | 'diagnosis' | 'treatment' | 'observation' | 'consent'
consent_type: 'general' | 'treatment' | 'data_processing' | 'whatsapp'

// API additions (patients.ts)
signConsent: (patientId: string, consentId: string, signatureBlob?: string) =>
  Promise<PatientConsent>
```

## Component Tree

```
PatientDetailPage
├── PageHeader (patient name, back button)
├── Tabs (shadcn Tabs)
│   ├── Tab: "Información"
│   │   └── PatientInfoCard (read-only display of patient data)
│   ├── Tab: "Notas Clínicas"
│   │   ├── NotesList (Table + status badges: firmada/pendiente)
│   │   ├── CreateNoteDialog (form: note_type, title, content)
│   │   └── SignNoteButton (with confirmation)
│   └── Tab: "Consentimientos"
│       ├── ConsentsList (Table + status badges)
│       ├── CreateConsentDialog (form: consent_type, content)
│       └── SignConsentDialog (with signature placeholder)
└── Loading / Error states
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Types | Enum values match backend | TypeScript compile check — no runtime test needed |
| Hooks | `useSignConsent` mutation flow | Verify query invalidation on success |
| Page | Tab navigation renders correct content | Render with mocked React Query data |
| Page | Signed notes show read-only with lock icon | Assert disabled state + lock icon present |
| Page | Sign action calls correct API | Assert mutation called with correct patientId + noteId |

## Migration / Rollout

No migration required. The type fixes and API path corrections are backward-incompatible only at the type level — runtime behavior was broken before (wrong enums = 400 from backend), so fixing them unblocks the feature.

## Open Questions

- [ ] Should the sign action capture a signature blob for consents? Backend accepts optional base64. For MVP, sign without blob and add canvas-based signature capture in a follow-up.
- [ ] The `PatientDetailPage` AppShell header shows "Pacientes" as active nav — is that acceptable, or should we update AppShell to show a breadcrumb?
