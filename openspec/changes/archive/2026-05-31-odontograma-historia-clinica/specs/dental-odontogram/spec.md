# dental-odontogram Specification

## Purpose & Scope

Interactive FDI teeth chart (SVG) for recording dental conditions at the surface level. Append-only audit trail via `DentalRecordEntry` with materialized `Tooth`/`ToothSurface` state updated via Django signals.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL render an SVG odontogram with two dental arches: upper (maxillary) and lower (mandibular). |
| FR-002 | The system SHALL display 32 permanent teeth using FDI numbering: 11–18 (UR), 21–28 (UL), 31–38 (LL), 41–48 (LR). |
| FR-003 | The system SHALL display 20 primary teeth: 51–55 (UR), 61–65 (UL), 71–75 (LL), 81–85 (LR). |
| FR-004 | Each permanent tooth SHALL expose 5 clickable surfaces: mesial, distal, buccal, lingual, occlusal. |
| FR-005 | Each primary tooth SHALL expose 4 clickable surfaces: mesial, distal, buccal, lingual (no occlusal). |
| FR-006 | Clicking a surface SHALL open a modal to record: condition (caries, filling, crown, bridge, missing, implant, root_canal, healthy, etc.), notes. |
| FR-007 | Surface condition records SHALL be append-only (no update/delete) via `DentalRecordEntry`. |
| FR-008 | `Tooth` and `ToothSurface` materialized tables SHALL be updated via `post_save` signal on `DentalRecordEntry`. |
| FR-009 | The SVG SHALL color-code teeth/surfaces by condition (e.g., red=caries, blue=filling, gray=missing). |

## Data Model / Schema

```
DentalRecordEntry
  - id: UUID (PK)
  - patient: FK → Patient
  - tooth_fdi: IntegerField (11–85)
  - surface: CharField (mesial|distal|buccal|lingual|occlusal)
  - condition: CharField (caries|filling|crown|bridge|missing|implant|root_canal|healthy|other)
  - notes: TextField (optional)
  - created_by: FK → User
  - created_at: DateTimeField (auto)

Tooth (materialized)
  - patient: FK → Patient
  - tooth_fdi: IntegerField (unique with patient)
  - current_condition: CharField (derived from latest entry)
  - updated_at: DateTimeField

ToothSurface (materialized)
  - tooth: FK → Tooth
  - surface: CharField
  - current_condition: CharField
  - updated_at: DateTimeField
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/{id}/odontogram/` | Get current materialized tooth state |
| GET | `/api/patients/{id}/dental-records/` | List all dental record entries |
| POST | `/api/patients/{id}/dental-records/` | Create new dental record entry |

## Validation Rules

- `tooth_fdi` MUST be valid FDI code: 11–18, 21–28, 31–38, 41–48, 51–55, 61–65, 71–75, 81–85
- `surface` MUST be valid for tooth type: permanent=5 surfaces, primary=4 surfaces
- `condition` MUST be one of: caries, filling, crown, bridge, missing, implant, root_canal, healthy, other
- POST requests SHALL be idempotent for same tooth+surface+condition (no duplicate entries)
- Created entries cannot be modified or deleted via API

## Permission / Tenant Rules

- All records scoped by `patient.clinic` (tenant isolation)
- User must have `view_patient` permission for the patient
- User must have `add_dentalrecordentry` permission to create records
- Tenant isolation enforced at queryset level via `Patient.clinic`

## Scenarios

### Scenario: Record caries on surface

- GIVEN a patient with existing odontogram
- WHEN a user clicks tooth 14, occlusal surface
- AND selects condition "caries" with notes "deep lesion"
- THEN system creates `DentalRecordEntry` with condition=caries
- AND `ToothSurface` for tooth 14 occlusal updates to caries
- AND SVG re-renders with red indicator on that surface

### Scenario: Record filling over caries

- GIVEN tooth 14 occlusal has condition=caries
- WHEN user clicks same surface and records filling
- THEN system appends NEW `DentalRecordEntry` (not modify)
- AND `ToothSurface` updates to filling (most recent entry wins)
- AND SVG shows filling color

### Scenario: Invalid FDI code

- GIVEN API receives POST with tooth_fdi=99
- THEN system returns 400 Bad Request
- AND error message indicates invalid FDI code

### Scenario: Attempt to delete entry

- GIVEN a `DentalRecordEntry` exists
- WHEN user sends DELETE request
- THEN system returns 405 Method Not Allowed

## Acceptance Criteria

- [ ] SVG renders 52 teeth (32 permanent + 20 primary) organized in 4 quadrants
- [ ] Each permanent tooth has 5 clickable surfaces; each primary has 4
- [ ] Clicking surface opens modal with condition options and notes field
- [ ] Submitting modal creates append-only `DentalRecordEntry`
- [ ] `Tooth` and `ToothSurface` materialized tables reflect latest state
- [ ] Color coding visually distinguishes conditions
- [ ] API enforces tenant isolation (patient→clinic)
- [ ] Historical entries retrievable (audit trail intact)
