import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface VitalSignsFormProps {
  onSubmit: (data: Record<string, unknown>) => void
  isSubmitting?: boolean
}

export function VitalSignsForm({ onSubmit, isSubmitting }: VitalSignsFormProps) {
  const [systolic, setSystolic] = useState('')
  const [diastolic, setDiastolic] = useState('')
  const [heartRate, setHeartRate] = useState('')
  const [temperature, setTemperature] = useState('')
  const [weight, setWeight] = useState('')
  const [height, setHeight] = useState('')
  const [notes, setNotes] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: Record<string, unknown> = {}
    if (systolic) data.blood_pressure_systolic = Number(systolic)
    if (diastolic) data.blood_pressure_diastolic = Number(diastolic)
    if (heartRate) data.heart_rate = Number(heartRate)
    if (temperature) data.temperature = Number(temperature)
    if (weight) data.weight = Number(weight)
    if (height) data.height = Number(height)
    if (notes) data.notes = notes
    onSubmit(data)
  }

  const hasAnyValue =
    systolic || diastolic || heartRate || temperature || weight || height

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Signos Vitales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Blood Pressure */}
          <div className="space-y-2">
            <Label>Presión Arterial (mmHg)</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                placeholder="Sistólica"
                min={60}
                max={250}
                value={systolic}
                onChange={(e) => setSystolic(e.target.value)}
                className="flex-1"
              />
              <span className="text-muted-foreground text-lg font-medium">/</span>
              <Input
                type="number"
                placeholder="Diastólica"
                min={30}
                max={150}
                value={diastolic}
                onChange={(e) => setDiastolic(e.target.value)}
                className="flex-1"
              />
            </div>
          </div>

          {/* Heart Rate */}
          <div className="space-y-2">
            <Label htmlFor="heart_rate">Frecuencia Cardíaca (bpm)</Label>
            <Input
              id="heart_rate"
              type="number"
              placeholder="60-100 bpm"
              min={30}
              max={250}
              value={heartRate}
              onChange={(e) => setHeartRate(e.target.value)}
            />
          </div>

          {/* Temperature */}
          <div className="space-y-2">
            <Label htmlFor="temperature">Temperatura (°C)</Label>
            <Input
              id="temperature"
              type="number"
              placeholder="36.5 °C"
              min={35}
              max={42}
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
            />
          </div>

          {/* Weight */}
          <div className="space-y-2">
            <Label htmlFor="weight">Peso (kg)</Label>
            <Input
              id="weight"
              type="number"
              placeholder="70 kg"
              min={1}
              max={300}
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </div>

          {/* Height */}
          <div className="space-y-2">
            <Label htmlFor="height">Talla (cm)</Label>
            <Input
              id="height"
              type="number"
              placeholder="170 cm"
              min={1}
              max={250}
              step="0.1"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
            />
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="vital_notes">Notas</Label>
            <textarea
              id="vital_notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              placeholder="Observaciones adicionales..."
            />
          </div>
        </CardContent>
      </Card>

      <Button type="submit" className="w-full" disabled={isSubmitting || !hasAnyValue}>
        {isSubmitting ? 'Registrando...' : 'Registrar'}
      </Button>
    </form>
  )
}
