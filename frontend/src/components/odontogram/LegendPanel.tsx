import {
  TOOTH_CONDITION_LABELS,
  CONDITION_COLORS,
  type ToothCondition,
} from '@/types/dental-records'

const CONDITIONS: ToothCondition[] = [
  'healthy', 'caries', 'filling', 'crown', 'bridge',
  'missing', 'implant', 'root_canal', 'extraction',
  'fracture', 'wear', 'sealant', 'prosthesis', 'other',
]

export function LegendPanel() {
  return (
    <div className="border rounded-lg p-4 bg-background">
      <h4 className="text-sm font-semibold mb-3">Leyenda de colores</h4>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        {CONDITIONS.map((condition) => {
          const color = CONDITION_COLORS[condition]
          return (
            <div key={condition} className="flex items-center gap-2">
              <span
                className="inline-block h-4 w-4 rounded-sm border border-border flex-shrink-0"
                style={{ backgroundColor: color === 'transparent' ? '#e5e7eb' : color }}
              />
              <span className="text-xs text-muted-foreground truncate">
                {TOOTH_CONDITION_LABELS[condition]}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
