// ── Tipo de antecedentes (JSONField) ──
export interface AntecedentePatologico {
  enfermedad: string
  notas: string
}

export interface AntecedenteQuirurgico {
  procedimiento: string
  fecha: string
  notas: string
}

export interface AntecedenteAlergico {
  alergeno: string
  reaccion: string
  notas: string
}

export interface AntecedenteFarmacologico {
  medicamento: string
  dosis: string
  notas: string
}

export interface AntecedenteFamiliar {
  parentesco: string
  enfermedad: string
  notas: string
}

// ── Enums (string unions matching backend choices.py) ──
export type ToothCondition =
  | 'healthy'
  | 'caries'
  | 'filling'
  | 'crown'
  | 'bridge'
  | 'missing'
  | 'implant'
  | 'root_canal'
  | 'extraction'
  | 'fracture'
  | 'wear'
  | 'sealant'
  | 'prosthesis'
  | 'other'

export type Surface = 'mesial' | 'distal' | 'buccal' | 'lingual' | 'occlusal' | 'root'

export type ImageType =
  | 'photo'
  | 'xray_periapical'
  | 'xray_panoramic'
  | 'xray_cephalometric'
  | 'document'
  | 'other'

export type PlanStatus = 'active' | 'completed' | 'cancelled'

export type PhaseStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'

export type ProcStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled'

// ── Labels ──
export const TOOTH_CONDITION_LABELS: Record<ToothCondition, string> = {
  healthy: 'Sano',
  caries: 'Caries',
  filling: 'Obturado',
  crown: 'Corona',
  bridge: 'Puente',
  missing: 'Ausente',
  implant: 'Implante',
  root_canal: 'Endodoncia',
  extraction: 'Extracción',
  fracture: 'Fractura',
  wear: 'Desgaste',
  sealant: 'Sellador',
  prosthesis: 'Prótesis',
  other: 'Otro',
}

export const SURFACE_LABELS: Record<Surface, string> = {
  mesial: 'Mesial',
  distal: 'Distal',
  buccal: 'Bucal',
  lingual: 'Lingual',
  occlusal: 'Oclusal',
  root: 'Raíz',
}

export const IMAGE_TYPE_LABELS: Record<ImageType, string> = {
  photo: 'Foto Clínica',
  xray_periapical: 'Radiografía Periapical',
  xray_panoramic: 'Radiografía Panorámica',
  xray_cephalometric: 'Radiografía Cefalométrica',
  document: 'Documento',
  other: 'Otro',
}

export const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  active: 'Activo',
  completed: 'Completado',
  cancelled: 'Cancelado',
}

export const PHASE_STATUS_LABELS: Record<PhaseStatus, string> = {
  pending: 'Pendiente',
  in_progress: 'En curso',
  completed: 'Completado',
  cancelled: 'Cancelado',
}

export const PROC_STATUS_LABELS: Record<ProcStatus, string> = {
  planned: 'Planeado',
  in_progress: 'En curso',
  completed: 'Realizado',
  cancelled: 'Cancelado',
}

// ── Condition colors map ──
export const CONDITION_COLORS: Record<ToothCondition, string> = {
  healthy: 'transparent',
  caries: '#ef4444',
  filling: '#3b82f6',
  crown: '#8b5cf6',
  bridge: '#f59e0b',
  missing: '#6b7280',
  implant: '#10b981',
  root_canal: '#f97316',
  extraction: '#dc2626',
  fracture: '#f43f5e',
  wear: '#fb923c',
  sealant: '#06b6d4',
  prosthesis: '#d946ef',
  other: '#e5e7eb',
}

// ── Interfaces (matching backend serializer output) ──

// DentalRecordEntry — append-only odontogram entry
export interface DentalRecordEntry {
  id: string
  patient: string
  tooth_fdi: number
  surface: Surface
  surface_display: string
  condition: ToothCondition
  condition_display: string
  notes: string
  created_by: string | null
  created_by_name: string | null
  created_at: string
}

// ToothSurfaceState — materialized current state of a tooth surface
export interface ToothSurfaceState {
  id: string
  surface: Surface
  surface_display: string
  condition: ToothCondition
  condition_display: string
  updated_at: string
}

// ToothState — materialized current state of a tooth
export interface ToothState {
  id: string
  tooth_fdi: number
  condition: ToothCondition
  condition_display: string
  surfaces: ToothSurfaceState[]
  updated_at: string
}

// MedicalHistory — versioned medical history
export interface MedicalHistory {
  id: string
  patient: string
  version: number
  antecedentes_patologicos: AntecedentePatologico[]
  antecedentes_quirurgicos: AntecedenteQuirurgico[]
  antecedentes_alergicos: AntecedenteAlergico[]
  antecedentes_farmacologicos: AntecedenteFarmacologico[]
  antecedentes_familiares: AntecedenteFamiliar[]
  motivo_consulta: string
  enfermedad_actual: string
  is_active: boolean
  created_by: string | null
  created_by_name: string | null
  updated_by: string | null
  updated_by_name: string | null
  created_at: string
  updated_at: string
}

// VitalSigns — vital signs recording
export interface VitalSigns {
  id: string
  patient: string
  appointment: string | null
  blood_pressure_systolic: number | null
  blood_pressure_diastolic: number | null
  heart_rate: number | null
  temperature: number | null
  weight: number | null
  height: number | null
  notes: string
  recorded_by: string | null
  recorded_by_name: string | null
  recorded_at: string
  created_at: string
}

// PatientImage — image upload with proxy URLs
export interface PatientImage {
  id: string
  patient: string
  tooth_fdi: number | null
  image_type: ImageType
  image_type_display: string
  image_url: string | null
  thumbnail_url: string | null
  description: string
  file_size: number | null
  content_type: string
  uploaded_by: string | null
  uploaded_by_name: string | null
  uploaded_at: string
}

// TreatmentProcedure — individual procedure within a phase
export interface TreatmentProcedure {
  id: string
  phase: string
  appointment: string | null
  tooth_fdi: number | null
  description: string
  cost: number
  status: ProcStatus
  status_display: string
  notes: string
}

// TreatmentPhase — phase within a treatment plan
export interface TreatmentPhase {
  id: string
  plan: string
  name: string
  description: string
  order: number
  status: PhaseStatus
  status_display: string
  procedures: TreatmentProcedure[]
}

// TreatmentPlan (list view) — without nested phases
export interface TreatmentPlanSummary {
  id: string
  patient: string
  name: string
  description: string
  status: PlanStatus
  status_display: string
  phases_count: number
  created_by: string | null
  created_at: string
  updated_at: string
}

// TreatmentPlan (detail view) — with nested phases + procedures
export interface TreatmentPlan extends TreatmentPlanSummary {
  phases: TreatmentPhase[]
}
