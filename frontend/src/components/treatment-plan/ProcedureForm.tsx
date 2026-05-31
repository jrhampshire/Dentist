import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PROC_STATUS_LABELS } from '@/types/dental-records'
import type { ProcStatus } from '@/types/dental-records'

interface ProcedureFormData {
  description: string
  tooth_fdi?: number
  cost?: number
  status?: string
  notes?: string
}

interface ProcedureFormProps {
  onSubmit: (data: ProcedureFormData) => void
  onCancel: () => void
  initialData?: {
    description: string
    tooth_fdi: number | null
    cost: number
    status: string
    notes: string
  }
  isSubmitting?: boolean
}

const STATUS_OPTIONS: ProcStatus[] = ['planned', 'in_progress', 'completed', 'cancelled']

export function ProcedureForm({
  onSubmit,
  onCancel,
  initialData,
  isSubmitting = false,
}: ProcedureFormProps) {
  const [description, setDescription] = useState('')
  const [toothFdi, setToothFdi] = useState('')
  const [cost, setCost] = useState('')
  const [status, setStatus] = useState<string>('planned')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (initialData) {
      setDescription(initialData.description || '')
      setToothFdi(initialData.tooth_fdi != null ? String(initialData.tooth_fdi) : '')
      setCost(initialData.cost > 0 ? String(initialData.cost) : '')
      setStatus(initialData.status || 'planned')
      setNotes(initialData.notes || '')
    }
  }, [initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!description.trim()) return
    onSubmit({
      description: description.trim(),
      tooth_fdi: toothFdi ? Number(toothFdi) : undefined,
      cost: cost ? Number(cost) : undefined,
      status: status || undefined,
      notes: notes.trim() || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border bg-muted/30 p-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="proc-description" className="text-xs">Descripción *</Label>
          <Input
            id="proc-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Ej. Exodoncia diente 38"
            required
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="proc-fdi" className="text-xs">Diente (FDI)</Label>
          <Input
            id="proc-fdi"
            type="number"
            value={toothFdi}
            onChange={(e) => setToothFdi(e.target.value)}
            placeholder="Ej. 11"
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="proc-cost" className="text-xs">Costo</Label>
          <Input
            id="proc-cost"
            type="number"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            placeholder="0.00"
            min="0"
            step="0.01"
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="proc-status" className="text-xs">Estado</Label>
          <select
            id="proc-status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {PROC_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="proc-notes" className="text-xs">Notas</Label>
          <textarea
            id="proc-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Notas adicionales..."
          />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={isSubmitting}>
          Cancelar
        </Button>
        <Button type="submit" size="sm" disabled={isSubmitting || !description.trim()}>
          {isSubmitting ? 'Guardando...' : initialData ? 'Actualizar' : 'Agregar'}
        </Button>
      </div>
    </form>
  )
}
