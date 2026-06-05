# Tasks: Configuración Clínica — Configuration Hub

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 700–900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 4 chained PRs |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Types + API modules + hooks | PR 1 | Base: feature/configuracion-clinica. Foundation only — no UI. |
| 2 | SettingsPage refactor + AppointmentTypesTab extraction | PR 2 | Base: PR 1 branch. Preserves existing behavior in new tab component. |
| 3 | GeneralInfoTab + FiscalConfigTab | PR 3 | Base: PR 2 branch. Heaviest UI — two forms with mutations. |
| 4 | IntegrationsTab + PlanSubscriptionTab + invoicesApi cleanup | PR 4 | Base: PR 3 branch. Lightweight placeholders + dead code removal. |

## Phase 1: Foundation — Types, API, Hooks

- [ ] 1.1 Add `Clinic` interface to `frontend/src/types/index.ts` (all fields from design)
- [ ] 1.2 Update `FiscalConfig` interface: add `id`, `csd_cert_path`, `csd_key_path`; remove `csd_cert_uploaded`, `clinic`
- [ ] 1.3 Create `frontend/src/api/clinics.ts` — `clinicsApi.get(id)`, `clinicsApi.update(id, data)`
- [ ] 1.4 Create `frontend/src/api/fiscalConfig.ts` — `fiscalConfigApi.get()`, `.create()`, `.update()`, `.validateCsd(id, password)`
- [ ] 1.5 Create `frontend/src/hooks/useClinic.ts` — `useClinic()`, `useUpdateClinic()` using tanstack query
- [ ] 1.6 Create `frontend/src/hooks/useFiscalConfig.ts` — `useFiscalConfig()`, `useUpdateFiscalConfig()`, `useCreateFiscalConfig()`, `useValidateCsd()`
- [ ] 1.7 Add re-exports to `frontend/src/hooks/index.ts`

## Phase 2: Settings Container + AppointmentTypesTab

- [ ] 2.1 Create `frontend/src/pages/Settings/AppointmentTypesTab.tsx` — extract existing table+dialog logic from SettingsPage
- [ ] 2.2 Rewrite `frontend/src/pages/SettingsPage.tsx` — shadcn Tabs with URL hash sync (`useEffect` + `popstate`)

## Phase 3: GeneralInfoTab + FiscalConfigTab

- [ ] 3.1 Create `frontend/src/pages/Settings/GeneralInfoTab.tsx` — form: name (req), phone (req), address; rfc/email disabled; PATCH on save; toast + invalidate
- [ ] 3.2 Create `frontend/src/pages/Settings/FiscalConfigTab.tsx` — create-or-edit form: razon_social, regimen_fiscal select (SAT codes), fiscal_address (9 fields), CSD paths, password; validated badge
- [ ] 3.3 Add CSD validation button: POST with spinner, badge updates reactively on success/error
- [ ] 3.4 Remove `getFiscalConfig`, `updateFiscalConfig`, `validateCsd` from `frontend/src/api/invoices.ts`

## Phase 4: IntegrationsTab + PlanSubscriptionTab + Wiring

- [ ] 4.1 Create `frontend/src/pages/Settings/IntegrationsTab.tsx` — 3 cards (Google, Gmail, WhatsApp) with status badges, placeholder "Próximamente" toast
- [ ] 4.2 Create `frontend/src/pages/Settings/PlanSubscriptionTab.tsx` — read-only plan, stamps (color thresholds), dates in Spanish locale, status badge, free plan CTA
- [ ] 4.3 Verify all tabs render in SettingsPage and deep links work
