import apiClient from './client'
import type { Appointment, AppointmentType, ScheduleSlot, PaginatedResponse } from '@/types'

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
  // NOTE: the backend reads `dentist_id` (not `dentist`); map it here so the
  // query param name matches the AppointmentViewSet.available_slots action.
  getAvailableSlots: (params: { date: string; dentist_id?: string; duration?: number }) =>
    apiClient
      .get<{ date: string; dentist_id: string; duration_minutes: number; slots: { start_time: string; end_time: string }[]; total_available: number }>(
        '/appointments/available-slots/',
        { params: { date: params.date, dentist_id: params.dentist_id, duration: params.duration } },
      )
      .then((r) => r.data),

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

  // Complete appointment (inventory kit consumption)
  complete: (id: string) =>
    apiClient.post<Appointment>(`/appointments/${id}/complete/`).then((r) => r.data),

  // Reschedule appointment (new date + start_time; re-arms reminders)
  reschedule: (id: string, data: { date: string; start_time: string }) =>
    apiClient.post<Appointment>(`/appointments/${id}/reschedule/`, data).then((r) => r.data),
}
