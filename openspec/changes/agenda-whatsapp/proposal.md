# Proposal: Agenda con WhatsApp

## Intent

Integrar piezas existentes de WhatsApp para habilitar recordatorios de citas bidireccionales con seguridad y consentimiento adecuados. Actualmente el sistema tiene gaps críticos: validación de firma rota, webhook no procesa respuestas, sin verificación de consentimiento, y resolución de clínica incorrecta.

## Scope

### In Scope
1. **Fix `validate_signature`**: Corregir bug de base64 decode en validación de firma Twilio (4 tests fallando)
2. **Wire webhook a `process_whatsapp_response`**: Conectar inbound messages al task Celery existente (hoy tiene TODO comment)
3. **Fix clinic resolution**: Implementar `_resolve_clinic` con mapeo phone→clinic en lugar de `Clinic.objects.first()`
4. **Enforce consent en reminders**: Verificar `Patient.whatsapp_opt_in` y `PatientConsent.whatsapp` antes de enviar
5. **Reset `whatsapp_sent` en reschedule**: Marcar `whatsapp_sent=False` al reagenda para permitir nuevo recordatorio
6. **Frontend indicators**: Mostrar estado WhatsApp en appointment detail y patient profile (opt-in badge, last message status)

### Out of Scope
- Template editor UI (se usa `template_service.py` vía código)
- Bulk messaging / campañas
- Analytics dashboard de WhatsApp
- Integración con otros canales (SMS, email)

## Capabilities

> Contract con sdd-spec — cada capability nueva → `openspec/specs/{name}/spec.md`

### New Capabilities
- `whatsapp-consent`: Gestión de consentimiento para comunicaciones WhatsApp (opt-in, opt-out, tracking)
- `whatsapp-webhook`: Procesamiento de webhook inbound con validación de firma y routing a tasks
- `whatsapp-reminders`: Recordatorios de citas bidireccionales con confirmación/cancelación

### Modified Capabilities
- `appointment-reminders`: Se modifica para incluir canal WhatsApp + verificación de consentimiento
- `patient-consent`: Se extiende para incluir tipo `WHATSAPP` en `PatientConsent`

## Approach

Single PR (~400 líneas) — fixes backend + indicadores frontend:

1. **Backend fixes** (prioridad crítica):
   - `twilio_service.py`: Fix `validate_signature` — decode bytes correctamente
   - `views.py`: Wire `process_whatsapp_response` en `_handle_inbound_message`
   - `views.py`: Implement `_resolve_clinic` con lookup por phone mapping
   - `tasks.py`: Check `whatsapp_opt_in` + `PatientConsent.whatsapp` antes de enviar
   - `models.py`: Reset `whatsapp_sent` en appointment reschedule

2. **Frontend indicators** (UX):
   - Patient profile: Badge `whatsapp_opt_in` + last message status
   - Appointment detail: Indicator `whatsapp_sent` + response received
   - Color coding: verde (confirmed), rojo (cancelled), gris (pending)

3. **Security**:
   - Signature validation obligatoria en prod (allow-through solo en dev sin creds)
   - Log de intentos de signature inválida

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/notifications/services/twilio_service.py` | Modified | Fix `validate_signature` base64 decode bug |
| `backend/notifications/views.py` | Modified | Wire `process_whatsapp_response`, fix `_resolve_clinic` |
| `backend/celery_app/tasks.py` | Modified | Add consent checks en `send_appointment_reminders` |
| `backend/appointments/models.py` | Modified | Reset `whatsapp_sent` on reschedule |
| `backend/patients/models.py` | No change | Ya tiene `whatsapp_opt_in` + `PatientConsent` |
| `frontend/src/features/patients/` | New | WhatsApp opt-in badge, message history |
| `frontend/src/features/appointments/` | New | WhatsApp status indicators |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Legal (consentimiento)** | Medium | Check dual: `whatsapp_opt_in` + `PatientConsent.whatsapp` antes de enviar |
| **Security (signature spoofing)** | High | Fix `validate_signature` primero; log intentos inválidos; bloquer en prod |
| **Multi-tenant isolation** | Medium | Clinic phone mapping explícito; nunca `Clinic.objects.first()` |
| **WhatsApp spam** | Low | Rate limiting en Twilio; opt-out inmediato con `BAJA` |

## Rollback Plan

1. **Backend**: Revert commit → deploy anterior funciona (no hay migraciones destructivas)
2. **Frontend**: Feature flag `WHATSAPP_INDICATORS` (si existe) o revert UI changes
3. **Datos**: `whatsapp_sent` reset es idempotente; no hay data corruption risk
4. **Twilio**: Desactivar webhook en Twilio Console → stop inbound processing

## Dependencies

- Twilio account configurado (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`)
- Celery worker corriendo (tasks ya existen)
- Frontend: Componentes de patient/appointment detail existentes

## Success Criteria

- [ ] 4 tests de contrato de `validate_signature` pasan
- [ ] Webhook llama a `process_whatsapp_response` (sin TODO comment)
- [ ] Reminder NO se envía si `whatsapp_opt_in=False` o sin consentimiento
- [ ] Appointment reschedule resetea `whatsapp_sent=False`
- [ ] Frontend muestra badge opt-in en patient profile
- [ ] Frontend muestra status WhatsApp en appointment detail
