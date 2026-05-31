import { useState } from 'react'
import { Activity, Plus, Stethoscope } from 'lucide-react'
import { useVitalSigns, useCreateVitalSigns } from '@/hooks/useVitalSigns'
import { VitalSignsForm } from './VitalSignsForm'
import { VitalSignsHistory } from './VitalSignsHistory'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface VitalSignsTabProps {
  patientId: string
}

export function VitalSignsTab({ patientId }: VitalSignsTabProps) {
  const [showForm, setShowForm] = useState(false)

  const { data: records, isLoading, error } = useVitalSigns(patientId)
  const createVitalSigns = useCreateVitalSigns()

  const handleSubmit = async (data: Record<string, unknown>) => {
    await createVitalSigns.mutateAsync({ patientId, data })
    setShowForm(false)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Activity className="h-12 w-12 mb-3 text-destructive opacity-40" />
        <p className="text-lg font-medium text-destructive">Error al cargar los signos vitales</p>
        <p className="text-sm mt-2">No se pudieron obtener los datos. Verifica la conexión e intenta de nuevo.</p>
      </div>
    )
  }

  const sortedRecords = records
    ? [...records].sort(
        (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
      )
    : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Signos Vitales</h3>
        <Button variant={showForm ? 'ghost' : 'default'} onClick={() => setShowForm(!showForm)}>
          {showForm ? (
            'Cancelar'
          ) : (
            <>
              <Plus className="mr-2 h-4 w-4" />
              Nuevos Signos
            </>
          )}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-6">
            <VitalSignsForm onSubmit={handleSubmit} isSubmitting={createVitalSigns.isPending} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {sortedRecords.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Stethoscope className="h-12 w-12 mb-3 opacity-40" />
              <p className="text-lg font-medium">Sin registros</p>
              <p className="text-sm mt-2 max-w-sm text-center">
                No hay signos vitales registrados para este paciente.
              </p>
            </div>
          ) : (
            <VitalSignsHistory records={sortedRecords} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
