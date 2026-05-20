import { useState } from 'react'
import { Plus, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAppointments, useCreateAppointment, useAvailableSlots, useAppointmentTypes } from '@/hooks/useAppointments'
import { usePatients } from '@/hooks/usePatients'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { formatDate, formatTime } from '@/lib/utils'

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
// const HOURS = Array.from({ length: 12 }, (_, i) => i + 8) // 8 AM to 7 PM

export function AppointmentsPage() {
  const [currentWeekStart, setCurrentWeekStart] = useState(() => {
    const today = new Date()
    const day = today.getDay()
    const diff = today.getDate() - day + (day === 0 ? -6 : 1)
    return new Date(today.setDate(diff))
  })
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedDate, _setSelectedDate] = useState<string>('')
  const [selectedDentist, _setSelectedDentist] = useState('')

  const { data: appointmentsData } = useAppointments()
  const { data: patients } = usePatients({ page: 1 })
  const { data: appointmentTypes } = useAppointmentTypes()
  const { data: availableSlots } = useAvailableSlots({
    date: selectedDate,
    dentist: selectedDentist || undefined,
  })
  const createAppointment = useCreateAppointment()

  const [formData, setFormData] = useState({
    patient: '',
    type: '',
    dentist: '',
    date: '',
    start_time: '',
    notes: '',
  })

  const weekDays = Array.from({ length: 6 }, (_, i) => {
    const date = new Date(currentWeekStart)
    date.setDate(currentWeekStart.getDate() + i)
    return date
  })

  const prevWeek = () => {
    const newStart = new Date(currentWeekStart)
    newStart.setDate(currentWeekStart.getDate() - 7)
    setCurrentWeekStart(newStart)
  }

  const nextWeek = () => {
    const newStart = new Date(currentWeekStart)
    newStart.setDate(currentWeekStart.getDate() + 7)
    setCurrentWeekStart(newStart)
  }

  const getAppointmentsForDay = (date: Date) => {
    const dateStr = date.toISOString().split('T')[0]
    return appointmentsData?.results?.filter((a) => a.date === dateStr) || []
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'scheduled': return 'bg-blue-100 text-blue-800'
      case 'confirmed': return 'bg-green-100 text-green-800'
      case 'in_progress': return 'bg-amber-100 text-amber-800'
      case 'completed': return 'bg-gray-100 text-gray-800'
      case 'cancelled': return 'bg-red-100 text-red-800'
      case 'no_show': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await createAppointment.mutateAsync(formData)
    setDialogOpen(false)
    setFormData({ patient: '', type: '', dentist: '', date: '', start_time: '', notes: '' })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Citas</h2>
          <p className="text-muted-foreground">Gestiona las citas de tu clínica</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Nueva cita
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Agendar nueva cita</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="patient">Paciente</Label>
                <select
                  id="patient"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={formData.patient}
                  onChange={(e) => setFormData({ ...formData, patient: e.target.value })}
                  required
                >
                  <option value="">Seleccionar paciente</option>
                  {patients?.results?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.first_name} {p.last_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="type">Tipo de cita</Label>
                <select
                  id="type"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  required
                >
                  <option value="">Seleccionar tipo</option>
                  {appointmentTypes?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.duration_minutes} min)
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="dentist">Dentista</Label>
                <Input
                  id="dentist"
                  placeholder="ID del dentista"
                  value={formData.dentist}
                  onChange={(e) => setFormData({ ...formData, dentist: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date">Fecha</Label>
                <Input
                  id="date"
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="start_time">Hora</Label>
                <Input
                  id="start_time"
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notas</Label>
                <Input
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>
              <Button type="submit" className="w-full" disabled={createAppointment.isPending}>
                Agendar cita
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Week Navigation */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <Button variant="outline" size="icon" onClick={prevWeek}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <CardTitle>
              {formatDate(weekDays[0])} — {formatDate(weekDays[weekDays.length - 1])}
            </CardTitle>
            <Button variant="outline" size="icon" onClick={nextWeek}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Week Grid */}
          <div className="grid grid-cols-6 gap-2">
            {weekDays.map((day, idx) => {
              const dayAppointments = getAppointmentsForDay(day)
              const isToday = day.toDateString() === new Date().toDateString()

              return (
                <div key={idx} className="space-y-2">
                  <div className={`rounded-md p-2 text-center ${isToday ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                    <p className="text-xs font-medium">{DAYS[idx]}</p>
                    <p className="text-lg font-bold">{day.getDate()}</p>
                  </div>
                  <div className="space-y-1">
                    {dayAppointments.map((appt) => (
                      <div
                        key={appt.id}
                        className={`rounded-md p-2 text-xs ${getStatusColor(appt.status)}`}
                      >
                        <p className="font-medium">{formatTime(appt.start_time)}</p>
                        <p className="truncate">{appt.patient_name}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Available Slots */}
      {selectedDate && (
        <Card>
          <CardHeader>
            <CardTitle>Horarios disponibles — {formatDate(selectedDate)}</CardTitle>
          </CardHeader>
          <CardContent>
            {availableSlots?.length === 0 ? (
              <p className="text-sm text-muted-foreground">No hay horarios disponibles</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {availableSlots?.map((slot, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    onClick={() => setFormData({ ...formData, date: slot.date, start_time: slot.start_time })}
                  >
                    {formatTime(slot.start_time)}
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
