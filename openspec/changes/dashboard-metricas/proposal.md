# SDD Change Proposal — Dashboard: Métricas y Reportes

**Change ID**: `dashboard-metricas`  
**Phase**: Proposal  
**Date**: 2026-05-21  
**Artifact Store**: Hybrid (Engram + openspec filesystem)

---

## 1. Intent

Replace broken client-side stat computation with **proper backend aggregation endpoints** + **Recharts visualizations** for the dashboard.

**Current Problem**: 
- Dashboard stats are computed client-side by filtering full API responses (`appointmentsData?.results?.filter`)
- This is inefficient (fetches all data, filters in browser)
- Revenue calculation is commented out (`// import { formatCurrency } from '@/lib/utils'`)
- No trend charts or historical metrics
- No backend aggregation for KPIs

**Why this matters**: 
- Client-side filtering doesn't scale (imagine 10K appointments loaded to compute "today's appointments")
- Revenue metrics require accurate backend logic (exclude drafts/cancelled, apply tenant isolation)
- Visual trends (7-day appointment trends, monthly revenue) require time-series aggregation only feasible in backend

---

## 2. Scope

### In Scope

| Component | Description |
|-----------|-------------|
| **Backend Metrics Endpoint** | New `GET /api/v1/dashboard/metrics/` with aggregated stats (appointments, revenue, patients, inventory) |
| **Date Range Support** | Query params: `?from=YYYY-MM-DD&to=YYYY-MM-DD` (default: last 7 days) |
| **Revenue Accuracy** | Exclude `status=draft` and `status=cancelled` invoices; only count `status=paid` |
| **Tenant Isolation** | All metrics filtered by `clinic_id` from authenticated user |
| **Recharts Integration** | Add `recharts` dependency; create trend charts (appointments by day, revenue by day) |
| **Dashboard Page Update** | Replace client-side filtering with backend metrics; add trend visualizations |
| **Type Definitions** | Add `DashboardMetrics` TypeScript interface matching backend response |

### Out of Scope (Post-MVP)

- Export reports (PDF/Excel)
- Custom date range picker UI (use preset ranges: 7d, 30d, 90d)
- Role-based metrics filtering (e.g., dentist sees only their patients)
- Real-time metrics (WebSocket updates)
- Comparative periods (e.g., "vs previous period")

---

## 3. Components

### Backend Changes

| File | Change | Reason |
|------|--------|--------|
| `backend/dashboard/` | **NEW**: Create Django app for dashboard logic | Separation of concerns; metrics don't belong to appointments/patients/invoicing |
| `backend/dashboard/views.py` | **NEW**: `DashboardMetricsViewSet` with `metrics` action | Aggregated endpoint |
| `backend/dashboard/serializers.py` | **NEW**: `DashboardMetricsSerializer` | Response schema |
| `backend/dashboard/urls.py` | **NEW**: Router registration | URL routing |
| `backend/config/urls.py` | Add `/api/v1/dashboard/` route | Integration |
| `backend/appointments/models.py` | No change (use existing `Appointment.Status` choices) | Source of truth |
| `backend/invoicing/models.py` | No change (use existing `Invoice.Status` choices) | Source of truth |

### Frontend Changes

| File | Change | Reason |
|------|--------|--------|
| `frontend/package.json` | Add `recharts` dependency (`^2.12.0`) | Chart library |
| `frontend/src/types/index.ts` | Add `DashboardMetrics` interface | Type safety |
| `frontend/src/api/dashboard.ts` | **NEW**: API client for metrics endpoint | Centralized API calls |
| `frontend/src/hooks/useDashboard.ts` | **NEW**: React Query hook (`useDashboardMetrics`) | Data fetching + caching |
| `frontend/src/pages/DashboardPage.tsx` | Replace client-side filtering with backend metrics; add trend charts | Core UI update |
| `frontend/src/components/dashboard/` | **NEW**: `AppointmentTrendChart.tsx`, `RevenueTrendChart.tsx` | Reusable chart components |

### Test Changes

| File | Change | Reason |
|------|--------|--------|
| `backend/dashboard/tests/test_views.py` | **NEW**: Metrics endpoint tests | Validate aggregation logic, tenant isolation, date filtering |
| `backend/dashboard/tests/test_permissions.py` | **NEW**: Auth + RLS tests | Ensure clinic_id filter enforced |
| `frontend/src/hooks/__tests__/useDashboard.test.ts` | **NEW**: Hook tests | Validate data transformation |

---

## 4. Approach

### Backend Implementation

**Step 1**: Create `dashboard` Django app
```bash
python manage.py startapp dashboard
```

**Step 2**: Implement metrics view with aggregation

