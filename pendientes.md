# Pendientes — ClínicaSaaS Dental MX

> Auditoría completa — Julio 2026. Proyecto al ~78% de completitud.

---

## 🔴 Críticos (1)

| # | Estado | Qué | Dónde |
|---|--------|-----|-------|
| C1 | ✅ | **TypeScript `tsc -b` roto** — build de producción omitía type-checking | `frontend/Dockerfile`, `DashboardPage.tsx`, `useWhatsAppStatus.ts` |
| C2 | ⬜ | **Google Calendar y Gmail nunca implementados** — botones disabled con "no implementada". Zero backend. | `IntegrationsTab.tsx` |

---

## 🟠 Alta prioridad (9)

| # | Estado | Qué | Dónde |
|---|--------|-----|-------|
| A1 | ⬜ | **Sin sistema de pagos** — PlanSubscriptionTab redirige a `mailto:soporte@`. Planes free/basic/pro solo informativos. Sin Stripe/PayPal. | `PlanSubscriptionTab.tsx` |
| A2 | ⬜ | **WhatsApp button siempre disabled** — integración Twilio SÍ funciona en backend, pero frontend hardcodea `disabled={true}`. | `IntegrationsTab.tsx:124` |
| A3 | ⬜ | **11 páginas frontend sin tests** — Register, Dashboard, Appointments, Patients, Inventory, Invoices, Settings tabs, etc. | `frontend/src/pages/` |
| A4 | ⬜ | **0 tests en hooks/store/api/components** — 18 hooks, Zustand store, 12 API modules, ~20 componentes. | `frontend/src/{hooks,store,api,components}/` |
| A5 | ⬜ | **6 apps backend sin tests locales** — accounts, appointments, clinics, inventory, invoicing, notifications. Solo tests indirectos. | `backend/{accounts,appointments,...}/` |
| A6 | ⬜ | **Frontend no corre en CI** — solo `pytest` en backend. `vitest` sin job. | `.github/workflows/ci.yml` |
| A7 | ⬜ | **Sin linting en CI** — ruff y eslint existen pero no en el pipeline. | `.github/workflows/ci.yml` |
| A8 | ⬜ | **`alert()` como error handling** — `InvoicesPage.tsx` usa `alert('Error al descargar...')` en vez de toast. | `frontend/src/pages/InvoicesPage.tsx:88` |
| A9 | ⬜ | **Coverage threshold inconsistente** — `pytest.ini` (75%) vs spec CI (80%). | `pytest.ini` + spec `ci-workflow` |

---

## 🟡 Media prioridad (9)

| # | Estado | Qué | Dónde |
|---|--------|-----|-------|
| M1 | ⬜ | **`print()` statements en prod** — `finkok_service.py:104` y `setup_rls.py:295`. | `backend/invoicing/services/`, `backend/core/management/` |
| M2 | ⬜ | **Sin specs canónicos** para audit-trail, dashboard, user-management (tienen código pero no spec). | `openspec/specs/` |
| M3 | ⬜ | **Backend tests parciales** — apps con tests pero faltan capas (serializers, modelos). | `backend/dashboard/tests/`, `backend/dental_records/tests/` |
| M4 | ⬜ | **Stamps CFDI no se pueden comprar desde UI** — solo alerta visual, sin botón de compra. | `PlanSubscriptionTab.tsx:125-163` |
| M5 | ⬜ | **Sin página "Mi Perfil"** — `MeView` (GET/PATCH) existe en backend pero sin UI. | `backend/accounts/views.py` |
| M6 | ⬜ | **Sin tests E2E de frontend** — 0 tests Cypress/Playwright. | `frontend/` |
| M7 | ⬜ | **Apple Sign In** documentado pero no testeable sin Developer Program ($99/año). | `LoginPage.tsx`, `backend/accounts/` |
| M8 | ⬜ | **Sin refresh token rotation** — tokens se reutilizan hasta expirar. | `authStore.ts`, `backend/accounts/` |
| M9 | ⬜ | **Sin healthcheck en contenedores de frontend** — `frontend-prod` y `frontend-dev`. | `docker-compose.yml` |

---

## 🟢 Baja prioridad (8)

| # | Estado | Qué | Dónde |
|---|--------|-----|-------|
| B1 | ⬜ | **Tests de Celery tasks incompletos** — 852 líneas de tasks, cobertura baja. | `backend/celery_app/tasks.py` |
| B2 | ⬜ | **Sin Storybook** para catálogo de componentes (~18 shadcn/ui). | `frontend/src/components/ui/` |
| B3 | ⬜ | **Sentry** — variable definida pero sin verificar inicialización real. | `docker-compose.yml`, frontend/backend |
| B4 | ⬜ | **Sin pre-commit hooks** (ruff, eslint, prettier). | Raíz del proyecto |
| B5 | ⬜ | **Tipos TypeScript dispersos** — solo 2 archivos en `types/`. | `frontend/src/types/` |
| B6 | ⬜ | **Sin tests para `lib/utils.ts`** (formatCurrency, formatDate). | `frontend/src/lib/utils.ts` |
| B7 | ⬜ | **Sin tests de middleware** — tenant isolation, request ID, audit. | `backend/core/middleware/` |
| B8 | ⬜ | **Sin ErrorBoundary global** en frontend. | `frontend/src/` |

---

## 📊 Completitud por dominio

| Dominio | Backend | Frontend | Tests BE | Tests FE | Spec | Integración |
|---------|:-------:|:--------:|:--------:|:--------:|:----:|:-----------:|
| Auth | ✅ | ✅ | Parcial | 1 page | ✅ | Google ✅, Apple ⚠️ |
| Pacientes | ✅ | ✅ | ✅ | 4 tests | ✅ | — |
| Citas | ✅ | ✅ | Parcial | ❌ | ✅ | Google Calendar ❌ |
| Dashboard | ✅ | ✅ | 1 file | ❌ | ❌ | — |
| Fichas dentales | ✅ | Parcial | 2 files | ❌ | ✅ | — |
| Inventario | ✅ | ✅ | ❌ local | ❌ | ✅ | Kits auto-consume ✅ |
| Facturación CFDI | ✅ | ✅ | Parcial | ❌ | ✅ | Finkok ✅, PDF ✅ |
| WhatsApp | ✅ | ⚠️ | Parcial | ❌ | ✅ | Twilio ✅ |
| Clínicas/Onboarding | ✅ | ✅ | ❌ local | Parcial | ✅ | — |
| Plan/Suscripción | ❌ | ⚠️ | ❌ | ❌ | ❌ | Stripe ❌ |
| Google Calendar | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Gmail | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auditoría | ✅ | ✅ | ❌ local | 1 test | ❌ | — |

---

## 📈 Métricas

| Métrica | Valor |
|---------|-------|
| Backend test files | 30 |
| Frontend test files | 6 |
| Coverage threshold CI | 75% |
| OpenSpec specs | 17 (faltan 3) |
| Backend apps con tests locales | 3/11 |
| Frontend pages con tests | 6/18 |
| Integraciones completas | 1/5 (Finkok) |
| Componentes UI sin test | ~20+ |
| Hooks sin test | 18 |
