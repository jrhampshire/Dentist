import apiClient from './client'
import type { Patient, ClinicalNote, PatientConsent, PaginatedResponse } from '@/types'

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
    apiClient.get<ClinicalNote[]>(`/patients/${patientId}/clinical-notes/`).then((r) => r.data),

  createNote: (patientId: string, data: Partial<ClinicalNote>) =>
    apiClient.post<ClinicalNote>(`/patients/${patientId}/clinical-notes/`, data).then((r) => r.data),

  signNote: (patientId: string, noteId: string) =>
    apiClient.post<ClinicalNote>(`/patients/${patientId}/clinical-notes/${noteId}/sign/`).then((r) => r.data),

  // Consents
  listConsents: (patientId: string) =>
    apiClient.get<PatientConsent[]>(`/patients/${patientId}/consents/`).then((r) => r.data),

  createConsent: (patientId: string, data: Partial<PatientConsent>) =>
    apiClient.post<PatientConsent>(`/patients/${patientId}/consents/`, data).then((r) => r.data),

  // Check duplicate phone
  checkDuplicatePhone: (phone: string) =>
    apiClient.get<{ exists: boolean; patient_id?: string }>(`/patients/check-phone/`, { params: { phone } }).then((r) => r.data),
}