```python
# backend/dashboard/views.py
from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

class DashboardMetricsViewSet(viewsets.ViewSet):
    """
    Aggregated dashboard metrics with tenant isolation.
    """
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        clinic = request.user.clinic
        
        # Date range
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        if not from_date or not to_date:
            # Default: last 7 days
            to_date = timezone.now().date()
            from_date = to_date - timedelta(days=6)
        
        # Appointments count
        appointments_count = Appointment.objects.filter(
            clinic=clinic,
            date__range=[from_date, to_date],
            status__in=['scheduled', 'confirmed', 'in_progress', 'completed']
        ).count()
        
        # Revenue (only paid invoices)
        revenue_data = Invoice.objects.filter(
            clinic=clinic,
            created_at__range=[from_date, to_date],
            status='paid'
        ).aggregate(total=Sum('total_amount'))
        revenue = revenue_data['total'] or 0
        
        # New patients
        new_patients = Patient.objects.filter(
            clinic=clinic,
            created_at__range=[from_date, to_date]
        ).count()
        
        # Low stock items
        low_stock = InventoryItem.objects.filter(
            clinic=clinic,
            stock_current__lte=models.F('stock_minimum'),
            is_active=True
        ).count()
        
        # Trend data (daily breakdown)
        appointments_trend = self._get_daily_appointments(clinic, from_date, to_date)
        revenue_trend = self._get_daily_revenue(clinic, from_date, to_date)
        
        return Response({
            'appointments': appointments_count,
            'revenue': float(revenue),
            'new_patients': new_patients,
            'low_stock_items': low_stock,
            'trends': {
                'appointments': appointments_trend,
                'revenue': revenue_trend
            }
        })
```

**Step 3**: Add URL routing
```python
# backend/dashboard/urls.py
from rest_framework.routers import DefaultRouter
from .views import DashboardMetricsViewSet

router = DefaultRouter()
router.register(r'', DashboardMetricsViewSet, basename='dashboard-metrics')

urlpatterns = router.urls
```

### Frontend Implementation

**Step 1**: Install Recharts
```bash
npm install recharts
```

**Step 2**: Create API client
```typescript
// frontend/src/api/dashboard.ts
import api from './client';

export interface DashboardMetrics {
  appointments: number;
  revenue: number;
  new_patients: number;
  low_stock_items: number;
  trends: {
    appointments: Array<{ date: string; count: number }>;
    revenue: Array<{ date: string; amount: number }>;
  };
}

export const dashboardApi = {
  getMetrics: (from?: string, to?: string) => 
    api.get<DashboardMetrics>('/dashboard/metrics/', { params: { from, to } }),
};
```

**Step 3**: Create React Query hook
```typescript
// frontend/src/hooks/useDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/dashboard';

export function useDashboardMetrics(from?: string, to?: string) {
  return useQuery({
    queryKey: ['dashboard-metrics', from, to],
    queryFn: () => dashboardApi.getMetrics(from, to).then(r => r.data),
  });
}
```

