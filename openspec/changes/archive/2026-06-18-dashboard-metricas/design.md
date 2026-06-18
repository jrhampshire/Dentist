# Design: Dashboard — Métricas y Reportes

## Technical Approach

Nuevo app Django `dashboard` con un ViewSet que expone `GET /api/v1/dashboard/metrics/` con agregaciones reales (appointments, revenue, patients, inventory). En el frontend, se agrega Recharts y un hook `useDashboardMetrics` que reemplaza el filtrado client-side. La respuesta es un único snapshot atómico con todas las métricas + trends diarios.

## Architecture Decisions

### Decision: Single ViewSet con action vs APIView independiente

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `DashboardMetricsViewSet` con `@action(detail=False, methods=['get'])` | Sigue patrón existente del código base (ej: `available_slots` en appointments); registro vía router consistente | ✅ |
| `APIView` standalone | Más simple pero rompe consistencia con el resto del proyecto donde todos los endpoints usan ViewSets + routers | ❌ |

### Decision: Response Schema — compacto vs rico

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Schema rico del task (appointments_today, appointments_this_week, revenue_trend, low_stock_count, upcoming_appointments, etc.) | Único request = dashboard completo sin llamadas adicionales; snapshot atómico | ✅ |
| Schema compacto del proposal | Menos data por request pero obliga al frontend a hacer llamadas adicionales para upcoming_appointments y trends detallados | ❌ |

### Decision: Acceso a clinic — `request.user.clinic` vs middleware

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `request.user.clinic` | Campo directo FK; ya existe en User model; superusers tienen `clinic=None` | ✅ |
| `request.clinic_id` (middleware) | Lo usan algunas views pero no está garantizado en todos los endpoints | ❌ |

### Decision: Trends con valores 0 para días sin datos

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Generar serie completa con 0s | El gráfico siempre muestra el rango completo sin huecos; consistente visualmente | ✅ |
| Solo días con datos | El gráfico se ve con saltos; confunde al usuario | ❌ |

### Decision: upcoming_appointments — próximos 7 días

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Query separada dentro del mismo endpoint | Evita request extra; límite 10 resultados; carga mínima | ✅ |
| Hook separado en frontend | Más requests, más estados de loading | ❌ |

## Data Flow

    Browser ──GET /api/v1/dashboard/metrics/──→ DashboardMetricsViewSet
                                                    │
                                                    ├── Appointment.objects.filter(clinic=user.clinic, ...)
                                                    ├── Invoice.objects.filter(clinic=user.clinic, status='paid', ...)
                                                    ├── Patient.objects.filter(clinic=user.clinic, ...)
                                                    ├── InventoryItem.objects.filter(clinic=user.clinic, ...)
                                                    │
                                                    └── Response(DashboardMetricsSerializer)
                                                          │
    DashboardPage.tsx ←── useDashboardMetrics() ←──────────┘
         │
         ├── StatCards (appointments_today, revenue_this_month, patients_total, low_stock)
         ├── RevenueTrendChart (LineChart, last 30d)
         ├── AppointmentTrendChart (BarChart, last 30d)
         └── UpcomingAppointments (list, next 7d)

## File Changes

| File | Acción | Descripción |
|------|--------|-------------|
| `backend/dashboard/apps.py` | Create | Django app config (`DashboardConfig`) |
| `backend/dashboard/models.py` | Create | Placeholder (this app has no models — queries external apps) |
| `backend/dashboard/views.py` | Create | `DashboardMetricsViewSet` with `metrics` action |
| `backend/dashboard/serializers.py` | Create | `DashboardMetricsSerializer` — read-only output serializer |
| `backend/dashboard/urls.py` | Create | Router registration for dashboard endpoint |
| `backend/dashboard/tests/test_views.py` | Create | Tests for metrics aggregation, tenant isolation, date filtering |
| `backend/config/urls.py` | Modify | Add `path("api/v1/dashboard/", include("dashboard.urls"))` |
| `frontend/package.json` | Modify | Add `"recharts": "^2.12.0"` to dependencies |
| `frontend/src/types/index.ts` | Modify | Add `DashboardMetrics`, `MetricsTrend`, `UpcomingAppointment` interfaces |
| `frontend/src/api/dashboard.ts` | Create | `dashboardApi.getMetrics()` API client |
| `frontend/src/hooks/useDashboardMetrics.ts` | Create | React Query hook `useDashboardMetrics()` |
| `frontend/src/pages/DashboardPage.tsx` | Modify | Replace client-side stats with backend metrics; add charts |
| `frontend/src/components/dashboard/MetricCard.tsx` | Create | Reusable stat card component |
| `frontend/src/components/dashboard/AppointmentTrendChart.tsx` | Create | BarChart for daily appointments |
| `frontend/src/components/dashboard/RevenueTrendChart.tsx` | Create | LineChart for daily revenue |

## Interfaces / Contracts

### Backend Response Schema

```json
{
  "appointments_today": 5,
  "appointments_this_week": {
    "total": 28,
    "by_status": {"scheduled": 10, "confirmed": 8, "completed": 10}
  },
  "appointments_this_month": {"total": 120, "completion_rate": 0.75},
  "revenue_this_month": 150000.00,
  "revenue_trend": [
    {"date": "2026-04-21", "total": 5000.00},
    {"date": "2026-04-22", "total": 3200.00}
  ],
  "appointments_trend": [
    {"date": "2026-04-21", "count": 8},
    {"date": "2026-04-22", "count": 5}
  ],
  "patients_total": 340,
  "patients_new_this_month": 15,
  "low_stock_count": 3,
  "expiring_soon_count": 5,
  "upcoming_appointments": [
    {
      "id": "uuid",
      "patient_name": "Juan Pérez",
      "date": "2026-05-21",
      "time": "10:00",
      "type_name": "Consulta General",
      "status": "confirmed"
    }
  ]
}
```

### Frontend Types

```typescript
export interface DashboardMetrics {
  appointments_today: number
  appointments_this_week: {
    total: number
    by_status: Record<string, number>
  }
  appointments_this_month: {
    total: number
    completion_rate: number
  }
  revenue_this_month: number
  revenue_trend: Array<{ date: string; total: number }>
  appointments_trend: Array<{ date: string; count: number }>
  patients_total: number
  patients_new_this_month: number
  low_stock_count: number
  expiring_soon_count: number
  upcoming_appointments: Array<{
    id: string
    patient_name: string
    date: string
    time: string
    type_name: string
    status: string
  }>
}
```

### Backend View Pattern

```python
class DashboardMetricsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        clinic = request.user.clinic
        today = timezone.now().date()
        # ... aggregation queries ...

        serializer = DashboardMetricsSerializer(data={...})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
```

## Testing Strategy

| Layer | Qué probar | Approach |
|-------|-----------|----------|
| Unit | `DashboardMetricsViewSet.metrics` aggregation logic | Factory Boy fixtures; assert counts/values match known fixture data |
| Integration | Tenant isolation | Create 2 clinics with different data; authenticate as user from Clinic A; verify Clinic B data is excluded |
| Integration | Revenue accuracy | Create paid, draft, cancelled invoices; verify only paid sum is returned |
| Unit | Empty state | No data in DB; verify response has 0s and empty arrays, not errors |
| Unit | Date filtering | Create appointments before/after range; verify only in-range counts |
| Frontend | Hook returns correct shape | Mock API response; verify hook returns typed `DashboardMetrics` |

## Migration / Rollout

No migration required — `dashboard` app tiene 0 modelos propios. Solo queries a apps existentes.

## Open Questions

- None — todos los detalles están resueltos en el proposal y el código base.
