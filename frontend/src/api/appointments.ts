import apiClient from './client'
import type { Appointment, AppointmentType, ScheduleSlot, AvailableSlot, PaginatedResponse } from '@/types'

export const appointmentsApi = {
  // CRUD Appointments
  list: (params?: { page?: number; date?: string; dentist?: string; status?: string }) =>
    apiClient.get<PaginatedResponse<Appointment>>('/appointments/', { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Appointment>(`/appointments/${id}/`).then((r) => r.data),

  create: (data: Partial<Appointment>) =>
    apiClient.post<Appointment>('/appointments/', data).then((r) => r.data),

  update: (id: string, data: Partial<Appointment>) =>
    apiClient.patch<Appointment>(`/appointments/${id}/`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/appointments/${id}/`).then((r) => r.data),

  // Available slots
  getAvailableSlots: (params: { date: string; dentist?: string; type?: string }) =>
    apiClient.get<AvailableSlot[]>('/appointments/available-slots/', { params }).then((r) => r.data),

  // Appointment Types
  listTypes: () =>
    apiClient.get<AppointmentType[]>('/appointment-types/').then((r) => r.data),

  createType: (data: Partial<AppointmentType>) =>
    apiClient.post<AppointmentType>('/appointment-types/', data).then((r) => r.data),

  updateType: (id: string, data: Partial<AppointmentType>) =>
    apiClient.patch<AppointmentType>(`/appointment-types/${id}/`, data).then((r) => r.data),

  deleteType: (id: string) =>
    apiClient.delete(`/appointment-types/${id}/`).then((r) => r.data),

  // Schedule
  listSchedule: (params?: { dentist?: string }) =>
    apiClient.get<ScheduleSlot[]>('/schedule/', { params }).then((r) => r.data),

  createSchedule: (data: Partial<ScheduleSlot>) =>
    apiClient.post<ScheduleSlot>('/schedule/', data).then((r) => r.data),

  updateSchedule: (id: string, data: Partial<ScheduleSlot>) =>
    apiClient.patch<ScheduleSlot>(`/schedule/${id}/`, data).then((r) => r.data),

  deleteSchedule: (id: string) =>
    apiClient.delete(`/schedule/${id}/`).then((r) => r.data),
}
