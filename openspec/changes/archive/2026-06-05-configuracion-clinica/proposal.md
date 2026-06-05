# Proposal: Configuración Clínica — Configuration Hub

## Intent

The current `/settings` page only manages appointment types. Clinic admins have no UI to view or edit their clinic profile, fiscal data (CFDI 4.0), integrations, or subscription status — despite all backend APIs being fully built. This forces admins to rely on support or raw API calls for basic configuration. We need a unified **Configuration Hub** that surfaces all clinic settings in one tabbed page.

## Scope

### In Scope
- Tab 1 **Información General**: Edit clinic name, RFC, phone, email, address (PATCH `/clinics/{id}/`)
- Tab 2 **Datos Fiscales / CFDI 4.0**: CRUD fiscal config + CSD upload + validate-csd action
- Tab 3 **Integraciones**: Google OAuth connect button (placeholder), WhatsApp config (placeholder)
- Tab 4 **Plan y Suscripción**: Read-only display of plan, stamps remaining, subscription dates
- Tab 5 **Tipos de Cita**: Preserve existing appointment types management as-is

### Out of Scope
- Backend API changes (all endpoints exist)
- Google OAuth backend implementation (placeholder only)
- WhatsApp Business API integration (placeholder only)
- Role-based tab visibility (future — all tabs visible to admin for now)
- Multi-language / i18n

## Capabilities

### New Capabilities
- `clinic-config-ui`: Frontend configuration hub with tabbed layout for clinic profile, fiscal data, integrations, and subscription display
- `clinic-integrations`: Integration settings UI — Google OAuth and WhatsApp config placeholders with connect/disconnect flows

### Modified Capabilities
- `fiscal-config`: Needs frontend UI (currently backend-only API). Add form for razón social, régimen fiscal, fiscal address, CSD certificate upload, password input, and validate-csd button

## Approach

**Frontend-only transformation.** Refactor `SettingsPage.tsx` from a single-card appointment types page into a tabbed layout using shadcn/ui `Tabs` component.

1. **Decompose** `SettingsPage` → tab container with 5 tab panels
2. **Extract** existing appointment types UI into `Settings/AppointmentTypesTab.tsx`
3. **Create** new tab components: `GeneralInfoTab`, `FiscalConfigTab`, `IntegrationsTab`, `PlanSubscriptionTab`
4. **Add** API layer: `frontend/src/api/clinics.ts` (clinic CRUD), `frontend/src/api/fiscalConfig.ts` (fiscal config + validate-csd)
5. **Add** hooks: `useClinic`, `useFiscalConfig` via TanStack Query
6. **Add** types: `Clinic` interface to `types/index.ts`

Each tab is an independent component with its own data fetching — no shared state between tabs.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/SettingsPage.tsx` | Modified | Refactor to tabbed container |
| `frontend/src/pages/Settings/GeneralInfoTab.tsx` | New | Clinic profile edit form |
| `frontend/src/pages/Settings/FiscalConfigTab.tsx` | New | Fiscal data form + CSD upload + validate |
| `frontend/src/pages/Settings/IntegrationsTab.tsx` | New | Google/WhatsApp placeholder cards |
| `frontend/src/pages/Settings/PlanSubscriptionTab.tsx` | New | Read-only plan display |
| `frontend/src/pages/Settings/AppointmentTypesTab.tsx` | New | Extracted from current SettingsPage |
| `frontend/src/api/clinics.ts` | New | Clinic GET/PATCH API calls |
| `frontend/src/api/fiscalConfig.ts` | New | FiscalConfig CRUD + validate-csd |
| `frontend/src/hooks/useClinic.ts` | New | TanStack Query hook for clinic data |
| `frontend/src/hooks/useFiscalConfig.ts` | New | TanStack Query hook for fiscal config |
| `frontend/src/types/index.ts` | Modified | Add `Clinic` interface |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CSD password sent in plaintext to frontend | High | Never return password from API; use write-only field. Show only `••••••••` mask |
| CSD file upload size/timeout | Medium | Set upload limit (5MB), show progress indicator |
| Stale clinic data after PATCH | Low | Invalidate TanStack Query cache on mutation success |

## Rollback Plan

1. Revert `SettingsPage.tsx` to single-card appointment types layout
2. Remove new tab components and API/hook files
3. No backend changes to revert

## Dependencies

- None — all backend APIs already exist and are functional

## Success Criteria

- [ ] `/settings` renders 5 tabs with correct data from backend APIs
- [ ] Admin can edit and save clinic name, phone, email, address
- [ ] Admin can create/edit fiscal config and trigger CSD validation
- [ ] Plan tab shows stamps remaining, subscription dates, and plan name
- [ ] Appointment types tab works identically to current behavior
- [ ] No console errors, all TanStack Query states handled (loading/error/success)
