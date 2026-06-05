# Design: Odontograma / Historia Clínica (Fase A)

## Technical Approach

Nueva app Django `dental_records` que agrupa 6 capacidades del expediente clínico expandido: odontograma FDI, historia médica, signos vitales, imágenes de paciente, extensión de nota clínica y plan de tratamiento. Los nuevos modelos se relacionan vía FK a `Patient` (herencia de tenant vía `patient.clinic`). La app no tiene modelo propio de tenant — todo escala por la cadena `patient → clinic`. El frontend se integra como nuevas tabs en `PatientDetailPage.tsx` y componentes independientes (odontograma SVG, galería de imágenes, visor).

## Architecture Decisions

### Decision: App `dental_records` — monolítica vs fragmentada

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| App única `dental_records` con todos los modelos | Modelos con dependencias cruzadas (e.g., `TreatmentProcedure.appointment`, `PatientImage.tooth_fdi`) resueltas en una sola migración inicial; menos apps que registrar | ✅ |
| Apps separadas por dominio (`odontogram`, `medical_history`, etc.) | Mayor aislamiento pero migraciones con FK circulares y registro de 6 apps en settings | ❌ |

### Decision: Storage de imágenes — django-storages + serve-through-Django

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| django-storages (S3/MinIO) + Django proxy view | Tenant isolation garantizada sin exponer URLs directas de S3; generación de thumbnails on-upload | ✅ |
| Solo S3 con URLs firmadas | Menor carga en Django pero expone storage backend en la URL; difícil revocar acceso por tenant | ❌ |
| FileSystemStorage en docker volume | Simple pero no escala horizontalmente; migrar a S3 después requiere data migration | ❌ (dev only) |

### Decision: Materialización vía `post_save` vs `pre_save` vs Celery

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `post_save` signal en `DentalRecordEntry` → update `Tooth`/`ToothSurface` inline | Sincrónico, instantáneo, sin cola de mensajes; operación trivial (1 write por surface) | ✅ |
| Celery task | Menor impacto en request pero introduce latencia y complejidad para operación O(1) | ❌ |
| `pre_save` + computed property | No hay materialización real; cada GET odontograma requeriría agregación desde DentalRecordEntry | ❌ |

### Decision: MedicalHistory versionado — upsert con toggle

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| PUT → desactiva `is_active` en anterior, crea nueva instancia | Sigue el patrón de "event sourcing ligero"; `version` auto-incrementada por paciente | ✅ |
| Misma instancia con `updated_at` | Pierde histórico de cambios; NOM-004 requiere trazabilidad | ❌ |

### Decision: SVG Odontograma — render nativo vs librería

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| SVG nativo con `<polygon>` por superficie + React state | 0 dependencias; control total sobre geometría (5 polígonos/diente); colores y tooltips nativos SVG | ✅ |
| Librería (rough.js, D3.js, konva) | Overhead de dependencia; geometría dental es simple (rectángulos + triángulos) | ❌ |

### Decision: DentalRecordEntry — idempotencia en POST

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Validation: si existe tooth+surface+condition, retornar 200 en vez de crear duplicado | Evita entradas duplicadas en UI (click doble); semántica REST discutible pero pragmática | ✅ |
| Siempre crear nuevo entry | Audit trail perfecto pero duplicados por UX | ❌ |

### Decision: Imágenes — extra field `file_size` y dimensiones

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Calcular y persistir metadatos (dimensiones, tamaño, formato) en `PatientImage` | Útil para UI sin leer el blob; evita lecturas de S3 solo para mostrar preview | ✅ |
| Solo almacenar referencia de archivo | Metadatos disponibles vía `storage.url()` pero requiere HEAD request a S3 | ❌ |

## Data Flow

### Odontograma Write Path

```
User click surface ──→ Modal: select condition + notes ──→ POST /patients/{id}/dental-records/
                                                              │
                                                    DentalRecordEntry.objects.create(...)
                                                              │
                                              post_save signal ──→ ToothSurface.objects.update_or_create(...)
                                                                      │
                                                              Tooth.current_condition = latest_condition
```

### Odontograma Read Path

