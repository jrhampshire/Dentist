import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, User, FileText, ClipboardCheck, Shield, Download, Stethoscope, Heart, Activity } from 'lucide-react'
import { usePatient } from '@/hooks/usePatients'
import { patientsApi } from '@/api/patients'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ClinicalNotesTab } from './ClinicalNotesTab'
import { ConsentsTab } from './ConsentsTab'
import { AuditTrailTab } from './AuditTrailTab'
import { OdontogramTab } from '../../components/odontogram/OdontogramTab'
import { MedicalHistoryTab } from '@/components/medical-history/MedicalHistoryTab'
import { VitalSignsTab } from '@/components/vital-signs/VitalSignsTab'
import { formatDate, formatPhone } from '@/lib/utils'

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState('info')

  const { data: patient, isLoading, error } = usePatient(id || '')

  const handleExport = async () => {
    if (!id) return
    try {
      const blob = await patientsApi.exportPatientData(id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `expediente_${id}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error al exportar expediente:', err)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (error || !patient) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => navigate('/patients')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a pacientes
        </Button>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <p className="text-lg font-medium text-destructive">Error al cargar el paciente</p>
            <p className="text-sm mt-2">
              {error instanceof Error ? error.message : 'El paciente no fue encontrado o no tienes acceso.'}
            </p>
            <Button variant="outline" className="mt-4" onClick={() => navigate('/patients')}>
              Volver a la lista
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const fullName = patient.full_name || `${patient.first_name} ${patient.last_name}`

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/patients')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold tracking-tight">{fullName}</h2>
          <p className="text-muted-foreground">
            {formatPhone(patient.phone)}{patient.email ? ` · ${patient.email}` : ''}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Exportar Expediente
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="w-full justify-start">
          <TabsTrigger value="info">
            <User className="mr-2 h-4 w-4" />
            Información
          </TabsTrigger>
          <TabsTrigger value="notes">
            <FileText className="mr-2 h-4 w-4" />
            Notas Clínicas
          </TabsTrigger>
          <TabsTrigger value="consents">
            <ClipboardCheck className="mr-2 h-4 w-4" />
            Consentimientos
          </TabsTrigger>
          <TabsTrigger value="audit">
            <Shield className="mr-2 h-4 w-4" />
            Auditoría
          </TabsTrigger>
          <TabsTrigger value="odontogram">
            <Stethoscope className="mr-2 h-4 w-4" />
            Odontograma
          </TabsTrigger>
          <TabsTrigger value="medical-history">
            <Heart className="mr-2 h-4 w-4" />
            Historia Médica
          </TabsTrigger>
          <TabsTrigger value="vital-signs">
            <Activity className="mr-2 h-4 w-4" />
            Signos Vitales
          </TabsTrigger>
        </TabsList>

        {/* Info Tab */}
        <TabsContent value="info">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Personal Info */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Datos Personales</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoRow label="Nombre completo" value={fullName} />
                <InfoRow label="Teléfono" value={formatPhone(patient.phone)} />
                {patient.email && <InfoRow label="Email" value={patient.email} />}
                {patient.curp && <InfoRow label="CURP" value={patient.curp} />}
                {patient.rfc && <InfoRow label="RFC" value={patient.rfc} />}
                <InfoRow label="Fecha de nacimiento" value={formatDate(patient.date_of_birth)} />
                <InfoRow label="Género" value={patient.gender} />
                {patient.blood_type && <InfoRow label="Tipo de sangre" value={patient.blood_type} />}
                {patient.occupation && <InfoRow label="Ocupación" value={patient.occupation} />}
              </CardContent>
            </Card>

            {/* Contact & Medical */}
            <div className="space-y-6">
              {/* Emergency Contact */}
              {(patient.emergency_contact_name || patient.emergency_contact_phone) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Contacto de Emergencia</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {patient.emergency_contact_name && (
                      <InfoRow label="Nombre" value={patient.emergency_contact_name} />
                    )}
                    {patient.emergency_contact_phone && (
                      <InfoRow label="Teléfono" value={formatPhone(patient.emergency_contact_phone)} />
                    )}
                    {patient.emergency_contact_relation && (
                      <InfoRow label="Parentesco" value={patient.emergency_contact_relation} />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Medical Info */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Información Médica</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <InfoRow label="Alergias" value={patient.allergies || 'Ninguna'} />
                  <InfoRow label="Condiciones crónicas" value={patient.chronic_conditions || 'Ninguna'} />
                  <InfoRow label="Medicamentos actuales" value={patient.current_medications || 'Ninguno'} />
                </CardContent>
              </Card>
            </div>

            {/* Insurance */}
            {(patient.insurance_provider || patient.insurance_policy_number) && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Seguro</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {patient.insurance_provider && (
                    <InfoRow label="Proveedor" value={patient.insurance_provider} />
                  )}
                  {patient.insurance_policy_number && (
                    <InfoRow label="Número de póliza" value={patient.insurance_policy_number} />
                  )}
                </CardContent>
              </Card>
            )}

            {/* Consent Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Consentimientos</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <InfoRow
                  label="Consentimiento general"
                  value={patient.consent_signed ? 'Firmado' : 'Pendiente'}
                />
                {patient.consent_signed_at && (
                  <InfoRow label="Fecha de firma" value={formatDate(patient.consent_signed_at)} />
                )}
                {patient.consent_version && (
                  <InfoRow label="Versión" value={patient.consent_version} />
                )}
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">WhatsApp</dt>
                  <dd className="mt-1">
                    {patient.whatsapp_opt_in ? (
                      <span className="inline-flex items-center gap-1.5 text-sm text-green-700">
                        <span className="h-2 w-2 rounded-full bg-green-500" />
                        Aceptado
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-sm text-red-700">
                        <span className="h-2 w-2 rounded-full bg-red-500" />
                        No aceptado
                      </span>
                    )}
                  </dd>
                </div>
                <InfoRow label="Email" value={patient.email_opt_in ? 'Aceptado' : 'No aceptado'} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Clinical Notes Tab */}
        <TabsContent value="notes">
          <ClinicalNotesTab patientId={patient.id} />
        </TabsContent>

        {/* Consents Tab */}
        <TabsContent value="consents">
          <ConsentsTab patientId={patient.id} />
        </TabsContent>

        {/* Audit Trail Tab (NOM-024) */}
        <TabsContent value="audit">
          <AuditTrailTab patientId={patient.id} />
        </TabsContent>

        {/* Odontogram Tab */}
        <TabsContent value="odontogram">
          <OdontogramTab patientId={patient.id} />
        </TabsContent>

        {/* Medical History Tab */}
        <TabsContent value="medical-history">
          <MedicalHistoryTab patientId={patient.id} />
        </TabsContent>

        {/* Vital Signs Tab */}
        <TabsContent value="vital-signs">
          <VitalSignsTab patientId={patient.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// Helper
function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm">{value || '—'}</dd>
    </div>
  )
}
