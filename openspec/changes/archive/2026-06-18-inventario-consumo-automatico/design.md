# Design: Inventario — Consumo automático por kit

## Technical Approach

Two stacked PRs. **Slice A (Backend)**: remove the broken `consume_inventory_kit` wrapper, add an `inventory_consumed_at` field to Appointment, create a synchronous `POST /api/v1/appointments/{id}/complete/` endpoint that calls `consume_kit()` in a single transaction, and validate `inventory_kit` at the serializer level. **Slice B (Frontend)**: fix the `inventory_kit` TS type, add a kit editor inside the appointment type form, add a "Completar cita" button on appointment detail, and align inventory categories.

---

## Architecture Decisions

### Decision 1: Remove `consume_inventory_kit` wrapper

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep wrapper, remove synthetic UUID | Still an unnecessary indirection layer | ❌ |
| **Delete wrapper, Celery task calls `consume_kit()` directly** | Simpler, audit trail uses real `appointment_id` | ✅ |
| Keep both wrapper and direct call | Confusion over which to use | ❌ |

**Rationale**: The wrapper at `stock_service.py:348` exists only for the Celery task. The Celery task already has the real `appointment_id`. Deleting the wrapper and passing `appointment_id=str(appt.id)` to `consume_kit()` eliminates the synthetic UUID that breaks the audit trail. No other caller references this wrapper.

### Decision 2: All-or-nothing via single transaction

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Single `transaction.atomic()` in the view + `consume_kit()`** | No partial consumption; fail-fast | ✅ |
| Partial consumption with compensation | Complex rollback logic; not needed for MVP | ❌ |

**Rationale**: `consume_kit()` already wraps in `transaction.atomic()`. The view wraps the entire completion flow (status update + consumption + timestamp) in another `transaction.atomic()`. If any item lacks stock or is blocked/expired, nothing is consumed and the appointment stays in_progress. The user gets a 400 with per-item error details.

### Decision 3: Kit editor inside AppointmentType dialog on Settings page

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Add to existing AppointmentTypeDialog (in Settings)** | Keeps kit config with type definition; minimal UI disruption | ✅ |
| Standalone kit management page | Over-engineered; adds navigation complexity | ❌ |

**Rationale**: No dedicated AppointmentType management dialog exists yet. The kit editor will be built as part of a new Settings area where appointment types can be created/edited. The kit section has a searchable inventory item selector + quantity input per item.

### Decision 4: Categories alignment — backend is source of truth

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Align frontend to backend categories** | Fixes the mismatch at the source; both match | ✅ |
| Normalize in the API layer | Extra translation layer with no benefit | ❌ |

**Rationale**: Backend categories: `material`, `supply`, `instrument`, `medication`, `lab`, `other`. Frontend currently uses `consumable`, `instrument`, `medication`, `equipment`, `other`. The frontend must change to match the backend enum exactly. The API already exposes `/api/v1/inventory/categories/` for this.

---

## Data Flow

### Complete Appointment Flow
```
User clicks "Completar cita" (frontend)
  │
  ▼
POST /api/v1/appointments/{id}/complete/  (with JWT auth)
  │
  ▼
AppointmentViewSet.complete() action
  │
  ├── 1. Validate: status in [scheduled, confirmed, in_progress]
  ├── 2. Validate: inventory_consumed_at is None (idempotency)
  ├── 3. Transaction start
  │     ├── Update appointment status → completed
  │     ├── Read appointment_type.inventory_kit
  │     ├── If kit non-empty: call consume_kit()        ← atomic inside
  │     │     └── For each item: adjust_stock(quantity=-n, reference_type="appointment", reference_id=appt.id)
  │     ├── Set inventory_consumed_at = now()
  │     └── Transaction commit
  │
  ▼
Response 200 OK (appointment data with inventory_consumed_at)
  or 400 Bad Request (validation/per-item errors)

Kit without items: skip consumption, mark completed, set timestamp.
```

### Kit Consumption Audit Trail
```
InventoryMovement
  ├── movement_type = "consumption"
  ├── reference_type = "appointment"
  ├── reference_id = "<real appointment UUID>"      ← was synthetic UUID, now real
  ├── quantity = -<kit item quantity>
  └── note = "Consumo automático por cita <appt_id>"
```

---

## File Changes

### Slice A — Backend

| File | Action | Description |
|------|--------|-------------|
| `backend/inventory/services/stock_service.py` | Modify | Delete `consume_inventory_kit()` wrapper (lines 348-373) |
| `backend/appointments/models.py` | Modify | Add `inventory_consumed_at = DateTimeField(null=True, blank=True)` to Appointment |
| `backend/appointments/serializers.py` | Modify | Add `validate_inventory_kit()` to `AppointmentTypeSerializer`: check `item_id` is valid UUID + references existing `InventoryItem`, `quantity` is positive int |
| `backend/appointments/views.py` | Modify | Add `@action(detail=True, methods=["post"])` named `complete` on `AppointmentViewSet` |
| `backend/appointments/urls.py` | No change | DRF router auto-registers the new action |
| `backend/celery_app/tasks.py` | Modify | `consume_inventory_kit` task: import `consume_kit` directly from stock_service (not the wrapper), pass `appointment_id=str(appt.id)` |
| `backend/appointments/migrations/XXXX_inventory_consumed_at.py` | Create | Auto-generated migration for the new field |
| `backend/tests/integration/test_appointment_complete.py` | Create | Integration tests for the complete endpoint |