```
GET /patients/{id}/odontogram/ ──→ Tooth + ToothSurface prefetched
                                       │
                                 Response: { teeth: [{ fdi: 11, surfaces: [{ name: "mesial", condition: "healthy" }] }] }
                                       │
                                 OdontogramSVG.tsx ──→ re-render con colores por condición
```

### Image Upload Flow

```
Multipart POST /patients/{id}/images/ ──→ DRF FileUploadParser
                                              │
                                        Validar: size < 20MB, type in (JPEG, PNG, PDF)
                                              │
                                        Pillow: generate thumbnail (256x256 max)
                                              │
                                        django-storages: save original + thumbnail
                                              │
                                        PatientImage.objects.create(...)
                                              │
                                        Response 201: { id, thumbnail_url, original_url }
```

### Tenant Isolation Chain

```
Patient ──→ clinic (FK) ──→ RLS scope
  ├── DentalRecordEntry ──→ patient (FK) ──→ clinic
  ├── MedicalHistory ──→ patient (FK) ──→ clinic
  ├── VitalSigns ──→ patient (FK) ──→ clinic
  ├── PatientImage ──→ patient (FK) ──→ clinic
  ├── Tooth ──→ patient (FK) ──→ clinic
  └── TreatmentPlan ──→ patient (FK) ──→ clinic
       └── TreatmentPhase ──→ plan ──→ patient ──→ clinic
            └── TreatmentProcedure ──→ phase ──→ patient ──→ clinic
```

## Data Model Design

### dental_records/models.py

