## Exploration: Inventario — Consumo automático por kit

### Current State

**What works today:**

1. **`consume_kit()` in `stock_service.py`** is solid. It wraps the kit consumption in `transaction.atomic()`, uses `select_for_update()` for each item, validates stock/block/expiration, and creates `InventoryMovement` records with `movement_type=CONSUMPTION`. Unit tests exist and pass.

2. **`AppointmentType.inventory_kit`** is a `JSONField(default=list)` that stores `[{"item_id": "uuid", "quantity": 2}, ...]`. It is exposed in the `AppointmentTypeSerializer` and returned by the API.

3. **Celery task `consume_inventory_kit`** exists in `celery_app/tasks.py` but is **orphaned** — it is never called by any signal, view, or flow.

**What is broken or missing:**

1. **No trigger mechanism**: There is NO `appointments/signals.py`. `Appointment` status changes to `completed` do NOT fire the consumption task. The task is unreachable code.

2. **Broken audit trail in the Celery task**: The task imports `consume_inventory_kit` (the wrapper in `stock_service.py`, line 348). That wrapper **generates a synthetic random UUID** for `appointment_id`, so `InventoryMovement.reference_id` points to a fake ID. The real appointment ID is lost in the audit trail. The `reason` parameter is also completely ignored by the wrapper.

3. **No idempotency**: If an appointment is updated to `completed` twice, the kit would be consumed twice. There is no `inventory_consumed_at` flag or deduplication.

4. **No kit validation in serializer**: `AppointmentTypeSerializer` accepts `inventory_kit` as raw JSON with zero validation. Users can store invalid item IDs, negative quantities, or malformed objects.

5. **Stale references**: If an `InventoryItem` is deleted, its UUID remains in any `AppointmentType.inventory_kit`. Consumption will raise `ValueError` at runtime.

6. **Frontend type mismatch**: `frontend/src/types/index.ts` declares `inventory_kit: string[]`, but the backend sends/expects `{item_id: string, quantity: number}[]`.

7. **No kit management UI**: The frontend has no screen to create/edit kits inside appointment types. `InventoryPage` only manages raw items.

8. **Category drift**: Frontend categories (`consumable`, `instrument`, `medication`, `equipment`, `other`) do not match backend categories (`material`, `supply`, `instrument`, `medication`, `lab`, `other`). There is no `kit` category on either side.

---

### Affected Areas

| File | Why it's affected |
|------|-------------------|
| `backend/inventory/services/stock_service.py` | `consume_inventory_kit` wrapper breaks audit trail; `consume_kit` core logic is correct but needs direct invocation |
| `backend/celery_app/tasks.py` | `consume_inventory_kit` task must call `consume_kit` directly with the real appointment ID |
| `backend/appointments/models.py` | `Appointment` needs an idempotency field (e.g., `inventory_consumed_at`) |
| `backend/appointments/serializers.py` | `AppointmentTypeSerializer` needs `inventory_kit` structure validation |
| `backend/appointments/views.py` | Needs a `complete` action or signal wiring to trigger consumption |
| `backend/appointments/signals.py` | **Does not exist** — needs creation for automatic trigger on status change |
| `frontend/src/types/index.ts` | `AppointmentType.inventory_kit` typed as `string[]`; should be `KitItem[]` |
| `frontend/src/pages/AppointmentsPage.tsx` | Needs a "Completar cita" button that hits the completion endpoint |
| `frontend/src/api/appointments.ts` | May need `completeAppointment(id)` method |

---

### Approaches

#### 1. DRF `@action` with synchronous consumption (Recommended)
Add a `POST /api/v1/appointments/{id}/complete/` endpoint on `AppointmentViewSet` that:
- Validates the appointment is in a completable state (`scheduled`, `confirmed`, `in_progress`).
- Updates status to `completed`.
- Calls `consume_kit()` **directly** (not via the broken wrapper) with the real appointment ID.
- Wraps everything in a DB transaction so if consumption fails, the appointment is NOT marked completed.
- Returns `400` with per-item stock errors if any item is unavailable.

- **Pros**: Immediate feedback to the user; atomic (all-or-nothing); explicit UX; easy to test; no hidden side effects.
- **Cons**: Slightly more frontend work (dedicated button); request may take ~100-300ms for large kits.
- **Effort**: Medium

#### 2. Pure signal-based auto-trigger
Create `appointments/signals.py` with a `post_save` signal on `Appointment`. When `status` transitions to `completed`, fire `consume_inventory_kit.delay(str(appt.id))`.

- **Pros**: Fully automatic; works for admin/patch updates too.
- **Cons**: Silent failures (Celery retry may hide problems); double-consumption risk without idempotency; harder to debug; user gets no feedback if stock is missing.
- **Effort**: Medium

#### 3. Hybrid — explicit action + signal fallback
Implement Option 1 as the primary path. Keep a lightweight signal that only triggers if a direct DB update bypassed the API (e.g., Django admin, management command).

- **Pros**: Best of both worlds.
- **Cons**: Slightly more code; risk of duplicate consumption if both paths fire (mitigated by idempotency field).
- **Effort**: Medium-High

---

### Recommendation

**Go with Option 1 (DRF `@action` with synchronous consumption)** as the primary path, and add an idempotency guard (`Appointment.inventory_consumed_at` datetime field) so that even if the action is called twice, consumption only happens once.

Why synchronous instead of Celery for this specific flow:
- A kit is typically 2–5 items. `select_for_update()` + a few INSERTs is sub-second.
- The user (dentist/receptionist) is staring at the screen waiting to confirm the appointment is done. They NEED to know *now* if guantes are out of stock.
- Celery is appropriate for background alerts (WhatsApp, expiration checks), not for a synchronous business-rule gate.

Steps:
1. Fix `consume_inventory_kit` wrapper in `stock_service.py` — remove synthetic UUID, or better, delete the wrapper and call `consume_kit()` directly.
2. Add `inventory_consumed_at` nullable DateTime to `Appointment` model.
3. Add `POST .../complete/` action on `AppointmentViewSet`.
4. Validate `inventory_kit` JSON structure in `AppointmentTypeSerializer`.
5. Add frontend `KitItem` type, kit editor inside appointment-type management, and a "Completar cita" button.
6. Align frontend/backend inventory categories.

---

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Double consumption | High — stock goes negative or too low | Add `inventory_consumed_at` timestamp; check it before consuming |
| Broken audit trail | Medium — can't trace consumption to appointment | Call `consume_kit()` directly with real `appointment_id`; remove broken wrapper |
| Stale kit references | Medium — consumption fails at runtime | Add serializer validation; soft-delete items instead of hard delete, or validate kit on save |
| No undo on cancellation | Low-Medium — stock permanently lost | Block reverting `completed` → other statuses; if needed, add a manual "return" movement later |
| Frontend type mismatch | Low — runtime bugs in kit editor | Fix `AppointmentType.inventory_kit` type to `{item_id: string; quantity: number}[]` |
| Category mismatch | Low — wrong labels/filters | Align frontend category options with backend `InventoryItem.Category` choices |

---

### Ready for Proposal

**Yes.**

The orchestrator should tell the user:
- The backend core logic (`consume_kit`) is already built and tested.
- The missing pieces are: (1) a trigger mechanism, (2) fixing the Celery wrapper's broken audit trail, (3) adding idempotency, (4) kit validation, and (5) frontend kit management.
- Complexity is **Medium** — roughly 1–2 days backend + 1–2 days frontend for a single developer.
