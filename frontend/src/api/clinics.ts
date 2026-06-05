import apiClient from './client'
import type { Clinic } from '@/types'

export const clinicsApi = {
  get: (id: string) =>
    apiClient.get<Clinic>(`/clinics/${id}/`).then(r => r.data),

  update: (id: string, data: Partial<Clinic>) =>
    apiClient.patch<Clinic>(`/clinics/${id}/`, data).then(r => r.data),
}
