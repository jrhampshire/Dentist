import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type {
  MedicalHistory,
  AntecedentePatologico,
  AntecedenteQuirurgico,
  AntecedenteAlergico,
  AntecedenteFarmacologico,
  AntecedenteFamiliar,
} from '@/types/dental-records'

interface MedicalHistoryFormProps {
  onSubmit: (data: Record<string, unknown>) => void
  initialData?: MedicalHistory
  isSubmitting?: boolean
}

function emptyPatologico(): AntecedentePatologico {
  return { enfermedad: '', notas: '' }
}

function emptyQuirurgico(): AntecedenteQuirurgico {
  return { procedimiento: '', fecha: '', notas: '' }
}

function emptyAlergico(): AntecedenteAlergico {
  return { alergeno: '', reaccion: '', notas: '' }
}

function emptyFarmacologico(): AntecedenteFarmacologico {
  return { medicamento: '', dosis: '', notas: '' }
}

function emptyFamiliar(): AntecedenteFamiliar {
  return { parentesco: '', enfermedad: '', notas: '' }
}

export function MedicalHistoryForm({ onSubmit, initialData, isSubmitting }: MedicalHistoryFormProps) {
  const [patologicos, setPatologicos] = useState<AntecedentePatologico[]>(
    initialData?.antecedentes_patologicos?.length
      ? initialData.antecedentes_patologicos
      : [emptyPatologico()]
  )
  const [quirurgicos, setQuirurgicos] = useState<AntecedenteQuirurgico[]>(
    initialData?.antecedentes_quirurgicos?.length
      ? initialData.antecedentes_quirurgicos
      : [emptyQuirurgico()]
  )
  const [alergicos, setAlergicos] = useState<AntecedenteAlergico[]>(
    initialData?.antecedentes_alergicos?.length
      ? initialData.antecedentes_alergicos
      : [emptyAlergico()]
  )
  const [farmacologicos, setFarmacologicos] = useState<AntecedenteFarmacologico[]>(
    initialData?.antecedentes_farmacologicos?.length
      ? initialData.antecedentes_farmacologicos
      : [emptyFarmacologico()]
  )
  const [familiares, setFamiliares] = useState<AntecedenteFamiliar[]>(
    initialData?.antecedentes_familiares?.length
      ? initialData.antecedentes_familiares
      : [emptyFamiliar()]
  )
  const [motivoConsulta, setMotivoConsulta] = useState(initialData?.motivo_consulta || '')
  const [enfermedadActual, setEnfermedadActual] = useState(initialData?.enfermedad_actual || '')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      antecedentes_patologicos: patologicos.filter((a) => a.enfermedad.trim()),
      antecedentes_quirurgicos: quirurgicos.filter((a) => a.procedimiento.trim()),
      antecedentes_alergicos: alergicos.filter((a) => a.alergeno.trim()),
      antecedentes_farmacologicos: farmacologicos.filter((a) => a.medicamento.trim()),
      antecedentes_familiares: familiares.filter((a) => a.enfermedad.trim() || a.parentesco.trim()),
      motivo_consulta: motivoConsulta,
      enfermedad_actual: enfermedadActual,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Antecedentes Patológicos */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Antecedentes Patológicos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {patologicos.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  placeholder="Enfermedad"
                  value={item.enfermedad}
                  onChange={(e) => {
                    const next = [...patologicos]
                    next[index] = { ...next[index], enfermedad: e.target.value }
                    setPatologicos(next)
                  }}
                />
                <Input
                  placeholder="Notas"
                  value={item.notas}
                  onChange={(e) => {
                    const next = [...patologicos]
                    next[index] = { ...next[index], notas: e.target.value }
                    setPatologicos(next)
                  }}
                />
              </div>
              {patologicos.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-1 text-muted-foreground hover:text-destructive"
                  onClick={() => setPatologicos(patologicos.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setPatologicos([...patologicos, emptyPatologico()])}
          >
            <Plus className="mr-1 h-3 w-3" />
            Agregar
          </Button>
        </CardContent>
      </Card>

      {/* Antecedentes Quirúrgicos */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Antecedentes Quirúrgicos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {quirurgicos.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  placeholder="Procedimiento"
                  value={item.procedimiento}
                  onChange={(e) => {
                    const next = [...quirurgicos]
                    next[index] = { ...next[index], procedimiento: e.target.value }
                    setQuirurgicos(next)
                  }}
                />
                <Input
                  placeholder="Fecha (ej. 2024-03-15)"
                  value={item.fecha}
                  onChange={(e) => {
                    const next = [...quirurgicos]
                    next[index] = { ...next[index], fecha: e.target.value }
                    setQuirurgicos(next)
                  }}
                />
                <Input
                  placeholder="Notas"
                  value={item.notas}
                  onChange={(e) => {
                    const next = [...quirurgicos]
                    next[index] = { ...next[index], notas: e.target.value }
                    setQuirurgicos(next)
                  }}
                />
              </div>
              {quirurgicos.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-1 text-muted-foreground hover:text-destructive"
                  onClick={() => setQuirurgicos(quirurgicos.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setQuirurgicos([...quirurgicos, emptyQuirurgico()])}
          >
            <Plus className="mr-1 h-3 w-3" />
            Agregar
          </Button>
        </CardContent>
      </Card>

      {/* Antecedentes Alérgicos */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Antecedentes Alérgicos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {alergicos.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  placeholder="Alérgeno"
                  value={item.alergeno}
                  onChange={(e) => {
                    const next = [...alergicos]
                    next[index] = { ...next[index], alergeno: e.target.value }
                    setAlergicos(next)
                  }}
                />
                <Input
                  placeholder="Reacción"
                  value={item.reaccion}
                  onChange={(e) => {
                    const next = [...alergicos]
                    next[index] = { ...next[index], reaccion: e.target.value }
                    setAlergicos(next)
                  }}
                />
                <Input
                  placeholder="Notas"
                  value={item.notas}
                  onChange={(e) => {
                    const next = [...alergicos]
                    next[index] = { ...next[index], notas: e.target.value }
                    setAlergicos(next)
                  }}
                />
              </div>
              {alergicos.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-1 text-muted-foreground hover:text-destructive"
                  onClick={() => setAlergicos(alergicos.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setAlergicos([...alergicos, emptyAlergico()])}
          >
            <Plus className="mr-1 h-3 w-3" />
            Agregar
          </Button>
        </CardContent>
      </Card>

      {/* Antecedentes Farmacológicos */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Antecedentes Farmacológicos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {farmacologicos.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  placeholder="Medicamento"
                  value={item.medicamento}
                  onChange={(e) => {
                    const next = [...farmacologicos]
                    next[index] = { ...next[index], medicamento: e.target.value }
                    setFarmacologicos(next)
                  }}
                />
                <Input
                  placeholder="Dosis"
                  value={item.dosis}
                  onChange={(e) => {
                    const next = [...farmacologicos]
                    next[index] = { ...next[index], dosis: e.target.value }
                    setFarmacologicos(next)
                  }}
                />
                <Input
                  placeholder="Notas"
                  value={item.notas}
                  onChange={(e) => {
                    const next = [...farmacologicos]
                    next[index] = { ...next[index], notas: e.target.value }
                    setFarmacologicos(next)
                  }}
                />
              </div>
              {farmacologicos.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-1 text-muted-foreground hover:text-destructive"
                  onClick={() => setFarmacologicos(farmacologicos.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setFarmacologicos([...farmacologicos, emptyFarmacologico()])}
          >
            <Plus className="mr-1 h-3 w-3" />
            Agregar
          </Button>
        </CardContent>
      </Card>

      {/* Antecedentes Familiares */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Antecedentes Familiares</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {familiares.map((item, index) => (
            <div key={index} className="flex gap-2 items-start">
              <div className="flex-1 space-y-2">
                <Input
                  placeholder="Parentesco"
                  value={item.parentesco}
                  onChange={(e) => {
                    const next = [...familiares]
                    next[index] = { ...next[index], parentesco: e.target.value }
                    setFamiliares(next)
                  }}
                />
                <Input
                  placeholder="Enfermedad"
                  value={item.enfermedad}
                  onChange={(e) => {
                    const next = [...familiares]
                    next[index] = { ...next[index], enfermedad: e.target.value }
                    setFamiliares(next)
                  }}
                />
                <Input
                  placeholder="Notas"
                  value={item.notas}
                  onChange={(e) => {
                    const next = [...familiares]
                    next[index] = { ...next[index], notas: e.target.value }
                    setFamiliares(next)
                  }}
                />
              </div>
              {familiares.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-1 text-muted-foreground hover:text-destructive"
                  onClick={() => setFamiliares(familiares.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setFamiliares([...familiares, emptyFamiliar()])}
          >
            <Plus className="mr-1 h-3 w-3" />
            Agregar
          </Button>
        </CardContent>
      </Card>

      {/* Motivo de consulta y enfermedad actual */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Motivo de Consulta y Enfermedad Actual</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="motivo_consulta">Motivo de consulta</Label>
            <textarea
              id="motivo_consulta"
              value={motivoConsulta}
              onChange={(e) => setMotivoConsulta(e.target.value)}
              rows={3}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="enfermedad_actual">Enfermedad actual</Label>
            <textarea
              id="enfermedad_actual"
              value={enfermedadActual}
              onChange={(e) => setEnfermedadActual(e.target.value)}
              rows={3}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
        </CardContent>
      </Card>

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? 'Guardando...' : 'Guardar'}
      </Button>
    </form>
  )
}
