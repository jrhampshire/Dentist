import { useState, useEffect } from 'react'
import { Save, ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react'
import { useFiscalConfig, useCreateFiscalConfig, useUpdateFiscalConfig, useValidateCsd } from '@/hooks/useFiscalConfig'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'

const REGIMEN_FISCAL_OPTIONS = [
  { value: '601', label: '601 - General de Ley Personas Morales' },
  { value: '603', label: '603 - Personas Morales sin Fines de Lucro' },
  { value: '605', label: '605 - Sueldos y Salarios' },
  { value: '606', label: '606 - Arrendamiento' },
  { value: '608', label: '608 - Demás ingresos' },
  { value: '610', label: '610 - Residentes en el Extranjero' },
  { value: '611', label: '611 - Dividendos' },
  { value: '612', label: '612 - Actividades Empresariales y Profesionales' },
  { value: '614', label: '614 - Intereses' },
  { value: '615', label: '615 - Premios' },
  { value: '616', label: '616 - Sin obligaciones fiscales' },
  { value: '620', label: '620 - Sociedades Cooperativas' },
  { value: '621', label: '621 - Incorporación Fiscal' },
  { value: '622', label: '622 - Actividades Agrícolas' },
  { value: '625', label: '625 - Plataformas Tecnológicas' },
  { value: '626', label: '626 - Régimen Simplificado de Confianza (RESICO)' },
]

interface FiscalAddressFields {
  calle: string
  no_exterior: string
  no_interior: string
  colonia: string
  localidad: string
  municipio: string
  estado: string
  pais: string
  codigo_postal: string
}

function parseAddress(data: Record<string, unknown> | undefined | null): FiscalAddressFields {
  return {
    calle: (data?.calle as string) || '',
    no_exterior: (data?.no_exterior as string) || '',
    no_interior: (data?.no_interior as string) || '',
    colonia: (data?.colonia as string) || '',
    localidad: (data?.localidad as string) || '',
    municipio: (data?.municipio as string) || '',
    estado: (data?.estado as string) || '',
    pais: (data?.pais as string) || '',
    codigo_postal: (data?.codigo_postal as string) || '',
  }
}

function buildAddress(fields: FiscalAddressFields): Record<string, unknown> {
  const addr: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(fields)) {
    if (value) addr[key] = value
  }
  return addr
}

