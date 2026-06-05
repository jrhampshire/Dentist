import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import { useClinic, useUpdateClinic } from '@/hooks/useClinic'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function GeneralInfoTab() {
  const { data: clinic, isLoading, isError, error } = useClinic()
  const updateClinic = useUpdateClinic()

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [saved, setSaved] = useState(false)

  // Initialize form when clinic data loads
  useEffect(() => {
    if (clinic) {
      setName(clinic.name)
      setPhone(clinic.phone || '')
      setAddress(
        clinic.address && typeof clinic.address === 'object'
          ? JSON.stringify(clinic.address, null, 2)
          : '',
      )
    }
  }, [clinic])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(false)

    let parsedAddress: Record<string, unknown> = {}
    if (address.trim()) {
      try {
        parsedAddress = JSON.parse(address)
      } catch {
        // If JSON parse fails, store as raw text
        parsedAddress = { raw: address }
      }
    }

    try {
      await updateClinic.mutateAsync({
        name,
        phone,
        address: parsedAddress,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      // Error handled by mutation state
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Información General</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-24 bg-muted rounded animate-pulse" />
              <div className="h-10 w-full bg-muted rounded animate-pulse" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-destructive font-medium mb-2">Error al cargar datos</p>
          <p className="text-sm text-muted-foreground mb-4">
            {(error as { message?: string })?.message || 'No se pudieron cargar los datos de la clínica'}
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Información General</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="clinic-name">Nombre de la clínica</Label>
              <Input
                id="clinic-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="clinic-rfc">RFC</Label>
              <Input
                id="clinic-rfc"
                value={clinic?.rfc || ''}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">El RFC se registró durante el onboarding y no puede modificarse</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="clinic-email">Email</Label>
              <Input
                id="clinic-email"
                value={clinic?.email || ''}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">El email se registró durante el onboarding y no puede modificarse</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="clinic-phone">Teléfono</Label>
              <Input
                id="clinic-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+52 55 1234 5678"
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="clinic-address">Dirección (JSON)</Label>
            <textarea
              id="clinic-address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono"
              placeholder='{"calle": "Ejemplo 123", "colonia": "Centro", "ciudad": "CDMX"}'
              rows={3}
            />
          </div>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={updateClinic.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateClinic.isPending ? 'Guardando...' : 'Guardar cambios'}
            </Button>
            {saved && (
              <span className="text-sm text-emerald-600 font-medium">
                ✓ Cambios guardados
              </span>
            )}
            {updateClinic.isError && (
              <span className="text-sm text-destructive font-medium">
                Error al guardar. Intenta de nuevo.
              </span>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
