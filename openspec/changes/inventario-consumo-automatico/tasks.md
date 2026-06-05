# Tasks: Inventario — Consumo automático por kit

**Change**: inventario-consumo-automatico
**Delivery strategy**: auto-chain (stacked-to-main)

---

## Slice A — Backend (PR 1)

### Phase 1: Model + Wrapper

#### [x] Task 1.1: Remove `consume_inventory_kit` wrapper from stock_service.py
- **File**: `backend/inventory/services/stock_service.py`
- **Action**: Delete the `consume_inventory_kit()` function (lines 348-373) including its docstring. This wrapper generates a synthetic UUID for `appointment_id` which breaks the audit trail. The Celery task will call `consume_kit()` directly instead.
- **Verify**: No other code references `consume_inventory_kit` from stock_service (search for imports)

#### [x] Task 1.2: Update Celery task to call `consume_kit()` directly
- **File**: `backend/celery_app/tasks.py`
- **Action**: In the `consume_inventory_kit` task (lines 594-649):
  - Change import from `from inventory.services.stock_service import consume_inventory_kit as _consume` to `from inventory.services.stock_service import consume_kit`
  - Replace the `_consume(kit=..., clinic_id=..., reason=...)` call with `consume_kit(clinic_id=str(appt.clinic_id), kit=kit, appointment_id=str(appt.id), user=None)`
  - Update the try/except logic to handle `ValueError` from `consume_kit` (returns list of movements on success)
- **Verify**: Task still returns `{"status": "success", "items_consumed": len(kit)}` on success

#### [x] Task 1.3: Add `inventory_consumed_at` field to Appointment model
- **File**: `backend/appointments/models.py`
- **Action**: Add field to the `Appointment` model (after the `cancelled_at` field, around line 137):
  ```python
  inventory_consumed_at = models.DateTimeField(
      blank=True, null=True,
      help_text="When inventory kit was consumed on completion"
  )
  ```
- **Verify**: Field is nullable, does not break existing migrations

#### [x] Task 1.4: Generate migration for `inventory_consumed_at`
- **File**: `backend/appointments/migrations/` (new file)
- **Action**: Run `python manage.py makemigrations appointments --name appointment_inventory_consumed_at`
- **Verify**: Migration file is created with `AddField` operation for `inventory_consumed_at`

---

### Phase 2: Complete Endpoint

#### [x] Task 2.1: Create `complete` action on AppointmentViewSet
#### [x] Task 2.2: Add `inventory_consumed_at` to AppointmentSerializer
#### [x] Task 3.1: Add `validate_inventory_kit` to AppointmentTypeSerializer
- **File**: `backend/appointments/serializers.py`
- **Action**: Add a `validate_inventory_kit(self, value)` method to `AppointmentTypeSerializer`:
  1. If value is empty list or None, return value (valid — no kit)
  2. For each item in the list:
     - Validate `item_id` key exists and is a valid UUID string
     - Validate `quantity` key exists and is a positive integer (> 0)
     - Query `InventoryItem.objects.filter(id=item_id, clinic_id=clinic_id)` to verify item exists in this clinic
     - If item not found, raise `serializers.ValidationError("Item de inventario no encontrado: {item_id}")`
  3. Return value
- **Note**: Need to get `clinic_id` from `self.context["request"].clinic_id`
- **Verify**: Invalid kit items are rejected at create/update time with clear error messages

---

### Phase 4: Tests

#### [x] Task 4.1: Integration test — complete appointment with kit → stock deducted
#### [x] Task 4.2: Integration test — complete appointment without kit → no-op
#### [x] Task 4.3: Integration test — complete twice → idempotent (400)
#### [x] Task 4.4: Integration test — insufficient stock → 400 with details
#### [x] Task 4.5: Integration test — invalid status → 400
#### [x] Task 4.6: Serializer test — invalid kit items
#### [x] Task 4.7: Unit test — Celery task calls `consume_kit()` with real appointment_id
- **File**: `backend/tests/unit/test_stock_service.py` (add to existing) or new `backend/tests/unit/test_celery_tasks.py`
- **Action**: Mock `consume_kit`, trigger `consume_inventory_kit` task, assert called with `appointment_id=str(appt.id)` (not synthetic UUID).

---

## Slice B — Frontend (PR 2)

### Phase 5: Types + API

#### [x] Task 5.1: Fix `AppointmentType.inventory_kit` type
- **File**: `frontend/src/types/index.ts`
- **Action**: 
  - Add `KitItem` interface: `{ item_id: string; quantity: number }`
  - Change `AppointmentType.inventory_kit` from `string[]` to `KitItem[]`
- **Verify**: TypeScript compilation passes

#### [x] Task 5.2: Add `inventory_consumed_at` to Appointment type
- **File**: `frontend/src/types/index.ts`
- **Action**: Add `inventory_consumed_at?: string` to the `Appointment` interface
- **Verify**: TypeScript compilation passes

