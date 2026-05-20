import apiClient from './client'
import type { Invoice, FiscalConfig, PaginatedResponse } from '@/types'

export const invoicesApi = {
  // CRUD Invoices
  list: (params?: { page?: number; status?: string; date_from?: string; date_to?: string }) =>
    apiClient.get<PaginatedResponse<Invoice>>('/invoices/', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Invoice>(`/invoices/${id}/`).then((r) => r.data),

  create: (data: Partial<Invoice>) =>
    apiClient.post<Invoice>('/invoices/', data).then((r) => r.data),

  update: (id: string, data: Partial<Invoice>) =>
    apiClient.patch<Invoice>(`/invoices/${id}/`, data).then((r) => r.data),

  // Stamp invoice
  stamp: (id: string) =>
    apiClient.post<Invoice>(`/invoices/${id}/stamp/`).then((r) => r.data),

  // Cancel invoice (admin only)
  cancel: (id: string, reason: string) =>
    apiClient.post<Invoice>(`/invoices/${id}/cancel/`, { cancellation_reason: reason }).then((r) => r.data),

  // Download PDF/XML
  downloadPdf: (id: string) =>
    apiClient.get(`/invoices/${id}/pdf/`, { responseType: 'blob' }).then((r) => r.data),

  downloadXml: (id: string) =>
    apiClient.get(`/invoices/${id}/xml/`, { responseType: 'blob' }).then((r) => r.data),

  // Fiscal Config
  getFiscalConfig: () =>
    apiClient.get<FiscalConfig>('/fiscal-config/').then((r) => r.data),

  updateFiscalConfig: (data: Partial<FiscalConfig>) =>
    apiClient.patch<FiscalConfig>('/fiscal-config/', data).then((r) => r.data),

  validateCsd: () =>
    apiClient.post<{ valid: boolean; message: string }>('/fiscal-config/validate-csd/').then((r) => r.data),
}
