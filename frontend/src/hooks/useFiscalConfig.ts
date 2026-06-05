import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fiscalConfigApi } from '@/api/fiscalConfig'
import type { FiscalConfig } from '@/types'

export function useFiscalConfig() {
  return useQuery({
    queryKey: ['fiscal-config'],
    queryFn: async () => {
      const configs = await fiscalConfigApi.list()
      return configs[0] ?? null
    },
  })
}

export function useCreateFiscalConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<FiscalConfig>) => fiscalConfigApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fiscal-config'] }),
  })
}

export function useUpdateFiscalConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FiscalConfig> }) =>
      fiscalConfigApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fiscal-config'] }),
  })
}

export function useValidateCsd() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) =>
      fiscalConfigApi.validateCsd(id, password),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['fiscal-config'] }),
  })
}
