## Exploration: Dashboard Métricas y Reportes

### Current State

**DashboardPage.tsx** already has a solid foundation but with critical flaws:

- **Stats cards**: Citas hoy, Pacientes totales, Alertas inventario, Citas pendientes — all computed by fetching page 1 of each collection and filtering client-side. This breaks as soon as any collection exceeds one page.
- **Lists**: Today's appointments (top 5) and inventory alerts (top 5) rendered as cards.
- **Quick actions**: Links to patients, appointments, invoices, inventory.
- **No charts**: Zero data visualization. No trend analysis.
- **No dedicated analytics endpoints**: Every stat is derived from full list endpoints with `page=1`.

**Backend readiness**:
- `Appointment` has `date`, `status` (6 states), `created_at`, and indexes on `clinic+date`, `clinic+status`, `clinic+date+status`.
- `Invoice` has `total`, `status` (draft → paid/cancelled), `created_at`, and indexes on `clinic+status`, `clinic+created_at`.
- `Patient` uses soft-delete (`is_deleted`) with `PatientManager` excluding deleted records; indexed on `clinic+created_at`.
- `stock_service.py` already provides `get_low_stock_items()`, `get_expiring_items()`, etc.

**Frontend stack**:
- React 18 + Vite + TypeScript + Tailwind.
- `@tanstack/react-query` for data fetching.
- `date-fns` for date manipulation.
- **No charting library installed**.

---

### Affected Areas

| File / Module | Why it's affected |
|---|---|
| `frontend/src/pages/DashboardPage.tsx` | Needs to consume new metrics endpoint and render charts |
| `backend/` (new or existing views) | Needs a cross-domain analytics endpoint aggregating appointments, invoices, patients |
| `frontend/src/api/` | Needs new `dashboardApi` module |
| `frontend/src/hooks/` | Needs new `useDashboardMetrics` hook |
| `frontend/package.json` | Add `recharts` dependency |

---

### Approaches

#### 1. Backend Aggregation Endpoint + Recharts (Recommended)
Create a single `GET /api/v1/dashboard/metrics/` that returns pre-aggregated KPIs:
- `appointments_today`, `appointments_this_week`, `appointments_this_month` (grouped by status)
- `upcoming_appointments` (next 7 days)
- `revenue_this_month`, `revenue_trend_last_6_months`
- `patients_total`, `patients_new_this_month`
- `completion_rate` (completed / total closed this month)
- `low_stock_count`, `expiring_soon_count`

Frontend: Add `recharts` and render:
- A **revenue trend line chart** (last 6 months).
- An **appointment status bar chart** or pie chart for the current period.
- Keep existing stat cards but feed them from the endpoint.

- **Pros**: Accurate regardless of data size; one round-trip; charts add real value for clinic owners; Recharts is declarative, SVG-based, and Tailwind-friendly.
- **Cons**: Adds one dependency; requires designing a cross-domain endpoint.
- **Effort**: Medium

#### 2. Backend Aggregation, No Charts (MVP-First)
Same backend endpoint, but frontend only renders metric cards and lists (no charts).

- **Pros**: Fastest to ship; no new dependency; still fixes the pagination bug.
- **Cons**: Missing trend visibility; users can't spot revenue dips or appointment backlog patterns.
- **Effort**: Low

#### 3. Fix Client-Side Filters Only
Increase `page_size` or fetch all pages client-side, then compute stats locally.

- **Pros**: No backend changes.
- **Cons**: Inherently unscalable; network and memory waste; still no charts.
- **Effort**: Low (but architecturally wrong)

---

### Recommendation

**Go with Approach 1** — Backend Aggregation + Recharts.

Why:
1. The current client-side filtering is a **bug waiting to happen**; it must be replaced.
2. Once you have a proper metrics endpoint, adding Recharts is trivial (~2 components).
3. Dental clinic owners *need* to see revenue trends and appointment completion rates — these are core business decisions.
4. The existing indexes (`idx_appts_clinic_date`, `idx_invoices_created`, `idx_patients_created`) make these aggregations fast without extra DB work.

**Recharts choice over Chart.js**: We're already all-in on React declarative patterns (shadcn/ui, Tailwind). Recharts uses SVG and composes like React components. Chart.js canvas is harder to theme and less accessible.

---

### Risks

- **Revenue accuracy**: Must ONLY sum invoices with `status IN ('stamped', 'sent', 'paid')`. Drafts and cancelled invoices must be excluded.
- **Tenant isolation**: New endpoint must enforce `clinic_id` filtering (RLS already does this at the DB level, but the view must also filter explicitly).
- **Performance on large datasets**: With existing indexes, monthly aggregations should be sub-100ms for clinics with <100k records. If data grows beyond that, consider materialized views or caching (out of scope for now).
- **Patient soft-delete**: Use `Patient.objects` (default manager) not `Patient.all_objects` when counting active patients.
- **Date boundaries**: Use timezone-aware date ranges (`django.utils.timezone`) to avoid off-by-one errors at month boundaries.

---

### Ready for Proposal

**Yes.**

What the orchestrator should tell the user:
> "Exploration confirms the dashboard has a good skeleton but is currently computing stats from the first page of list endpoints — that breaks at scale. The models already have the right fields and indexes for aggregation. I recommend a single backend metrics endpoint plus `recharts` for revenue trends and appointment status charts. This replaces inaccurate client-side math with proper DB aggregations and adds real visual value for clinic owners."
