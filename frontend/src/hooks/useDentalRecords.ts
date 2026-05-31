import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dentalRecordsApi } from '@/api/dental-records'

// ── Odontogram (tooth state) ──

export function useOdontogram(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'teeth-state'],
    queryFn: () => dentalRecordsApi.listTeethState(patientId),
    enabled: !!patientId,
  })
}

// ── Dental Records (entries) ──

export function useDentalRecords(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'entries'],
    queryFn: () => dentalRecordsApi.listDentalRecords(patientId),
    enabled: !!patientId,
  })
}

export function useCreateDentalRecord() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: { tooth_fdi: number; surface: string; condition: string; notes?: string } }) =>
      dentalRecordsApi.createDentalRecord(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dental-records'] })
    },
  })
}