```python
# ---------------------------------------------------------------------------
# FDI Validator Helper
# ---------------------------------------------------------------------------
VALID_FDI_CODES = set(range(11,19)) | set(range(21,29)) | set(range(31,39)) | \
                  set(range(41,49)) | set(range(51,56)) | set(range(61,66)) | \
                  set(range(71,76)) | set(range(81,86))

SURFACE_CHOICES = [
    ('mesial', 'Mesial'),
    ('distal', 'Distal'),
    ('buccal', 'Buccal'),
    ('lingual', 'Lingual'),
    ('occlusal', 'Occlusal'),  # only for permanent
]

CONDITION_CHOICES = [
    ('healthy', 'Sano'),
    ('caries', 'Caries'),
    ('filling', 'Obturación'),
    ('crown', 'Corona'),
    ('bridge', 'Puente'),
    ('missing', 'Ausente'),
    ('implant', 'Implante'),
    ('root_canal', 'Endodoncia'),
    ('other', 'Otro'),
]

def validate_fdi(value):
    if value not in VALID_FDI_CODES:
        raise ValidationError(f"{value} no es un código FDI válido.")

# ---------------------------------------------------------------------------
# 1. DentalRecordEntry (append-only)
# ---------------------------------------------------------------------------
class DentalRecordEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='dental_records')
    tooth_fdi = models.IntegerField(validators=[validate_fdi])
    surface = models.CharField(max_length=20, choices=SURFACE_CHOICES)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dental_record_entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'tooth_fdi'], name='idx_dre_patient_tooth'),
            models.Index(fields=['patient', 'created_at'], name='idx_dre_patient_date'),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding is False:
            raise ValidationError("DentalRecordEntry is append-only. Updates are not allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("DentalRecordEntry is append-only. Deletion is not allowed.")

# ---------------------------------------------------------------------------
# 2. Tooth (materialized)
# ---------------------------------------------------------------------------
class Tooth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='teeth')
    tooth_fdi = models.IntegerField(validators=[validate_fdi])
    current_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES,
                                         default='healthy')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teeth'
        constraints = [
            models.UniqueConstraint(fields=['patient', 'tooth_fdi'],
                                    name='uq_tooth_patient_fdi'),
        ]
        indexes = [
            models.Index(fields=['patient', 'tooth_fdi'], name='idx_tooth_patient_fdi'),
        ]

# ---------------------------------------------------------------------------
# 3. ToothSurface (materialized)
# ---------------------------------------------------------------------------
class ToothSurface(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tooth = models.ForeignKey(Tooth, on_delete=models.CASCADE, related_name='surfaces')
    surface = models.CharField(max_length=20, choices=SURFACE_CHOICES)
    current_condition = models.CharField(max_length=20, choices=CONDITION_CHOICES,
                                         default='healthy')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tooth_surfaces'
        constraints = [
            models.UniqueConstraint(fields=['tooth', 'surface'],
                                    name='uq_tooth_surface'),
        ]
        indexes = [
            models.Index(fields=['tooth', 'surface'], name='idx_tooth_surface'),
        ]

# ---------------------------------------------------------------------------
# 4. MedicalHistory
# ---------------------------------------------------------------------------
class MedicalHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='medical_histories')
    antecedentes_patologicos = models.TextField(blank=True, default='')
    antecedentes_quirurgicos = models.TextField(blank=True, default='')
    antecedentes_alergicos = models.TextField(blank=True, default='')
    antecedentes_farmacologicos = models.TextField(blank=True, default='')
    antecedentes_familiares = models.TextField(blank=True, default='')
    motivo_consulta = models.TextField(blank=True, default='')
    enfermedad_actual = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'medical_histories'
        ordering = ['-version']
        indexes = [
            models.Index(fields=['patient', 'is_active'], name='idx_mh_patient_active'),
            models.Index(fields=['patient', 'version'], name='idx_mh_patient_version'),
        ]

# ---------------------------------------------------------------------------
# 5. VitalSigns
# ---------------------------------------------------------------------------
class VitalSigns(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='vital_signs')
    appointment = models.ForeignKey('appointments.Appointment',
                                    on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='vital_signs')
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    recorded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'vital_signs'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['patient', 'recorded_at'], name='idx_vs_patient_date'),
            models.Index(fields=['appointment'], name='idx_vs_appointment'),
        ]

# ---------------------------------------------------------------------------
# 6. PatientImage
# ---------------------------------------------------------------------------
class PatientImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ('photo', 'Foto intraoral'),
        ('xray_periapical', 'Radiografía periapical'),
        ('xray_panoramic', 'Radiografía panorámica'),
        ('xray_cephalometric', 'Radiografía cefalométrica'),
        ('document', 'Documento'),
        ('other', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='images')
    tooth_fdi = models.IntegerField(null=True, blank=True, validators=[validate_fdi])
    image_type = models.CharField(max_length=30, choices=IMAGE_TYPE_CHOICES)
    original_file = models.ImageField(upload_to=image_upload_path)
    thumbnail = models.ImageField(upload_to=image_upload_path, null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True,
                                            help_text="File size in bytes")
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'patient_images'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['patient', 'uploaded_at'], name='idx_img_patient_date'),
            models.Index(fields=['patient', 'tooth_fdi'], name='idx_img_tooth'),
            models.Index(fields=['patient', 'image_type'], name='idx_img_type'),
        ]

def image_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    uuid_name = uuid.uuid4().hex
    return f'patients/{instance.patient_id}/images/{instance.image_type}/{uuid_name}.{ext}'

# ---------------------------------------------------------------------------
# 7. TreatmentPlan
# ---------------------------------------------------------------------------
class TreatmentPlan(models.Model):
    PLAN_STATUS = [
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE,
                                related_name='treatment_plans')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=PLAN_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'treatment_plans'
        ordering = ['-created_at']

class TreatmentPhase(models.Model):
    PHASE_STATUS = [
        ('pending', 'Pendiente'),
        ('in_progress', 'En progreso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(TreatmentPlan, on_delete=models.CASCADE,
                             related_name='phases')
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField()
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=PHASE_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'treatment_phases'
        ordering = ['order']
        indexes = [
            models.Index(fields=['plan', 'order'], name='idx_tp_plan_order'),
        ]

class TreatmentProcedure(models.Model):
    PROC_STATUS = [
        ('planned', 'Planeado'),
        ('in_progress', 'En progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phase = models.ForeignKey(TreatmentPhase, on_delete=models.CASCADE,
                              related_name='procedures')
    appointment = models.ForeignKey('appointments.Appointment',
                                    on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='treatment_procedures')
    tooth_fdi = models.IntegerField(null=True, blank=True, validators=[validate_fdi])
    description = models.TextField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROC_STATUS, default='planned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'treatment_procedures'
        indexes = [
            models.Index(fields=['phase', 'status'], name='idx_tproc_phase_status'),
            models.Index(fields=['appointment'], name='idx_tproc_appointment'),
        ]
```

