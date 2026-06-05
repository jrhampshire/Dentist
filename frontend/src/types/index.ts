// Inventory Kit types
export interface KitItem {
  item_id: string
  quantity: number
}

export type InventoryCategory = 'material' | 'supply' | 'instrument' | 'medication' | 'lab' | 'other'

export const INVENTORY_CATEGORY_LABELS: Record<InventoryCategory, string> = {
  material: 'Material',
  supply: 'Insumo',
  instrument: 'Instrumento',
  medication: 'Medicamento',
  lab: 'Laboratorio',
  other: 'Otro',
}

// User & Auth types
export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'admin' | 'dentist' | 'recepcionista'
  clinic: string
  is_active: boolean
  date_joined: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  expires_in: number
  user: User
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials {
  email: string
  password: string
  first_name: string
  last_name: string
  phone?: string
  accept_terms: boolean
}

// Patient types
export interface Patient {
  id: string
  clinic: string
  first_name: string
  last_name: string
  second_last_name?: string
  full_name?: string
  phone: string
  email: string
  alternate_phone?: string
  curp: string
  rfc: string
  date_of_birth: string
  gender: string
  address: {
    street?: string
    city?: string
    state?: string
    postal_code?: string
  }
  occupation?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  emergency_contact_relation?: string
  blood_type: string
  allergies: string
  chronic_conditions: string
  current_medications: string
  insurance_provider?: string
  insurance_policy_number?: string
  consent_signed: boolean
  consent_signed_at?: string
  consent_version?: string
  consent_status?: string
  whatsapp_opt_in: boolean
  email_opt_in?: boolean
  created_by?: string
  created_by_name?: string
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export type NoteType = 'evolution' | 'diagnosis' | 'treatment' | 'observation' | 'consent'

export interface ClinicalNote {
  id: string
  patient: string
  appointment: string
  author: string
  author_name?: string
  note_type: NoteType
  note_type_display?: string
  title: string
  content: string
  is_signed: boolean
  signed_at?: string
  signature_hash: string
  attachments: string[]
  created_at: string
  updated_at: string
}

export const NOTE_TYPE_LABELS: Record<NoteType, string> = {
  evolution: 'Evolución',
  diagnosis: 'Diagnóstico',
  treatment: 'Tratamiento',
  observation: 'Observación',
  consent: 'Consentimiento',
}

export type ConsentType = 'general' | 'treatment' | 'data_processing' | 'whatsapp'

export interface PatientConsent {
  id: string
  patient: string
  consent_type: ConsentType
  consent_type_display?: string
  version: string
  content: string
  signed: boolean
  signature_blob?: string
  signature_hash: string
  signed_by?: string
  signed_by_name?: string
  ip_address?: string
  signed_at?: string
  created_at: string
}

export const CONSENT_TYPE_LABELS: Record<ConsentType, string> = {
  general: 'General',
  treatment: 'Tratamiento',
  data_processing: 'Datos Personales',
  whatsapp: 'WhatsApp',
}

// Appointment types
export interface AppointmentType {
  id: string
  clinic: string
  name: string
  description: string
  duration_minutes: number
  price: number
  color: string
  inventory_kit: KitItem[]
  is_active: boolean
}

export interface Appointment {
  id: string
  clinic: string
  patient: string
  patient_name: string
  type: string
  type_name: string
  dentist: string
  dentist_name: string
  date: string
  start_time: string
  end_time: string
  status: 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show'
  notes: string
  cancellation_reason: string
  cancelled_by: string
  cancelled_at: string
  inventory_consumed_at?: string
  inventory_items_consumed?: number
  whatsapp_sent: boolean
  whatsapp_response: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface ScheduleSlot {
  id: string
  clinic: string
  dentist: string
  day_of_week: number
  start_time: string
  end_time: string
  is_active: boolean
}

export interface AvailableSlot {
  date: string
  start_time: string
  end_time: string
  dentist: string
}

// Clinic types
export interface Clinic {
  id: string
  name: string
  rfc: string
  email: string
  phone: string
  address: Record<string, unknown>
  plan: 'free' | 'basic' | 'pro'
  status: 'pending' | 'active' | 'suspended' | 'cancelled'
  email_verified: boolean
  onboarding_completed: boolean
  subscription_start: string | null
  subscription_end: string | null
  stamps_remaining: number
  settings: Record<string, unknown>
  onboarding_progress: Record<string, unknown>
  created_at: string
  updated_at: string
}

// Invoice types
export interface FiscalConfig {
  id: string
  rfc: string
  razon_social: string
  regimen_fiscal: string
  fiscal_address: Record<string, unknown>
  csd_cert_path: string
  csd_key_path: string
  email: string
  is_validated: boolean
}

export interface Invoice {
  id: string
  clinic: string
  patient: string
  patient_name: string
  appointment: string
  folio: string
  rfc_receptor: string
  nombre_receptor: string
  uso_cfdi: string
  metodo_pago: string
  forma_pago: string
  moneda: string
  subtotal: number
  iva: number
  total: number
  concepts: {
    description: string
    quantity: number
    unit_price: number
    amount: number
  }[]
  status: 'draft' | 'pending_stamp' | 'stamped' | 'cancelled' | 'error'
  cfdi_uuid: string
  xml_url: string
  pdf_url: string
  cfdi_sat_certificate: string
  cfdi_stamp_date: string
  cancellation_reason: string
  cancellation_date: string
  error_message: string
  created_at: string
  updated_at: string
}

// Inventory types
export interface InventoryItem {
  id: string
  clinic: string
  name: string
  category: InventoryCategory
  unit: string
  stock_current: number
  stock_minimum: number
  stock_maximum: number
  expiration_date: string
  batch_number: string
  supplier: string
  unit_price: number
  barcode: string
  is_expired: boolean
  is_blocked: boolean
  created_at: string
  updated_at: string
}

export interface InventoryMovement {
  id: string
  clinic: string
  item: string
  item_name: string
  movement_type: 'entry' | 'exit' | 'adjustment' | 'consumption' | 'return'
  quantity: number
  previous_stock: number
  new_stock: number
  reference_type: string
  reference_id: string
  note: string
  created_by: string
  created_at: string
}

export interface InventoryAlert {
  type: 'low_stock' | 'expiration'
  item: InventoryItem
  message: string
}

// WhatsApp types
export interface NotificationLog {
  id: string
  clinic: string
  patient: string
  patient_name: string
  appointment: string
  channel: 'whatsapp' | 'sms' | 'email'
  template: string
  status: 'pending' | 'sent' | 'delivered' | 'failed'
  recipient: string
  content: string
  provider_id: string
  provider_response: Record<string, unknown>
  error_message: string
  sent_at: string
  delivered_at: string
  created_at: string
}

export interface WhatsAppTemplate {
  id: string
  name: string
  content: string
  variables: string[]
}

// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
  request_id?: string
}

export interface ApiError {
  error: string
  message: string
  details?: Record<string, unknown>
  request_id?: string
}

export interface PaginatedResponse<T> {
  results: T[]
  next: string | null
  previous: string | null
  count: number
}

// Role types
export type UserRole = 'admin' | 'dentist' | 'recepcionista'

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrador',
  dentist: 'Dentista',
  recepcionista: 'Recepcionista',
}

