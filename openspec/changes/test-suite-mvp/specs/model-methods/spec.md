# model-methods — Test Spec

## Purpose

Unit tests for model-level business logic across appointments, patients, and inventory models: Appointment.save() auto end_time, Patient.delete() soft delete, InventoryItem.deduct_stock().

## Requirements

### Requirement: Appointment.save() MUST auto-calculate end_time from duration_minutes

The system SHALL set `Appointment.end_time` automatically based on `start_time` + `appointment_type.duration_minutes` when `start_time` changes.

#### Scenario: Appointment start_time update triggers end_time recalculation

- GIVEN an Appointment with `start_time=09:00`, `appointment_type.duration_minutes=60`, `end_time=10:00`
- WHEN `appointment.start_time` is set to `10:00` and `save()` is called
- THEN `appointment.end_time` SHALL be automatically set to `11:00`

#### Scenario: Saving without changing start_time does not recalculate

- GIVEN an Appointment with `start_time=09:00`, `end_time=10:00`
- WHEN `save()` is called without changing `start_time`
- THEN `end_time` SHALL remain `10:00`

### Requirement: Patient.delete() MUST perform a soft delete

The system SHALL set `deleted_at` timestamp instead of hard-deleting, preserving referential integrity.

#### Scenario: Patient soft delete

- GIVEN an existing Patient with no `deleted_at` value
- WHEN `Patient.delete()` is called
- THEN the system SHALL set `deleted_at` to the current timestamp and SHALL NOT remove the database row

#### Scenario: Soft-deleted patient is excluded from queries

- GIVEN a soft-deleted Patient
- WHEN `Patient.objects.get(id=patient_id)` is called
- THEN the system SHALL raise `Patient.DoesNotExist`

#### Scenario: Patient hard_delete bypasses soft delete

- GIVEN an existing Patient
- WHEN `Patient.hard_delete()` is called
- THEN the database row SHALL be permanently removed

### Requirement: InventoryItem.deduct_stock() MUST prevent negative stock

The system SHALL refuse to deduct stock if the resulting quantity would be negative.

#### Scenario: Sufficient stock deduction

- GIVEN an InventoryItem with `quantity=50`
- WHEN `item.deduct_stock(30)` is called
- THEN `item.quantity` SHALL be set to `20` and the operation SHALL succeed

#### Scenario: Insufficient stock deduction

- GIVEN an InventoryItem with `quantity=10`
- WHEN `item.deduct_stock(30)` is called
- THEN the system SHALL raise `InsufficientStockError` and `item.quantity` SHALL remain `10`

#### Scenario: Zero stock deduction matches exactly

- GIVEN an InventoryItem with `quantity=30`
- WHEN `item.deduct_stock(30)` is called
- THEN `item.quantity` SHALL be set to `0` and the operation SHALL succeed