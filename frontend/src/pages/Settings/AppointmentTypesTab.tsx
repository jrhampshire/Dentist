import { useState } from 'react'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { useAppointmentTypes, useDeleteAppointmentType } from '@/hooks/useAppointments'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { AppointmentType } from '@/types'
import { AppointmentTypeDialog } from './AppointmentTypeDialog'

export function AppointmentTypesTab() {
  const { data: types, isLoading } = useAppointmentTypes()
  const deleteType = useDeleteAppointmentType()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingType, setEditingType] = useState<AppointmentType | null>(null)

  const handleEdit = (type: AppointmentType) => {
    setEditingType(type)
    setDialogOpen(true)
  }

  const handleNew = () => {
    setEditingType(null)
    setDialogOpen(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm('¿Eliminar este tipo de cita?')) {
      await deleteType.mutateAsync(id)
    }
  }

  const handleDialogClose = (open: boolean) => {
    setDialogOpen(open)
    if (!open) setEditingType(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Tipos de cita</h3>
          <p className="text-sm text-muted-foreground">
            Configura los tipos de consulta, duración y componentes de inventario asociados
          </p>
        </div>
        <Button onClick={handleNew} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Nuevo tipo de cita
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Todos los tipos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Duración (min)</TableHead>
                  <TableHead>Componentes del Kit</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {types?.map((type) => (
                  <TableRow key={type.id}>
                    <TableCell className="font-medium">{type.name}</TableCell>
                    <TableCell>{type.duration_minutes}</TableCell>
                    <TableCell>
                      {type.inventory_kit && type.inventory_kit.length > 0
                        ? `${type.inventory_kit.length} componente(s)`
                        : 'Sin kit'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(type)}>
                          <Pencil className="mr-1 h-3 w-3" />
                          Editar
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(type.id)}
                          disabled={deleteType.isPending}
                        >
                          <Trash2 className="mr-1 h-3 w-3" />
                          Eliminar
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {(!types || types.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No hay tipos de cita registrados
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <AppointmentTypeDialog
        open={dialogOpen}
        onOpenChange={handleDialogClose}
        type={editingType}
      />
    </div>
  )
}
