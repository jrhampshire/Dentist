import { useState, useEffect } from 'react'
import { Plus, X, Search } from 'lucide-react'
import { useCreateAppointmentType, useUpdateAppointmentType } from '@/hooks/useAppointments'
import { useInventoryItems } from '@/hooks/useInventory'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { INVENTORY_CATEGORY_LABELS, type AppointmentType, type KitItem } from '@/types'

interface AppointmentTypeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  type: AppointmentType | null
}

export function AppointmentTypeDialog({ open, onOpenChange, type }: AppointmentTypeDialogProps) {
  const isEditing = !!type
  const createType = useCreateAppointmentType()
  const updateType = useUpdateAppointmentType()

  const [name, setName] = useState('')
  const [duration, setDuration] = useState(60)
  const [kitItems, setKitItems] = useState<KitItem[]>([])
  const [showAddItem, setShowAddItem] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
  const [itemQuantity, setItemQuantity] = useState(1)

  // Fetch inventory items for the kit editor dropdown
  const { data: inventoryData } = useInventoryItems({
    search: searchQuery || undefined,
  })

  // Initialize form when dialog opens
  useEffect(() => {
    if (open && type) {
      setName(type.name)
      setDuration(type.duration_minutes)
      setKitItems(type.inventory_kit || [])
    } else if (open && !type) {
      setName('')
      setDuration(60)
      setKitItems([])
    }
    setShowAddItem(false)
    setSearchQuery('')
    setSelectedItemId(null)
    setItemQuantity(1)
  }, [open, type])

  const handleAddItem = () => {
    if (selectedItemId && itemQuantity > 0) {
      // Prevent duplicate items
      if (kitItems.some((k) => k.item_id === selectedItemId)) {
        return
      }
      setKitItems([...kitItems, { item_id: selectedItemId, quantity: itemQuantity }])
      setSelectedItemId(null)
      setItemQuantity(1)
      setShowAddItem(false)
      setSearchQuery('')
    }
  }

  const handleRemoveItem = (itemId: string) => {
    setKitItems(kitItems.filter((k) => k.item_id !== itemId))
  }

  const getItemName = (itemId: string) => {
    const found = inventoryData?.results?.find((i) => i.id === itemId)
    return found ? found.name : itemId
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      name,
      duration_minutes: duration,
      inventory_kit: kitItems,
    }

    if (isEditing && type) {
      await updateType.mutateAsync({ id: type.id, data })
    } else {
      await createType.mutateAsync(data)
    }
    onOpenChange(false)
  }

  const inventoryItems = inventoryData?.results || []
  const isPending = createType.isPending || updateType.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Editar tipo de cita' : 'Nuevo tipo de cita'}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="type-name">Nombre</Label>
              <Input
                id="type-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type-duration">Duración (minutos)</Label>
              <Input
                id="type-duration"
                type="number"
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value) || 0)}
                min={5}
                required
              />
            </div>
          </div>

          {/* Kit Components */}
          <div className="space-y-3">
            <Label>Componentes del Kit (inventario)</Label>

            {kitItems.length > 0 && (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Producto</TableHead>
                      <TableHead>Cantidad</TableHead>
                      <TableHead className="w-[50px]" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {kitItems.map((ki) => (
                      <TableRow key={ki.item_id}>
                        <TableCell className="font-medium">
                          {getItemName(ki.item_id)}
                        </TableCell>
                        <TableCell>{ki.quantity}</TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            onClick={() => handleRemoveItem(ki.item_id)}
                            type="button"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Add item section */}
            {showAddItem ? (
              <div className="space-y-3 rounded-md border p-3">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar producto de inventario..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8"
                  />
                </div>

                <div className="max-h-44 overflow-y-auto rounded-md border">
                  {inventoryItems.length > 0 ? (
                    inventoryItems.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className={`w-full px-3 py-2 text-left text-sm hover:bg-accent transition-colors ${
                          selectedItemId === item.id ? 'bg-accent' : ''
                        } ${
                          kitItems.some((k) => k.item_id === item.id)
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                        onClick={() => {
                          if (kitItems.some((k) => k.item_id === item.id)) return
                          setSelectedItemId(
                            selectedItemId === item.id ? null : item.id,
                          )
                        }}
                        disabled={kitItems.some((k) => k.item_id === item.id)}
                      >
                        <span className="font-medium">{item.name}</span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {INVENTORY_CATEGORY_LABELS[item.category]} · Stock:{' '}
                          {item.stock_current}
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="px-3 py-4 text-center text-sm text-muted-foreground">
                      {searchQuery
                        ? 'No se encontraron productos'
                        : 'No hay productos en inventario'}
                    </p>
                  )}
                </div>

                {selectedItemId && (
                  <div className="flex items-center gap-3">
                    <Label
                      htmlFor="item-qty"
                      className="whitespace-nowrap text-xs"
                    >
                      Cantidad:
                    </Label>
                    <Input
                      id="item-qty"
                      type="number"
                      min={1}
                      value={itemQuantity}
                      onChange={(e) =>
                        setItemQuantity(parseInt(e.target.value) || 1)
                      }
                      className="w-20"
                    />
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleAddItem}
                      disabled={!selectedItemId || itemQuantity < 1}
                    >
                      Agregar
                    </Button>
                  </div>
                )}

                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowAddItem(false)
                    setSelectedItemId(null)
                    setSearchQuery('')
                  }}
                >
                  Cancelar
                </Button>
              </div>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowAddItem(true)}
              >
                <Plus className="mr-1 h-3 w-3" />
                Agregar componente
              </Button>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending
                ? 'Guardando...'
                : isEditing
                  ? 'Guardar cambios'
                  : 'Crear tipo de cita'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
