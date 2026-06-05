# treatment-plan Specification

## Purpose & Scope

Multi-phase treatment plans with procedures linked to appointments. Enables tracking of planned, in-progress, completed, and cancelled treatments organized hierarchically: `TreatmentPlan` → `TreatmentPhase` → `TreatmentProcedure`.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL create `TreatmentPlan` linked to a patient with name, description, status. |
| FR-002 | The system SHALL create `TreatmentPhase` linked to a plan with name, order, description, status. |
| FR-003 | The system SHALL create `TreatmentProcedure` linked to a phase with optional appointment and tooth reference. |
| FR-004 | The system SHALL support status transitions: plan (active, completed, cancelled), phase (pending, in_progress, completed, cancelled), procedure (planned, in_progress, completed, cancelled). |
| FR-005 | The system SHALL nest CRUD under patient: plans → phases → procedures. |
| FR-006 | The system SHALL optionally link procedures to appointments. |

## Data Model / Schema

```
TreatmentPlan
  - id: UUID (PK)
  - patient: FK → Patient
  - name: CharField
  - description: TextField (optional)
  - status: CharField (active|completed|cancelled)
  - created_at: DateTimeField
  - updated_at: DateTimeField
  - created_by: FK → User

TreatmentPhase
  - id: UUID (PK)
  - plan: FK → TreatmentPlan
  - name: CharField
  - order: PositiveIntegerField
  - description: TextField (optional)
  - status: CharField (pending|in_progress|completed|cancelled)
  - created_at: DateTimeField
  - updated_at: DateTimeField

TreatmentProcedure
  - id: UUID (PK)
  - phase: FK → TreatmentPhase
  - appointment: FK → Appointment (optional, null)
  - tooth_fdi: IntegerField (optional, null)
  - description: TextField
  - cost: DecimalField (MXN, optional)
  - status: CharField (planned|in_progress|completed|cancelled)
  - created_at: DateTimeField
  - updated_at: DateTimeField
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/{id}/treatment-plans/` | List all plans for patient |
| POST | `/api/patients/{id}/treatment-plans/` | Create treatment plan |
| GET | `/api/patients/{id}/treatment-plans/{plan_id}/` | Get plan with phases and procedures |
| PUT/PATCH | `/api/patients/{id}/treatment-plans/{plan_id}/` | Update plan |
| DELETE | `/api/patients/{id}/treatment-plans/{plan_id}/` | Delete plan (cascades to phases/procedures) |
| POST | `/api/patients/{id}/treatment-plans/{plan_id}/phases/` | Create phase |
| PUT/PATCH | `/api/patients/{id}/treatment-plans/{plan_id}/phases/{phase_id}/` | Update phase |
| DELETE | `/api/patients/{id}/treatment-plans/{plan_id}/phases/{phase_id}/` | Delete phase (cascades to procedures) |
| POST | `/api/patients/{id}/treatment-plans/{plan_id}/phases/{phase_id}/procedures/` | Create procedure |
| PUT/PATCH | `/api/patients/{id}/treatment-plans/{plan_id}/phases/{phase_id}/procedures/{proc_id}/` | Update procedure |
| DELETE | `/api/patients/{id}/treatment-plans/{plan_id}/phases/{phase_id}/procedures/{proc_id}/` | Delete procedure |

## Validation Rules

- `tooth_fdi` MUST be valid FDI code if provided (11–85, 51–85)
- Phase `order` SHOULD be unique per plan (enforced at application level)
- Deleting a plan SHALL cascade delete all phases and procedures
- Deleting a phase SHALL cascade delete all procedures
- `cost` MUST be non-negative if provided

## Permission / Tenant Rules

- Tenant isolation: all records scoped by `patient.clinic`
- User must have `view_treatmentplan` to read plans
- User must have `add_treatmentplan` to create plans
- Nested resources inherit parent's tenant scope
- Appointment FK link inherits appointment's clinic (cross-checked)

## Scenarios

### Scenario: Create treatment plan with phases

- GIVEN a patient
- WHEN user creates plan "Ortodoncia Full" with 3 phases
- THEN system creates `TreatmentPlan` with status=active
- AND creates 3 `TreatmentPhase` records with order 1, 2, 3

### Scenario: Add procedure to phase

- GIVEN a phase exists with order=1
- WHEN user adds procedure "Extracción 14" with tooth_fdi=14, cost=1500
- THEN system creates `TreatmentProcedure` linked to phase
- AND procedure appears in phase's procedure list

### Scenario: Link procedure to appointment

- GIVEN a phase exists and an appointment is scheduled
- WHEN user creates procedure linked to appointment
- THEN `TreatmentProcedure.appointment` FK is populated
- AND procedure appears in appointment's treatment list

### Scenario: Complete phase

- GIVEN phase has status=in_progress and 2 procedures (both completed)
- WHEN user updates phase status to completed
- THEN phase status becomes completed
- AND no cascade to procedures

### Scenario: Delete plan cascades

- GIVEN plan with 2 phases, each with procedures
- WHEN user deletes plan
- THEN all phases and procedures are deleted
- AND returns 204 No Content

## Acceptance Criteria

- [ ] Plans can be created, listed, updated, deleted
- [ ] Phases nested under plans with ordering
- [ ] Procedures nested under phases with optional appointment/tooth links
- [ ] Cascade delete from plan down to procedures
- [ ] Status transitions enforced per entity type
- [ ] Cost tracking optional per procedure
- [ ] Tenant isolation on all resources
- [ ] FDI validation when tooth_fdi provided