### Migration Ordering Strategy

```
Migration dependencies (guaranteeing correct FK resolution):

dental_records.0001_initial:
  - depends on: patients.XXXX_XXXX (whichever migration adds ClinicalNote tooth_fdi/surface)
  - requires: patients.Patient, appointments.Appointment, accounts.User to exist

patients.XXXX_add_clinical_note_dental_fields:
  - adds tooth_fdi + surface to ClinicalNote
  - this runs BEFORE dental_records.0001_initial because the spec says "extend ClinicalNote first"

Sequence:
1. patients: add tooth_fdi, surface to ClinicalNote (nullable)
2. dental_records: create all new models (DentalRecordEntry, Tooth, ToothSurface,
   MedicalHistory, VitalSigns, PatientImage, TreatmentPlan, TreatmentPhase,
   TreatmentProcedure)
```

## API Design

### Full Endpoint List

| Method | Endpoint | ViewSet | Serializer | Permission |
|--------|----------|---------|------------|------------|
| GET | `/api/v1/patients/{id}/odontogram/` | OdontogramViewSet (retrieve) | OdontogramSerializer | IsAuthenticated + `view_patient` |
| GET | `/api/v1/patients/{id}/dental-records/` | DentalRecordEntryViewSet (list) | DentalRecordEntrySerializer | IsAuthenticated |
| POST | `/api/v1/patients/{id}/dental-records/` | DentalRecordEntryViewSet (create) | DentalRecordEntryCreateSerializer | IsDentist |
| GET | `/api/v1/patients/{id}/medical-history/` | MedicalHistoryViewSet (retrieve_active) | MedicalHistorySerializer | IsAuthenticated |
| PUT | `/api/v1/patients/{id}/medical-history/` | MedicalHistoryViewSet (upsert) | MedicalHistoryUpsertSerializer | IsDentist |
| GET | `/api/v1/patients/{id}/medical-history/history/` | MedicalHistoryViewSet (list_versions) | MedicalHistorySerializer | IsAuthenticated |
| GET | `/api/v1/patients/{id}/vital-signs/` | VitalSignsViewSet (list) | VitalSignsSerializer | IsAuthenticated |
| POST | `/api/v1/patients/{id}/vital-signs/` | VitalSignsViewSet (create) | VitalSignsCreateSerializer | IsDentist |
| GET | `/api/v1/patients/{id}/vital-signs/{pk}/` | VitalSignsViewSet (retrieve) | VitalSignsSerializer | IsAuthenticated |
| GET | `/api/v1/appointments/{id}/vital-signs/` | VitalSignsViewSet (by_appointment) | VitalSignsSerializer | IsAuthenticated |
| POST | `/api/v1/patients/{id}/images/` | PatientImageViewSet (create) | PatientImageCreateSerializer | IsDentist |
| GET | `/api/v1/patients/{id}/images/` | PatientImageViewSet (list) | PatientImageListSerializer | IsAuthenticated |
| GET | `/api/v1/patients/{id}/images/{pk}/` | PatientImageViewSet (retrieve) | PatientImageSerializer | IsAuthenticated |
| GET | `/api/v1/patients/{id}/images/{pk}/file/` | PatientImageViewSet (serve_file) | — | IsAuthenticated |
| GET | `/api/v1/patients/{id}/images/{pk}/thumbnail/` | PatientImageViewSet (serve_thumbnail) | — | IsAuthenticated |
| DELETE | `/api/v1/patients/{id}/images/{pk}/` | PatientImageViewSet (destroy) | — | IsClinicAdmin |
| GET | `/api/v1/patients/{id}/treatment-plans/` | TreatmentPlanViewSet (list) | TreatmentPlanListSerializer | IsAuthenticated |
| POST | `/api/v1/patients/{id}/treatment-plans/` | TreatmentPlanViewSet (create) | TreatmentPlanCreateSerializer | IsDentist |
| GET | `/api/v1/patients/{id}/treatment-plans/{pk}/` | TreatmentPlanViewSet (retrieve) | TreatmentPlanDetailSerializer | IsAuthenticated |
| PUT/PATCH | `/api/v1/patients/{id}/treatment-plans/{pk}/` | TreatmentPlanViewSet (update) | TreatmentPlanCreateSerializer | IsDentist |
| DELETE | `/api/v1/patients/{id}/treatment-plans/{pk}/` | TreatmentPlanViewSet (destroy) | — | IsDentist |
| POST | `/api/v1/patients/{id}/treatment-plans/{plan_pk}/phases/` | TreatmentPhaseViewSet (create) | TreatmentPhaseSerializer | IsDentist |
| PUT/PATCH | `/api/v1/patients/{id}/.../phases/{pk}/` | TreatmentPhaseViewSet (update) | TreatmentPhaseSerializer | IsDentist |
| DELETE | `/api/v1/patients/{id}/.../phases/{pk}/` | TreatmentPhaseViewSet (destroy) | — | IsDentist |
| POST | `/api/v1/patients/{id}/.../phases/{phase_pk}/procedures/` | TreatmentProcedureViewSet (create) | TreatmentProcedureSerializer | IsDentist |
| PUT/PATCH | `/api/v1/patients/{id}/.../phases/{phase_pk}/procedures/{pk}/` | TreatmentProcedureViewSet (update) | TreatmentProcedureSerializer | IsDentist |
| DELETE | `/api/v1/patients/{id}/.../phases/{phase_pk}/procedures/{pk}/` | TreatmentProcedureViewSet (destroy) | — | IsDentist |

