import { useState } from 'react'
import { AlertCircle, ClipboardList } from 'lucide-react'
import {
  useTreatmentPlans,
  useTreatmentPlan,
  useCreateTreatmentPlan,
  useUpdateTreatmentPlan,
  useDeleteTreatmentPlan,
  useCreateTreatmentPhase,
  useUpdateTreatmentPhase,
  useDeleteTreatmentPhase,
  useCreateTreatmentProcedure,
  useUpdateTreatmentProcedure,
  useDeleteTreatmentProcedure,
} from '@/hooks/useTreatmentPlans'
import { TreatmentPlanList } from './TreatmentPlanList'
import { TreatmentPlanDetail } from './TreatmentPlanDetail'
import { TreatmentPlanForm } from './TreatmentPlanForm'

interface TreatmentPlanTabProps {
  patientId: string
}

export function TreatmentPlanTab({ patientId }: TreatmentPlanTabProps) {
  const [selectedPlanId, setSelectedPlanId] = useState<string | undefined>(undefined)
  const [formOpen, setFormOpen] = useState(false)

  const { data: plans, isLoading, error } = useTreatmentPlans(patientId)
  const { data: selectedPlan } = useTreatmentPlan(
    patientId,
    selectedPlanId || '',
  )

  const createPlan = useCreateTreatmentPlan()
  const updatePlan = useUpdateTreatmentPlan()
  const deletePlan = useDeleteTreatmentPlan()

  const createPhase = useCreateTreatmentPhase()
  const updatePhase = useUpdateTreatmentPhase()
  const deletePhase = useDeleteTreatmentPhase()

  const createProcedure = useCreateTreatmentProcedure()
  const updateProcedure = useUpdateTreatmentProcedure()
  const deleteProcedure = useDeleteTreatmentProcedure()

  const handleSelectPlan = (planId: string) => {
    setSelectedPlanId(planId)
  }

  const handleCreatePlan = async (data: { name: string; description?: string; status?: string }) => {
    try {
      const result = await createPlan.mutateAsync({ patientId, data })
      setFormOpen(false)
      setSelectedPlanId(result.id)
    } catch {
      // errors handled by React Query
    }
  }

  const handleUpdatePlan = async (data: { name: string; description?: string; status?: string }) => {
    if (!selectedPlanId) return
    await updatePlan.mutateAsync({ patientId, planId: selectedPlanId, data })
  }

  const handleDeletePlan = async () => {
    if (!selectedPlanId) return
    await deletePlan.mutateAsync({ patientId, planId: selectedPlanId })
    setSelectedPlanId(undefined)
  }

  const handleCreatePhase = async (data: { name: string; description?: string; order?: number; status?: string }) => {
    if (!selectedPlanId) return
    await createPhase.mutateAsync({ patientId, planId: selectedPlanId, data })
  }

  const handleUpdatePhase = async (phaseId: string, data: { name: string; description?: string; order?: number; status?: string }) => {
    if (!selectedPlanId) return
    await updatePhase.mutateAsync({ patientId, planId: selectedPlanId, phaseId, data })
  }

  const handleDeletePhase = async (phaseId: string) => {
    if (!selectedPlanId) return
    await deletePhase.mutateAsync({ patientId, planId: selectedPlanId, phaseId })
  }

  const handleCreateProcedure = async (phaseId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => {
    if (!selectedPlanId) return
    await createProcedure.mutateAsync({ patientId, planId: selectedPlanId, phaseId, data })
  }

  const handleUpdateProcedure = async (phaseId: string, procId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => {
    if (!selectedPlanId) return
    await updateProcedure.mutateAsync({ patientId, planId: selectedPlanId, phaseId, procId, data })
  }

  const handleDeleteProcedure = async (phaseId: string, procId: string) => {
    if (!selectedPlanId) return
    await deleteProcedure.mutateAsync({ patientId, planId: selectedPlanId, phaseId, procId })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="h-12 w-12 mb-3 text-destructive opacity-40" />
        <p className="text-lg font-medium text-destructive">Error al cargar los planes</p>
        <p className="text-sm mt-2">
          No se pudieron obtener los planes de tratamiento. Verifica la conexión e intenta de nuevo.
        </p>
      </div>
    )
  }

  const plansList = plans || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Plan de Tratamiento</h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left panel — plan list */}
        <div className="lg:col-span-1">
          <TreatmentPlanList
            plans={plansList}
            selectedPlanId={selectedPlanId}
            onSelectPlan={handleSelectPlan}
            onCreatePlan={() => setFormOpen(true)}
          />
        </div>

        {/* Right panel — plan detail */}
        <div className="lg:col-span-2">
          {selectedPlanId && selectedPlan ? (
            <TreatmentPlanDetail
              plan={selectedPlan}
              isUpdating={updatePlan.isPending}
              isDeleting={deletePlan.isPending}
              onUpdate={handleUpdatePlan}
              onDelete={handleDeletePlan}
              onCreatePhase={handleCreatePhase}
              onUpdatePhase={handleUpdatePhase}
              onDeletePhase={handleDeletePhase}
              onCreateProcedure={handleCreateProcedure}
              onUpdateProcedure={handleUpdateProcedure}
              onDeleteProcedure={handleDeleteProcedure}
            />
          ) : plansList.length > 0 ? (
            <div className="flex flex-col items-center justify-center py-16 border rounded-lg bg-muted/20 text-muted-foreground">
              <ClipboardList className="h-12 w-12 mb-3 opacity-40" />
              <p className="text-sm">Selecciona un plan para ver sus fases y procedimientos.</p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Create plan dialog */}
      <TreatmentPlanForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSubmit={handleCreatePlan}
        isSubmitting={createPlan.isPending}
      />
    </div>
  )
}
