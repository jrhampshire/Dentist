import { useState } from 'react'
import { FileText, Edit3, History, ChevronDown, ChevronRight } from 'lucide-react'
import { useMedicalHistory, useMedicalHistoryVersions, useCreateMedicalHistory, useUpsertMedicalHistory } from '@/hooks/useMedicalHistory'
import { MedicalHistoryForm } from './MedicalHistoryForm'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { formatDateTime } from '@/lib/utils'
import type { MedicalHistory } from '@/types/dental-records'

interface MedicalHistoryTabProps {
  patientId: string
}

function AntecedentCard({ title, items, render }: { title: string; items: unknown[]; render: (item: unknown) => React.ReactNode }) {
  if (items.length === 0) return null
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground mb-2">{title}</h4>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-muted-foreground border-l-2 border-primary/30 pl-3">
            {render(item)}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ReadOnlyView({ record }: { record: MedicalHistory }) {
  return (
    <div className="space-y-6">
      <AntecedentCard
        title="Antecedentes Patológicos"
        items={record.antecedentes_patologicos}
        render={(a) => (
          <>
            <span className="font-medium text-foreground">{(a as { enfermedad: string }).enfermedad}</span>
            {(a as { notas: string }).notas && (
              <span className="block text-xs mt-0.5">{(a as { notas: string }).notas}</span>
            )}
          </>
        )}
      />
      <AntecedentCard
        title="Antecedentes Quirúrgicos"
        items={record.antecedentes_quirurgicos}
        render={(a) => (
          <>
            <span className="font-medium text-foreground">{(a as { procedimiento: string }).procedimiento}</span>
            {(a as { fecha: string }).fecha && (
              <span className="ml-2 text-xs">({(a as { fecha: string }).fecha})</span>
            )}
            {(a as { notas: string }).notas && (
              <span className="block text-xs mt-0.5">{(a as { notas: string }).notas}</span>
            )}
          </>
        )}
      />
      <AntecedentCard
        title="Antecedentes Alérgicos"
        items={record.antecedentes_alergicos}
        render={(a) => (
          <>
            <span className="font-medium text-foreground">{(a as { alergeno: string }).alergeno}</span>
            {(a as { reaccion: string }).reaccion && (
              <span className="ml-2">— {(a as { reaccion: string }).reaccion}</span>
            )}
            {(a as { notas: string }).notas && (
              <span className="block text-xs mt-0.5">{(a as { notas: string }).notas}</span>
            )}
          </>
        )}
      />
      <AntecedentCard
        title="Antecedentes Farmacológicos"
        items={record.antecedentes_farmacologicos}
        render={(a) => (
          <>
            <span className="font-medium text-foreground">{(a as { medicamento: string }).medicamento}</span>
            {(a as { dosis: string }).dosis && (
              <span className="ml-2 text-xs">({(a as { dosis: string }).dosis})</span>
            )}
            {(a as { notas: string }).notas && (
              <span className="block text-xs mt-0.5">{(a as { notas: string }).notas}</span>
            )}
          </>
        )}
      />
      <AntecedentCard
        title="Antecedentes Familiares"
        items={record.antecedentes_familiares}
        render={(a) => (
          <>
            <span className="font-medium text-foreground">{(a as { parentesco: string }).parentesco}</span>
            <span className="ml-2">— {(a as { enfermedad: string }).enfermedad}</span>
            {(a as { notas: string }).notas && (
              <span className="block text-xs mt-0.5">{(a as { notas: string }).notas}</span>
            )}
          </>
        )}
      />
      {record.motivo_consulta && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">Motivo de consulta</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{record.motivo_consulta}</p>
        </div>
      )}
      {record.enfermedad_actual && (
        <div>
          <h4 className="text-sm font-semibold text-foreground mb-1">Enfermedad actual</h4>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{record.enfermedad_actual}</p>
        </div>
      )}
      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
        <span>Versión {record.version}</span>
        {record.created_by_name && <span>Por: {record.created_by_name}</span>}
        <span>Actualizado: {formatDateTime(record.updated_at)}</span>
      </div>
    </div>
  )
}

function VersionHistory({ patientId }: { patientId: string }) {
  const { data: versions, isLoading } = useMedicalHistoryVersions(patientId)

  if (isLoading) {
    return (
      <div className="flex justify-center py-4">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!versions || versions.length <= 1) {
    return <p className="text-sm text-muted-foreground py-2">No hay versiones anteriores.</p>
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {versions
        .filter((v) => !v.is_active)
        .map((v) => (
          <div key={v.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
            <div>
              <span className="font-medium">Versión {v.version}</span>
              {v.created_by_name && (
                <span className="text-muted-foreground ml-2">— {v.created_by_name}</span>
              )}
            </div>
            <span className="text-xs text-muted-foreground">{formatDateTime(v.created_at)}</span>
          </div>
        ))}
    </div>
  )
}

export function MedicalHistoryTab({ patientId }: MedicalHistoryTabProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [showVersions, setShowVersions] = useState(false)

  const { data: history, isLoading, error } = useMedicalHistory(patientId)
  const createHistory = useCreateMedicalHistory()
  const upsertHistory = useUpsertMedicalHistory()

  const activeRecord: MedicalHistory | null =
    history && history.length > 0 ? history.find((h) => h.is_active) || history[0] : null

  const handleCreate = async (data: Record<string, unknown>) => {
    await createHistory.mutateAsync({ patientId, data })
    setIsEditing(false)
  }

  const handleUpdate = async (data: Record<string, unknown>) => {
    if (!activeRecord) return
    await upsertHistory.mutateAsync({ patientId, id: activeRecord.id, data })
    setIsEditing(false)
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
        <FileText className="h-12 w-12 mb-3 text-destructive opacity-40" />
        <p className="text-lg font-medium text-destructive">Error al cargar la historia médica</p>
        <p className="text-sm mt-2">No se pudieron obtener los datos. Verifica la conexión e intenta de nuevo.</p>
      </div>
    )
  }

  // Editing mode (create or update)
  if (isEditing) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">
            {activeRecord ? 'Editar Historia Médica' : 'Nueva Historia Médica'}
          </h3>
          <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
            Cancelar
          </Button>
        </div>
        <MedicalHistoryForm
          initialData={activeRecord || undefined}
          onSubmit={activeRecord ? handleUpdate : handleCreate}
          isSubmitting={createHistory.isPending || upsertHistory.isPending}
        />
      </div>
    )
  }

  // Empty state
  if (!activeRecord) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Historia Médica</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-12 border rounded-lg bg-muted/20 text-muted-foreground">
          <FileText className="h-12 w-12 mb-3 opacity-40" />
          <p className="text-lg font-medium">Sin historia médica</p>
          <p className="text-sm mt-2 max-w-sm text-center">
            No se ha registrado historia médica para este paciente.
          </p>
          <Button className="mt-4" onClick={() => setIsEditing(true)}>
            Crear historia médica
          </Button>
        </div>
      </div>
    )
  }

  // Active record view
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Historia Médica</h3>
        <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
          <Edit3 className="mr-2 h-4 w-4" />
          Editar
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          <ReadOnlyView record={activeRecord} />
        </CardContent>
      </Card>

      {/* Version history toggle */}
      <div>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => setShowVersions(!showVersions)}
        >
          <History className="h-4 w-4" />
          Historial de versiones
          {showVersions ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </button>
        {showVersions && (
          <div className="mt-2">
            <VersionHistory patientId={patientId} />
          </div>
        )}
      </div>
    </div>
  )
}
