import { Activity } from 'lucide-react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDateTime } from '@/lib/utils'
import type { VitalSigns } from '@/types/dental-records'

interface VitalSignsHistoryProps {
  records: VitalSigns[]
}

function formatBP(systolic: number | null, diastolic: number | null): string {
  if (systolic == null && diastolic == null) return '—'
  return `${systolic ?? '—'}/${diastolic ?? '—'}`
}

export function VitalSignsHistory({ records }: VitalSignsHistoryProps) {
  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Activity className="h-10 w-10 mb-2 opacity-30" />
        <p className="text-sm">No hay registros de signos vitales</p>
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Fecha</TableHead>
          <TableHead>Presión Arterial</TableHead>
          <TableHead>Frec. Cardíaca</TableHead>
          <TableHead>Temp</TableHead>
          <TableHead>Peso</TableHead>
          <TableHead>Talla</TableHead>
          <TableHead>Registrado por</TableHead>
          <TableHead>Notas</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.map((record) => (
          <TableRow key={record.id}>
            <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
              {formatDateTime(record.recorded_at)}
            </TableCell>
            <TableCell className="font-medium">
              {formatBP(record.blood_pressure_systolic, record.blood_pressure_diastolic)}
            </TableCell>
            <TableCell>
              {record.heart_rate != null ? `${record.heart_rate} bpm` : '—'}
            </TableCell>
            <TableCell>
              {record.temperature != null ? `${record.temperature} °C` : '—'}
            </TableCell>
            <TableCell>
              {record.weight != null ? `${record.weight} kg` : '—'}
            </TableCell>
            <TableCell>
              {record.height != null ? `${record.height} cm` : '—'}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {record.recorded_by_name || '—'}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground max-w-[150px] truncate">
              {record.notes || '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
