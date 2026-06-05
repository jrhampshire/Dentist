# clinical-note-extension Specification

## Purpose & Scope

Add optional `tooth_fdi` and `surface` reference fields to the existing `ClinicalNote` model, enabling clinical notes to reference specific teeth/surfaces without changing existing behavior for notes that don't use these fields.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL add nullable `tooth_fdi` IntegerField to `ClinicalNote`. |
| FR-002 | The system SHALL add nullable `surface` CharField to `ClinicalNote` with surface enum choices. |
| FR-003 | The system SHALL NOT change behavior for existing `ClinicalNote` records (null values for new fields). |
| FR-004 | The system SHALL validate `tooth_fdi` against FDI numbering when provided. |
| FR-005 | The system SHALL validate `surface` against allowed surfaces when provided. |

## Data Model / Schema

```python
# In patients/models.py — ClinicalNote extension
class ClinicalNote(models.Model):
    # ... existing fields ...
    
    tooth_fdi = models.IntegerField(
        null=True,
        blank=True,
        help_text="FDI tooth number (11-85, 51-85)"
    )
    
    SURFACE_CHOICES = [
        ('mesial', 'Mesial'),
        ('distal', 'Distal'),
        ('buccal', 'Buccal'),
        ('lingual', 'Lingual'),
        ('occlusal', 'Occlusal'),
    ]
    surface = models.CharField(
        max_length=20,
        choices=SURFACE_CHOICES,
        null=True,
        blank=True
    )
```

## API Endpoints

No new endpoints required. Existing `ClinicalNote` endpoints accept the new fields via serializers.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients/{id}/notes/` | List notes (existing) |
| POST | `/api/patients/{id}/notes/` | Create note (now accepts tooth_fdi, surface) |
| GET | `/api/patients/{id}/notes/{note_id}/` | Get note (existing) |
| PUT/PATCH | `/api/patients/{id}/notes/{note_id}/` | Update note (existing) |

## Validation Rules

- `tooth_fdi` MUST be valid FDI code (11–18, 21–28, 31–38, 41–48, 51–55, 61–65, 71–75, 81–85) if not null
- `surface` MUST be one of: mesial, distal, buccal, lingual, occlusal if not null
- If `surface` is provided, `tooth_fdi` SHOULD also be provided (SHOULD, not MUST — some notes may reference surface without specific tooth)

## Permission / Tenant Rules

- Existing `ClinicalNote` permissions apply unchanged
- Tenant isolation via `patient.clinic` unchanged

## Scenarios

### Scenario: Create note with tooth reference

- GIVEN a patient
- WHEN user creates `ClinicalNote` with content, tooth_fdi=14, surface=occlusal
- THEN system saves note with both fields populated
- AND note is retrievable with tooth reference intact

### Scenario: Create note without tooth reference

- GIVEN a patient
- WHEN user creates `ClinicalNote` with content only
- THEN system saves note with tooth_fdi=null, surface=null
- AND existing notes behavior is unchanged

### Scenario: Update existing note with tooth reference

- GIVEN an existing `ClinicalNote` with null tooth_fdi
- WHEN user updates it with tooth_fdi=36, surface=mesial
- THEN system saves updated values
- AND no data loss for other existing fields

### Scenario: Invalid FDI code

- GIVEN API receives POST with tooth_fdi=99
- THEN system returns 400 Bad Request
- AND error indicates invalid FDI code

## Acceptance Criteria

- [ ] Migration adds nullable fields without data loss
- [ ] Existing notes continue to work with null values
- [ ] New notes can reference specific tooth and surface
- [ ] Validation enforces FDI codes when tooth_fdi provided
- [ ] Validation enforces surface enum when surface provided
- [ ] API serializers accept new fields without breaking existing clients
