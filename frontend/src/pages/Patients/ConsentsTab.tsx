import { useState } from 'react'
import { Plus, Lock, CheckCircle, ClipboardCheck } from 'lucide-react'
import { useConsents, useCreateConsent } from '@/hooks/usePatientConsents'
import { useSignConsent } from '@/hooks/usePatientConsents'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CONSENT_TYPE_LABELS, type ConsentType } from '@/types'
import { formatDateTime } from '@/lib/utils'

interface ConsentsTabProps {
  patientId: string
}

export function ConsentsTab({ patientId }: ConsentsTabProps) {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newConsentType, setNewConsentType] = useState<ConsentType>('general')
  const [newContent, setNewContent] = useState('')
  const [newVersion, setNewVersion] = useState('1.0')
  const [signingConsentId, setSigningConsentId] = useState<string | null>(null)

  const { data: consents, isLoading } = useConsents(patientId)
  const createConsent = useCreateConsent()
  const signConsent = useSignConsent()

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newContent.trim()) return

    await createConsent.mutateAsync({
      patientId,
      data: { consent_type: newConsentType, content: newContent, version: newVersion },
    })
    setDialogOpen(false)
    setNewContent('')
    setNewConsentType('general')
    setNewVersion('1.0')
  }

  const handleSign = async (consentId: string) => {
    setSigningConsentId(consentId)
    try {
      await signConsent.mutateAsync({ patientId, consentId })
    } finally {
      setSigningConsentId(null)
    }
  }

  const getTypeBadge = (type: ConsentType) => {
    const variants: Record<ConsentType, 'info' | 'success' | 'warning' | 'default'> = {
      general: 'info',
      treatment: 'success',
      data_processing: 'warning',
      whatsapp: 'default',
    }
    return <Badge variant={variants[type]}>{CONSENT_TYPE_LABELS[type]}</Badge>
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Consentimientos</h3>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Consentimiento
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {(!consents || consents.length === 0) ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ClipboardCheck className="h-12 w-12 mb-3 opacity-40" />
              <p>No hay consentimientos registrados</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Versión</TableHead>
                  <TableHead>Contenido</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {consents.map((consent) => (
                  <TableRow key={consent.id}>
                    <TableCell>{getTypeBadge(consent.consent_type)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      v{consent.version}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {consent.content?.substring(0, 80)}{consent.content?.length > 80 ? '...' : ''}
                    </TableCell>
                    <TableCell>
                      {consent.signed ? (
                        <Badge variant="signed">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Firmado
                        </Badge>
                      ) : (
                        <Badge variant="pending">Pendiente</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {consent.signed_at
                        ? formatDateTime(consent.signed_at)
                        : formatDateTime(consent.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      {!consent.signed ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={signingConsentId === consent.id}
                          onClick={() => handleSign(consent.id)}
                        >
                          {signingConsentId === consent.id ? (
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                          ) : (
                            'Firmar'
                          )}
                        </Button>
                      ) : (
                        <Lock className="h-4 w-4 text-muted-foreground" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Consent Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nuevo Consentimiento</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="consent_type">Tipo de consentimiento</Label>
              <select
                id="consent_type"
                value={newConsentType}
                onChange={(e) => setNewConsentType(e.target.value as ConsentType)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {Object.entries(CONSENT_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="version">Versión</Label>
              <Input
                id="version"
                value={newVersion}
                onChange={(e) => setNewVersion(e.target.value)}
                placeholder="1.0"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="content">Contenido</Label>
              <textarea
                id="content"
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                rows={5}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                required
                placeholder="Texto del consentimiento informado..."
              />
            </div>
            <Button type="submit" className="w-full" disabled={createConsent.isPending}>
              {createConsent.isPending ? 'Creando...' : 'Crear consentimiento'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
