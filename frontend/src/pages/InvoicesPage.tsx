import { useState } from 'react'
import { FileText, Download, Stamp, X } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { invoicesApi } from '@/api/invoices'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { formatCurrency, formatDate } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

export function InvoicesPage() {
  const { isAdmin } = useAuth()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState<string | null>(null)
  const [cancelReason, setCancelReason] = useState('')

  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', { page, status: statusFilter || undefined }],
    queryFn: () => invoicesApi.list({ page, status: statusFilter || undefined }),
  })

  const stampMutation = useMutation({
    mutationFn: (id: string) => invoicesApi.stamp(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => invoicesApi.cancel(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      setCancelDialogOpen(false)
      setCancelReason('')
    },
  })

  const handleDownload = async (id: string, type: 'pdf' | 'xml') => {
    try {
      const blob = await (type === 'pdf' ? invoicesApi.downloadPdf(id) : invoicesApi.downloadXml(id))
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoice-${id}.${type}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch {
      alert('Error al descargar el archivo')
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-gray-100 text-gray-800'
      case 'pending': return 'bg-blue-100 text-blue-800'
      case 'stamped': return 'bg-green-100 text-green-800'
      case 'cancelled': return 'bg-red-100 text-red-800'
      case 'error': return 'bg-amber-100 text-amber-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'draft': return 'Borrador'
      case 'pending': return 'Pendiente'
      case 'stamped': return 'Timbrada'
      case 'cancelled': return 'Cancelada'
      case 'error': return 'Error'
      default: return status
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Facturas CFDI</h2>
          <p className="text-muted-foreground">Gestiona la facturación electrónica de tu clínica</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <FileText className="mr-2 h-4 w-4" />
              Nueva factura
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Crear factura (borrador)</DialogTitle>
            </DialogHeader>
            <form className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="patient">Paciente</Label>
                <Input id="patient" placeholder="ID del paciente" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rfc_receptor">RFC del receptor</Label>
                <Input id="rfc_receptor" placeholder="XAXX010101000" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nombre_receptor">Nombre del receptor</Label>
                <Input id="nombre_receptor" placeholder="Nombre completo" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="uso_cfdi">Uso de CFDI</Label>
                <select id="uso_cfdi" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="G03">G03 - Gastos en general</option>
                  <option value="P01">P01 - Por definir</option>
                </select>
              </div>
              <Button type="submit" className="w-full">
                Crear borrador
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex gap-2">
            <Button
              variant={statusFilter === '' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('')}
            >
              Todas
            </Button>
            <Button
              variant={statusFilter === 'pending' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('pending')}
            >
              Pendientes
            </Button>
            <Button
              variant={statusFilter === 'stamped' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('stamped')}
            >
              Timbradas
            </Button>
            <Button
              variant={statusFilter === 'cancelled' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('cancelled')}
            >
              Canceladas
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Folio</TableHead>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Fecha</TableHead>
                    <TableHead>Total</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.results?.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell className="font-medium">{invoice.folio || '—'}</TableCell>
                      <TableCell>{invoice.patient_name}</TableCell>
                      <TableCell>{formatDate(invoice.created_at)}</TableCell>
                      <TableCell className="font-medium">{formatCurrency(invoice.total)}</TableCell>
                      <TableCell>
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${getStatusBadge(invoice.status)}`}>
                          {getStatusLabel(invoice.status)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          {invoice.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => stampMutation.mutate(invoice.id)}
                              disabled={stampMutation.isPending}
                            >
                              <Stamp className="h-4 w-4" />
                            </Button>
                          )}
                          {invoice.status === 'stamped' && (
                            <>
                              <Button variant="ghost" size="icon" onClick={() => handleDownload(invoice.id, 'pdf')}>
                                <Download className="h-4 w-4" />
                              </Button>
                              {isAdmin && (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => { setSelectedInvoice(invoice.id); setCancelDialogOpen(true) }}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {data?.results?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        No se encontraron facturas
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              {data && data.count > 0 && (
                <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                  <span>Mostrando {data.results.length} de {data.count} facturas</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>
                      Anterior
                    </Button>
                    <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage(page + 1)}>
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancelar factura</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="cancel_reason">Motivo de cancelación</Label>
              <select id="cancel_reason" className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="01">01 - Comprobante emitido con errores con relación</option>
                <option value="02">02 - Comprobante emitido con errores sin relación</option>
                <option value="03">03 - No se llevó a cabo la operación</option>
                <option value="04">04 - Operación nominativa relacionada en una global</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="cancel_notes">Notas adicionales</Label>
              <Input
                id="cancel_notes"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
              />
            </div>
            <Button
              variant="destructive"
              className="w-full"
              onClick={() => selectedInvoice && cancelMutation.mutate({ id: selectedInvoice, reason: cancelReason })}
              disabled={cancelMutation.isPending}
            >
              Cancelar factura
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
