## Exploration: Odontograma / Historia Clínica Completa (NOM-004-SSA3-2012)

### Current State

The **Expediente Clínico Digital** (cambio `expediente-clinico`) ya está implementado en su **Slice A**: `PatientDetailPage` con tabs (Info, Notas Clínicas, Consentimientos, Auditoría), `ClinicalNote` con firma e inmutabilidad, `PatientConsent`, y export de expediente.

**Lo que EXISTE y se puede reutilizar:**
- `Patient` con datos básicos, contacto, alergias, condiciones crónicas y medicamentos (encriptados).
- `ClinicalNote` con tipos `evolution|diagnosis|treatment|observation|consent`, firma SHA-256, e inmutabilidad.
- `Appointment` con tipos, flujo de estados, y `inventory_kit`.
- `Invoice` con `concepts` JSONB, estados CFDI, y FK a `Appointment`.
- Frontend: tabs funcionales, hooks con React Query, API client centralizado.
- Tenant isolation: `clinic` FK + RLS en todos los modelos.
- `AuditLog` append-only para trazabilidad NOM-024.

**Lo que NO EXISTE (gap para NOM-004):**
- Odontograma interactivo (gráfica dental FDI 11–48 / 51–85).
- Historia médica completa: antecedentes patológicos, quirúrgicos, alérgicos, farmacológicos, familiares (más allá de los 3 campos encriptados de `Patient`).
- Historia dental: motivo de consulta, enfermedad actual.
- Signos vitales: presión arterial, frecuencia cardíaca, temperatura, peso, talla.
- Plan de tratamiento multi-visita con fases y procedimientos vinculados a citas.
- Recetas digitales (prescripciones).
- Imágenes / radiografías vinculadas a dientes específicos.
- Modelo relacional de dientes, superficies y condiciones.

### Affected Areas

| Ruta | Por qué se ve afectado |
|------|------------------------|
| `backend/patients/models.py` | Campos de historia médica actual son insuficientes; hay que extender o crear modelos nuevos |
| `backend/patients/views.py` | Nuevos endpoints anidados bajo paciente (historia médica, signos vitales) |
| `backend/patients/serializers.py` | Serializers para los nuevos modelos |
| `backend/patients/urls.py` | Rutas anidadas para historia clínica completa |
| `backend/config/settings/base.py` | Registrar nueva app `dental_records` en `LOCAL_APPS` |
| `backend/invoicing/models.py` | `Invoice.concepts` JSONB puede necesitar FK a procedimientos del plan de tratamiento |
| `frontend/src/pages/Patients/PatientDetailPage.tsx` | Nuevas tabs: Odontograma, Historia Médica, Plan de Tratamiento, Recetas, Imágenes |
| `frontend/src/types/index.ts` | Nuevos tipos: `Tooth`, `ToothSurface`, `MedicalHistory`, `VitalSigns`, `TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure`, `Prescription`, `PatientImage` |
| `frontend/src/api/patients.ts` | Nuevos métodos para los endpoints de historia clínica completa |
| `frontend/src/hooks/` | Nuevos hooks React Query para odontograma, tratamientos, recetas |
| `frontend/src/components/` | **Nuevo**: `OdontogramSVG`, `TreatmentPlanEditor`, `PrescriptionForm`, `ImageGallery` |

### Approaches

#### 1. Extensión monolítica del app `patients`
Agrupar todos los nuevos modelos dentro de `backend/patients/` y extender las vistas/serializers existentes.

- **Pros**: Menos apps que registrar, todo el expediente en un solo lugar, menos imports entre apps.
- **Cons**: `patients/models.py` pasaría de 430 a ~1000+ líneas; viola responsabilidad única; difícil de probar y mantener; acopla historia médica general con lógica dental específica.
- **Esfuerzo**: Medio-Alto.

#### 2. Nueva app `dental_records` + extensión de `patients` (Recomendado)
Crear `backend/dental_records/` con modelos puramente dentales: `Tooth`, `ToothSurface`, `DentalRecordEntry`, `TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure`, `Prescription`, `PatientImage`. Extender `patients` solo para `MedicalHistory` y `VitalSigns` (o también migrarlos a `dental_records` si se prefiere).

- **Pros**: Separación de dominios (datos generales vs. datos dentales), escalable para especialidades futuras (ortodoncia, endodoncia), testing aislado, alinea con Django best practices.
- **Cons**: Más archivos iniciales, imports cruzados (`dental_records` → `patients`, `appointments`, `invoicing`), requiere coordinar migraciones.
- **Esfuerzo**: Alto.

#### 3. JSONB-first (MVP rápido)
Almacenar odontograma, plan de tratamiento e historia médica expandida como campos `JSONField` en `Patient`.

- **Pros**: Implementación inicial muy rápida, pocas migraciones, lectura/escritura atómica del chart completo.
- **Cons**: Imposible consultar relacionalmente (ej. "pacientes con caries en el 36"), sin integridad referencial, auditoría NOM-004 deficiente, migración a modelo relacional posterior es dolorosa y riesgosa.
- **Esfuerzo**: Medio.

### Recommendation

**Approach 2 — app dedicada `dental_records` — implementada en 3 fases entregables:**

