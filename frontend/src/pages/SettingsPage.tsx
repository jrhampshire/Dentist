import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Building2, Receipt, Link2, CreditCard, CalendarClock } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { GeneralInfoTab } from './Settings/GeneralInfoTab'
import { FiscalConfigTab } from './Settings/FiscalConfigTab'
import { AppointmentTypesTab } from './Settings/AppointmentTypesTab'

const TABS = [
  { value: 'general', label: 'Información General', icon: Building2 },
  { value: 'fiscal', label: 'Datos Fiscales', icon: Receipt },
  { value: 'integrations', label: 'Integraciones', icon: Link2 },
  { value: 'plan', label: 'Plan y Suscripción', icon: CreditCard },
  { value: 'types', label: 'Tipos de Cita', icon: CalendarClock },
] as const

type TabValue = (typeof TABS)[number]['value']

function PlaceholderTab({ title, description }: { title: string; description: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Building2 className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground text-center max-w-md">
          {description}
        </p>
      </CardContent>
    </Card>
  )
}

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabFromUrl = searchParams.get('tab') as TabValue | null
  const validTab = TABS.find((t) => t.value === tabFromUrl)?.value ?? 'general'
  const [activeTab, setActiveTab] = useState<TabValue>(validTab)

  // Sync URL -> state on mount and popstate
  useEffect(() => {
    const currentTab = searchParams.get('tab') as TabValue | null
    if (currentTab && TABS.some((t) => t.value === currentTab)) {
      setActiveTab(currentTab)
    }
  }, [searchParams])

  // Sync state -> URL
  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value as TabValue)
      setSearchParams({ tab: value }, { replace: true })
    },
    [setSearchParams],
  )

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Configuración</h2>
        <p className="text-muted-foreground">
          Administra la información de tu clínica, datos fiscales, integraciones y más
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="w-full flex-wrap h-auto">
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value} className="gap-2">
              <tab.icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="general">
          <GeneralInfoTab />
        </TabsContent>

        <TabsContent value="fiscal">
          <FiscalConfigTab />
        </TabsContent>

        <TabsContent value="integrations">
          <PlaceholderTab
            title="Integraciones"
            description="Conecta tu clínica con Google Calendar, Gmail y WhatsApp para automatizar recordatorios y sincronizar citas. Esta sección estará disponible próximamente."
          />
        </TabsContent>

        <TabsContent value="plan">
          <PlaceholderTab
            title="Plan y Suscripción"
            description="Consulta los detalles de tu plan actual, timbres CFDI disponibles y fechas de suscripción. Esta sección estará disponible próximamente."
          />
        </TabsContent>

        <TabsContent value="types">
          <AppointmentTypesTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