export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin: ['all'],
  dentist: ['patients:read', 'patients:write', 'appointments:read', 'appointments:write', 'clinical_notes:read', 'clinical_notes:write'],
  recepcionista: ['patients:read', 'patients:write', 'appointments:read', 'appointments:write', 'invoices:read'],
}

// Dashboard metrics types
export interface MetricsTrendPoint {
  date: string
  count: number
}

export interface RevenueTrendPoint {
  date: string
  total: number
}

export interface AppointmentsByStatus {
  total: number
  by_status: Record<string, number>
}

export interface MonthlyAppointmentsSummary {
  total: number
  completion_rate: number
}

export interface UpcomingAppointment {
  id: string
  patient_name: string
  date: string
  time: string
  type_name: string
  status: string
}

export interface DashboardMetrics {
  appointments_today: number
  appointments_this_week: AppointmentsByStatus
  appointments_this_month: MonthlyAppointmentsSummary
  revenue_this_month: number
  revenue_trend: RevenueTrendPoint[]
  appointments_trend: MetricsTrendPoint[]
  patients_total: number
  patients_new_this_month: number
  low_stock_count: number
  expiring_soon_count: number
  upcoming_appointments: UpcomingAppointment[]
}

// Audit log types (NOM-024 compliance)
export interface AuditLog {
  id: string
  action: string
  resource_type: string
  resource_id: string
  user?: string
  user_name?: string
  details: Record<string, unknown>
  result: string
  ip_address?: string
  created_at: string
}