1. **Fase A**: Odontograma relacional (`Tooth`, `ToothSurface`, `DentalRecordEntry` para trazabilidad) + Historia Médica expandida (`MedicalHistory`, `VitalSigns`).
2. **Fase B**: Plan de Tratamiento (`TreatmentPlan`, `TreatmentPhase`, `TreatmentProcedure`) con vinculación a citas y costos.
3. **Fase C**: Recetas (`Prescription`) e Imágenes (`PatientImage`) con vinculación a dientes.

**Razones:**
- NOM-004-SSA3-2012 exige **trazabilidad completa** del estado bucal a través del tiempo. Un modelo relacional con eventos (`DentalRecordEntry`) permite reconstruir la evolución de cada diente/superficie.
- El odontograma requiere queries espaciales implícitas (por diente, por superficie). JSONB dificulta esto.
- El dominio dental es lo suficientemente grande y especializado para merecer su propia app.

**Modelo de datos sugerido (resumen):**

```
DentalRecordEntry (evento append-only)
├── patient FK
├── tooth_fdi (11–48, 51–85)
├── surface (M|D|B|L|O|root|null)
├── entry_type: condition | treatment | observation | xray
├── condition: caries | filled | crown | bridge | missing | ...
├── treatment_performed
├── notes
├── appointment FK (nullable)
├── image_url (nullable)
├── created_by, created_at

Tooth (materialized current state, cache)
├── patient FK
├── fdi_number
├── is_primary
├── overall_status
├── notes

ToothSurface (materialized current state, cache)
├── tooth FK
├── surface
├── current_condition
├── current_treatment
├── color_code

TreatmentPlan
├── patient FK
├── status: draft | active | completed | cancelled
├── total_estimated_cost | total_actual_cost

TreatmentPhase
├── plan FK
├── phase_type: diagnosis | emergency | basic | restorative | aesthetic | maintenance
├── order, status, notes

TreatmentProcedure
├── phase FK
├── appointment FK (nullable)
├── procedure_code, description
├── tooth_fdi, surfaces
├── estimated_cost, actual_cost
├── status: planned | in_progress | completed | cancelled

MedicalHistory
├── patient FK
├── history_type: pathological | surgical | allergic | pharmacological | familial
├── description, diagnosed_date, notes

VitalSigns
├── patient FK
├── appointment FK (nullable)
├── blood_pressure_systolic/diastolic, heart_rate, temperature, weight_kg, height_cm
├── recorded_by, recorded_at

Prescription
├── patient FK
├── appointment FK (nullable)
├── medication_name, dosage, frequency, duration, instructions
├── prescribed_by, prescribed_at

PatientImage
├── patient FK
├── image_type: xray | photo | scan | other
├── tooth_fdi (nullable)
├── file_url, thumbnail_url, description
├── uploaded_by, uploaded_at
```

**Frontend — Odontograma:**
- **SVG nativo** (no Canvas, no librerías de terceros). Ventajas: escalable, eventos por diente/superficie individuales, coloración precisa por polígono, accesible.
- Componente `OdontogramSVG` con dos arcos (superior e inferior), 32 dientes permanentes + 20 primarios. Cada diente es un `<g>` con formas base + 5 polígonos de superficie.
- Click en diente/superficie abre modal de registro de condición/tratamiento que crea un `DentalRecordEntry` y refresca el estado materializado.

**Interacción con `ClinicalNote`:**
- Agregar campos opcionales `tooth_fdi` y `surface` a `ClinicalNote` para que las notas de evolución/diagnóstico referencien dientes específicos. Esto mantiene la inmutabilidad del sistema de notas existente sin romper nada.

### Risks

1. **Tamaño del cambio**: Es un feature grande (~800–1200 líneas backend + ~600–900 frontend). Excede el presupuesto de 400 líneas por PR. Debe dividirse en fases o PRs encadenados.
2. **Complejidad del SVG**: El componente odontograma es el mayor riesgo de UI. Requiere geometría dental simplificada pero funcional. Si el SVG es muy detallado, se vuelve difícil de mantener.
3. **Acoplamiento con `invoicing`**: `TreatmentProcedure` genera líneas de factura. El modelo `Invoice` actual usa `concepts` JSONB. Hay que decidir si se agrega un `InvoiceItem` modelo relacional o se enriquece el JSONB con `treatment_procedure_id`. Lo recomendado es crear `InvoiceItem` como refactor aparte para no tocar CFDI.
4. **Almacenamiento de imágenes**: Radiografías son archivos pesados. `PatientImage` debe almacenar URL en object storage (S3/MinIO), no en PostgreSQL. Requiere configuración de uploads presignados.
5. **NOM-004 trazabilidad**: `DentalRecordEntry` debe ser append-only (sin `update`/`delete`). Solo crear correcciones vía nuevos registros. Igualar la filosofía de `ClinicalNote`.
6. **Migraciones entre apps**: Crear `dental_records` implica dependencias cruzadas con `patients` y `appointments`. Hay que cuidar el orden de migraciones iniciales.
7. **Performance del odontograma**: Calcular el estado actual de 32 dientes × 5 superficies desde el log de eventos puede ser lento. Se recomienda mantener tablas materializadas (`Tooth`, `ToothSurface`) que se actualizan al crear un `DentalRecordEntry`, posiblemente vía señales o en el serializer.

### Ready for Proposal

**Sí**, pero con la recomendación explícita de **dividir la propuesta en 3 fases** (A: Odontograma + Historia médica, B: Plan de tratamiento, C: Recetas + Imágenes). La fase A es la más crítica y puede ser el PR inicial enfocado.
