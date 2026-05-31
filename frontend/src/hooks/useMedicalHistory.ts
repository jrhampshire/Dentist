import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dentalRecordsApi } from '@/api/dental-records'
import type { MedicalHistory } from '@/types/dental-records'

// ── Active medical history ──

export function useMedicalHistory(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'medical-history'],
    queryFn: () => dentalRecordsApi.listMedicalHistory(patientId),
    enabled: !!patientId,
  })
}

// ── Medical history version chain ──

export function useMedicalHistoryVersions(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'medical-history', 'versions'],
    queryFn: () => dentalRecordsApi.listMedicalHistoryVersions(patientId),
    enabled: !!patientId,
  })
}

// ── Create initial medical history ──

export function useCreateMedicalHistory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.createMedicalHistory(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'medical-history'] })
    },
  })
}

// ── Upsert (versioned update) medical history ──

export function useUpsertMedicalHistory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, id, data }: { patientId: string; id: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.upsertMedicalHistory(patientId, id, data),
    onSuccess: (newVersion: MedicalHistory) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', newVersion.patient, 'medical-history'] })
    },
  })
}
