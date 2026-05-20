import apiClient from './client'
import type { Patient, ClinicalNote, PatientConsent, AuditLog, PaginatedResponse } from '@/types'

export const patientsApi = {
  // CRUD Patients
  list: (params?: { page?: number; q?: string; phone?: string; curp?: string }) =>
    apiClient.get<PaginatedResponse<Patient>>('/patients/', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Patient>(`/patients/${id}/`).then((r) => r.data),

  create: (data: Partial<Patient>) =>
    apiClient.post<Patient>('/patients/', data).then((r) => r.data),

  update: (id: string, data: Partial<Patient>) =>
    apiClient.patch<Patient>(`/patients/${id}/`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/patients/${id}/`).then((r) => r.data),

  // Clinical Notes
  listNotes: (patientId: string) =>
    apiClient.get<ClinicalNote[]>(`/patients/${patientId}/notes/`).then((r) => r.data),

  createNote: (patientId: string, data: Partial<ClinicalNote>) =>
    apiClient.post<ClinicalNote>(`/patients/${patientId}/notes/`, data).then((r) => r.data),

  signNote: (patientId: string, noteId: string) =>
    apiClient.post<ClinicalNote>(`/patients/${patientId}/notes/${noteId}/sign/`).then((r) => r.data),

  // Consents
  listConsents: (patientId: string) =>
    apiClient.get<PatientConsent[]>(`/patients/${patientId}/consents/`).then((r) => r.data),

  createConsent: (patientId: string, data: Partial<PatientConsent>) =>
    apiClient.post<PatientConsent>(`/patients/${patientId}/consents/`, data).then((r) => r.data),

  signConsent: (patientId: string, consentId: string, signatureBlob?: string) =>
    apiClient.post<PatientConsent>(
      `/patients/${patientId}/consents/${consentId}/sign/`,
      signatureBlob ? { signature_blob: signatureBlob } : {},
    ).then((r) => r.data),

  // Check duplicate phone
  checkDuplicatePhone: (phone: string) =>
    apiClient.get<{ exists: boolean; patient_id?: string }>(`/patients/check-phone/`, { params: { phone } }).then((r) => r.data),

  // Audit trail (NOM-024 compliance)
  getAuditTrail: (resourceType: string, resourceId: string, params?: { page?: number }) =>
    apiClient.get<PaginatedResponse<AuditLog>>('/patients/audit-trail/', {
      params: { resource_type: resourceType, resource_id: resourceId, ...params },
    }).then((r) => r.data),

  // Export patient data (NOM-024 data portability)
  exportPatientData: (id: string) =>
    apiClient.get<Blob>(`/patients/${id}/export/`, { responseType: 'blob' }).then((r) => r.data),
}
