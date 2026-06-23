# dental_records — Dental Clinical Records Specification

## Purpose

NOM-004-SSA3-2012 compliant dental records: odontogram (FDI notation), medical history, vital signs, patient images, and treatment plans.

## Requirements

### Requirement: Odontogram entries MUST be append-only (immutable)

The system SHALL enforce immutable odontogram entries for NOM-004 compliance. Once created, `DentalRecordEntry` records cannot be modified or deleted.

#### Scenario: New entry is created successfully

- GIVEN an authenticated dentist and a patient
- WHEN a `DentalRecordEntry` is created with `tooth_fdi=11`, `surface=occlusal`, `condition=caries`
- THEN the system SHALL save the entry
- AND the `Tooth` materialized view SHALL be updated for tooth 11
- AND a `ToothSurface` record SHALL be created/updated for tooth 11 occlusal

#### Scenario: Modifying an existing entry is rejected

- GIVEN an existing `DentalRecordEntry`
- WHEN an attempt is made to modify its `condition` and call `save()`
- THEN the system SHALL raise `ValidationError` with message indicating immutability
- AND the original condition SHALL remain unchanged

#### Scenario: Deleting an entry is rejected

- GIVEN an existing `DentalRecordEntry`
- WHEN an attempt is made to delete it
- THEN the system SHALL raise `ValidationError`
- AND the entry SHALL remain in the database

### Requirement: FDI tooth numbers MUST be validated

The system SHALL accept only valid FDI tooth numbers: permanent 11-48 and deciduous 51-85.

#### Scenario: Valid FDI code accepted

- GIVEN `tooth_fdi=36` (lower left first molar)
- WHEN a record is created with this value
- THEN the system SHALL accept it

#### Scenario: Invalid FDI code rejected

- GIVEN `tooth_fdi=99`
- WHEN a record is created with this value
- THEN the system SHALL raise `ValidationError` indicating the code is not valid

### Requirement: Medical history MUST support versioned records

The system SHALL maintain versioned `MedicalHistory` records per patient. Creating a new history deactivates the previous one (`is_active=False`) and increments the version number.

#### Scenario: First medical history is version 1

- GIVEN a patient with no existing medical history
- WHEN a new `MedicalHistory` is created
- THEN `version` SHALL be `1`
- AND `is_active` SHALL be `True`

#### Scenario: Second version deactivates previous

- GIVEN a patient with an active medical history version 1
- WHEN a new `MedicalHistory` is upserted
- THEN the new record SHALL have `version=2` and `is_active=True`
- AND the previous record SHALL have `is_active=False`

#### Scenario: Five typed antecedents are supported

- GIVEN a medical history record
- THEN it SHALL support `antecedentes_patologicos` (pathological), `antecedentes_quirurgicos` (surgical), `antecedentes_alergicos` (allergic), `antecedentes_farmacologicos` (pharmacological), and `antecedentes_familiares` (family)
- AND each antecedent type SHALL be a JSON array of structured objects

### Requirement: Vital signs MUST validate blood pressure

The system SHALL enforce that systolic blood pressure is greater than diastolic.

#### Scenario: Valid blood pressure accepted

- GIVEN `blood_pressure_systolic=120` and `blood_pressure_diastolic=80`
- WHEN vital signs are saved
- THEN the system SHALL accept the values

#### Scenario: Invalid blood pressure rejected

- GIVEN `blood_pressure_systolic=80` and `blood_pressure_diastolic=120`
- WHEN vital signs are saved
- THEN the system SHALL raise `ValidationError` indicating systolic must be greater than diastolic

### Requirement: Patient images MUST support multiple types

The system SHALL support `PatientImage` uploads with types: `photo`, `xray`, `panoramic`, `cephalometric`, `document`, and `other`. Thumbnails SHALL be auto-generated for image types.

#### Scenario: Image upload with thumbnail

- GIVEN a patient and a JPEG image upload
- WHEN the image is saved
- THEN a thumbnail SHALL be generated via Pillow
- AND both `image` and `thumbnail` fields SHALL be populated
- AND `file_size` and `content_type` SHALL be recorded

#### Scenario: Images are served through proxy for tenant enforcement

- GIVEN a `PatientImage` belonging to clinic A's patient
- WHEN a user from clinic B requests the image via proxy view
- THEN the system SHALL return 403 Forbidden
- AND the image SHALL NOT be served directly via S3 URLs

### Requirement: Treatment plans MUST support multi-phase workflows

The system SHALL support `TreatmentPlan` containing ordered `TreatmentPhase` records, each with `TreatmentProcedure` items.

#### Scenario: Plan with multiple phases

- GIVEN a treatment plan "Ortodoncia Completa"
- WHEN phases are added: "Fase 1: Brackets" (order=0), "Fase 2: Alineadores" (order=1)
- THEN the phases SHALL be returned ordered by `order`
- AND each phase MAY contain multiple procedures

#### Scenario: Procedure linked to tooth and appointment

- GIVEN a procedure "Colocación de bracket" in phase 1
- WHEN `tooth_fdi=11` and an `appointment_id` are specified
- THEN the procedure SHALL reference the specific tooth and appointment
- AND the procedure cost SHALL be tracked independently

#### Scenario: Procedure status transitions

- GIVEN a procedure with status `planned`
- WHEN it is set to `in_progress` then `completed`
- THEN the system SHALL accept each transition
- AND the phase and plan statuses MAY be derived from procedure completion