#### [x] Task 5.3: Align `InventoryItem.category` with backend
- **File**: `frontend/src/types/index.ts`
- **Action**: Change category type from `'consumable' | 'instrument' | 'medication' | 'equipment' | 'other'` to `'material' | 'supply' | 'instrument' | 'medication' | 'lab' | 'other'`
- **Verify**: TypeScript compilation passes

#### [x] Task 5.4: Add `complete(id)` to appointments API
- **File**: `frontend/src/api/appointments.ts`
- **Action**: Add method:
  ```typescript
  complete: (id: string) =>
    apiClient.post<AppointmentCompleteResponse>(`/appointments/${id}/complete/`).then((r) => r.data),
  ```
- **Add type**: `AppointmentCompleteResponse` with `{ id: string; status: string; inventory_consumed_at: string; inventory_items_consumed: number }`
- **Verify**: API call works with existing auth setup

---

### Phase 6: Kit Editor

#### [x] Task 6.1: Add `useCompleteAppointment` mutation hook
- **File**: `frontend/src/hooks/useAppointments.ts`
- **Action**: Add mutation that calls `appointmentsApi.complete(id)` and invalidates `['appointment', id]` and `['appointments']` queries
- **Verify**: Hook follows same pattern as existing mutations in the file

#### [x] Task 6.2: Create SettingsPage with AppointmentType management
- **File**: `frontend/src/pages/SettingsPage.tsx`
- **Action**: Created settings page with header "Configuración", card with table of appointment types showing Name, Duration, Kit Components count, and Edit/Delete actions. Uses `useAppointmentTypes()`, `useDeleteAppointmentType()`. "Nuevo tipo de cita" button opens `AppointmentTypeDialog`. Follows InventoryPage layout pattern.
- **Verify**: Table renders, edit opens dialog with pre-filled data, delete shows confirmation

#### [x] Task 6.3: Create AppointmentTypeDialog with Kit Editor
- **File**: `frontend/src/pages/Settings/AppointmentTypeDialog.tsx` (new `Settings/` directory)
- **Action**: Created dialog with Name, Duration form fields. Kit Components section: table of selected items with Name | Quantity | Remove button. "Agregar componente" button opens searchable dropdown for InventoryItem (name + category + stock). Quantity input after selection. Stores as `KitItem[]`. On save calls `useCreateAppointmentType()` or `useUpdateAppointmentType()` with `inventory_kit`. Fetches inventory via `useInventoryItems()` for the dropdown.
- **Verify**: Dialog works for create and edit, kit items persist, inventory search filters correctly

#### [x] Task 6.4: Add route + navigation
- **Files**: `frontend/src/App.tsx`, `frontend/src/components/layout/AppShell.tsx`
- **Action**: Added `<Route path="/settings">` to App.tsx with protected route wrapper. Added "Configuración" navigation item with `Settings` icon from lucide-react to AppShell sidebar.
- **Verify**: `/settings` route accessible, sidebar link highlights correctly

---

### Phase 7: Complete Button

#### [x] Task 7.1: Add "Completar cita" button to appointment detail
- **File**: `frontend/src/pages/AppointmentsPage.tsx`
- **Action**: In the appointment detail view/modal:
  - Show "Completar cita" button when `appointment.status === 'in_progress'` AND `!appointment.inventory_consumed_at`
  - On click, show confirmation dialog ("¿Completar esta cita? Se consumirá el inventario asociado.")
  - On confirm, call `completeAppointment(id)` mutation
  - On success: refresh appointment data, show success toast
  - On failure (400): display per-item error details inline
  - Disable button after `inventory_consumed_at` is set
- **Verify**: Button visibility logic is correct, errors are displayed

---

### Phase 8: Categories

#### [x] Task 8.1: Update InventoryPage category options
- **File**: `frontend/src/pages/InventoryPage.tsx`
- **Action**: Find all category dropdowns, filters, and labels. Replace:
  - Remove: `'consumable'`, `'equipment'`
  - Add: `'material'`, `'supply'`, `'lab'`
  - Keep: `'instrument'`, `'medication'`, `'other'`
- **Update labels**: `material` → "Material", `supply` → "Insumo", `lab` → "Laboratorio"
- **Verify**: Category filter works, new categories appear in create/edit forms

#### [x] Task 8.2: Add category labels constant
- **File**: `frontend/src/types/index.ts`
- **Action**: Add `INVENTORY_CATEGORY_LABELS` constant mapping category keys to Spanish labels:
  ```typescript
  export const INVENTORY_CATEGORY_LABELS: Record<string, string> = {
    material: 'Material',
    supply: 'Insumo',
    instrument: 'Instrumento',
    medication: 'Medicamento',
    lab: 'Laboratorio',
    other: 'Otro',
  }
  ```
- **Verify**: Used consistently across InventoryPage and any other inventory-related components
