import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { inventoryApi } from '@/api/inventory'
import type { InventoryItem } from '@/types'

// Items
export function useInventoryItems(params?: { page?: number; category?: string; search?: string }) {
  return useQuery({
    queryKey: ['inventory-items', params],
    queryFn: () => inventoryApi.list(params),
  })
}

export function useInventoryItem(id: string) {
  return useQuery({
    queryKey: ['inventory-item', id],
    queryFn: () => inventoryApi.get(id),
    enabled: !!id,
  })
}

export function useCreateInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<InventoryItem>) => inventoryApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] })
    },
  })
}

export function useUpdateInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<InventoryItem> }) => inventoryApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] })
    },
  })
}

export function useDeleteInventoryItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] })
    },
  })
}

export function useAdjustStock() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { quantity: number; movement_type: string; note?: string } }) =>
      inventoryApi.adjustStock(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory-items'] })
      queryClient.invalidateQueries({ queryKey: ['inventory-movements'] })
    },
  })
}

// Movements
export function useInventoryMovements(params?: { page?: number; item?: string; movement_type?: string }) {
  return useQuery({
    queryKey: ['inventory-movements', params],
    queryFn: () => inventoryApi.listMovements(params),
  })
}

// Alerts
export function useInventoryAlerts() {
  return useQuery({
    queryKey: ['inventory-alerts'],
    queryFn: () => inventoryApi.getAlerts(),
  })
}

// Categories
export function useInventoryCategories() {
  return useQuery({
    queryKey: ['inventory-categories'],
    queryFn: () => inventoryApi.getCategories(),
  })
}
