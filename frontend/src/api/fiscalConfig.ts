import apiClient from './client'
import type { FiscalConfig } from '@/types'

export const fiscalConfigApi = {
  list: () =>
    apiClient.get<FiscalConfig[]>('/fiscal-config/').then(r => r.data),

  get: (id: string) =>
    apiClient.get<FiscalConfig>(`/fiscal-config/${id}/`).then(r => r.data),

  create: (data: Partial<FiscalConfig>) =>
    apiClient.post<FiscalConfig>('/fiscal-config/', data).then(r => r.data),

  update: (id: string, data: Partial<FiscalConfig>) =>
    apiClient.patch<FiscalConfig>(`/fiscal-config/${id}/`, data).then(r => r.data),

  validateCsd: (id: string, password: string) =>
    apiClient.post<{ valid: boolean; message: string }>(
      `/fiscal-config/${id}/validate-csd/`,
      { csd_password: password },
    ).then(r => r.data),
}
