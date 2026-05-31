import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/api/dashboard'

export function useDashboardMetrics(from?: string, to?: string) {
  return useQuery({
    queryKey: ['dashboard-metrics', from, to],
    queryFn: () => dashboardApi.getMetrics(from, to),
    staleTime: 60_000, // 1 min — dashboard data ages fast
  })
}
