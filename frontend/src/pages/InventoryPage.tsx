import { useState } from 'react'
import { Plus, AlertTriangle, Package, ArrowUpDown } from 'lucide-react'
import { useInventoryItems, useInventoryAlerts, useInventoryMovements, useCreateInventoryItem, useAdjustStock } from '@/hooks/useInventory'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { formatCurrency, formatDate } from '@/lib/utils'

export function InventoryPage() {
  const [page, setPage] = useState(1)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [adjustDialogOpen, setAdjustDialogOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<string | null>(null)

  const { data, isLoading } = useInventoryItems({ page, category: categoryFilter || undefined, search: search || undefined })
  const { data: alerts } = useInventoryAlerts()
  const { data: movements } = useInventoryMovements({ page: 1 })
  const createItem = useCreateInventoryItem()
  const adjustStock = useAdjustStock()

  const [formData, setFormData] = useState<{
    name: string
    category: 'consumable' | 'instrument' | 'medication' | 'equipment' | 'other'
    unit: string
    stock_current: number
    stock_minimum: number
    stock_maximum: number
    unit_price: number
    supplier: string
    barcode: string
  }>({
    name: '',
    category: 'consumable',
    unit: 'pieza',
    stock_current: 0,
    stock_minimum: 0,
    stock_maximum: 0,
    unit_price: 0,
    supplier: '',
    barcode: '',
  })

  const [adjustData, setAdjustData] = useState({
    quantity: 0,
    movement_type: 'entry',
    note: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await createItem.mutateAsync(formData)
    setDialogOpen(false)
    setFormData({ name: '', category: 'consumable', unit: 'pieza', stock_current: 0, stock_minimum: 0, stock_maximum: 0, unit_price: 0, supplier: '', barcode: '' })
  }

  const handleAdjust = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedItem) {
      await adjustStock.mutateAsync({ id: selectedItem, data: adjustData })
      setAdjustDialogOpen(false)
      setAdjustData({ quantity: 0, movement_type: 'entry', note: '' })
      setSelectedItem(null)
    }
  }

  const categories = ['consumable', 'instrument', 'medication', 'equipment', 'other']

  const getCategoryLabel = (cat: string) => {
    switch (cat) {
      case 'consumable': return 'Consumible'
      case 'instrument': return 'Instrumento'
      case 'medication': return 'Medicamento'
      case 'equipment': return 'Equipo'
      case 'other': return 'Otro'
      default: return cat
    }
  }

  const getStockStatus = (item: { stock_current: number; stock_minimum: number; is_expired: boolean }) => {
    if (item.is_expired) return { label: 'Vencido', color: 'bg-red-100 text-red-800' }
    if (item.stock_current <= item.stock_minimum) return { label: 'Stock bajo', color: 'bg-amber-100 text-amber-800' }
    return { label: 'Disponible', color: 'bg-green-100 text-green-800' }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Inventario</h2>
          <p className="text-muted-foreground">Control de stock y movimientos de inventario</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Nuevo producto
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Agregar producto al inventario</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nombre</Label>
                <Input id="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="category">Categoría</Label>
                  <select
                    id="category"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value as typeof formData.category })}
                  >
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>{getCategoryLabel(cat)}</option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit">Unidad</Label>
                  <Input id="unit" value={formData.unit} onChange={(e) => setFormData({ ...formData, unit: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="stock_current">Stock actual</Label>
                  <Input id="stock_current" type="number" value={formData.stock_current} onChange={(e) => setFormData({ ...formData, stock_current: parseInt(e.target.value) || 0 })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="stock_minimum">Stock mínimo</Label>
                  <Input id="stock_minimum" type="number" value={formData.stock_minimum} onChange={(e) => setFormData({ ...formData, stock_minimum: parseInt(e.target.value) || 0 })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="stock_maximum">Stock máximo</Label>
                  <Input id="stock_maximum" type="number" value={formData.stock_maximum} onChange={(e) => setFormData({ ...formData, stock_maximum: parseInt(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="unit_price">Precio unitario</Label>
                <Input id="unit_price" type="number" step="0.01" value={formData.unit_price} onChange={(e) => setFormData({ ...formData, unit_price: parseFloat(e.target.value) || 0 })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="supplier">Proveedor</Label>
                <Input id="supplier" value={formData.supplier} onChange={(e) => setFormData({ ...formData, supplier: e.target.value })} />
              </div>
              <Button type="submit" className="w-full" disabled={createItem.isPending}>
                Agregar producto
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Alerts */}
      {alerts && alerts.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-800">
              <AlertTriangle className="h-5 w-5" />
              Alertas de inventario ({alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert, idx) => (
                <div key={idx} className="rounded-md bg-white p-3 text-sm">
                  {alert.message}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inventory Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-2">
              <Button variant={categoryFilter === '' ? 'default' : 'outline'} size="sm" onClick={() => setCategoryFilter('')}>
                Todos
              </Button>
              {categories.map((cat) => (
                <Button
                  key={cat}
                  variant={categoryFilter === cat ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCategoryFilter(cat)}
                >
                  {getCategoryLabel(cat)}
                </Button>
              ))}
            </div>
            <Input
              placeholder="Buscar producto..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-xs"
            />
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
                    <TableHead>Producto</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead>Mín/Máx</TableHead>
                    <TableHead>Precio</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data?.results?.map((item) => {
                    const status = getStockStatus(item)
                    return (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">{item.name}</TableCell>
                        <TableCell>{getCategoryLabel(item.category)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Package className="h-3 w-3 text-muted-foreground" />
                            {item.stock_current}
                          </div>
                        </TableCell>
                        <TableCell>{item.stock_minimum} / {item.stock_maximum}</TableCell>
                        <TableCell>{formatCurrency(item.unit_price)}</TableCell>
                        <TableCell>
                          <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${status.color}`}>
                            {status.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setSelectedItem(item.id); setAdjustDialogOpen(true) }}
                          >
                            <ArrowUpDown className="mr-1 h-3 w-3" />
                            Ajustar
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {data?.results?.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        No se encontraron productos
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              {data && data.count > 0 && (
                <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                  <span>Mostrando {data.results.length} de {data.count} productos</span>
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

      {/* Movements Log */}
      <Card>
        <CardHeader>
          <CardTitle>Últimos movimientos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Cantidad</TableHead>
                <TableHead>Stock anterior</TableHead>
                <TableHead>Stock nuevo</TableHead>
                <TableHead>Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {movements?.results?.slice(0, 10).map((mov) => (
                <TableRow key={mov.id}>
                  <TableCell>{mov.item_name}</TableCell>
                  <TableCell>
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      mov.movement_type === 'entry' ? 'bg-green-100 text-green-800' :
                      mov.movement_type === 'exit' ? 'bg-red-100 text-red-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {mov.movement_type}
                    </span>
                  </TableCell>
                  <TableCell className={mov.quantity > 0 ? 'text-green-600' : 'text-red-600'}>
                    {mov.quantity > 0 ? '+' : ''}{mov.quantity}
                  </TableCell>
                  <TableCell>{mov.previous_stock}</TableCell>
                  <TableCell>{mov.new_stock}</TableCell>
                  <TableCell>{formatDate(mov.created_at)}</TableCell>
                </TableRow>
              ))}
              {movements?.results?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No hay movimientos registrados
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Adjust Stock Dialog */}
      <Dialog open={adjustDialogOpen} onOpenChange={setAdjustDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ajustar stock</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAdjust} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="movement_type">Tipo de movimiento</Label>
              <select
                id="movement_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={adjustData.movement_type}
                onChange={(e) => setAdjustData({ ...adjustData, movement_type: e.target.value })}
              >
                <option value="entry">Entrada</option>
                <option value="exit">Salida</option>
                <option value="adjustment">Ajuste</option>
                <option value="return">Devolución</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="quantity">Cantidad</Label>
              <Input
                id="quantity"
                type="number"
                value={adjustData.quantity}
                onChange={(e) => setAdjustData({ ...adjustData, quantity: parseInt(e.target.value) || 0 })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="note">Nota</Label>
              <Input
                id="note"
                value={adjustData.note}
                onChange={(e) => setAdjustData({ ...adjustData, note: e.target.value })}
              />
            </div>
            <Button type="submit" className="w-full" disabled={adjustStock.isPending}>
              Ajustar stock
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