### Image Upload Specifics

- **Parser**: `MultiPartParser` (DRF default, not FileUploadParser — we want metadata + file in same request)
- **Validation**: DRF Serializer validates `file` field with:
  - `FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])`
  - Custom size validator: `validate_file_size(value)` → raise if `value.size > 20*1024*1024`
- **Thumbnail generation**: In serializer `create()` or a separate service:
  ```python
  def generate_thumbnail(image_file, max_size=(256, 256)):
      if image_file.content_type == 'application/pdf':
          return None  # No thumbnail for PDFs
      from PIL import Image
      from io import BytesIO
      img = Image.open(image_file)
      img.thumbnail(max_size, Image.Lanczos)
      thumb_io = BytesIO()
      img.save(thumb_io, format='JPEG', quality=85)
      return InMemoryUploadedFile(thumb_io, None, 'thumb.jpg', 'image/jpeg',
                                  thumb_io.tell(), None)
  ```
- **Image serving endpoint**: `serve_file` action reads `self.get_object()`, opens `obj.original_file`, returns `FileResponse` with content-type sniffing. Tenant check already done via `get_object()` (queryset filtered by `patient__clinic` via RLS).

## Frontend Architecture

### Component Tree

```
PatientDetailPage.tsx (modified)
├── TabsList (expanded)
│   ├── Información (existing)
│   ├── Notas Clínicas (existing)
│   ├── Consentimientos (existing)
│   ├── Auditoría (existing)
│   ├── Odontograma (NEW)
│   │   └── OdontogramTab.tsx
│   │       ├── OdontogramSVG.tsx (NEW)
│   │       ├── SurfaceConditionModal.tsx (NEW)
│   │       └── LegendPanel.tsx (NEW)
│   ├── Historia Médica (NEW)
│   │   └── MedicalHistoryTab.tsx
│   │       └── MedicalHistoryForm.tsx
│   ├── Signos Vitales (NEW)
│   │   └── VitalSignsTab.tsx
│   │       ├── VitalSignsForm.tsx
│   │       └── VitalSignsHistory.tsx
│   ├── Imágenes (NEW)
│   │   └── PatientImagesTab.tsx
│   │       ├── ImageGallery.tsx
│   │       ├── ImageUploader.tsx (drag & drop)
│   │       └── ImageViewer.tsx (modal, keyboard nav)
│   └── Plan de Tratamiento (NEW)
│       └── TreatmentPlanTab.tsx
│           ├── TreatmentPlanList.tsx
│           ├── TreatmentPlanDetail.tsx
│           │   ├── PhaseList.tsx
│           │   └── ProcedureList.tsx
│           └── TreatmentPlanForm.tsx
```

