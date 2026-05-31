import apiClient from './client'
import type { DashboardMetrics } from '@/types'

export const dashboardApi = {
  getMetrics: (from?: string, to?: string) =>
    apiClient.get<DashboardMetrics>('/dashboard/metrics/', { params: { from, to } }).then((r) => r.data),
}
