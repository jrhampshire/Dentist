import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  TOOTH_CONDITION_LABELS,
  SURFACE_LABELS,
  CONDITION_COLORS,
  type ToothCondition,
} from '@/types/dental-records'

const CONDITIONS: ToothCondition[] = [
  'healthy', 'caries', 'filling', 'crown', 'bridge',
  'missing', 'implant', 'root_canal', 'extraction',
  'fracture', 'wear', 'sealant', 'prosthesis', 'other',
]

interface SurfaceConditionModalProps {
  open: boolean
  onClose: () => void
  toothFdi: number | null
  surface: string | null
  onSubmit: (data: { tooth_fdi: number; surface: string; condition: string; notes?: string }) => void
  isSubmitting?: boolean
}

export function SurfaceConditionModal({
  open,
  onClose,
  toothFdi,
  surface,
  onSubmit,
  isSubmitting,
}: SurfaceConditionModalProps) {
  const [condition, setCondition] = useState<string>('healthy')
  const [notes, setNotes] = useState('')

  const surfaceLabel = surface ? SURFACE_LABELS[surface as keyof typeof SURFACE_LABELS] || surface : ''
  const selectedColor = CONDITION_COLORS[condition as ToothCondition] || '#e5e7eb'

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      if (!toothFdi || !surface || !condition) return
      onSubmit({
        tooth_fdi: toothFdi,
        surface,
        condition,
        notes: notes.trim() || undefined,
      })
    },
    [toothFdi, surface, condition, notes, onSubmit]
  )

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>
            Registrar Condición — Diente {toothFdi}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          {/* Surface display */}
          {surfaceLabel && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Superficie:</span>
              {surfaceLabel}
            </div>
          )}

          {/* Condition select */}
          <div className="space-y-2">
            <Label htmlFor="condition">Condición</Label>
            <select
              id="condition"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {CONDITIONS.map((c) => (
                <option key={c} value={c}>
                  {TOOTH_CONDITION_LABELS[c]}
                </option>
              ))}
            </select>
          </div>

          {/* Color swatch preview */}
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-5 w-5 rounded border border-border"
              style={{ backgroundColor: selectedColor === 'transparent' ? '#e5e7eb' : selectedColor }}
            />
            <span className="text-sm text-muted-foreground">
              {TOOTH_CONDITION_LABELS[condition as ToothCondition] || condition}
            </span>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notas (opcional)</Label>
            <textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Observaciones sobre la condición..."
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Registrar'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
