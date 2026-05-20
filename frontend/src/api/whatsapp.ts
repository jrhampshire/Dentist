import apiClient from './client'
import type { NotificationLog, WhatsAppTemplate, PaginatedResponse } from '@/types'

export const whatsappApi = {
  // Notification logs
  listLogs: (params?: { page?: number; patient?: string; status?: string }) =>
    apiClient.get<PaginatedResponse<NotificationLog>>('/whatsapp/logs/', { params }).then((r) => r.data),

  // Send test message
  sendTest: (data: { patient_id: string; template: string }) =>
    apiClient.post<{ status: string; message: string }>('/whatsapp/send-test/', data).then((r) => r.data),

  // Templates
  getTemplates: () =>
    apiClient.get<WhatsAppTemplate[]>('/whatsapp/templates/').then((r) => r.data),
}
