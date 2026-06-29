import { useState } from 'react'
import { CreditCard, Stamp, CalendarDays, ShieldCheck, AlertTriangle, TrendingUp } from 'lucide-react'
import { useClinic } from '@/hooks/useClinic'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

const PLAN_LABELS: Record<string, string> = {
  free: 'Starter (Gratuito)',
  basic: 'Básico',
  pro: 'Pro',
}

const PLAN_PRICES: Record<string, string> = {
  free: '$0/mes',
  basic: '$299/mes',
  pro: '$599/mes',
}

const STATUS_LABELS: Record<string, { label: string; variant: 'success' | 'warning' | 'destructive' | 'secondary' }> = {
  active: { label: 'Activo', variant: 'success' },
  pending: { label: 'Pendiente', variant: 'warning' },
  suspended: { label: 'Suspendido', variant: 'destructive' },
  cancelled: { label: 'Cancelado', variant: 'secondary' },
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function PlanSubscriptionTab() {
  const { data: clinic, isLoading, isError, error } = useClinic()
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardContent className="p-6 space-y-4">
              <div className="h-6 w-48 bg-muted rounded animate-pulse" />
              <div className="h-4 w-32 bg-muted rounded animate-pulse" />
<div className="h-10 w-full bg-muted rounded animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-destructive font-medium mb-2">Error al cargar información del plan</p>
          <p className="text-sm text-muted-foreground mb-4">
            {(error as { message?: string })?.message || 'No se pudo cargar la información de la suscripción'}
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (!clinic) return null

  const planLabel = PLAN_LABELS[clinic.plan] || clinic.plan
  const planPrice = PLAN_PRICES[clinic.plan] || '—'
  const statusInfo = STATUS_LABELS[clinic.status] || { label: clinic.status, variant: 'secondary' as const }
  const isFree = clinic.plan === 'free'
  const stampsLow = clinic.stamps_remaining <= 10
  const stampsCritical = clinic.stamps_remaining <= 5
  const stampsColor = stampsCritical ? 'text-destructive' : stampsLow ? 'text-amber-600' : 'text-emerald-600'
  const stampsBg = stampsCritical ? 'bg-red-50' : stampsLow ? 'bg-amber-50' : 'bg-emerald-50'

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Plan y Suscripción</h3>
        <p className="text-sm text-muted-foreground">
          Información de tu plan actual y recursos disponibles
        </p>
      </div>

      {/* Plan Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              Plan Actual
            </CardTitle>
            <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-2xl font-bold">{planLabel}</p>
              <p className="text-sm text-muted-foreground">{planPrice}</p>
            </div>
            {isFree && (
              <Button className="shrink-0" size="sm" onClick={() => setUpgradeDialogOpen(true)}>
                <TrendingUp className="mr-2 h-4 w-4" />
                Actualizar plan
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stamps Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Stamp className="h-5 w-5 text-primary" />
            Timbres CFDI
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`rounded-lg p-4 ${stampsBg}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-3xl font-bold ${stampsColor}`}>
                  {clinic.stamps_remaining}
                </p>
                <p className="text-sm text-muted-foreground">timbres disponibles</p>
              </div>
              {stampsCritical && (
                <div className="flex items-center gap-1 text-destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm font-medium">Crítico</span>
                </div>
              )}
              {stampsLow && !stampsCritical && (
                <div className="flex items-center gap-1 text-amber-600">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-sm font-medium">Bajo</span>
                </div>
              )}
              {!stampsLow && (
                <div className="flex items-center gap-1 text-emerald-600">
                  <ShieldCheck className="h-4 w-4" />
                  <span className="text-sm font-medium">Disponible</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Subscription Dates Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-primary" />
            Suscripción
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Inicio</p>
              <p className="font-medium">{formatDate(clinic.subscription_start)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Fin</p>
              <p className="font-medium">{formatDate(clinic.subscription_end)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Upgrade plan dialog (no payment flow yet — route to support) */}
      <Dialog open={upgradeDialogOpen} onOpenChange={setUpgradeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Actualizar plan</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Contacta a soporte para actualizar tu plan. Aún no contamos con un
              proceso de pago en línea.
            </p>
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p className="font-medium">Soporte ClínicaSaaS</p>
              <a
                className="text-primary underline-offset-4 hover:underline"
                href="mailto:soporte@clinicasaas.mx?subject=Actualizar%20plan"
              >
                soporte@clinicasaas.mx
              </a>
            </div>
            <Button className="w-full" onClick={() => setUpgradeDialogOpen(false)}>
              Entendido
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
