# appointments — Appointment Scheduling Specification

## Purpose

Appointment types, individual scheduling with conflict detection, recurring schedule slots, slot availability calculation, and WhatsApp integration triggers.

## Requirements

### Requirement: Appointment CRUD MUST enforce tenant isolation

The system SHALL scope all appointment operations to the requesting user's clinic.

#### Scenario: Create appointment with auto-calculated end_time

- GIVEN an authenticated user and an `AppointmentType` with `duration_minutes=30`
- WHEN an appointment is created with `start_time=09:00` and no explicit `end_time`
- THEN the system SHALL auto-calculate `end_time=09:30` from the appointment type's duration

#### Scenario: List appointments filtered by date range

- GIVEN appointments spread across multiple dates
- WHEN `GET /api/v1/appointments/?date_from=2026-06-01&date_to=2026-06-30`
- THEN the system SHALL return only appointments within that date range
- AND appointments outside the range SHALL be excluded

### Requirement: Double-booking prevention MUST enforce unique dentist time slots

The system SHALL prevent two active appointments (scheduled/confirmed/in_progress) for the same dentist at the same date+start_time.

#### Scenario: Double-booking is rejected

- GIVEN an existing appointment for Dr. Pérez on 2026-06-22 at 09:00 with status `scheduled`
- WHEN a new appointment is created for Dr. Pérez on the same date and start_time
- THEN the system SHALL raise a database integrity error
- AND the duplicate SHALL NOT be saved

#### Scenario: Cancelled slots are freed for reuse

- GIVEN Dr. Pérez has a cancelled appointment at 09:00 on 2026-06-22
- WHEN a new appointment is booked for Dr. Pérez at the same date+time
- THEN the system SHALL allow the booking
- AND the unique constraint SHALL NOT fire (cancelled appointments are excluded from the condition)

### Requirement: Status flow MUST follow the defined lifecycle

The system SHALL enforce the appointment status transition: `scheduled → confirmed → in_progress → completed`, with side paths to `cancelled` or `no_show`.

#### Scenario: Valid status transition

- GIVEN an appointment with status `scheduled`
- WHEN the status is changed to `confirmed`
- THEN the system SHALL accept the transition

#### Scenario: Cancelling a completed appointment is rejected

- GIVEN an appointment with status `completed`
- WHEN `appointment.cancel(reason="...", user=...)` is called
- THEN the system SHALL raise `ValueError`
- AND the status SHALL remain `completed`

### Requirement: Available slots MUST be calculated from schedule

The system SHALL calculate available appointment slots based on dentist `ScheduleSlot` records and existing booked appointments.

#### Scenario: Available slots for a given day

- GIVEN Dr. Pérez has a `ScheduleSlot` for Monday 9:00-17:00 and no booked appointments
- WHEN `GET /api/v1/appointments/available-slots/?date=2026-06-22&dentist_id={id}`
- THEN the system SHALL return 15-minute slots from 9:00 to 16:45
- AND each slot SHALL indicate whether it's available

#### Scenario: Booked slots are excluded

- GIVEN Dr. Pérez has an appointment at 09:00-09:30 on Monday
- WHEN available slots are calculated for that Monday
- THEN the 09:00, 09:15, and 09:30 slots SHALL NOT appear as available

### Requirement: Inventory kit MUST auto-consume on appointment completion

When an appointment is marked `completed` and its `AppointmentType` has an `inventory_kit`, the system SHALL automatically deduct the specified quantities from inventory.

#### Scenario: Kit consumption on completion

- GIVEN an appointment type "Limpieza Dental" with `inventory_kit=[{item_id: "x", quantity: 2}]`
- WHEN the appointment is marked `completed`
- THEN the inventory item's stock SHALL be reduced by 2
- AND an `InventoryMovement` with `movement_type=consumption` SHALL be created
- AND `appointment.inventory_consumed_at` SHALL be set

#### Scenario: No kit means no consumption

- GIVEN an appointment type without an inventory kit
- WHEN the appointment is marked `completed`
- THEN no inventory items SHALL be consumed
- AND `inventory_consumed_at` SHALL remain null

### Requirement: WhatsApp reminders MUST integrate with appointment lifecycle

The system SHALL trigger WhatsApp reminder messages via Celery tasks when appointments are created, confirmed, or rescheduled.

#### Scenario: Reminder sent on appointment creation

- GIVEN a new appointment is created with a patient who has `whatsapp_opt_in=True`
- WHEN the appointment is saved
- THEN a Celery task SHALL be dispatched to send a WhatsApp reminder
- AND the appointment's `whatsapp_sent` flag SHALL be set to `True` on success

#### Scenario: No reminder for opted-out patients

- GIVEN a patient with `whatsapp_opt_in=False`
- WHEN an appointment is created for this patient
- THEN no WhatsApp reminder SHALL be dispatched
- AND `whatsapp_sent` SHALL remain `False`
