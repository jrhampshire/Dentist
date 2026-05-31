import { useQuery } from '@tanstack/react-query'
import { patientsApi } from '@/api/patients'
import type { AuditLog, PaginatedResponse } from '@/types'

export function useAuditTrail(resourceType: string, resourceId: string, params?: { page?: number }) {
  return useQuery<PaginatedResponse<AuditLog>>({
    queryKey: ['audit-trail', resourceType, resourceId, params],
    queryFn: () => patientsApi.getAuditTrail(resourceType, resourceId, params),
    enabled: !!resourceType && !!resourceId,
  })
}
