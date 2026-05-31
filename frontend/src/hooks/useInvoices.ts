import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { invoicesApi } from '@/api/invoices'
import type { Invoice, PaginatedResponse } from '@/types'

export interface UseInvoicesParams {
  page?: number
  status?: string
}

export function useInvoices(params?: UseInvoicesParams) {
  return useQuery<PaginatedResponse<Invoice>>({
    queryKey: ['invoices', params],
    queryFn: () => invoicesApi.list({ page: params?.page, status: params?.status }),
  })
}

export function useInvoice(id: string) {
  return useQuery<Invoice>({
    queryKey: ['invoices', id],
    queryFn: () => invoicesApi.get(id),
    enabled: !!id,
  })
}

export interface CreateInvoicePayload {
  patient_id: string
  rfc_receptor: string
  nombre_receptor: string
  uso_cfdi?: string
  concepts?: Array<{
    clave_sat: string
    descripcion: string
    cantidad: number
    valor_unitario: number
    iva_rate?: number
  }>
}

export function useCreateInvoice() {
  const queryClient = useQueryClient()

  return useMutation<Invoice, Error, CreateInvoicePayload>({
    mutationFn: (data) => invoicesApi.create(data as Partial<Invoice>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useStampInvoice() {
  const queryClient = useQueryClient()

  return useMutation<Invoice, Error, string>({
    mutationFn: (id) => invoicesApi.stamp(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useCancelInvoice() {
  const queryClient = useQueryClient()

  return useMutation<Invoice, Error, { id: string; reason: string }>({
    mutationFn: ({ id, reason }) => invoicesApi.cancel(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}
