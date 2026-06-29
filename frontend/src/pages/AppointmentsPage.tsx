import { useState } from 'react'
import { Plus, ChevronLeft, ChevronRight, CheckCircle, MessageCircle, CalendarClock } from 'lucide-react'
import { useAppointments, useCreateAppointment, useCompleteAppointment, useRescheduleAppointment, useAvailableSlots, useAppointmentTypes } from '@/hooks/useAppointments'
import { usePatients } from '@/hooks/usePatients'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { formatDate, formatTime, cn } from '@/lib/utils'
import type { Appointment, ApiError } from '@/types'

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
  const [detailAppointment, setDetailAppointment] = useState<Appointment | null>(null)
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false)
  const [completeError, setCompleteError] = useState<ApiError | null>(null)

  const [rescheduleOpen, setRescheduleOpen] = useState(false)
  const [rescheduleDate, setRescheduleDate] = useState('')
  const [rescheduleTime, setRescheduleTime] = useState('')
  const [rescheduleError, setRescheduleError] = useState<ApiError | null>(null)

  const { data: appointmentsData } = useAppointments()
  const { data: patients } = usePatients({ page: 1 })
  const { data: appointmentTypes } = useAppointmentTypes()
  const { data: availableSlots } = useAvailableSlots({
    date: selectedDate,
    dentist_id: selectedDentist || undefined,
  })
  const createAppointment = useCreateAppointment()
  const completeAppointment = useCompleteAppointment()
  const rescheduleAppointment = useRescheduleAppointment()

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

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'scheduled': return 'Programada'
      case 'confirmed': return 'Confirmada'
      case 'in_progress': return 'En curso'
      case 'completed': return 'Completada'
      case 'cancelled': return 'Cancelada'
      case 'no_show': return 'No asistió'
      default: return status
    }
  }

  const canComplete = (appt: Appointment) =>
    (appt.status === 'scheduled' || appt.status === 'confirmed' || appt.status === 'in_progress') &&
    !appt.inventory_consumed_at

  const handleCompleteClick = (appt: Appointment) => {
    setDetailAppointment(appt)
    setCompleteError(null)
    setCompleteDialogOpen(true)
  }

  const handleCompleteConfirm = async () => {
    if (!detailAppointment) return
    try {
      await completeAppointment.mutateAsync(detailAppointment.id)
      setCompleteDialogOpen(false)
      setDetailAppointment(null)
    } catch (err) {
      setCompleteError(err as ApiError)
    }
  }

  // Available slots for the reschedule dialog (driven by the picked date +
  // the appointment's dentist).
  const { data: rescheduleSlots } = useAvailableSlots({
    date: rescheduleDate,
    dentist_id: detailAppointment?.dentist || undefined,
  })

  const canReschedule = (appt: Appointment) => appt.status !== 'completed'

  const handleRescheduleClick = (appt: Appointment) => {
    setDetailAppointment(appt)
    setRescheduleDate(appt.date)
    setRescheduleTime(appt.start_time)
    setRescheduleError(null)
    setRescheduleOpen(true)
  }

  const handleRescheduleConfirm = async () => {
    if (!detailAppointment) return
    if (!rescheduleDate || !rescheduleTime) {
      setRescheduleError({ message: 'Selecciona una fecha y hora.' } as ApiError)
      return
    }
    try {
      await rescheduleAppointment.mutateAsync({
        id: detailAppointment.id,
        data: { date: rescheduleDate, start_time: rescheduleTime },
      })
      setRescheduleOpen(false)
      setDetailAppointment(null)
    } catch (err) {
      setRescheduleError(err as ApiError)
    }
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
                        className={`cursor-pointer rounded-md p-2 text-xs transition-shadow hover:shadow-md ${getStatusColor(appt.status)}`}
                        onClick={() => { setDetailAppointment(appt); setCompleteError(null) }}
                      >
                        <p className="font-medium">{formatTime(appt.start_time)}</p>
                        <p className="truncate">{appt.patient_name}</p>
                        {appt.whatsapp_sent && (
                          <MessageCircle className={cn(
                            'mt-0.5 h-3 w-3',
                            appt.whatsapp_response === 'confirmar' ? 'text-green-500' :
                            appt.whatsapp_response === 'cancelar' ? 'text-red-500' :
                            'text-gray-400'
                          )} />
                        )}
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
            {!availableSlots || availableSlots.total_available === 0 ? (
              <p className="text-sm text-muted-foreground">No hay horarios disponibles</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {availableSlots.slots.map((slot, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    onClick={() => setFormData({ ...formData, date: availableSlots.date, start_time: slot.start_time })}
                  >
                    {formatTime(slot.start_time)}
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Appointment Detail Dialog */}
      <Dialog open={!!detailAppointment && !completeDialogOpen} onOpenChange={(open) => { if (!open) setDetailAppointment(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Detalle de cita</DialogTitle>
          </DialogHeader>
          {detailAppointment && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <Label className="text-xs text-muted-foreground">Paciente</Label>
                  <p className="font-medium">{detailAppointment.patient_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Tipo</Label>
                  <p className="font-medium">{detailAppointment.type_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Dentista</Label>
                  <p className="font-medium">{detailAppointment.dentist_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Estado</Label>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${getStatusColor(detailAppointment.status)}`}>
                    {getStatusLabel(detailAppointment.status)}
                  </span>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Fecha</Label>
                  <p className="font-medium">{formatDate(detailAppointment.date)}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Hora</Label>
                  <p className="font-medium">{formatTime(detailAppointment.start_time)} — {formatTime(detailAppointment.end_time)}</p>
                </div>
              </div>
              {detailAppointment.whatsapp_sent && (
                <div className="flex items-center gap-2 rounded-md border px-3 py-2">
                  <MessageCircle className={cn(
                    'h-4 w-4',
                    detailAppointment.whatsapp_response === 'confirmar' ? 'text-green-600' :
                    detailAppointment.whatsapp_response === 'cancelar' ? 'text-red-600' :
                    'text-gray-400'
                  )} />
                  <span className={cn(
                    'text-xs font-medium',
                    detailAppointment.whatsapp_response === 'confirmar' ? 'text-green-700' :
                    detailAppointment.whatsapp_response === 'cancelar' ? 'text-red-700' :
                    'text-gray-500'
                  )}>
                    {detailAppointment.whatsapp_response === 'confirmar' ? 'WhatsApp Confirmado' :
                     detailAppointment.whatsapp_response === 'cancelar' ? 'WhatsApp Cancelado' :
                     'WhatsApp Enviado'}
                  </span>
                </div>
              )}
              {detailAppointment.notes && (
                <div>
                  <Label className="text-xs text-muted-foreground">Notas</Label>
                  <p className="text-sm">{detailAppointment.notes}</p>
                </div>
              )}
              {detailAppointment.inventory_consumed_at && (
                <div>
                  <Label className="text-xs text-muted-foreground">Inventario consumido</Label>
                  <p className="text-sm">{formatDate(detailAppointment.inventory_consumed_at)}</p>
                </div>
              )}
              {canComplete(detailAppointment) && (
                <Button className="w-full" onClick={() => handleCompleteClick(detailAppointment)}>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Completar cita
                </Button>
              )}
              {canReschedule(detailAppointment) && (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleRescheduleClick(detailAppointment)}
                >
                  <CalendarClock className="mr-2 h-4 w-4" />
                  Reagendar cita
                </Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Complete Confirmation Dialog */}
      <Dialog open={completeDialogOpen} onOpenChange={setCompleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Completar cita</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              ¿Consumir kit de inventario y marcar cita como completada?
            </p>
            {detailAppointment && (
              <p className="text-sm font-medium">
                Paciente: {detailAppointment.patient_name} — {detailAppointment.type_name}
              </p>
            )}
            {completeError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-medium text-red-800">{completeError.message}</p>
                {completeError.details && Array.isArray(completeError.details) && completeError.details.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {(completeError.details as Array<{ item_name: string; available: number; required: number }>).map((d, i) => (
                      <li key={i} className="text-xs text-red-700">
                        {d.item_name}: disponible {d.available}, requiere {d.required}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setCompleteDialogOpen(false)}>
                Cancelar
              </Button>
              <Button className="flex-1" onClick={handleCompleteConfirm} disabled={completeAppointment.isPending}>
                {completeAppointment.isPending ? 'Completando...' : 'Confirmar'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reschedule Dialog */}
      <Dialog open={rescheduleOpen} onOpenChange={setRescheduleOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reagendar cita</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {detailAppointment && (
              <p className="text-sm text-muted-foreground">
                {detailAppointment.patient_name} — {detailAppointment.type_name}
              </p>
            )}
            <div className="space-y-2">
              <Label htmlFor="reschedule-date">Nueva fecha</Label>
              <Input
                id="reschedule-date"
                type="date"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reschedule-time">Nueva hora</Label>
              <Input
                id="reschedule-time"
                type="time"
                value={rescheduleTime}
                onChange={(e) => setRescheduleTime(e.target.value)}
                required
              />
            </div>

            {/* Available slot quick-picks for the selected date */}
            {rescheduleDate && rescheduleSlots && rescheduleSlots.total_available > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Horarios disponibles</Label>
                <div className="flex flex-wrap gap-2">
                  {rescheduleSlots.slots.map((slot, idx) => (
                    <Button
                      key={idx}
                      type="button"
                      variant={rescheduleTime === slot.start_time ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setRescheduleTime(slot.start_time)}
                    >
                      {formatTime(slot.start_time)}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {rescheduleError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-medium text-red-800">
                  {rescheduleError.message || 'No se pudo reagendar la cita.'}
                </p>
              </div>
            )}

            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setRescheduleOpen(false)}>
                Cancelar
              </Button>
              <Button
                className="flex-1"
                onClick={handleRescheduleConfirm}
                disabled={rescheduleAppointment.isPending || !rescheduleDate || !rescheduleTime}
              >
                {rescheduleAppointment.isPending ? 'Reagendando...' : 'Confirmar reagendado'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
