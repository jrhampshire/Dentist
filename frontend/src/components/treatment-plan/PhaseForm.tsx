import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PHASE_STATUS_LABELS } from '@/types/dental-records'
import type { PhaseStatus } from '@/types/dental-records'

interface PhaseFormData {
  name: string
  order?: number
  description?: string
  status?: string
}

interface PhaseFormProps {
  onSubmit: (data: PhaseFormData) => void
  onCancel: () => void
  initialData?: {
    name: string
    order: number
    description: string
    status: string
  }
  isSubmitting?: boolean
}

const STATUS_OPTIONS: PhaseStatus[] = ['pending', 'in_progress', 'completed', 'cancelled']

export function PhaseForm({
  onSubmit,
  onCancel,
  initialData,
  isSubmitting = false,
}: PhaseFormProps) {
  const [name, setName] = useState('')
  const [order, setOrder] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState<string>('pending')

  useEffect(() => {
    if (initialData) {
      setName(initialData.name || '')
      setOrder(initialData.order > 0 ? String(initialData.order) : '')
      setDescription(initialData.description || '')
      setStatus(initialData.status || 'pending')
    } else {
      setName('')
      setOrder('')
      setDescription('')
      setStatus('pending')
    }
  }, [initialData])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({
      name: name.trim(),
      order: order ? Number(order) : undefined,
      description: description.trim() || undefined,
      status: status || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border bg-muted/30 p-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="phase-name" className="text-xs">Nombre *</Label>
          <Input
            id="phase-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej. Fase 1: Higiene"
            required
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="phase-order" className="text-xs">Orden</Label>
          <Input
            id="phase-order"
            type="number"
            value={order}
            onChange={(e) => setOrder(e.target.value)}
            placeholder="1"
            min="0"
            className="h-8 text-sm"
          />
        </div>

        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="phase-description" className="text-xs">Descripción</Label>
          <textarea
            id="phase-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-1.5 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Descripción de la fase..."
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="phase-status" className="text-xs">Estado</Label>
          <select
            id="phase-status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {PHASE_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={isSubmitting}>
          Cancelar
        </Button>
        <Button type="submit" size="sm" disabled={isSubmitting || !name.trim()}>
          {isSubmitting ? 'Guardando...' : initialData ? 'Actualizar' : 'Agregar'}
        </Button>
      </div>
    </form>
  )
}