### Slice B — Frontend

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/types/index.ts` | Modify | `AppointmentType.inventory_kit`: `string[]` → `{item_id: string; quantity: number}[]`. `InventoryItem.category`: add `'material' \| 'supply' \| 'lab'` to union, align with backend. Add `inventory_consumed_at?: string` to `Appointment`. |
| `frontend/src/api/appointments.ts` | Modify | Add `complete(id: string)` method |
| `frontend/src/hooks/useAppointments.ts` | Modify | Add `useCompleteAppointment()` mutation that calls `appointmentsApi.complete()` and invalidates `['appointment', id]` and `['appointments']` queries |
| `frontend/src/pages/AppointmentsPage.tsx` | Modify | Add "Completar cita" button in appointment detail (when status is `in_progress` and `inventory_consumed_at` is null), with confirmation dialog and inline error display |
| `frontend/src/pages/InventoryPage.tsx` | Modify | Fix categories to match backend: remove `consumable`/`equipment`, add `material`/`supply`/`lab` |
| `frontend/src/pages/SettingsPage.tsx` | Create (new) | Settings page with appointment type management including kit editor section |

---

## Interfaces / Contracts

### API: `POST /api/v1/appointments/{id}/complete/`

**Request**: empty body (no payload needed)

**Success (200)**:
```json
{
  "id": "uuid",
  "status": "completed",
  "inventory_consumed_at": "2026-05-21T14:30:00Z",
  "inventory_items_consumed": 2
}
```

**Error — already completed (400)**:
```json
{
  "error": "already_completed",
  "message": "La cita ya fue completada. Inventario consumido en: 2026-05-21T14:30:00Z"
}
```

**Error — wrong status (400)**:
```json
{
  "error": "invalid_status",
  "message": "Solo se pueden completar citas en estado 'programada', 'confirmada' o 'en curso'."
}
```

**Error — insufficient stock (400)**:
```json
{
  "error": "insufficient_stock",
  "message": "Stock insuficiente para consumir el kit de inventario.",
  "details": [
    {"item_id": "uuid", "item_name": "Guantes de látex", "available": 3, "required": 5},
    {"item_id": "uuid", "item_name": "Mascarillas", "available": 0, "required": 2}
  ]
}
```

### Appointment model (new field)
```python
inventory_consumed_at = models.DateTimeField(
    blank=True, null=True,
    help_text="When inventory kit was consumed on completion"
)
```

### frontend KitItem type
```typescript
interface KitItem {
  item_id: string;
  quantity: number;
}
```

### Frontend categories (aligned with backend)
```typescript
type InventoryCategory = 'material' | 'supply' | 'instrument' | 'medication' | 'lab' | 'other';
```

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (service) | `consume_kit()` continues working after wrapper removal | Existing tests in `test_stock_service.py::TestConsumeKit` — no changes needed, they test `consume_kit()` directly |
| Integration (viewset) | Complete endpoint: happy path, idempotency, wrong status, insufficient stock, blocked/expired items, appointment without kit, with kit, across clinics (RLS) | New `test_appointment_complete.py` using `APIClient`, `auth_headers`, existing fixtures |
| Integration (serializer) | `inventory_kit` validation: valid structure, missing item_id, invalid UUID, negative quantity, non-existent item_id | Add to existing serializer test class or create dedicated |
| Unit (Celery task) | `consume_inventory_kit` task calls `consume_kit()` with real appointment_id | Mock `consume_kit`, assert called with correct args |
| Frontend (hook) | `useCompleteAppointment` mutation fires correct API call and invalidates queries | `@tanstack/react-query` test utils or manual assertion |
| Frontend (component) | "Completar cita" button appears/hides based on status and `inventory_consumed_at` | Render test with different appointment states |

---

## Migration / Rollout

1. Create migration `appointments.XXXX_appointment_inventory_consumed_at`
2. Deploy Slice A (backend) — new endpoint, migration, wrapper deletion
3. Deploy Slice B (frontend) — types, kit editor, complete button, categories
4. Existing appointments: `inventory_consumed_at` stays null (no backfill needed)
5. The old Celery task keeps working because we change it to call `consume_kit()` directly (same signature minus the wrapper)

---

## Open Questions

- [ ] Where exactly is the AppointmentTypeDialog/management UI rendered? Need to confirm if it's in a Settings page or somewhere else. If no Settings page exists, need to create one.
- [ ] Should the complete endpoint also update related invoices or treatment plans? (Out of scope per proposal, but worth confirming.)
- [ ] The Celery task `consume_inventory_kit` still exists after Slice A — should we keep it as a fallback, or remove it entirely once the sync endpoint ships? (Proposal says "post-MVP".)
