import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { patientsApi } from '@/api/patients'
import type { ClinicalNote } from '@/types'

export function useClinicalNotes(patientId: string) {
  return useQuery({
    queryKey: ['clinical-notes', patientId],
    queryFn: () => patientsApi.listNotes(patientId),
    enabled: !!patientId,
  })
}

export function useCreateClinicalNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Partial<ClinicalNote> }) =>
      patientsApi.createNote(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clinical-notes', variables.patientId] })
    },
  })
}

export function useSignClinicalNote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, noteId }: { patientId: string; noteId: string }) =>
      patientsApi.signNote(patientId, noteId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clinical-notes', variables.patientId] })
    },
  })
}
