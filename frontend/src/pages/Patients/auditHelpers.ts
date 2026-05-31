import type { AuditLog } from '@/types'

/**
 * Translate backend action strings to Spanish labels.
 * NOM-024 audit action conventions.
 */
export const ACTION_LABELS: Record<string, string> = {
  'patient.created': 'Paciente creado',
  'patient.updated': 'Paciente actualizado',
  'patient.deleted': 'Paciente eliminado',
  'clinicalnote.created': 'Nota clínica creada',
  'clinicalnote.signed': 'Nota clínica firmada',
  'clinicalnote.updated': 'Nota clínica actualizada',
  'patientconsent.created': 'Consentimiento creado',
  'patientconsent.signed': 'Consentimiento firmado',
  'patientconsent.updated': 'Consentimiento actualizado',
}

/** Translate result to Spanish. */
export const RESULT_LABELS: Record<string, string> = {
  success: 'Éxito',
  failure: 'Error',
}

/** Format audit timestamp to locale string (es-MX). */
export function formatAuditDate(dateString: string): string {
  return new Date(dateString).toLocaleString('es-MX')
}

/**
 * Format audit details object into readable key-value pairs.
 * Skips internal/empty values for cleaner display.
 */
export function formatDetails(details: Record<string, unknown>): string {
  return Object.entries(details)
    .filter(([, v]) => v !== null && v !== undefined && String(v).length > 0)
    .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join('\n')
}

/** Get a translated action label (fallback to raw action string). */
export function getActionLabel(audit: AuditLog): string {
  return ACTION_LABELS[audit.action] || audit.action
}

/** Get Spanish result label with fallback. */
export function getResultLabel(audit: AuditLog): string {
  return RESULT_LABELS[audit.result] || audit.result
}
