import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clinicsApi } from '@/api/clinics'
import { useAuth } from './useAuth'
import type { Clinic } from '@/types'

export function useClinic() {
  const { clinicId } = useAuth()

  return useQuery({
    queryKey: ['clinic'],
    queryFn: () => clinicsApi.get(clinicId!),
    enabled: !!clinicId,
  })
}

export function useUpdateClinic() {
  const queryClient = useQueryClient()
  const { clinicId } = useAuth()

  return useMutation({
    mutationFn: (data: Partial<Clinic>) => clinicsApi.update(clinicId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clinic'] })
    },
  })
}
