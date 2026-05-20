import apiClient from './client'
import type { InventoryItem, InventoryMovement, InventoryAlert, PaginatedResponse } from '@/types'

export const inventoryApi = {
  // CRUD Items
  list: (params?: { page?: number; category?: string; search?: string }) =>
    apiClient.get<PaginatedResponse<InventoryItem>>('/inventory/items/', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<InventoryItem>(`/inventory/items/${id}/`).then((r) => r.data),

  create: (data: Partial<InventoryItem>) =>
    apiClient.post<InventoryItem>('/inventory/items/', data).then((r) => r.data),

  update: (id: string, data: Partial<InventoryItem>) =>
    apiClient.patch<InventoryItem>(`/inventory/items/${id}/`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/inventory/items/${id}/`).then((r) => r.data),

  // Adjust stock
  adjustStock: (id: string, data: { quantity: number; movement_type: string; note?: string }) =>
    apiClient.post<InventoryMovement>(`/inventory/items/${id}/adjust/`, data).then((r) => r.data),

  // Movements
  listMovements: (params?: { page?: number; item?: string; movement_type?: string }) =>
    apiClient.get<PaginatedResponse<InventoryMovement>>('/inventory/movements/', { params }).then((r) => r.data),

  // Alerts (low stock + expiration)
  getAlerts: () =>
    apiClient.get<InventoryAlert[]>('/inventory/alerts/').then((r) => r.data),

  // Categories
  getCategories: () =>
    apiClient.get<string[]>('/inventory/categories/').then((r) => r.data),
}
