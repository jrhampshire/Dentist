import { useState } from 'react'
import { Edit3, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ProcedureForm } from './ProcedureForm'
import { PROC_STATUS_LABELS } from '@/types/dental-records'
import type { TreatmentProcedure } from '@/types/dental-records'

function getStatusBadgeVariant(status: string): 'info' | 'success' | 'destructive' | 'warning' | 'pending' {
  switch (status) {
    case 'planned':
      return 'info'
    case 'completed':
      return 'success'
    case 'cancelled':
      return 'destructive'
    case 'in_progress':
      return 'warning'
    default:
      return 'pending'
  }
}

function formatCost(cost: number): string {
  if (cost === 0) return '—'
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
  }).format(cost)
}

interface ProcedureListProps {
  procedures: TreatmentProcedure[]
  onEdit: (procId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => void
  onDelete: (procId: string) => void
  isEditing?: boolean
  isDeleting?: boolean
}

export function ProcedureList({
  procedures,
  onEdit,
  onDelete,
  isEditing = false,
  isDeleting = false,
}: ProcedureListProps) {
  const [editingId, setEditingId] = useState<string | null>(null)

  const handleEdit = (procId: string, data: { description: string; tooth_fdi?: number; cost?: number; status?: string; notes?: string }) => {
    onEdit(procId, data)
    setEditingId(null)
  }

  if (procedures.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No hay procedimientos en esta fase.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Descripción</TableHead>
            <TableHead className="text-xs w-16">Diente</TableHead>
            <TableHead className="text-xs w-24">Costo</TableHead>
            <TableHead className="text-xs w-24">Estado</TableHead>
            <TableHead className="text-xs w-20 text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {procedures.map((proc) => (
            <TableRow key={proc.id}>
              {editingId === proc.id ? (
                <TableCell colSpan={5} className="p-2">
                  <ProcedureForm
                    initialData={{
                      description: proc.description,
                      tooth_fdi: proc.tooth_fdi,
                      cost: proc.cost,
                      status: proc.status,
                      notes: proc.notes,
                    }}
                    onSubmit={(data) => handleEdit(proc.id, data)}
                    onCancel={() => setEditingId(null)}
                    isSubmitting={isEditing}
                  />
                </TableCell>
              ) : (
                <>
                  <TableCell className="text-sm">
                    <div>{proc.description}</div>
                    {proc.notes && (
                      <p className="text-xs text-muted-foreground mt-0.5">{proc.notes}</p>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-center">
                    {proc.tooth_fdi != null ? proc.tooth_fdi : '—'}
                  </TableCell>
                  <TableCell className="text-sm">
                    {formatCost(proc.cost)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={getStatusBadgeVariant(proc.status)} className="text-xs">
                      {PROC_STATUS_LABELS[proc.status] || proc.status_display}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setEditingId(proc.id)}
                        title="Editar procedimiento"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive"
                        onClick={() => onDelete(proc.id)}
                        disabled={isDeleting}
                        title="Eliminar procedimiento"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
