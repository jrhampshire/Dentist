# vital-signs Specification

## Purpose & Scope

Recording and tracking vital signs per patient: blood pressure (systolic/diastolic), heart rate, temperature, weight, height. Optionally linked to appointments. Multiple records per patient (history), typically recorded per visit.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL record blood pressure as systolic/diastolic (mmHg). |
| FR-002 | The system SHALL record heart rate (bpm). |
| FR-003 | The system SHALL record temperature (°C or °F, configurable). |
| FR-004 | The system SHALL record weight (kg) and height (cm). |
| FR-005 | The system SHALL optionally link `VitalSigns` to an `Appointment`. |
| FR-006 | The system SHALL allow multiple vital signs records per patient. |
| FR-007 | The system SHALL support filtering by patient and date range. |
| FR-008 | The system SHALL record `recorded_at` timestamp (may differ from creation time). |

## Data Model / Schema

```
VitalSigns
  - id: UUID (PK)
  - patient: FK → Patient
  - appointment: FK → Appointment (optional, null)
  - blood_pressure_systolic: PositiveIntegerField (optional)
  - blood_pressure_diastolic: PositiveIntegerField (optional)
  - heart_rate: PositiveIntegerField (bpm, optional)
  - temperature: DecimalField (°C, optional)
  - weight: DecimalField (kg, optional)
  - height: DecimalField (cm, optional)
  - notes: TextField (optional)
  - recorded_at: DateTimeField (when vitals were taken)
  - created_at: DateTimeField (auto)
  - created_by: FK → User
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/{id}/vital-signs/` | List all vital signs (filterable by date range) |
| POST | `/api/patients/{id}/vital-signs/` | Create new vital signs record |
| GET | `/api/patients/{id}/vital-signs/{record_id}/` | Get specific record |
| GET | `/api/appointments/{id}/vital-signs/` | Get vital signs for appointment (if linked) |

## Validation Rules

- `blood_pressure_systolic` MUST be 60–300 if provided
- `blood_pressure_diastolic` MUST be 30–200 if provided
- `blood_pressure_systolic` MUST be greater than `blood_pressure_diastolic`
- `heart_rate` MUST be 20–300 if provided
- `temperature` MUST be 30–45 if provided
- `weight` MUST be 0.5–500 if provided
- `height` MUST be 20–300 if provided
- At least ONE vital sign field must be provided

## Permission / Tenant Rules

- Tenant isolation: all records scoped by `patient.clinic`
- User must have `view_vitalsigns` to read
- User must have `add_vitalsigns` to create
- Appointment-linked records inherit appointment's clinic

## Scenarios

### Scenario: Record vitals at appointment

- GIVEN a patient with scheduled appointment
- WHEN nurse records BP 120/80, HR 72, temp 36.5, weight 70kg, height 170cm
- AND links to appointment
- THEN system creates `VitalSigns` with all values
- AND `appointment` FK populated

### Scenario: Record vitals without appointment

- GIVEN a patient arrives without appointment
- WHEN nurse records BP 140/90, HR 88, temp 37.0
- AND does not link to appointment
- THEN system creates `VitalSigns` with appointment=null
- AND records are retrievable under patient

### Scenario: Filter by date range

- GIVEN patient has 10 vital signs records over 2 years
- WHEN user requests GET with `?from=2025-01-01&to=2025-06-30`
- THEN system returns only records within that range

### Scenario: Invalid blood pressure (systolic < diastolic)

- GIVEN user submits systolic=80, diastolic=120
- THEN system returns 400 Bad Request
- AND error indicates systolic must be greater than diastolic

## Acceptance Criteria

- [ ] Vital signs can be recorded with any subset of fields (at least one required)
- [ ] Records linkable to appointments (optional)
- [ ] Multiple records retrievable per patient
- [ ] Date range filtering works correctly
- [ ] Validation enforces physiological ranges
- [ ] Tenant isolation prevents cross-clinic access