export function FiscalConfigTab() {
  const { data: config, isLoading, isError, error } = useFiscalConfig()
  const createConfig = useCreateFiscalConfig()
  const updateConfig = useUpdateFiscalConfig()
  const validateCsd = useValidateCsd()

  const isEditing = !!config

  // Main form fields
  const [razonSocial, setRazonSocial] = useState('')
  const [regimenFiscal, setRegimenFiscal] = useState('')
  const [email, setEmail] = useState('')
  const [csdCertPath, setCsdCertPath] = useState('')
  const [csdKeyPath, setCsdKeyPath] = useState('')
  const [csdPassword, setCsdPassword] = useState('')
  const [addressFields, setAddressFields] = useState<FiscalAddressFields>({
    calle: '', no_exterior: '', no_interior: '', colonia: '',
    localidad: '', municipio: '', estado: '', pais: '', codigo_postal: '',
  })
  const [saved, setSaved] = useState(false)
  const [validateResult, setValidateResult] = useState<{ valid: boolean; message: string } | null>(null)

  // Initialize form when config loads
  useEffect(() => {
    if (config) {
      setRazonSocial(config.razon_social)
      setRegimenFiscal(config.regimen_fiscal)
      setEmail(config.email || '')
      setCsdCertPath(config.csd_cert_path || '')
      setCsdKeyPath(config.csd_key_path || '')
      setAddressFields(parseAddress(config.fiscal_address))
    }
  }, [config])

  const handleAddressChange = (field: keyof FiscalAddressFields, value: string) => {
    setAddressFields((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaved(false)

    const data = {
      razon_social: razonSocial,
      regimen_fiscal: regimenFiscal,
      email: email || undefined,
      csd_cert_path: csdCertPath || undefined,
      csd_key_path: csdKeyPath || undefined,
      fiscal_address: buildAddress(addressFields),
    }

    try {
      if (isEditing && config) {
        await updateConfig.mutateAsync({ id: config.id, data })
      } else {
        await createConfig.mutateAsync(data)
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      // Error handled by mutation state
    }
  }

  const handleValidateCsd = async () => {
    if (!config?.id || !csdPassword) return
    setValidateResult(null)

    try {
      const result = await validateCsd.mutateAsync({ id: config.id, password: csdPassword })
      setValidateResult(result)
    } catch {
      setValidateResult({ valid: false, message: 'Error al validar el CSD. Verifica la contraseña.' })
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>Datos Fiscales / CFDI 4.0</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
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
          <p className="text-destructive font-medium mb-2">Error al cargar datos fiscales</p>
          <p className="text-sm text-muted-foreground mb-4">
            {(error as { message?: string })?.message || 'No se pudieron cargar los datos fiscales'}
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
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Datos Fiscales / CFDI 4.0</CardTitle>
          {config?.rfc && (
            <p className="text-sm text-muted-foreground mt-1">RFC: {config.rfc}</p>
          )}
        </div>
        {config && (
          <Badge variant={config.is_validated ? 'success' : 'warning'}>
            <span className="flex items-center gap-1">
              {config.is_validated ? (
                <><ShieldCheck className="h-3 w-3" /> CSD Validado</>
              ) : (
                <><ShieldAlert className="h-3 w-3" /> CSD No validado</>
              )}
            </span>
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="razon-social">Razón Social</Label>
              <Input
                id="razon-social"
                value={razonSocial}
                onChange={(e) => setRazonSocial(e.target.value)}
                placeholder="Nombre o razón social del contribuyente"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="regimen-fiscal">Régimen Fiscal</Label>
              <select
                id="regimen-fiscal"
                value={regimenFiscal}
                onChange={(e) => setRegimenFiscal(e.target.value)}
                required
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="">Seleccionar régimen fiscal...</option>
                {REGIMEN_FISCAL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="fiscal-email">Email para facturas</Label>
              <Input
                id="fiscal-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="facturacion@clinica.com"
              />
            </div>
          </div>

          {/* Fiscal Address */}
          <div className="space-y-3">
            <Label>Dirección Fiscal</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Calle</Label>
                <Input value={addressFields.calle} onChange={(e) => handleAddressChange('calle', e.target.value)} placeholder="Calle" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">No. Exterior</Label>
                <Input value={addressFields.no_exterior} onChange={(e) => handleAddressChange('no_exterior', e.target.value)} placeholder="123" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">No. Interior</Label>
                <Input value={addressFields.no_interior} onChange={(e) => handleAddressChange('no_interior', e.target.value)} placeholder="A" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Colonia</Label>
                <Input value={addressFields.colonia} onChange={(e) => handleAddressChange('colonia', e.target.value)} placeholder="Colonia" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Localidad</Label>
                <Input value={addressFields.localidad} onChange={(e) => handleAddressChange('localidad', e.target.value)} placeholder="Localidad" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Municipio</Label>
                <Input value={addressFields.municipio} onChange={(e) => handleAddressChange('municipio', e.target.value)} placeholder="Municipio" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Estado</Label>
                <Input value={addressFields.estado} onChange={(e) => handleAddressChange('estado', e.target.value)} placeholder="Estado" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">País</Label>
                <Input value={addressFields.pais} onChange={(e) => handleAddressChange('pais', e.target.value)} placeholder="México" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Código Postal</Label>
                <Input value={addressFields.codigo_postal} onChange={(e) => handleAddressChange('codigo_postal', e.target.value)} placeholder="12345" />
              </div>
            </div>
          </div>

          {/* CSD Section */}
          <div className="space-y-3">
            <Label>CSD (Certificado de Sello Digital)</Label>
            <p className="text-xs text-muted-foreground">
              Ingresa las rutas de los archivos .cer y .key del CSD. Por ahora se admiten rutas de archivo; la carga de archivos estará disponible próximamente.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Ruta del archivo .cer</Label>
                <Input
                  value={csdCertPath}
                  onChange={(e) => setCsdCertPath(e.target.value)}
                  placeholder="/path/to/csd.cer"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Ruta del archivo .key</Label>
                <Input
                  value={csdKeyPath}
                  onChange={(e) => setCsdKeyPath(e.target.value)}
                  placeholder="/path/to/csd.key"
                />
              </div>
            </div>

            <div className="flex items-end gap-3">
              <div className="space-y-1 flex-1">
                <Label className="text-xs text-muted-foreground">Contraseña del CSD</Label>
                <Input
                  type="password"
                  value={csdPassword}
                  onChange={(e) => setCsdPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handleValidateCsd}
                disabled={!csdPassword || !config?.id || validateCsd.isPending}
              >
                {validateCsd.isPending ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Validando...</>
                ) : (
                  <>Validar CSD</>
                )}
              </Button>
            </div>

            {validateResult && (
              <div className={`text-sm ${validateResult.valid ? 'text-emerald-600' : 'text-destructive'}`}>
                {validateResult.valid ? '✓ ' : '✗ '}
                {validateResult.message}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={createConfig.isPending || updateConfig.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {createConfig.isPending || updateConfig.isPending
                ? 'Guardando...'
                : isEditing
                  ? 'Guardar cambios'
                  : 'Crear configuración fiscal'}
            </Button>
            {saved && (
              <span className="text-sm text-emerald-600 font-medium">
                ✓ Configuración guardada
              </span>
            )}
            {(createConfig.isError || updateConfig.isError) && (
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
