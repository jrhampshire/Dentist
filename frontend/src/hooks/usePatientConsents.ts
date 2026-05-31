import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { patientsApi } from '@/api/patients'
import type { PatientConsent } from '@/types'

export function useConsents(patientId: string) {
  return useQuery({
    queryKey: ['consents', patientId],
    queryFn: () => patientsApi.listConsents(patientId),
    enabled: !!patientId,
  })
}

export function useCreateConsent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: Partial<PatientConsent> }) =>
      patientsApi.createConsent(patientId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['consents', variables.patientId] })
    },
  })
}

export function useSignConsent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      patientId,
      consentId,
      signatureBlob,
    }: {
      patientId: string
      consentId: string
      signatureBlob?: string
    }) => patientsApi.signConsent(patientId, consentId, signatureBlob),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['consents', variables.patientId] })
    },
  })
}
