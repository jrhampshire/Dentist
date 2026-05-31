import { useState } from 'react'
import { Plus, Edit3, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { TreatmentPlanForm } from './TreatmentPlanForm'
import { PhaseList } from './PhaseList'
import { PhaseForm } from './PhaseForm'
import { PLAN_STATUS_LABELS } from '@/types/dental-records'
import type { TreatmentPlan } from '@/types/dental-records'

function getStatusBadgeVariant(status: string): 'info' | 'success' | 'destructive' {
  switch (status) {
    case 'active':
      return 'info'
    case 'completed':
      return 'success'
    case 'cancelled':
      return 'destructive'
    default:
      return 'info'
  }
}

interface TreatmentPlanDetailProps {
  plan: TreatmentPlan
  isUpdating?: boolean
  isDeleting?: boolean
  onUpdate: (data: { name: string; description?: string; status?: string }) => void
  onDelete: () => void
  onCreatePhase: (data: { name: string; description?: string; order?: number; status?: string }) => void
  onUpdatePhase: (phaseId: string, data: { name: string; description?: string; order?: number; status?: string }) => void
  onDeletePhase: (phaseId: string) => void
  onCreateProcedure: (phaseId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => void
  onUpdateProcedure: (phaseId: string, procId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => void
  onDeleteProcedure: (phaseId: string, procId: string) => void
}

export function TreatmentPlanDetail({
  plan,
  isUpdating = false,
  isDeleting = false,
  onUpdate,
  onDelete,
  onCreatePhase,
  onUpdatePhase,
  onDeletePhase,
  onCreateProcedure,
  onUpdateProcedure,
  onDeleteProcedure,
}: TreatmentPlanDetailProps) {
  const [editing, setEditing] = useState(false)
  const [addingPhase, setAddingPhase] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleUpdate = (data: { name: string; description?: string; status?: string }) => {
    onUpdate(data)
    setEditing(false)
  }

  const handleCreatePhase = (data: { name: string; description?: string; order?: number; status?: string }) => {
    onCreatePhase(data)
    setAddingPhase(false)
  }

  const handleDelete = () => {
    setConfirmDelete(false)
    onDelete()
  }

  const isSubmitting = isUpdating || isDeleting

  return (
    <div className="space-y-4">
      {/* Plan header */}
      {editing ? (
        <TreatmentPlanForm
          open={editing}
          onClose={() => setEditing(false)}
          onSubmit={handleUpdate}
          initialData={{
            name: plan.name,
            description: plan.description,
            status: plan.status,
          }}
          isSubmitting={isUpdating}
        />
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg truncate">{plan.name}</CardTitle>
                  <Badge variant={getStatusBadgeVariant(plan.status)} className="text-xs">
                    {PLAN_STATUS_LABELS[plan.status] || plan.status_display}
                  </Badge>
                </div>
                {plan.description && (
                  <p className="text-sm text-muted-foreground mt-1">{plan.description}</p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0 ml-2">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setEditing(true)}
                  title="Editar plan"
                >
                  <Edit3 className="h-4 w-4" />
                </Button>
                {confirmDelete ? (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleDelete}
                      disabled={isDeleting}
                    >
                      {isDeleting ? 'Eliminando...' : 'Confirmar'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmDelete(false)}
                    >
                      Cancelar
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    onClick={() => setConfirmDelete(true)}
                    title="Eliminar plan"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
        </Card>
      )}

      {/* Phases */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Fases ({plan.phases.length})
          </h4>
        </div>

        <PhaseList
          phases={plan.phases}
          onUpdatePhase={onUpdatePhase}
          onDeletePhase={onDeletePhase}
          onCreateProcedure={onCreateProcedure}
          onUpdateProcedure={onUpdateProcedure}
          onDeleteProcedure={onDeleteProcedure}
          isSubmitting={isSubmitting}
        />

        {addingPhase ? (
          <div className="mt-3">
            <PhaseForm
              onSubmit={handleCreatePhase}
              onCancel={() => setAddingPhase(false)}
              isSubmitting={isSubmitting}
            />
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="mt-3 w-full"
            onClick={() => setAddingPhase(true)}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Agregar Fase
          </Button>
        )}
      </div>
    </div>
  )
}
