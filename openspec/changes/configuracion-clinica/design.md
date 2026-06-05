# Design: Configuración Clínica — Configuration Hub

## Technical Approach

Frontend-only refactor: transform `SettingsPage.tsx` from a single-card appointment types page into a tabbed container with 5 independent tab panels. Each tab is a standalone component with its own data-fetching hooks, using URL hash for tab state (`/settings#general`). No shared state between tabs. Existing fiscal config API methods in `invoicesApi` are extracted to a dedicated `fiscalConfigApi` module.

## Architecture Decisions

### Decision: Tab navigation via URL hash vs local state

| Option | Tradeoff | Decision |
|--------|----------|----------|
| URL hash (`#general`, `#fiscal`) | Enables deep linking, browser back/forward; slight complexity in sync | ✅ |
| `useState` for active tab | Simpler but breaks deep linking and browser navigation | ❌ |

### Decision: Fiscal config — extract vs keep in `invoicesApi`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Extract to `api/fiscalConfig.ts` | Clean separation; unused methods in invoices.ts are dead code | ✅ |
| Keep in `invoicesApi` | Creates cross-domain coupling; fiscal config ≠ invoices | ❌ |

Remove unused `getFiscalConfig`, `updateFiscalConfig`, `validateCsd` from `invoicesApi`. Update `FiscalConfig` type in `types/index.ts` to match backend response shape (has `csd_cert_path` and `csd_key_path`, not `csd_cert_uploaded`).

### Decision: Form library for clinic/fiscal forms

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Native HTML + `useState` | Matches existing `AppointmentTypeDialog` pattern; no new dependency | ✅ |
| `react-hook-form` | Inconsistent with codebase; adds bundle weight | ❌ |

### Decision: CSD upload approach

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Text inputs for cert/key paths + note "file upload coming soon" | Backend stores paths; no upload endpoint exists | ✅ |
| File input + base64 | Not supported by current backend; would require backend changes | ❌ |

### Decision: Clinic ID source

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `useAuth().clinicId` from `user.clinic` | Already available in AppShell pattern; no extra context needed | ✅ |
| Pass as prop from router | Requires route loader changes; not needed | ❌ |

## Data Flow

```
SettingsPage (tab container)
  │  reads/writes window.location.hash
  │
  ├─ GeneralInfoTab
  │    useClinic() → GET /api/v1/clinics/{clinicId}/
  │    useUpdateClinic() → PATCH /api/v1/clinics/{clinicId}/
  │
  ├─ FiscalConfigTab
  │    useFiscalConfig() → GET /api/v1/fiscal-config/
  │    useUpdateFiscalConfig() → PATCH /api/v1/fiscal-config/
  │    useValidateCsd() → POST /api/v1/fiscal-config/{id}/validate-csd/
  │
  ├─ IntegrationsTab (placeholder cards — no queries)
  │
  ├─ PlanSubscriptionTab
  │    useClinic() → GET /api/v1/clinics/{clinicId}/  (read-only display)
  │
  └─ AppointmentTypesTab (extracted, unchanged logic)
       useAppointmentTypes() → existing hook
```

## Component Tree

```
SettingsPage
  ├─ Tabs (shadcn/ui) — defaultValue from URL hash
  │   ├─ TabsList
  │   │   ├─ TabsTrigger value="general"    → "Información General"
  │   │   ├─ TabsTrigger value="fiscal"     → "Datos Fiscales"
  │   │   ├─ TabsTrigger value="integrations" → "Integraciones"
  │   │   ├─ TabsTrigger value="plan"       → "Plan y Suscripción"
  │   │   └─ TabsTrigger value="types"      → "Tipos de Cita"
  │   ├─ TabsContent value="general"    → GeneralInfoTab
  │   ├─ TabsContent value="fiscal"     → FiscalConfigTab
  │   ├─ TabsContent value="integrations" → IntegrationsTab
  │   ├─ TabsContent value="plan"       → PlanSubscriptionTab
  │   └─ TabsContent value="types"      → AppointmentTypesTab
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/SettingsPage.tsx` | Modify | Rewrite as tabbed container with URL hash sync |
| `frontend/src/pages/Settings/AppointmentTypesTab.tsx` | Create | Extract existing appointment types UI (Table + dialog) |
| `frontend/src/pages/Settings/GeneralInfoTab.tsx` | Create | Clinic profile form: name, phone, email, address |
| `frontend/src/pages/Settings/FiscalConfigTab.tsx` | Create | Fiscal data form: RFC, razón social, CSD paths, validate |
| `frontend/src/pages/Settings/IntegrationsTab.tsx` | Create | Placeholder cards for Google OAuth, WhatsApp |
| `frontend/src/pages/Settings/PlanSubscriptionTab.tsx` | Create | Read-only display: plan, stamps, subscription dates |
| `frontend/src/api/clinics.ts` | Create | `clinicsApi.get(id)`, `clinicsApi.update(id, data)` |
| `frontend/src/api/fiscalConfig.ts` | Create | `fiscalConfigApi.get()`, `update()`, `validateCsd(id, password)` |
| `frontend/src/api/invoices.ts` | Modify | Remove `getFiscalConfig`, `updateFiscalConfig`, `validateCsd` and their import |
| `frontend/src/hooks/useClinic.ts` | Create | `useClinic()`, `useUpdateClinic()` hooks |
| `frontend/src/hooks/useFiscalConfig.ts` | Create | `useFiscalConfig()`, `useUpdateFiscalConfig()`, `useValidateCsd()` |
| `frontend/src/hooks/index.ts` | Modify | Add `useClinic` and `useFiscalConfig` re-exports |
| `frontend/src/types/index.ts` | Modify | Add `Clinic` interface; update `FiscalConfig` to match backend |

