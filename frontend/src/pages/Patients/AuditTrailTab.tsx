import { useState } from 'react'
import { Search, Shield, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { useAuditTrail } from '@/hooks/useAuditTrail'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { getActionLabel, getResultLabel, formatAuditDate, formatDetails } from './auditHelpers'
import type { AuditLog } from '@/types'

interface AuditTrailTabProps {
  patientId: string
}

export function AuditTrailTab({ patientId }: AuditTrailTabProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [page, setPage] = useState(1)

  const {
    data,
    isLoading,
    isError,
    error,
  } = useAuditTrail('Patient', patientId, { page })

  const auditEntries = data?.results ?? []

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <XCircle className="h-12 w-12 mb-3 text-destructive opacity-60" />
        <p className="text-lg font-medium text-destructive">Error al cargar la auditoría</p>
        <p className="text-sm mt-2">
          {error instanceof Error ? error.message : 'No se pudo obtener el registro de auditoría.'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Auditoría</h3>
      </div>

      <Card>
        <CardContent className="p-0">
          {auditEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Search className="h-12 w-12 mb-3 opacity-40" />
              <p>No hay registros de auditoría</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10" />
                  <TableHead>Acción</TableHead>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Resultado</TableHead>
                  <TableHead className="text-right">Detalles</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditEntries.map((entry) => (
                  <AuditRow
                    key={entry.id}
                    entry={entry}
                    isExpanded={expandedId === entry.id}
                    onToggle={() => toggleExpand(entry.id)}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Mostrando {auditEntries.length} de {data.count} registros
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.previous}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Internal row component ---

function AuditRow({
  entry,
  isExpanded,
  onToggle,
}: {
  entry: AuditLog
  isExpanded: boolean
  onToggle: () => void
}) {
  const isSuccess = entry.result === 'success'
  const hasDetails = entry.details && Object.keys(entry.details).length > 0
  const detailsText = hasDetails ? formatDetails(entry.details) : null

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-muted/50"
        onClick={onToggle}
      >
        <TableCell>
          {isSuccess ? (
            <CheckCircle className="h-4 w-4 text-emerald-600" />
          ) : (
            <XCircle className="h-4 w-4 text-red-500" />
          )}
        </TableCell>
        <TableCell className="font-medium">
          <div className="flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-muted-foreground" />
            {getActionLabel(entry)}
          </div>
        </TableCell>
        <TableCell className="text-muted-foreground">
          {entry.user_name || 'Sistema'}
        </TableCell>
        <TableCell className="text-sm text-muted-foreground">
          {formatAuditDate(entry.created_at)}
        </TableCell>
        <TableCell className="text-sm font-mono text-muted-foreground">
          {entry.ip_address || '—'}
        </TableCell>
        <TableCell>
          <Badge variant={isSuccess ? 'success' : 'destructive'}>
            {getResultLabel(entry)}
          </Badge>
        </TableCell>
        <TableCell className="text-right">
          <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); onToggle() }}>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </TableCell>
      </TableRow>

      {/* Expandable details */}
      {isExpanded && hasDetails && (
        <TableRow>
          <TableCell colSpan={7} className="bg-muted/20">
            <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono p-2">
              {detailsText}
            </pre>
          </TableCell>
        </TableRow>
      )}
    </>
  )
}
