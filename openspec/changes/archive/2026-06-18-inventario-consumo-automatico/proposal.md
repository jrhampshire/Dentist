# Proposal: Inventario - Consumo automático por kit

## Intent

Automatically consume inventory kits when appointments are completed, ensuring accurate stock tracking and audit trail. Currently, the `consume_inventory_kit` wrapper generates synthetic random UUIDs for `appointment_id`, breaking the audit trail, and no idempotency mechanism exists.

## Scope

### In Scope
- Fix `consume_inventory_kit` wrapper (remove broken audit trail)
- Add `inventory_consumed_at` field to Appointment model for idempotency
- Create `POST /api/v1/appointments/{id}/complete/` endpoint (synchronous)
- Validate `inventory_kit` JSONField in AppointmentTypeSerializer
- Add frontend KitItem type matching backend structure
- Add kit editor in appointment type management
- Add "Completar cita" button in appointment detail view
- Align frontend/backend inventory categories
- Tests (backend service + frontend integration)

### Out of Scope
- Undo/revert consumption (post-MVP)
- Celery-based fallback signal (post-MVP)
- Kit consumption reporting/analytics (post-MVP)

## Capabilities

### New Capabilities
- `appointment-completion`: Endpoint and logic for completing appointments with inventory kit consumption
- `inventory-kit-tracking`: Kit definition on appointment types and consumption tracking

### Modified Capabilities
- `inventory-movement`: Audit trail now correctly links to appointments via real IDs

## Approach

**Synchronous explicit action**: DRF `@action` on AppointmentViewSet (`POST .../complete/`) calling `consume_kit()` directly. No Celery signals.

**Idempotency**: `inventory_consumed_at` timestamp on Appointment prevents double consumption.

**Audit trail**: Remove `consume_inventory_kit` wrapper; call `consume_kit(appointment_id=appointment.id)` directly.

**Slicing**:
- Slice A (Backend): Wrapper fix, model migration, complete endpoint, validation — 1 PR
- Slice B (Frontend): Kit editor, complete button, category alignment — 1 PR

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/inventory/services/stock_service.py` | Modified | Remove broken `consume_inventory_kit` wrapper |
| `backend/appointments/models.py` | Modified | Add `inventory_consumed_at` DateTimeField (nullable) |
| `backend/appointments/views.py` | Modified | Add `complete` action endpoint |
| `backend/appointments/serializers.py` | Modified | Validate `inventory_kit` JSONField structure |
| `frontend/src/types/index.ts` | Modified | Add KitItem type `{item_id, quantity}[]` |
| `frontend/src/pages/AppointmentsPage.tsx` | Modified | Add "Completar cita" button, kit editor |
| `frontend/src/pages/InventoryPage.tsx` | Modified | Align category constants with backend |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Double consumption | Medium | `inventory_consumed_at` check before consumption |
| Stale kit references (items deleted) | Low | Validate kit items exist before consumption; fail gracefully |
| No undo mechanism | High (design choice) | Document as post-MVP; manual adjustment via inventory movements |
| Frontend/backend category mismatch | Medium | Define single source of truth (backend `InventoryItem.Category`) |

## Rollback Plan

1. Revert backend PR: Remove `complete` endpoint, drop `inventory_consumed_at` column via migration rollback
2. Revert frontend PR: Remove kit editor and complete button
3. No data loss: `inventory_consumed_at` is nullable; existing appointments unaffected
4. Inventory movements created are legitimate; reverse via manual adjustment if needed

## Dependencies

- Existing `consume_kit()` service method (already tested, atomic, uses `select_for_update`)
- Django migration system for `inventory_consumed_at` field

## Success Criteria

- [ ] `POST /api/v1/appointments/{id}/complete/` returns 200 and consumes kit items
- [ ] Second completion attempt returns 400 (already completed)
- [ ] Inventory movements reference correct `appointment_id` (audit trail intact)
- [ ] Frontend kit editor saves `{item_id, quantity}[]` structure
- [ ] Frontend categories match backend enum values
- [ ] All tests pass (backend service + frontend integration)
