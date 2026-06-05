import { useState } from 'react'
import { Calendar, Mail, MessageSquare, Plug, Loader2, Clock } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface IntegrationCardProps {
  title: string
  description: string
  icon: React.ElementType
  isConnected: boolean
  onConnect: () => void
  isPending: boolean
}

function IntegrationCard({ title, description, icon: Icon, isConnected, onConnect, isPending }: IntegrationCardProps) {
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
        </div>
      </CardContent>
    </Card>
  )
}

export function IntegrationsTab() {
  const [pendingId, setPendingId] = useState<string | null>(null)

  const handleConnect = (id: string) => {
    setPendingId(id)
    setTimeout(() => {
      alert(
        `Conectar con ${id === 'google-calendar' ? 'Google Calendar' : id === 'gmail' ? 'Gmail' : 'WhatsApp'} estará disponible en una próxima actualización.`,
      )
      setPendingId(null)
    }, 400)
  }

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
        isPending={pendingId === 'google-calendar'}
        onConnect={() => handleConnect('google-calendar')}
      />

      <IntegrationCard
        title="Gmail"
        description="Envía correos electrónicos desde la plataforma usando tu cuenta de Gmail"
        icon={Mail}
        isConnected={false}
        isPending={pendingId === 'gmail'}
        onConnect={() => handleConnect('gmail')}
      />

      <IntegrationCard
        title="WhatsApp"
        description="Envía recordatorios automáticos de citas y notificaciones a través de WhatsApp"
        icon={MessageSquare}
        isConnected={false}
        isPending={pendingId === 'whatsapp'}
        onConnect={() => handleConnect('whatsapp')}
      />

      <Card className="bg-muted/30">
        <CardContent className="py-4 text-center">
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>
              Las integraciones con servicios externos estarán disponibles en una próxima actualización.
              Esta sección es actualmente una vista previa del diseño.
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