### State Management

- **Server state**: React Query (tanstack-query) for all API calls — same pattern as existing `useClinicalNotes`, `usePatients`, etc.
- **Global state**: Only `authStore.ts` (Zustand) for user/clinic context — no new global stores needed
- **Odontogram local state**: Component-level state for:
  - `selectedTooth: number | null`
  - `selectedSurface: string | null`
  - `modalOpen: boolean`
  - Colors computed from API response (not stored in state — derived from data)
- **Image gallery state**: React Query with `keepPreviousData` for pagination; local state for:
  - `viewerImage: PatientImage | null` (modal)
- **Filter state**: React Query query params via URL search params or local state

### SVG Odontogram Architecture

```
OdontogramSVG.tsx
├── <svg viewBox="0 0 800 500">
│   ├── <g id="maxillary-arch">     (upper teeth 11-18, 21-28, 51-55, 61-65)
│   │   ├── <g id="tooth-11">       (one <g> per tooth)
│   │   │   ├── <polygon id="s-mesial" />
│   │   │   ├── <polygon id="s-distal" />
│   │   │   ├── <polygon id="s-buccal" />
│   │   │   ├── <polygon id="s-lingual" />
│   │   │   └── <polygon id="s-occlusal" />
│   │   ├── <text>11</text>          (FDI label)
│   │   └── ...
│   ├── <g id="mandibular-arch">    (lower teeth 31-38, 41-48, 71-75, 81-85)
│   │   └── ...
│   └── <g id="legend" />
```

**Geometry approach**: Cada diente permanente mide ~24×32px en el SVG. Las 5 superficies se representan como:
- **Oclusal**: rectángulo central horizontal (8×16px)
- **Mesial/Distal**: rectángulos verticales izquierdo/derecho (8×24px)
- **Buccal/Lingual**: rectángulos horizontales superior/inferior (24×8px)

Dientes primarios: mismas 4 superficies (excluyendo oclusal) pero más pequeños (~18×24px).

**Interaction model**:
```typescript
// Each polygon gets:
onClick={() => onSurfaceClick(toothFdi, surfaceName)}
onMouseEnter={() => setHovered(toothFdi, surfaceName)}
onMouseLeave={() => setHovered(null)}

// Color mapping from API response
const conditionColors: Record<string, string> = {
  healthy: '#E8F5E9',    // light green
  caries: '#FFCDD2',     // light red
  filling: '#BBDEFB',    // light blue
  crown: '#FFF9C4',      // light yellow
  bridge: '#D1C4E9',     // light purple
  missing: '#BDBDBD',    // gray
  implant: '#C8E6C9',    // green
  root_canal: '#FFE0B2', // orange
  other: '#F5F5F5',      // light gray
}
```

### Image Viewer/Gallery Approach

- **Gallery**: CSS Grid (3-4 columns), thumbnail previews, filter chips by `image_type`
- **ImageViewer**: Modal overlay with:
  - `<img>` with original image (served via Django proxy endpoint)
  - Keyboard navigation (← → for prev/next)
  - Zoom via CSS `transform: scale()` + mouse position tracking
  - Metadata panel (type, tooth, date, uploader)
  - Delete button (admin only)

## Storage Strategy

### django-storages Configuration

```python
# base.py — default config (local dev)
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
THUMBNAIL_STORAGE = 'django.core.files.storage.FileSystemStorage'

# dev.py / docker.py — local overrides
MEDIA_ROOT = BASE_DIR / 'media'

# production.py — S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', '')
AWS_DEFAULT_ACL = 'private'  # CRITICAL: no public access
AWS_QUERYSTRING_AUTH = False  # We serve via Django proxy, not signed S3 URLs
AWS_S3_FILE_OVERWRITE = False
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
```

### File Path Convention

