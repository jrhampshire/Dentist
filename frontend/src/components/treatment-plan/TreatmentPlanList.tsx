import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatDate } from '@/lib/utils'
import { PLAN_STATUS_LABELS } from '@/types/dental-records'
import type { TreatmentPlanSummary } from '@/types/dental-records'
import { cn } from '@/lib/utils'

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

interface TreatmentPlanListProps {
  plans: TreatmentPlanSummary[]
  selectedPlanId?: string
  onSelectPlan: (planId: string) => void
  onCreatePlan: () => void
}

export function TreatmentPlanList({
  plans,
  selectedPlanId,
  onSelectPlan,
  onCreatePlan,
}: TreatmentPlanListProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Planes de Tratamiento</h3>
        <Button size="sm" onClick={onCreatePlan}>
          <Plus className="mr-1.5 h-4 w-4" />
          Crear Plan de Tratamiento
        </Button>
      </div>

      {plans.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-8 text-muted-foreground">
            <p className="text-sm">No hay planes de tratamiento.</p>
            <p className="text-xs mt-1">Crea uno nuevo para comenzar.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {plans.map((plan) => (
            <Card
              key={plan.id}
              className={cn(
                'cursor-pointer border-muted transition-colors hover:bg-muted/30',
                selectedPlanId === plan.id && 'border-primary bg-primary/5',
              )}
              onClick={() => onSelectPlan(plan.id)}
            >
              <CardContent className="p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-medium text-sm truncate">{plan.name}</h4>
                    {plan.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {plan.description}
                      </p>
                    )}
                  </div>
                  <Badge variant={getStatusBadgeVariant(plan.status)} className="text-xs shrink-0">
                    {PLAN_STATUS_LABELS[plan.status] || plan.status_display}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{plan.phases_count} fase{plan.phases_count !== 1 ? 's' : ''}</span>
                  <span>{formatDate(plan.created_at)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
