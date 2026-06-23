# patients — Patient Management Specification

## Purpose

Patient CRUD with encrypted medical fields (NOM-024 compliance), clinical notes with digital signature, consent tracking, and retention policy.

## Requirements

### Requirement: Patient CRUD MUST enforce tenant isolation

The system SHALL scope all patient operations to the requesting user's clinic via RLS (Row Level Security).

#### Scenario: Create patient with required fields

- GIVEN an authenticated user with role `admin` or `recepcionista`
- WHEN a `POST /api/v1/patients/` is made with `first_name`, `last_name`, `phone`, and `date_of_birth`
- THEN the system SHALL create the patient in the user's clinic and return status `201`
- AND the `clinic_id` SHALL be set automatically from the authenticated user

#### Scenario: List patients filtered by clinic

- GIVEN clinic A has 3 patients and clinic B has 2 patients
- WHEN an authenticated user from clinic A calls `GET /api/v1/patients/`
- THEN the system SHALL return exactly 3 patients (only clinic A's)
- AND patients from clinic B SHALL NOT appear in the response

#### Scenario: Soft-delete patient preserves audit trail

- GIVEN an existing patient in clinic A
- WHEN a `DELETE /api/v1/patients/{id}/` is called by an admin from clinic A
- THEN the system SHALL set `is_deleted=True` instead of removing the row
- AND `Patient.objects` manager SHALL exclude the soft-deleted patient from normal queries
- AND `Patient.all_objects` manager SHALL still return the soft-deleted patient

### Requirement: Encrypted medical fields MUST use AES-256-GCM

The system SHALL encrypt `allergies`, `chronic_conditions`, and `current_medications` at rest using AES-256-GCM with a configured `ENCRYPTION_KEY`.

#### Scenario: Medical fields are encrypted at rest

- GIVEN a patient with allergies set to "Penicilina, Aspirina"
- WHEN the patient record is stored to the database
- THEN the `allergies` column SHALL NOT contain the plaintext value "Penicilina"
- AND the field SHALL be decryptable by the encryption service using the configured key

#### Scenario: Reading encrypted fields returns decrypted values

- GIVEN a patient with `chronic_conditions` encrypted in the database
- WHEN the patient is retrieved via the DRF serializer
- THEN the `chronic_conditions` field in the response SHALL contain the original plaintext

### Requirement: Clinical notes MUST be immutable once signed

The system SHALL prevent modification of a `ClinicalNote` after `is_signed=True` is set.

#### Scenario: Signing a clinical note

- GIVEN an unsigned clinical note
- WHEN `note.sign(user)` is called
- THEN `is_signed` SHALL be set to `True`
- AND `signed_at` SHALL be set to the current timestamp
- AND `signature_hash` SHALL be a SHA-256 hash of content+title+note_type+author_id

#### Scenario: Modifying a signed note is rejected

- GIVEN a signed clinical note
- WHEN an attempt is made to modify `content` and call `note.save()`
- THEN the system SHALL raise `ValueError` with message indicating immutability
- AND the note's content SHALL remain unchanged

#### Scenario: Creating a new note is always allowed

- GIVEN a patient with existing signed notes
- WHEN a new `ClinicalNote` is created for the same patient
- THEN the system SHALL allow creation regardless of existing signed notes

### Requirement: Patient consent MUST track signature with content hash

The system SHALL support consent types: `general`, `treatment`, `data_processing`, and `whatsapp`. Signed consents SHALL include a SHA-256 hash for integrity verification.

#### Scenario: Signing a consent

- GIVEN an unsigned `PatientConsent`
- WHEN `consent.sign(signature_blob=b"...", ip_address="192.0.2.1", user=user)` is called
- THEN `signed` SHALL be set to `True`
- AND `signed_at`, `signature_blob`, `ip_address`, and `signature_hash` SHALL be populated

#### Scenario: WhatsApp consent is tracked per patient

- GIVEN a patient with `whatsapp_opt_in=True` and no existing consent record
- WHEN a WhatsApp consent is created and signed
- THEN the consent `consent_type` SHALL be `whatsapp`
- AND the patient SHALL have a record of their opt-in decision

### Requirement: NOM-024 retention MUST purge expired records

The system SHALL provide `purge_expired_records` management command that soft-deletes inactive patients and anonymizes unsigned clinical notes older than N years (default 5).

#### Scenario: Dry-run previews without modifications

- GIVEN patients and notes eligible for retention purge
- WHEN `purge_expired_records --years=5 --dry-run` is called
- THEN the system SHALL output a preview of affected records
- AND SHALL NOT modify any patient or note in the database

#### Scenario: Live mode soft-deletes inactive patients

- GIVEN a patient with no appointments in 5+ years and `created_at` before the cutoff
- WHEN `purge_expired_records --years=5` is called without `--dry-run`
- THEN the patient SHALL be soft-deleted (`is_deleted=True`)
- AND an `AuditLog` entry SHALL be created with action `patients.patient.retention_purge`

#### Scenario: Signed notes are never anonymized

- GIVEN a signed clinical note older than 5 years
- WHEN `purge_expired_records` runs in live mode
- THEN the signed note's content SHALL NOT be changed
- AND the note SHALL remain intact

#### Scenario: Unsigned old notes are anonymized

- GIVEN an unsigned clinical note older than 5 years
- WHEN `purge_expired_records` runs in live mode
- THEN the note's content SHALL be replaced with `[REDACTED - Retention period expired]`
- AND an `AuditLog` entry SHALL be created with action `patients.clinicalnote.retention_anonymized`

### Requirement: Patient data export MUST be available for compliance

The system SHALL provide an endpoint to export all patient data including notes, consents, and audit trail.

#### Scenario: Export patient complete record

- GIVEN an authenticated admin user
- WHEN `GET /api/v1/patients/{id}/export/` is called
- THEN the system SHALL return a JSON or archive with all patient data
- AND the response SHALL include clinical notes, consents, and audit trail entries
