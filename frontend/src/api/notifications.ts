import apiClient from './client'
import type { NotificationLog, PaginatedResponse } from '@/types'

export interface NotificationLogParams {
  status?: string
  channel?: string
  patient_id?: string
}

export const notificationsApi = {
  /**
   * List notification logs (WhatsApp / SMS / email).
   * GET /api/v1/whatsapp/logs/
   */
  list: (params?: NotificationLogParams) =>
    apiClient
      .get<PaginatedResponse<NotificationLog> | NotificationLog[]>('/whatsapp/logs/', { params })
      .then((r) => r.data),
}