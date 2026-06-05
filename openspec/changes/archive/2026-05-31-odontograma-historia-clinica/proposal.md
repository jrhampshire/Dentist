# Proposal: Odontograma / Historia Clínica (Fase A)

## Intent

Cumplir con NOM-004-SSA3-2012 agregando el odontograma FDI interactivo y la historia clínica expandida al expediente digital. El expediente actual tiene `Patient` con datos básicos y `ClinicalNote`, pero carece de la representación gráfica del estado bucal, historial médico completo, signos vitales, y plan de tratamiento — elementos obligatorios para la normativa mexicana.

## Scope

### In Scope
- Odontograma FDI interactivo (dientes 11–48, 51–85) con 5 superficies por diente, basado en SVG nativo
- Historia Médica expandida — modelo `MedicalHistory` con antecedentes patológicos, quirúrgicos, alérgicos, farmacológicos y familiares
- Signos Vitales — modelo `VitalSigns` con presión arterial, frecuencia cardíaca, temperatura, peso y talla
- Imágenes / Radiografías — modelo `PatientImage` con carga de archivos (fotos intraorales, radiografías, documentación), vinculación opcional a diente específico y tipo de imagen
- Extensión de `ClinicalNote` — campos `tooth_fdi` y `surface` opcionales para referenciar dientes
- Plan de Tratamiento básico — `TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure` con vinculación a `Appointment`
- Estados materializados (`Tooth`, `ToothSurface`) actualizados vía señales desde `DentalRecordEntry`
- Append-only en `DentalRecordEntry` (sin update/delete)
- Nueva app Django `dental_records`

### Out of Scope
- Recetas digitales / Prescripciones (Fase B)
- Vinculación con facturación / `InvoiceItem` (requiere refactor separado)

## Capabilities

### New Capabilities
- `dental-odontogram`: Interactive FDI teeth chart (SVG) with surface-level condition recording and append-only audit trail
- `medical-history`: Expanded medical history with typed antecedents (pathological, surgical, allergic, pharmacological, familial)
- `vital-signs`: Vital signs recording per patient, optionally linked to appointments
- `treatment-plan`: Multi-phase treatment plans with procedures linked to appointments
- `patient-images`: Image upload (photos, X-rays) with tooth-level linking and image type classification
- `clinical-note-extension`: Optional tooth/surface reference fields on ClinicalNote

### Modified Capabilities
None — no existing spec changes at the capability level.

## Approach

Nueva app Django `dental_records` con modelos relacionales. `DentalRecordEntry` como tabla de eventos append-only. `Tooth` y `ToothSurface` como tablas materializadas del estado actual, actualizadas mediante `django.db.models.signals.post_save`. Odontograma renderizado con SVG nativo en el frontend (dos arcos, 32 dientes permanentes + 20 primarios, 5 polígonos de superficie por diente). Vista anidada bajo `patients/` en el frontend como nueva tab en `PatientDetailPage`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/dental_records/` | New | App con modelos, serializers, views, urls, signals |
| `backend/config/settings/base.py` | Modified | Registrar `dental_records` en LOCAL_APPS |
| `backend/patients/models.py` | Modified | Agregar `tooth_fdi`, `surface` a `ClinicalNote` |
| `backend/patients/views.py` | Modified | Nuevos endpoints anidados si no se mueven a dental_records |
| `backend/appointments/models.py` | Minor | FK opcional de `TreatmentProcedure` a `Appointment` |
| `frontend/src/pages/Patients/PatientDetailPage.tsx` | Modified | Nuevas tabs (Odontograma, Historia Médica, Plan Tx) |
| `frontend/src/components/odontogram/OdontogramSVG.tsx` | New | Componente SVG del odontograma interactivo |
| `backend/config/settings/base.py` | Modified | Config de almacenamiento (S3/MinIO/local) para imágenes |
| `backend/dental_records/models.py` | New | Modelo `PatientImage` con archivo, tipo, diente opcional, metadata |
| `backend/dental_records/views.py` | New | Endpoint upload + serve de imágenes (con autenticación y tenant isolation) |
| `frontend/src/components/patients/PatientImages.tsx` | New | Galería de imágenes con upload, zoom, filtro por tipo/diente |
| `frontend/src/components/patients/ImageViewer.tsx` | New | Visor modal con navegación entre imágenes |
| `docker-compose.yml` | Modified | Volumen para archivos subidos (media/) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tamaño del cambio ~1400–2100 líneas | High | Entregar en PRs encadenados por subsistema |
| Complejidad geométrica del SVG dental | Medium | Usar formas simplificadas (rectángulos + triángulos) no realistas |
| Migraciones entre apps (orden de dependencias) | Low | Crear `dental_records` migraciones iniciales con dependencias explícitas a `patients`, `appointments` |
| Performance del odontograma (materializar 32×5 estados) | Low | Señales post-save mantienen `Tooth`/`ToothSurface` actualizados; sin necesidad de recomputación |
| Almacenamiento de imágenes (tamaño, backups, S3 vs local) | Medium | Usar django-storages con backend configurable; thumbnails automáticos vía sorl-thumbnail o similar |

## Rollback Plan

1. `git revert` los commits del PR encadenado correspondiente
2. Ejecutar `python manage.py migrate dental_records zero` para revertir migraciones
3. Remover `dental_records` de `LOCAL_APPS` en settings
4. Revertir cambios a `ClinicalNote` y `Appointment` (nullable FK, no hay pérdida de datos existentes)

## Dependencies

- Django 5 + DRF (existente)
- PostgreSQL 16 (existente)
- React 18 + TypeScript + Tailwind + Shadcn/ui (existente)
- Ninguna dependencia externa nueva

## Success Criteria

- [ ] Odontograma renderiza 52 dientes (32 permanentes + 20 primarios) con 5 superficies cliqueables cada uno
- [ ] Click en superficie abre modal y crea `DentalRecordEntry` persistido
- [ ] `MedicalHistory` permite registrar antecedentes de 5 tipos y listarlos por paciente
- [ ] `VitalSigns` registra y muestra presión arterial, frecuencia cardíaca, temperatura, peso y talla
- [ ] `TreatmentPlan` permite crear plan con fases y procedimientos vinculados a citas
- [ ] `ClinicalNote` existente acepta `tooth_fdi`/`surface` opcionales sin romper notas previas
- [ ] `PatientImage` permite subir y visualizar fotos y radiografías vinculadas a paciente y opcionalmente a diente
- [ ] Imágenes se sirven con autenticación y respetan tenant isolation
- [ ] Todas las migraciones corren sin conflictos entre apps
