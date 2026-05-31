import apiClient from './client'
import type {
  DentalRecordEntry,
  ToothState,
  MedicalHistory,
  VitalSigns,
  PatientImage,
  TreatmentPlanSummary,
  TreatmentPlan,
  TreatmentPhase,
  TreatmentProcedure,
} from '@/types/dental-records'

const BASE = (patientId: string) => `dental-records/patients/${patientId}`

export const dentalRecordsApi = {
  // ── Odontogram ──

  listDentalRecords: (patientId: string) =>
    apiClient
      .get<DentalRecordEntry[]>(`${BASE(patientId)}/teeth/entries/`)
      .then((r) => r.data),

  getDentalRecord: (patientId: string, id: string) =>
    apiClient
      .get<DentalRecordEntry>(`${BASE(patientId)}/teeth/entries/${id}/`)
      .then((r) => r.data),

  createDentalRecord: (patientId: string, data: { tooth_fdi: number; surface: string; condition: string; notes?: string }) =>
    apiClient
      .post<DentalRecordEntry>(`${BASE(patientId)}/teeth/entries/`, data)
      .then((r) => r.data),

  listTeethState: (patientId: string) =>
    apiClient
      .get<ToothState[]>(`${BASE(patientId)}/teeth/state/`)
      .then((r) => r.data),

  // ── Medical History ──

  listMedicalHistory: (patientId: string) =>
    apiClient
      .get<MedicalHistory[]>(`${BASE(patientId)}/medical-history/`)
      .then((r) => r.data),

  getMedicalHistory: (patientId: string, id: string) =>
    apiClient
      .get<MedicalHistory>(`${BASE(patientId)}/medical-history/${id}/`)
      .then((r) => r.data),

  listMedicalHistoryVersions: (patientId: string) =>
    apiClient
      .get<MedicalHistory[]>(`${BASE(patientId)}/medical-history/history/`)
      .then((r) => r.data),

  upsertMedicalHistory: (patientId: string, id: string, data: Record<string, unknown>) =>
    apiClient
      .put<MedicalHistory>(`${BASE(patientId)}/medical-history/${id}/`, data)
      .then((r) => r.data),

  createMedicalHistory: (patientId: string, data: Record<string, unknown>) =>
    apiClient
      .post<MedicalHistory>(`${BASE(patientId)}/medical-history/`, data)
      .then((r) => r.data),

  // ── Vital Signs ──

  listVitalSigns: (patientId: string) =>
    apiClient
      .get<VitalSigns[]>(`${BASE(patientId)}/vital-signs/`)
      .then((r) => r.data),

  getVitalSigns: (patientId: string, id: string) =>
    apiClient
      .get<VitalSigns>(`${BASE(patientId)}/vital-signs/${id}/`)
      .then((r) => r.data),

  createVitalSigns: (patientId: string, data: Record<string, unknown>) =>
    apiClient
      .post<VitalSigns>(`${BASE(patientId)}/vital-signs/`, data)
      .then((r) => r.data),

  // ── Patient Images ──

  listImages: (patientId: string) =>
    apiClient
      .get<PatientImage[]>(`${BASE(patientId)}/images/`)
      .then((r) => r.data),

  getImage: (patientId: string, id: string) =>
    apiClient
      .get<PatientImage>(`${BASE(patientId)}/images/${id}/`)
      .then((r) => r.data),

  createImage: (patientId: string, formData: FormData) =>
    apiClient
      .post<PatientImage>(`${BASE(patientId)}/images/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data),

  deleteImage: (patientId: string, id: string) =>
    apiClient.delete(`${BASE(patientId)}/images/${id}/`).then((r) => r.data),

  getImageFile: (patientId: string, id: string) =>
    apiClient
      .get<Blob>(`${BASE(patientId)}/images/${id}/file/`, { responseType: 'blob' })
      .then((r) => r.data),

  getImageThumbnail: (patientId: string, id: string) =>
    apiClient
      .get<Blob>(`${BASE(patientId)}/images/${id}/thumbnail/`, { responseType: 'blob' })
      .then((r) => r.data),

  // ── Treatment Plans ──

  listPlans: (patientId: string) =>
    apiClient
      .get<TreatmentPlanSummary[]>(`${BASE(patientId)}/plans/`)
      .then((r) => r.data),

  getPlan: (patientId: string, id: string) =>
    apiClient
      .get<TreatmentPlan>(`${BASE(patientId)}/plans/${id}/`)
      .then((r) => r.data),

  createPlan: (patientId: string, data: { name: string; description?: string; status?: string }) =>
    apiClient
      .post<TreatmentPlanSummary>(`${BASE(patientId)}/plans/`, data)
      .then((r) => r.data),

  updatePlan: (patientId: string, id: string, data: Record<string, unknown>) =>
    apiClient
      .put<TreatmentPlan>(`${BASE(patientId)}/plans/${id}/`, data)
      .then((r) => r.data),

  partialUpdatePlan: (patientId: string, id: string, data: Record<string, unknown>) =>
    apiClient
      .patch<TreatmentPlan>(`${BASE(patientId)}/plans/${id}/`, data)
      .then((r) => r.data),

  deletePlan: (patientId: string, id: string) =>
    apiClient.delete(`${BASE(patientId)}/plans/${id}/`).then((r) => r.data),

  // ── Treatment Phases (nested under plan) ──

  listPhases: (patientId: string, planId: string) =>
    apiClient
      .get<TreatmentPhase[]>(`${BASE(patientId)}/plans/${planId}/phases/`)
      .then((r) => r.data),

  getPhase: (patientId: string, planId: string, phaseId: string) =>
    apiClient
      .get<TreatmentPhase>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/`)
      .then((r) => r.data),

  createPhase: (patientId: string, planId: string, data: { name: string; description?: string; order?: number; status?: string }) =>
    apiClient
      .post<TreatmentPhase>(`${BASE(patientId)}/plans/${planId}/phases/`, data)
      .then((r) => r.data),

  updatePhase: (patientId: string, planId: string, phaseId: string, data: Record<string, unknown>) =>
    apiClient
      .put<TreatmentPhase>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/`, data)
      .then((r) => r.data),

  partialUpdatePhase: (patientId: string, planId: string, phaseId: string, data: Record<string, unknown>) =>
    apiClient
      .patch<TreatmentPhase>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/`, data)
      .then((r) => r.data),

  deletePhase: (patientId: string, planId: string, phaseId: string) =>
    apiClient.delete(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/`).then((r) => r.data),

  // ── Treatment Procedures (nested under phase) ──

  listProcedures: (patientId: string, planId: string, phaseId: string) =>
    apiClient
      .get<TreatmentProcedure[]>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/`)
      .then((r) => r.data),

  getProcedure: (patientId: string, planId: string, phaseId: string, procId: string) =>
    apiClient
      .get<TreatmentProcedure>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/${procId}/`)
      .then((r) => r.data),

  createProcedure: (patientId: string, planId: string, phaseId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) =>
    apiClient
      .post<TreatmentProcedure>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/`, data)
      .then((r) => r.data),

  updateProcedure: (patientId: string, planId: string, phaseId: string, procId: string, data: Record<string, unknown>) =>
    apiClient
      .put<TreatmentProcedure>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/${procId}/`, data)
      .then((r) => r.data),

  partialUpdateProcedure: (patientId: string, planId: string, phaseId: string, procId: string, data: Record<string, unknown>) =>
    apiClient
      .patch<TreatmentProcedure>(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/${procId}/`, data)
      .then((r) => r.data),

  deleteProcedure: (patientId: string, planId: string, phaseId: string, procId: string) =>
    apiClient.delete(`${BASE(patientId)}/plans/${planId}/phases/${phaseId}/procedures/${procId}/`).then((r) => r.data),
}