## Interfaces / Contracts

```typescript
// New: Clinic interface (backend ClinicSerializer)
export interface Clinic {
  id: string
  name: string
  rfc: string
  email: string
  phone: string
  address: Record<string, unknown>
  plan: 'free' | 'basic' | 'pro'
  status: 'pending' | 'active' | 'suspended' | 'cancelled'
  email_verified: boolean
  onboarding_completed: boolean
  subscription_start: string | null
  subscription_end: string | null
  stamps_remaining: number
  settings: Record<string, unknown>
  onboarding_progress: Record<string, unknown>
  created_at: string
  updated_at: string
}

// Updated: FiscalConfig — match backend FiscalConfigSerializer
export interface FiscalConfig {
  id: string
  rfc: string
  razon_social: string
  regimen_fiscal: string
  fiscal_address: Record<string, unknown>
  csd_cert_path: string
  csd_key_path: string
  email: string
  is_validated: boolean
}

// Tab component props (all receive no props — internal data fetching)
interface GeneralInfoTabProps {}  // trivially empty / no props
interface FiscalConfigTabProps {}
interface IntegrationsTabProps {}
interface PlanSubscriptionTabProps {}
interface AppointmentTypesTabProps {}
```

## State Management

| State | Where | Mechanism |
|-------|-------|-----------|
| Active tab | URL hash | `useEffect` + `window.location.hash` |
| Clinic data | TanStack Query | `queryKey: ['clinic', clinicId]` |
| Fiscal config | TanStack Query | `queryKey: ['fiscal-config']` |
| Form fields | Per-tab local state | `useState` per field |
| CSD validation | TanStack Mutation | `mutationFn` calls validate endpoint |
| Appointment types | TanStack Query | Existing `useAppointmentTypes()` — unchanged |

## Error Handling

| State | GeneralInfoTab | FiscalConfigTab | PlanTab | IntegrationsTab |
|-------|---------------|-----------------|---------|-----------------|
| **Loading** | Skeleton (Card + 3 Input placeholders) | Skeleton (Card + 5 Input placeholders) | Skeleton (2 Cards) | Static cards — no loading |
| **Error** | Alert: "Error al cargar datos de la clínica" + retry | Alert: "Error al cargar configuración fiscal" + retry | Alert: "Error al cargar datos del plan" + retry | N/A |
| **Empty** | Pre-filled empty form | Empty form + "No hay configuración fiscal" | N/A (always has plan) | Placeholder text |
| **Mutation error** | Toast/Sonner with API error message | Toast/Sonner with API error message | N/A | N/A |

## Edge Cases

| Case | Behavior |
|------|----------|
| Clinic has no fiscal config (400 from GET) | Show empty form + "No hay configuración fiscal registrada. Crea una nueva." |
| Plan is `free` | Show "Plan Gratuito" badge + upgrade CTA; stamps_remaining displayed |
| Clinic status is `suspended` | Show warning banner on all tabs + disable form submissions |
| CSD validation fails | Show error message from API response in FiscalConfigTab |
| Invalid hash in URL (e.g. `/settings#nonexistent`) | Fall back to `#general` as default tab |
| User navigates via browser back/forward | `popstate` event + `useEffect` sync keeps Tabs in sync |
| User is not admin | All tabs visible but read-only fields (future: role-based gating) |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Tab URL hash sync (`popstate`, initial load) | Mock `window.location` + render SettingsPage |
| Unit | `GeneralInfoTab` form submit calls correct mutation | Render + fill inputs + submit + assert mutation called |
| Unit | `FiscalConfigTab` validate-CSD button | Mock mutation success/failure + verify toast |
| Unit | Empty fiscal config state | Mock `useFiscalConfig` returning no data |
| Integration | Full settings page renders all 5 tabs | Mount SettingsPage + verify tab triggers exist |
| E2E | Navigate to `/settings#fiscal` → FiscalConfigTab visible | Playwright test verifying URL hash routing |

## Migration / Rollout

No migration required. All changes are frontend-only — no data schema changes, no backend changes. The existing `/settings` route path stays the same.

## Open Questions

- None. All backend APIs confirmed working, existing codebase patterns documented in this design.
