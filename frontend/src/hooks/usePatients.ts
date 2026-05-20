import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { patientsApi } from '@/api/patients'
import type { Patient, ClinicalNote, PatientConsent } from '@/types'

// Patients
export function usePatients(params?: { page?: number; q?: string; phone?: string; curp?: string }) {
  return useQuery({
    queryKey: ['patients', params],
    queryFn: () => patientsApi.list(params),
  })
}

export function usePatient(id: string) {
  return useQuery({
    queryKey: ['patient', id],
    queryFn: () => patientsApi.get(id),
    enabled: !!id,
  })
}

export function useCreatePatient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Patient>) => patientsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
    },
  })
}

export function useUpdatePatient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Patient> }) => patientsApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      queryClient.invalidateQueries({ queryKey: ['patient', variables.id] })
    },
  })
}

export function useDeletePatient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => patientsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
    },
  })
}

// Clinical Notes
export function useClinicalNotes(patientId: string) {
  return useQuery({
    queryKey: ['clinical-notes', patientId],
    queryFn: () => patientsApi.listNotes(patientId),
    enabled: !!patientId,
  })
}

export function useCreateClinicalNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Partial<ClinicalNote> }) =>
      patientsApi.createNote(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clinical-notes', variables.patientId] })
    },
  })
}

export function useSignClinicalNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, noteId }: { patientId: string; noteId: string }) =>
      patientsApi.signNote(patientId, noteId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clinical-notes', variables.patientId] })
    },
  })
}

// Consents
export function useConsents(patientId: string) {
  return useQuery({
    queryKey: ['consents', patientId],
    queryFn: () => patientsApi.listConsents(patientId),
    enabled: !!patientId,
  })
}

export function useCreateConsent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Partial<PatientConsent> }) =>
      patientsApi.createConsent(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['consents', variables.patientId] })
    },
  })
}