```
patients/{patient_id}/images/{image_type}/{uuid}.{ext}
patients/{patient_id}/images/thumbnails/{image_type}/{uuid}.{ext}
```

Example: `patients/a1b2c3d4/images/xray_periapical/abc123def456.jpg`

### Thumbnail Generation

- **Approach**: Pillow inline in serializer `create()`, no sorl-thumbnail dependency (avoids cache backend and template tag complexity)
- **Max size**: 256×256px, preserving aspect ratio
- **Format**: JPEG, quality 85
- **Storage path**: Same base as original but under `thumbnails/` subdirectory
- **PDF handling**: No thumbnail — serve a PDF icon placeholder on frontend

### Dev vs Production

| Aspect | Dev | Production |
|--------|-----|------------|
| Backend | `FileSystemStorage` | `S3Boto3Storage` |
| Path | `media/patients/...` | S3 bucket `patients/...` |
| Thumbnails | Same storage, `thumbnails/` prefix | Same bucket, `thumbnails/` prefix |
| Serving | Django dev server `/media/` | Django proxy view (reads from S3, streams response) |
| Docker volume | `./backend/media/` mounted | N/A (S3) |

## Tenant Isolation

Todos los nuevos modelos escalan la isolación de tenant a través de la cadena `patient → clinic`. No hay FK directo a `Clinic` en ningún modelo de `dental_records`. La isolación se logra vía:

1. **PostgreSQL RLS**: El `TenantMiddleware` ya setea `app.current_clinic_id`. Cualquier query que cruce pacientes de otra clínica es bloqueada por RLS.
2. **QuerySet scoping**: Todas las ViewSets filtran por `patient_id` del URL (que a su vez pasa por `PatientViewSet` auth check). Ejemplo:
   ```python
   def get_queryset(self):
       return DentalRecordEntry.objects.filter(patient_id=self.kwargs['patient_id'])
   ```
3. **Image serving**: El endpoint `serve_file` abre el archivo SOLO después de verificar que la imagen pertenece al paciente, y el paciente a la clínica del usuario autenticado. No se exponen URLs directas de S3.
4. **404 vs 403**: Para evitar disclosure de existencia, endpoints devuelven 404 si el paciente no pertenece a la clínica del usuario (mismo patrón que las views existentes).

## Signal Design

### DentalRecordEntry post_save → Tooth/ToothSurface

```python
# dental_records/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from dental_records.models import DentalRecordEntry, Tooth, ToothSurface

logger = logging.getLogger(__name__)


@receiver(post_save, sender=DentalRecordEntry)
def materialize_tooth_state(sender, instance, created, **kwargs):
    """
    On every DentalRecordEntry creation, update the materialized
    Tooth and ToothSurface for the affected tooth.

    Performance: This is a single update_or_create per surface (O(1)).
    No aggregation queries — the entry IS the latest state.
    """
    if not created:
        return  # Append-only, but guard defensively

    # 1. Upsert Tooth
    tooth, _ = Tooth.objects.update_or_create(
        patient=instance.patient,
        tooth_fdi=instance.tooth_fdi,
        defaults={'current_condition': instance.condition},
    )

    # 2. Upsert ToothSurface
    ToothSurface.objects.update_or_create(
        tooth=tooth,
        surface=instance.surface,
        defaults={'current_condition': instance.condition},
    )

    logger.debug(
        "Materialized tooth %d surface %s → %s for patient %s",
        instance.tooth_fdi,
        instance.surface,
        instance.condition,
        instance.patient_id,
    )
```

**Performance considerations**:
- Cada POST crea 1 `DentalRecordEntry` + 1 `update_or_create` en `Tooth` + 1 `update_or_create` en `ToothSurface` = 3 queries total
- No hay agregación ni recomputación — el último entry ES el estado actual
- `update_or_create` con `defaults` no dispara señales adicionales
- Para odontograma inicial con 32 dientes × 5 superficies = 160 entries, son ~480 queries en un PUT batch — trivial para PostgreSQL

### App Registration

```python
# dental_records/apps.py
class DentalRecordsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dental_records'
    verbose_name = 'Dental Records (Odontograma / Historia Clínica)'

    def ready(self):
        import dental_records.signals  # noqa: F401
```

