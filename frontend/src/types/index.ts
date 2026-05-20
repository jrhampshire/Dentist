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

// Patient types
export interface Patient {
  id: string
  clinic: string
  first_name: string
  last_name: string
  phone: string
  email: string
  curp: string
  rfc: string
  date_of_birth: string
  gender: string
  address: {
    street: string
    city: string
    state: string
    postal_code: string
  }
  emergency_contact: {
    name: string
    phone: string
  }
  blood_type: string
  allergies: string
  chronic_conditions: string
  current_medications: string
  consent_signed: boolean
  whatsapp_opt_in: boolean
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export interface ClinicalNote {
  id: string
  patient: string
  appointment: string
  author: string
  note_type: 'consultation' | 'treatment' | 'follow_up' | 'other'
  title: string
  content: string
  is_signed: boolean
  signature_hash: string
  attachments: string[]
  created_at: string
  updated_at: string
}

export interface PatientConsent {
  id: string
  patient: string
  consent_type: 'treatment' | 'data_processing' | 'marketing'
  version: string
  content: string
  signed: boolean
  signature_blob: string
  signature_hash: string
  signed_by: string
  ip_address: string
  signed_at: string
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
  inventory_kit: string[]
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

// Invoice types
export interface FiscalConfig {
  clinic: string
  rfc: string
  razon_social: string
  regimen_fiscal: string
  fiscal_address: {
    street: string
    city: string
    state: string
    postal_code: string
    country: string
  }
  csd_cert_uploaded: boolean
  is_validated: boolean
  email: string
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
  status: 'draft' | 'pending' | 'stamped' | 'cancelled' | 'error'
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
  category: 'consumable' | 'instrument' | 'medication' | 'equipment' | 'other'
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
