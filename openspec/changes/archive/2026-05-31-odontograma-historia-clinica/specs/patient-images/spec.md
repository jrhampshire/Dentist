# patient-images Specification

## Purpose & Scope

Upload and serve patient images (intraoral photos, X-rays, documents) with optional tooth-level linking and image type classification. Images stored via django-storages (S3/MinIO or local), served through Django for auth and tenant enforcement.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | The system SHALL accept image uploads (JPEG, PNG, PDF) up to 20MB. |
| FR-002 | The system SHALL classify images by type: photo, xray_periapical, xray_panoramic, xray_cephalometric, document, other. |
| FR-003 | The system SHALL optionally link an image to a specific tooth (FDI code, nullable). |
| FR-004 | The system SHALL generate thumbnails on upload (configurable size). |
| FR-005 | The system SHALL store images via django-storages (S3/MinIO or local). |
| FR-006 | The system SHALL serve images through Django endpoints (not direct S3) to enforce auth + tenant isolation. |
| FR-007 | The system SHALL support filtering by patient, tooth, and image type. |

## Data Model / Schema

```
PatientImage
  - id: UUID (PK)
  - patient: FK → Patient
  - tooth_fdi: IntegerField (optional, null) — 11–85 if provided
  - image_type: CharField (photo|xray_periapical|xray_panoramic|xray_cephalometric|document|other)
  - original_file: ImageField (storage backend)
  - thumbnail: ImageField (generated)
  - description: CharField (optional)
  - uploaded_at: DateTimeField (auto)
  - uploaded_by: FK → User
```

## Storage Configuration

- Backend configured via `settings.py`: `DEFAULT_FILE_STORAGE` (S3/MinIO or local)
- Local dev: `media/patient_images/` with `FileSystemStorage`
- Production: S3 bucket with signed URLs (via django-storages)
- Thumbnails: generated via Pillow or sorl-thumbnail

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/patients/{id}/images/` | Upload new image (multipart/form-data) |
| GET | `/api/patients/{id}/images/` | List images (filterable by tooth, type) |
| GET | `/api/patients/{id}/images/{image_id}/` | Get image metadata |
| GET | `/api/patients/{id}/images/{image_id}/file/` | Serve image (auth + tenant check) |
| GET | `/api/patients/{id}/images/{image_id}/thumbnail/` | Serve thumbnail |
| DELETE | `/api/patients/{id}/images/{image_id}/` | Soft-delete or hard delete |

## Validation Rules

- File size MUST NOT exceed 20MB
- File type MUST be: image/jpeg, image/png, or application/pdf
- `tooth_fdi` MUST be valid FDI code if provided (11–85, or 51–85 for primary)
- `image_type` MUST be one of the defined enum values
- Filename sanitized server-side before storage

## Permission / Tenant Rules

- Tenant isolation: `patient.clinic` enforced on all access
- User must have `view_patientimage` to read metadata
- User must have `add_patientimage` to upload
- User must have `delete_patientimage` to remove
- Image serving endpoint enforces same permissions
- Direct S3 URLs are NEVER exposed; all access goes through Django

## Scenarios

### Scenario: Upload intraoral photo

- GIVEN a patient
- WHEN user uploads JPEG file with image_type=photo, description="Vista oclusal superior"
- THEN system saves file, generates thumbnail
- AND creates `PatientImage` record with metadata
- AND returns 201 with image_id and thumbnail_url

### Scenario: Upload X-ray linked to tooth

- GIVEN a patient
- WHEN user uploads X-ray with image_type=xray_periapical, tooth_fdi=36
- THEN system saves file and creates record
- AND tooth_fdi=36 is stored

### Scenario: Retrieve images filtered by tooth

- GIVEN patient has images for teeth 14, 36, and 47
- WHEN user requests GET `/images/?tooth_fdi=36`
- THEN system returns only images linked to tooth 36

### Scenario: Serve image enforces tenant

- GIVEN Clinic A user requests image belonging to Clinic B patient
- THEN system returns 404 (not 403)
- AND image data is never leaked

### Scenario: Upload oversized file

- GIVEN user submits file with size > 20MB
- THEN system returns 413 Request Entity Too Large
- AND error message indicates size limit

## Acceptance Criteria

- [ ] Images uploaded via multipart/form-data with metadata
- [ ] Thumbnails auto-generated on upload
- [ ] Images served through Django (auth + tenant enforcement)
- [ ] Filtering by patient, tooth, type works
- [ ] File type and size validation enforced
- [ ] No direct S3/storage URLs exposed to clients
- [ ] Tenant isolation prevents unauthorized access