## Testing Strategy

### Backend Tests

| Layer | Capability | What to Test | Approach |
|-------|-----------|-------------|----------|
| Unit | Odontogram | FDI validation (valid codes pass, invalid codes 400) | Pytest parametrize con 10+ FDI codes |
| Unit | Odontogram | Append-only enforcement (save/delete raise ValidationError) | Direct model call |
| Unit | Odontogram | Signal materialization (create entry → Tooth/ToothSurface updated) | Signal.assert_has_call or direct query |
| Unit | Odontogram | Surface count per tooth type (perm=5, primary=4) | Model clean/validation |
| Integration | Odontogram | POST entry + GET odontogram reflects new state | DRF APIClient |
| Unit | MedicalHistory | Versión incrementa correctamente en upsert | Direct model create sequence |
| Integration | MedicalHistory | PUT crea nueva versión, GET retorna active, GET /history/ lista todas | DRF APIClient |
| Unit | VitalSigns | BP validation (systolic > diastolic, physiological ranges) | Serializer validation tests |
| Integration | VitalSigns | CRUD, date range filtering, appointment link | DRF APIClient |
| Unit | PatientImage | File size rejection (>20MB → 413) | SimpleUploadedFile + 21MB |
| Unit | PatientImage | File type rejection (non-image/pdf → 400) | SimpleUploadedFile with text/plain |
| Integration | PatientImage | Upload → thumbnail generated + metadata persisted | APIClient + Pillow open |
| Integration | PatientImage | `serve_file` returns 404 for cross-clinic | Two-clinic fixture + auth_headers |
| Integration | TreatmentPlan | Cascading delete plan → phases → procedures | APIClient, assert 204 + DoesNotExist |
| Integration | Tenant isolation | All endpoints return 404 for cross-clinic patient | `two_clinics` fixture pattern |
| Integration | ClinicalNote | `tooth_fdi`/`surface` accepted in POST/PUT, optional | Existing note test con nuevos campos |

### Frontend Tests

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | OdontogramSVG renders 52 teeth | Shallow render + count `<g>` tooth groups |
| Unit | OdontogramSVG colors by condition | Mock data with known conditions, assert fill colors |
| Unit | SurfaceConditionModal opens on click | fireEvent.click on polygon, assert modal visible |
| Unit | PatientImages filter by type | Mock API response, assert rendered images filtered |
| Unit | ImageViewer keyboard navigation | fireEvent.keyDown(ArrowRight), assert next image |
| Integration | Tab renders with data | Mock React Query, assert tab content renders |
| Integration | Upload flow (drag & drop + submit) | Mock `patientsApi.createImage()`, assert success |

### Image Upload Test Pattern

```python
# Backend test
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

def _create_test_image(width=800, height=600, format='JPEG'):
    """Create a minimal test image in memory."""
    img = Image.new('RGB', (width, height), color='red')
    buf = BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return SimpleUploadedFile(
        name=f'test.{format.lower()}',
        content=buf.read(),
        content_type=f'image/{format.lower()}'
    )

def test_upload_image_generates_thumbnail(auth_client, patient):
    image = _create_test_image()
    response = auth_client.post(
        f'/api/v1/patients/{patient.id}/images/',
        {'original_file': image, 'image_type': 'photo'},
        format='multipart',
    )
    assert response.status_code == 201
    assert response.data['thumbnail'] is not None
    # Verify thumbnail file exists
    from django.core.files.storage import default_storage
    assert default_storage.exists(response.data['thumbnail'])
```

## Migration / Rollout

1. **Migration 1**: `patients` app — add `tooth_fdi` + `surface` fields to `ClinicalNote` (nullable)
2. **Migration 2**: `dental_records` initial migration — all 12 models
3. **Rollback**: `migrate dental_records zero`, revert patients migration, remove from LOCAL_APPS
4. **No data migration**: All new fields are nullable, no backfill needed
5. **Feature flag**: No flag needed — endpoints are additive; existing UI unchanged

## Open Questions

- None — todos los detalles están resueltos en specs y código base existente.
