import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dentalRecordsApi } from '@/api/dental-records'

// ── Treatment Plans ──

export function useTreatmentPlans(patientId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'plans'],
    queryFn: () => dentalRecordsApi.listPlans(patientId),
    enabled: !!patientId,
  })
}

export function useTreatmentPlan(patientId: string, planId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'plans', planId],
    queryFn: () => dentalRecordsApi.getPlan(patientId, planId),
    enabled: !!patientId && !!planId,
  })
}

export function useCreateTreatmentPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: { name: string; description?: string; status?: string } }) =>
      dentalRecordsApi.createPlan(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans'] })
    },
  })
}

export function useUpdateTreatmentPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, data }: { patientId: string; planId: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.updatePlan(patientId, planId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans'] })
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId] })
    },
  })
}

export function useDeleteTreatmentPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId }: { patientId: string; planId: string }) =>
      dentalRecordsApi.deletePlan(patientId, planId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans'] })
    },
  })
}

// ── Treatment Phases ──

export function useTreatmentPhases(patientId: string, planId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'plans', planId, 'phases'],
    queryFn: () => dentalRecordsApi.listPhases(patientId, planId),
    enabled: !!patientId && !!planId,
  })
}

export function useCreateTreatmentPhase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, data }: { patientId: string; planId: string; data: { name: string; description?: string; order?: number; status?: string } }) =>
      dentalRecordsApi.createPhase(patientId, planId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases'] })
    },
  })
}

export function useUpdateTreatmentPhase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, phaseId, data }: { patientId: string; planId: string; phaseId: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.updatePhase(patientId, planId, phaseId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases'] })
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases', variables.phaseId] })
    },
  })
}

export function useDeleteTreatmentPhase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, phaseId }: { patientId: string; planId: string; phaseId: string }) =>
      dentalRecordsApi.deletePhase(patientId, planId, phaseId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases'] })
    },
  })
}

// ── Treatment Procedures ──

export function useTreatmentProcedures(patientId: string, planId: string, phaseId: string) {
  return useQuery({
    queryKey: ['dental-records', patientId, 'plans', planId, 'phases', phaseId, 'procedures'],
    queryFn: () => dentalRecordsApi.listProcedures(patientId, planId, phaseId),
    enabled: !!patientId && !!planId && !!phaseId,
  })
}

export function useCreateTreatmentProcedure() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, phaseId, data }: { patientId: string; planId: string; phaseId: string; data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string } }) =>
      dentalRecordsApi.createProcedure(patientId, planId, phaseId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases', variables.phaseId, 'procedures'] })
    },
  })
}

export function useUpdateTreatmentProcedure() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, phaseId, procId, data }: { patientId: string; planId: string; phaseId: string; procId: string; data: Record<string, unknown> }) =>
      dentalRecordsApi.updateProcedure(patientId, planId, phaseId, procId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases', variables.phaseId, 'procedures'] })
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases', variables.phaseId, 'procedures', variables.procId] })
    },
  })
}

export function useDeleteTreatmentProcedure() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, planId, phaseId, procId }: { patientId: string; planId: string; phaseId: string; procId: string }) =>
      dentalRecordsApi.deleteProcedure(patientId, planId, phaseId, procId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['dental-records', variables.patientId, 'plans', variables.planId, 'phases', variables.phaseId, 'procedures'] })
    },
  })
}