**Step 4**: Update DashboardPage with charts
```tsx
// frontend/src/pages/DashboardPage.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function DashboardPage() {
  const { data: metrics, isLoading } = useDashboardMetrics();
  
  if (isLoading) return <LoadingSpinner />;
  
  return (
    <div className="space-y-6">
      {/* Stats Grid - using backend metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Citas" value={metrics.appointments} icon={CalendarDays} />
        <StatCard title="Ingresos" value={formatCurrency(metrics.revenue)} icon={TrendingUp} />
        <StatCard title="Pacientes nuevos" value={metrics.new_patients} icon={Users} />
        <StatCard title="Alertas inventario" value={metrics.low_stock_items} icon={AlertTriangle} />
      </div>
      
      {/* Trend Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Citas por día</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={metrics.trends.appointments}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#4A90D9" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader><CardTitle>Ingresos por día</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={metrics.trends.revenue}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="amount" stroke="#10B981" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

---

## 5. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Revenue Accuracy** | 🔴 Critical | Backend logic MUST exclude `draft` and `cancelled` invoices; only count `paid` status. Add tests verifying this. |
| **Tenant Isolation** | 🔴 Critical | All queries MUST filter by `clinic=request.user.clinic`. RLS at DB level + application-level filter. |
| **Date Range Edge Cases** | 🟠 High | Handle timezone correctly (use `timezone.now().date()`). Default to last 7 days if params missing. |
| **Empty State Handling** | 🟡 Medium | Charts show empty state when no data; don't crash on null/empty arrays. |
| **Performance on Large Datasets** | 🟡 Medium | Add DB indexes on `clinic`, `date`, `status` fields. Monitor query performance. |
| **Recharts Bundle Size** | 🟡 Medium | ~50KB gzipped. Acceptable for dashboard page only (code-split if needed). |

---

## 6. Key Decisions

### 6.1 Single Endpoint vs Multiple

**Decision**: Single `/api/v1/dashboard/metrics/` endpoint returning all metrics.

**Rationale**:
- Dashboard needs all stats at once; multiple calls add latency
- Atomic snapshot (all metrics from same time range)
- Simpler frontend (one hook, one loading state)

**Tradeoff**: Less granular caching, but acceptable for dashboard use case.

---

### 6.2 Revenue Calculation Logic

**Decision**: Revenue = Sum of `Invoice.total_amount` where `status='paid'` only.

**Excluded**:
- `status='draft'` — not finalized
- `status='cancelled'` — voided
- `status='pending'` — not yet paid

**Rationale**: Cash-basis accounting (recognize revenue when received, not when invoiced). Matches typical small dental practice needs.

---

### 6.3 Chart Library Choice

**Decision**: Recharts (not Chart.js, Victory, or D3).

**Rationale**:
- React-native (declarative, component-based)
- Already popular in React ecosystem (good docs, community)
- Tree-shakeable (import only needed components)
- Responsive container built-in
- ~50KB gzipped (acceptable)

---

### 6.4 Date Range Defaults

**Decision**: Default to last 7 days if no params provided.

**Rationale**:
- Most relevant for daily operations
- Fast queries (small date range)
- User can extend if needed (future feature: date picker)

---

### 6.5 Trend Granularity

**Decision**: Daily breakdown (not hourly, not weekly).

**Rationale**:
- Hourly too granular for dashboard (noise)
- Weekly too coarse for 7-day range
- Daily strikes balance between signal and simplicity

---

## 7. Success Criteria

- ✅ Backend endpoint returns accurate metrics (verified against manual DB queries)
- ✅ Revenue excludes draft/cancelled invoices (test with fixtures)
- ✅ Tenant isolation enforced (user from Clinic A cannot see Clinic B metrics)
- ✅ Dashboard loads in <2 seconds (with 1K+ appointments in DB)
- ✅ Charts render correctly on mobile (responsive)
- ✅ Empty state handled gracefully (no data = "Sin datos en el rango seleccionado")
- ✅ PR size ~350 lines (backend + frontend combined)

---

## 8. Recommendation

**Proceed with single PR** (~350 lines) containing:
1. Backend: `dashboard` app with metrics endpoint
2. Frontend: Recharts integration + DashboardPage update

**Why single PR**:
- Tightly coupled (frontend useless without backend)
- Small enough for focused review
- End-to-end testable in one go

**Next Step**: If approved, move to **Design Phase** to create detailed technical design (DB indexes, exact serializer schema, component props).

---

## Appendix: Backend Response Schema

```json
{
  "appointments": 15,
  "revenue": 4500.00,
  "new_patients": 8,
  "low_stock_items": 3,
  "trends": {
    "appointments": [
      { "date": "2026-05-15", "count": 2 },
      { "date": "2026-05-16", "count": 3 },
      { "date": "2026-05-17", "count": 1 },
      { "date": "2026-05-18", "count": 4 },
      { "date": "2026-05-19", "count": 2 },
      { "date": "2026-05-20", "count": 3 },
      { "date": "2026-05-21", "count": 0 }
    ],
    "revenue": [
      { "date": "2026-05-15", "amount": 600.00 },
      { "date": "2026-05-16", "amount": 900.00 },
      { "date": "2026-05-17", "amount": 300.00 },
      { "date": "2026-05-18", "amount": 1200.00 },
      { "date": "2026-05-19", "amount": 600.00 },
      { "date": "2026-05-20", "amount": 900.00 },
      { "date": "2026-05-21", "amount": 0.00 }
    ]
  }
}
```

---

## Appendix: Frontend Type Definitions

```typescript
// frontend/src/types/index.ts

export interface DashboardMetrics {
  appointments: number;
  revenue: number;
  new_patients: number;
  low_stock_items: number;
  trends: {
    appointments: Array<{
      date: string;
      count: number;
    }>;
    revenue: Array<{
      date: string;
      amount: number;
    }>;
  };
}

export type DateRangePreset = '7d' | '30d' | '90d';
```

---

## Appendix: DB Indexes Required

```python
# backend/appointments/models.py
class Meta:
    indexes = [
        models.Index(fields=["clinic", "date"], name="idx_appt_clinic_date"),
        models.Index(fields=["clinic", "status", "date"], name="idx_appt_clinic_status_date"),
    ]

# backend/invoicing/models.py
class Meta:
    indexes = [
        models.Index(fields=["clinic", "created_at"], name="idx_inv_clinic_created"),
        models.Index(fields=["clinic", "status", "created_at"], name="idx_inv_clinic_status_created"),
    ]
```
