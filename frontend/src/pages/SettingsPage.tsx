import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Building2, Receipt, Link2, CreditCard, CalendarClock } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { GeneralInfoTab } from './Settings/GeneralInfoTab'
import { FiscalConfigTab } from './Settings/FiscalConfigTab'
import { IntegrationsTab } from './Settings/IntegrationsTab'
import { PlanSubscriptionTab } from './Settings/PlanSubscriptionTab'
import { AppointmentTypesTab } from './Settings/AppointmentTypesTab'

const TABS = [
  { value: 'general', label: 'Información General', icon: Building2 },
  { value: 'fiscal', label: 'Datos Fiscales', icon: Receipt },
  { value: 'integrations', label: 'Integraciones', icon: Link2 },
  { value: 'plan', label: 'Plan y Suscripción', icon: CreditCard },
  { value: 'types', label: 'Tipos de Cita', icon: CalendarClock },
] as const

type TabValue = (typeof TABS)[number]['value']

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
          <IntegrationsTab />
        </TabsContent>

        <TabsContent value="plan">
          <PlanSubscriptionTab />
        </TabsContent>

        <TabsContent value="types">
          <AppointmentTypesTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
