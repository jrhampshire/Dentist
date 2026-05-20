import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { appointmentsApi } from '@/api/appointments'
import type { Appointment, AppointmentType, ScheduleSlot } from '@/types'

// Appointments
export function useAppointments(params?: { page?: number; date?: string; dentist?: string; status?: string }) {
  return useQuery({
    queryKey: ['appointments', params],
    queryFn: () => appointmentsApi.list(params),
  })
}

export function useAppointment(id: string) {
  return useQuery({
    queryKey: ['appointment', id],
    queryFn: () => appointmentsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateAppointment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Appointment>) => appointmentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
    },
  })
}

export function useUpdateAppointment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Appointment> }) => appointmentsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
    },
  })
}

export function useDeleteAppointment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => appointmentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] })
    },
  })
}

// Available Slots
export function useAvailableSlots(params: { date: string; dentist?: string; type?: string }) {
  return useQuery({
    queryKey: ['available-slots', params],
    queryFn: () => appointmentsApi.getAvailableSlots(params),
    enabled: !!params.date,
  })
}

// Appointment Types
export function useAppointmentTypes() {
  return useQuery({
    queryKey: ['appointment-types'],
    queryFn: () => appointmentsApi.listTypes(),
  })
}

export function useCreateAppointmentType() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<AppointmentType>) => appointmentsApi.createType(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointment-types'] })
    },
  })
}

export function useUpdateAppointmentType() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<AppointmentType> }) => appointmentsApi.updateType(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointment-types'] })
    },
  })
}

export function useDeleteAppointmentType() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => appointmentsApi.deleteType(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointment-types'] })
    },
  })
}

// Schedule
export function useSchedule(params?: { dentist?: string }) {
  return useQuery({
    queryKey: ['schedule', params],
    queryFn: () => appointmentsApi.listSchedule(params),
  })
}

export function useCreateSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<ScheduleSlot>) => appointmentsApi.createSchedule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}

export function useUpdateSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ScheduleSlot> }) => appointmentsApi.updateSchedule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => appointmentsApi.deleteSchedule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] })
    },
  })
}
