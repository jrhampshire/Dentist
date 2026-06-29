import { Calendar, Mail, MessageSquare, Plug, Loader2, Lock } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useWhatsAppStatus } from '@/hooks/useWhatsAppStatus'

interface IntegrationCardProps {
  title: string
  description: string
  icon: React.ElementType
  isConnected: boolean
  isPending: boolean
  disabled?: boolean
  disabledTooltip?: string
  onConnect?: () => void
}

function IntegrationCard({
  title,
  description,
  icon: Icon,
  isConnected,
  isPending,
  disabled,
  disabledTooltip,
  onConnect,
}: IntegrationCardProps) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className={`rounded-lg p-3 ${isConnected ? 'bg-emerald-50' : 'bg-muted'}`}>
              <Icon className={`h-6 w-6 ${isConnected ? 'text-emerald-600' : 'text-muted-foreground'}`} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold">{title}</h3>
                <Badge variant={isConnected ? 'success' : 'secondary'} className="text-[10px] px-1.5 py-0">
                  {isConnected ? 'Conectado' : 'Desconectado'}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{description}</p>
            </div>
          </div>
          {disabled ? (
            <Button
              variant="outline"
              size="sm"
              className="shrink-0"
              disabled
              title={disabledTooltip}
            >
              <Lock className="mr-1 h-3 w-3" />
              No disponible
            </Button>
          ) : (
            <Button
              variant={isConnected ? 'outline' : 'default'}
              size="sm"
              onClick={onConnect}
              disabled={isPending}
              className="shrink-0"
            >
              {isPending ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : isConnected ? (
                <>
                  <Plug className="mr-1 h-3 w-3" />
                  Desconectar
                </>
              ) : (
                <>
                  <Plug className="mr-1 h-3 w-3" />
                  Conectar
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function IntegrationsTab() {
  const { isConnected: whatsappConnected, isLoading: whatsappLoading } = useWhatsAppStatus()

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Integraciones</h3>
        <p className="text-sm text-muted-foreground">
          Conecta tu clínica con servicios externos para automatizar procesos
        </p>
      </div>

      <IntegrationCard
        title="Google Calendar"
        description="Sincroniza las citas de tu clínica con Google Calendar para tener todo en un solo lugar"
        icon={Calendar}
        isConnected={false}
        isPending={false}
        disabled
        disabledTooltip="Integración con Google Calendar aún no implementada"
      />

      <IntegrationCard
        title="Gmail"
        description="Envía correos electrónicos desde la plataforma usando tu cuenta de Gmail"
        icon={Mail}
        isConnected={false}
        isPending={false}
        disabled
        disabledTooltip="Integración con Gmail aún no implementada"
      />

      <IntegrationCard
        title="WhatsApp"
        description="Envía recordatorios automáticos de citas y notificaciones a través de WhatsApp"
        icon={MessageSquare}
        isConnected={whatsappConnected}
        isPending={whatsappLoading}
        disabled
        disabledTooltip={
          whatsappConnected
            ? 'Conectado vía Twilio. La configuración se gestiona en el backend.'
            : 'Conecta tus credenciales de Twilio en el backend para activar WhatsApp.'
        }
      />
    </div>
  )
}