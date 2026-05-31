import { useState } from 'react'
import { AlertCircle, Stethoscope } from 'lucide-react'
import { useOdontogram, useCreateDentalRecord } from '@/hooks/useDentalRecords'
import { OdontogramSVG } from './OdontogramSVG'
import { SurfaceConditionModal } from './SurfaceConditionModal'
import { LegendPanel } from './LegendPanel'

interface OdontogramTabProps {
  patientId: string
}

export function OdontogramTab({ patientId }: OdontogramTabProps) {
  const [selectedTooth, setSelectedTooth] = useState<number | null>(null)
  const [selectedSurface, setSelectedSurface] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const { data: teeth, isLoading, error } = useOdontogram(patientId)
  const createRecord = useCreateDentalRecord()

  const handleSurfaceClick = (toothFdi: number, surface: string) => {
    setSelectedTooth(toothFdi)
    setSelectedSurface(surface)
    setModalOpen(true)
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setSelectedTooth(null)
    setSelectedSurface(null)
  }

  const handleSubmit = async (data: { tooth_fdi: number; surface: string; condition: string; notes?: string }) => {
    await createRecord.mutateAsync({
      patientId,
      data,
    })
    handleModalClose()
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="h-12 w-12 mb-3 text-destructive opacity-40" />
        <p className="text-lg font-medium text-destructive">Error al cargar el odontograma</p>
        <p className="text-sm mt-2">
          No se pudieron obtener los registros dentales. Verifica la conexión e intenta de nuevo.
        </p>
      </div>
    )
  }

  const hasData = teeth && teeth.length > 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Odontograma</h3>
      </div>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-12 border rounded-lg bg-muted/20 text-muted-foreground">
          <Stethoscope className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-lg font-medium">Odontograma vacío</p>
          <p className="text-sm mt-2 max-w-sm text-center">
            Haz clic sobre cualquier superficie de un diente para registrar su primera condición.
          </p>
        </div>
      ) : (
        <div className="border rounded-lg bg-background p-2 sm:p-4 overflow-x-auto">
          <OdontogramSVG teeth={teeth} onSurfaceClick={handleSurfaceClick} />
        </div>
      )}

      <LegendPanel />

      <SurfaceConditionModal
        open={modalOpen}
        onClose={handleModalClose}
        toothFdi={selectedTooth}
        surface={selectedSurface}
        onSubmit={handleSubmit}
        isSubmitting={createRecord.isPending}
      />
    </div>
  )
}
