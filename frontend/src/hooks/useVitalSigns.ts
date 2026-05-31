import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dentalRecordsApi } from '@/api/dental-records'

// ── Vital Signs list ──

export function useVitalSigns(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'vital-signs'],
    queryFn: () => dentalRecordsApi.listVitalSigns(patientId),
    enabled: !!patientId,
  })
}

// ── Create Vital Signs ──

export function useCreateVitalSigns() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.createVitalSigns(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'vital-signs'] })
    },
  })
}
