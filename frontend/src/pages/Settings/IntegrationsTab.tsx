import { useState } from 'react'
import { Calendar, Mail, MessageSquare, Plug, Unplug, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface IntegrationCardProps {
  title: string
  description: string
  icon: React.ElementType
  isConnected: boolean
  onToggle: () => void
  isPending: boolean
}

function IntegrationCard({ title, description, icon: Icon, isConnected, onToggle, isPending }: IntegrationCardProps) {
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
            onClick={onToggle}
            disabled={isPending}
            className="shrink-0"
          >
            {isPending ? (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            ) : isConnected ? (
              <Unplug className="mr-1 h-3 w-3" />
            ) : (
              <Plug className="mr-1 h-3 w-3" />
            )}
            {isConnected ? 'Desconectar' : 'Conectar'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function IntegrationsTab() {
  const [googleConnected, setGoogleConnected] = useState(false)
  const [gmailConnected, setGmailConnected] = useState(false)
  const [whatsappConnected, setWhatsappConnected] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)

  const handleToggle = (id: string, currentState: boolean, setter: (v: boolean) => void) => {
    setPendingId(id)
    // Simulate a brief interaction
    setTimeout(() => {
      setter(!currentState)
      setPendingId(null)
    }, 500)
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
        isConnected={googleConnected}
        isPending={pendingId === 'google-calendar'}
        onToggle={() => handleToggle('google-calendar', googleConnected, setGoogleConnected)}
      />

      <IntegrationCard
        title="Gmail"
        description="Envía correos electrónicos desde la plataforma usando tu cuenta de Gmail"
        icon={Mail}
        isConnected={gmailConnected}
        isPending={pendingId === 'gmail'}
        onToggle={() => handleToggle('gmail', gmailConnected, setGmailConnected)}
      />

      <IntegrationCard
        title="WhatsApp"
        description="Envía recordatorios automáticos de citas y notificaciones a través de WhatsApp"
        icon={MessageSquare}
        isConnected={whatsappConnected}
        isPending={pendingId === 'whatsapp'}
        onToggle={() => handleToggle('whatsapp', whatsappConnected, setWhatsappConnected)}
      />

      <Card className="bg-muted/30">
        <CardContent className="py-4 text-center">
          <p className="text-sm text-muted-foreground">
            Las integraciones con servicios externos estarán disponibles en una próxima actualización.
            Actualmente los botones son una vista previa del diseño.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
