import { Link } from 'react-router-dom'
import { CalendarDays, Users, FileText, AlertTriangle, TrendingUp, Clock } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useAppointments } from '@/hooks/useAppointments'
import { usePatients } from '@/hooks/usePatients'
import { useInventoryAlerts } from '@/hooks/useInventory'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
// import { formatCurrency } from '@/lib/utils'

export function DashboardPage() {
  const { user, isAdmin, isRecepcionista } = useAuth()

  // Fetch summary data
  const { data: appointmentsData } = useAppointments({ page: 1 })
  const { data: patientsData } = usePatients({ page: 1 })
  const { data: alerts } = useInventoryAlerts()

  const todayAppointments = appointmentsData?.results?.filter((a) => {
    const apptDate = new Date(a.date)
    const today = new Date()
    return apptDate.toDateString() === today.toDateString()
  }) || []

  const pendingInvoices = appointmentsData?.results?.filter((a) => a.status === 'scheduled') || []

  const stats = [
    {
      title: 'Citas hoy',
      value: todayAppointments.length.toString(),
      icon: CalendarDays,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Pacientes totales',
      value: patientsData?.count?.toString() || '0',
      icon: Users,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Alertas inventario',
      value: alerts?.length?.toString() || '0',
      icon: AlertTriangle,
      color: 'text-amber-600',
      bgColor: 'bg-amber-50',
    },
    {
      title: 'Citas pendientes',
      value: pendingInvoices.length.toString(),
      icon: Clock,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight">
          Bienvenido, {user?.first_name || 'Usuario'}
        </h2>
        <p className="text-muted-foreground">
          Resumen de tu clínica — {new Date().toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <div className={`${stat.bgColor} rounded-md p-2`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Acciones rápidas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Link to="/patients">
              <Button variant="outline" className="w-full justify-start">
                <Users className="mr-2 h-4 w-4" />
                Nuevo paciente
              </Button>
            </Link>
            <Link to="/appointments">
              <Button variant="outline" className="w-full justify-start">
                <CalendarDays className="mr-2 h-4 w-4" />
                Agendar cita
              </Button>
            </Link>
            {(isAdmin || isRecepcionista) && (
              <Link to="/invoices">
                <Button variant="outline" className="w-full justify-start">
                  <FileText className="mr-2 h-4 w-4" />
                  Nueva factura
                </Button>
              </Link>
            )}
            {isAdmin && (
              <Link to="/inventory">
                <Button variant="outline" className="w-full justify-start">
                  <AlertTriangle className="mr-2 h-4 w-4" />
                  Ver alertas
                </Button>
              </Link>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Today's Appointments */}
      <Card>
        <CardHeader>
          <CardTitle>Citas de hoy</CardTitle>
        </CardHeader>
        <CardContent>
          {todayAppointments.length === 0 ? (
            <p className="text-sm text-muted-foreground">No hay citas programadas para hoy.</p>
          ) : (
            <div className="space-y-3">
              {todayAppointments.slice(0, 5).map((appointment) => (
                <div
                  key={appointment.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium">{appointment.patient_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {appointment.type_name} — {appointment.dentist_name}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{appointment.start_time}</p>
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                        appointment.status === 'confirmed'
                          ? 'bg-green-100 text-green-800'
                          : appointment.status === 'scheduled'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {appointment.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Inventory Alerts */}
      {alerts && alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5" />
              Alertas de inventario
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert, index) => (
                <div key={index} className="rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                  {alert.message}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
