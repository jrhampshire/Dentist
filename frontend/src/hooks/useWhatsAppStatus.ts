import { useQuery } from '@tanstack/react-query'
import { notificationsApi } from '@/api/notifications'
import type { NotificationLog } from '@/types'

/**
 * Determine whether the WhatsApp integration is connected for the current clinic.
 *
 * There is no dedicated `whatsapp_configured` flag on the Clinic model — Twilio
 * credentials live server-side. We probe the notification logs instead: if the
 * clinic has any sent or delivered WhatsApp messages, the integration is
 * actively connected and working. If the endpoint errors or no logs exist,
 * WhatsApp is treated as disconnected.
 */
export function useWhatsAppStatus() {
  return useQuery({
    queryKey: ['whatsapp-status'],
    queryFn: async () => {
      const data = await notificationsApi.list({ channel: 'whatsapp' })

      // Normalize: list endpoint may return either a paginated object or a bare array.
      const logs: NotificationLog[] = Array.isArray(data)
        ? data
        : (data as PaginatedResponse<NotificationLog>).results ?? []

      const hasSuccessful = logs.some(
        (log) => log.status === 'sent' || log.status === 'delivered',
      )

      return {
        isConnected: hasSuccessful,
        totalMessages: logs.length,
      }
    },
    staleTime: 60_000,
  })
}

interface PaginatedResponse<T> {
  results: T[]
}