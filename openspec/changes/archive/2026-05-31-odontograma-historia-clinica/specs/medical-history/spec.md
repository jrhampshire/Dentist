# medical-history Specification

## Purpose & Scope

Expanded medical history model capturing typed antecedents (pathological, surgical, allergic, pharmacological, familial), motivo de consulta, and enfermedad actual per patient, compliant with NOM-004-SSA3-2012. One active record per patient with version history.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL store one active `MedicalHistory` per patient. |
| FR-002 | The system SHALL support upsert (create or update) for the active record. |
| FR-003 | The system SHALL maintain version history of all `MedicalHistory` records. |
| FR-004 | The system SHALL store 5 typed antecedents: patológicos, quirúrgicos, alérgicos, farmacológicos, familiares. |
| FR-005 | The system SHALL store `motivo_consulta` (reason for visit) as TextField. |
| FR-006 | The system SHALL store `enfermedad_actual` (current condition) as TextField. |
| FR-007 | GET SHALL return active record; historical versions retrievable via query param. |

## Data Model / Schema

```
MedicalHistory
  - id: UUID (PK)
  - patient: FK → Patient (unique=True for is_active=True)
  - antecedentes_patologicos: TextField or JSON
  - antecedentes_quirurgicos: TextField or JSON
  - antecedentes_alergicos: TextField or JSON
  - antecedentes_farmacologicos: TextField or JSON
  - antecedentes_familiares: TextField or JSON
  - motivo_consulta: TextField
  - enfermedad_actual: TextField
  - is_active: BooleanField (default=True)
  - version: IntegerField (auto)
  - created_at: DateTimeField
  - updated_at: DateTimeField
  - created_by: FK → User
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/{id}/medical-history/` | Get active medical history |
| PUT | `/api/patients/{id}/medical-history/` | Upsert medical history (creates new version) |
| GET | `/api/patients/{id}/medical-history/history/` | List all versions |
| GET | `/api/patients/{id}/medical-history/{version}/` | Get specific version |

## Validation Rules

- Only one `is_active=True` record per patient at any time
- Upsert deactivates previous active record and creates new version
- All antecedent fields are optional (may be empty string/array)
- `version` increments atomically per patient

## Permission / Tenant Rules

- Tenant isolation: `patient.clinic` enforced on all queries
- User must have `view_medicalhistory` to read
- User must have `change_medicalhistory` to create/update
- All records scoped by tenant

## Scenarios

### Scenario: Create initial medical history

- GIVEN patient has no medical history
- WHEN user submits PUT with all antecedent fields and motivo/enfermedad
- THEN system creates `MedicalHistory` with `is_active=True`, `version=1`
- AND returns 200 with created record

### Scenario: Update medical history (new version)

- GIVEN patient has active medical history version=3
- WHEN user submits PUT with updated antecedentes
- THEN system sets previous record `is_active=False`
- AND creates new `MedicalHistory` with `is_active=True`, `version=4`
- AND returns 200 with new version

### Scenario: Retrieve version history

- GIVEN patient has 3 medical history versions
- WHEN user calls GET `/history/`
- THEN system returns list of all 3 versions with metadata

### Scenario: Access another tenant's record

- GIVEN user from Clinic A tries to GET patient from Clinic B
- THEN system returns 404 (not 403, to avoid existence disclosure)

## Acceptance Criteria

- [ ] Patient has exactly one active medical history at any time
- [ ] Upserting creates new version, deactivates old
- [ ] All 5 antecedent types stored per record
- [ ] Version history fully retrievable
- [ ] Tenant isolation prevents cross-clinic access
- [ ] API returns 404 for non-existent or unauthorized records
