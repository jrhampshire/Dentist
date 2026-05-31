import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dentalRecordsApi } from '@/api/dental-records'

// ── Patient Images list ──

export function usePatientImages(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'images'],
    queryFn: () => dentalRecordsApi.listImages(patientId),
    enabled: !!patientId,
  })
}

// ── Create Patient Image (multipart FormData) ──

export function useCreatePatientImage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, formData }: { patientId: string; formData: FormData }) =>
      dentalRecordsApi.createImage(patientId, formData),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'images'] })
    },
  })
}

// ── Delete Patient Image ──

export function useDeletePatientImage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, id }: { patientId: string; id: string }) =>
      dentalRecordsApi.deleteImage(patientId, id),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'images'] })
    },
  })
}
