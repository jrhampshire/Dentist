import { useState } from 'react'
import { Plus, Edit3, Trash2, ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { PhaseForm } from './PhaseForm'
import { ProcedureList } from './ProcedureList'
import { ProcedureForm } from './ProcedureForm'
import { PHASE_STATUS_LABELS } from '@/types/dental-records'
import type { TreatmentPhase } from '@/types/dental-records'

function getPhaseStatusBadgeVariant(status: string): 'warning' | 'success' | 'destructive' | 'pending' {
  switch (status) {
    case 'in_progress':
      return 'warning'
    case 'completed':
      return 'success'
    case 'cancelled':
      return 'destructive'
    default:
      return 'pending'
  }
}

interface PhaseListProps {
  phases: TreatmentPhase[]
  onUpdatePhase: (phaseId: string, data: { name: string; order?: number; description?: string; status?: string }) => void
  onDeletePhase: (phaseId: string) => void
  onCreateProcedure: (phaseId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => void
  onUpdateProcedure: (phaseId: string, procId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => void
  onDeleteProcedure: (phaseId: string, procId: string) => void
  isSubmitting?: boolean
}

export function PhaseList({
  phases,
  onUpdatePhase,
  onDeletePhase,
  onCreateProcedure,
  onUpdateProcedure,
  onDeleteProcedure,
  isSubmitting = false,
}: PhaseListProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [editingPhaseId, setEditingPhaseId] = useState<string | null>(null)
  const [addingProcPhaseId, setAddingProcPhaseId] = useState<string | null>(null)

  const toggle = (phaseId: string) => {
    setExpanded((prev) => ({ ...prev, [phaseId]: !prev[phaseId] }))
  }

  const handleUpdatePhase = (phaseId: string, data: { name: string; order?: number; description?: string; status?: string }) => {
    onUpdatePhase(phaseId, data)
    setEditingPhaseId(null)
  }

  const handleCreateProcedure = (phaseId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => {
    onCreateProcedure(phaseId, data)
    setAddingProcPhaseId(null)
  }

  const sorted = [...phases].sort((a, b) => a.order - b.order)

  return (
    <div className="space-y-3">
      {sorted.map((phase) => {
        const isExpanded = !!expanded[phase.id]
        const isEditing = editingPhaseId === phase.id
        const isAddingProc = addingProcPhaseId === phase.id

        return (
          <Card key={phase.id} className="border-muted">
            <CardContent className="p-0">
              {isEditing ? (
                <div className="p-3">
                  <PhaseForm
                    initialData={{
                      name: phase.name,
                      order: phase.order,
                      description: phase.description,
                      status: phase.status,
                    }}
                    onSubmit={(data) => handleUpdatePhase(phase.id, data)}
                    onCancel={() => setEditingPhaseId(null)}
                    isSubmitting={isSubmitting}
                  />
                </div>
              ) : (
                <div>
                  {/* Phase header */}
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 p-3 text-left hover:bg-muted/30 transition-colors rounded-t-lg"
                    onClick={() => toggle(phase.id)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm truncate">{phase.name}</span>
                        <Badge variant={getPhaseStatusBadgeVariant(phase.status)} className="text-xs">
                          {PHASE_STATUS_LABELS[phase.status] || phase.status_display}
                        </Badge>
                      </div>
                      {phase.description && (
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {phase.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setEditingPhaseId(phase.id)}
                        title="Editar fase"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => onDeletePhase(phase.id)}
                        disabled={isSubmitting}
                        title="Eliminar fase"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </button>

                  {/* Expanded procedures */}
                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-3 border-t">
                      <ProcedureList
                        procedures={phase.procedures}
                        onEdit={(procId, data) => onUpdateProcedure(phase.id, procId, data)}
                        onDelete={(procId) => onDeleteProcedure(phase.id, procId)}
                        isEditing={isSubmitting}
                        isDeleting={isSubmitting}
                      />

                      {isAddingProc ? (
                        <ProcedureForm
                          onSubmit={(data) => handleCreateProcedure(phase.id, data)}
                          onCancel={() => setAddingProcPhaseId(null)}
                          isSubmitting={isSubmitting}
                        />
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full"
                          onClick={() => setAddingProcPhaseId(phase.id)}
                        >
                          <Plus className="mr-1.5 h-3.5 w-3.5" />
                          Agregar Procedimiento
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
