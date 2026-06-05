# Design: Agenda con WhatsApp

## Technical Approach

Siete cambios quirúrgicos sobre código existente: 5 backend fixes críticos + 2 frontend indicators. Sin nuevas migraciones, sin nuevas tablas. El flujo completo ya existe — solo hay que conectar piezas rotas o faltantes.

## Architecture Decisions

### Decision: Signature validation — base64 encode, no decode

**Choice**: `base64.b64encode(expected).decode()` + `hmac.compare_digest()` contra el signature string
**Alternatives considered**: Seguir haciendo `b64decode()` en ambos lados (código actual, roto)
**Rationale**: `hmac.digest()` ya devuelve bytes raw. El signature de Twilio es un string base64. El bug actual decodifica el digest (bytes → garbage) y también decodifica el signature string (bytes → different garbage). La comparación falla siempre con bytes basura. Tests existentes generan el signature correctamente con `b64encode()`, confirmando que el fix es encode, no decode.

### Decision: process_whatsapp_response recibe webhook_id, no parámetros sueltos

**Choice**: El webhook guarda el `WhatsAppWebhook` y pasa su `webhook_id` al task, no `from_number`+`body`+`clinic_id`
**Alternatives considered**: Pasar params sueltos (firm actual del task)
**Rationale**: Ya existe el modelo `WhatsAppWebhook` con todos los datos. Pasar el ID evita duplicar datos en Celery, permite audit trail completo, y el task ya resuelve clinic/patient internamente. Solo ajustamos la firma del task para recibir `webhook_id` como string.

### Decision: Clinic resolution por phone + cfdi_config

**Choice**: Iterar `Clinic.objects.all()`, matchear `clinic.phone` o `clinic.cfdi_config.get("phone")`
**Alternatives considered**: Tabla de phone mappings (requiere migración), lookup inverso desde Appointment
**Rationale**: Sin migración nueva. El to_number del webhook es el número Twilio de la clínica, que está en `clinic.phone` o en `cfdi_config` para clínicas con fiscales configurados. Multi-tenant safe vs el `Clinic.objects.first()` actual.

### Decision: Consent check dual — opt_in + PatientConsent

**Choice**: Verificar `patient.whatsapp_opt_in` AND `PatientConsent.objects.filter(patient=patient, consent_type="whatsapp", signed=True).exists()`
**Alternatives considered**: Solo opt_in, solo PatientConsent
**Rationale**: `whatsapp_opt_in` es un flag rápido en Patient model. `PatientConsent` con type=whatsapp es el registro legal firmado. Ambos deben existir. El opt_in puede resetearse (UI toggle), el consent es inmutable una vez firmado.

### Decision: Appointment reschedule vía signal post_save

**Choice**: Signal `post_save` en Appointment que detecta status change de completed/cancelled → scheduled/confirmed y resetea `whatsapp_sent=False`
**Alternatives considered**: Override en `save()`, método `reschedule()` dedicado
**Rationale**: Hay múltiples paths que cambian el status (API, admin, importación). Un signal centralizado cubre todos sin riesgo de olvidar un path. El check de transition evita resets espurios.

### Decision: Template service en reminder — reemplazo directo

**Choice**: Llamar `render_template("appointment_reminder", {nombre, fecha, hora, doctor})` en lugar de f-string
**Alternatives considered**: Mantener f-string, template híbrido
**Rationale**: `template_service.py` ya existe con el template `appointment_reminder`. El reminder actual usa f-string con emojis que no están en el template aprobado de Twilio — el template service resuelve compliance con Twilio TOS. Variables mapean 1:1.

## Data Flow

```
Twilio Webhook POST
    │
    ▼
WebhookView.post()
    │
    ├─ validate_signature() ← FIX: compare_digest
    │
    ├─ _handle_inbound_message()
    │   ├─ WhatsAppWebhook.objects.create()
    │   ├─ _resolve_clinic(to_clean) ← FIX: phone lookup
    │   └─ process_whatsapp_response.delay(webhook_id) ← FIX: wire task
    │
    └─ _handle_status_callback()
        └─ Update NotificationLog

Celery Beat
    │
    ▼
send_appointment_reminders
    ├─ Check consent ← NEW: opt_in + PatientConsent
    ├─ render_template() ← FIX: usar template service
    ├─ TwilioService.send_message()
    ├─ NotificationLog.create()
    └─ Appointment.whatsapp_sent = True

Appointment reschedule
    │
    ▼
post_save signal ← NEW
    └─ whatsapp_sent = False
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/notifications/services/twilio_service.py` | Modify | Fix `validate_signature`: replace `b64decode(digest)` with `b64encode(digest).decode()` + `compare_digest` |
| `backend/notifications/views.py` | Modify | Wire `process_whatsapp_response.delay(webhook_id)` in `_handle_inbound_message`; fix `_resolve_clinic` to iterate clinics matching phone |
| `backend/celery_app/tasks.py` | Modify | `send_appointment_reminders`: add consent check + use `render_template`, `process_whatsapp_response`: accept `webhook_id` param |
| `backend/appointments/models.py` | Modify | No change needed — signal lives in `signals.py` (or `models.py` if signals not separated) |
| `backend/appointments/signals.py` | Create | `post_save` signal: detect completed/cancelled→scheduled transition, reset `whatsapp_sent=False` |
| `backend/appointments/apps.py` | Modify | Import signals module in `ready()` |
| `frontend/src/types/index.ts` | No change | `whatsapp_sent` y `whatsapp_response` ya existen en `Appointment` interface |
| `frontend/src/pages/AppointmentsPage.tsx` | Modify | Add WhatsApp badge (sent/response) in appointment detail dialog |
| `frontend/src/pages/Patients/PatientDetailPage.tsx` | Modify | Replace raw `whatsapp_opt_in` text with colored badge in Consent Status card |

### Detail: validate_signature fix

```python
# Current (BROKEN):
expected_b64 = b64decode(expected)     # digest bytes → garbage
provided_b64 = b64decode(signature)    # base64 string → different garbage
return hmac.compare_digest(expected_b64, provided_b64)

# Fixed:
expected_b64 = base64.b64encode(expected).decode("utf-8")  # digest → base64 string
return hmac.compare_digest(expected_b64, signature)        # string vs string
```

### Detail: _resolve_clinic fix

```python
# Current:
clinic = Clinic.objects.first()
return clinic.id if clinic else None

# Fixed:
for clinic in Clinic.objects.filter(is_deleted=False):
    if clinic.phone and clean_phone(clinic.phone) == phone_number:
        return clinic.id
    cfdi_phone = clinic.cfdi_config.get("phone", "")
    if cfdi_phone and clean_phone(cfdi_phone) == phone_number:
        return clinic.id
return None
```

### Detail: process_whatsapp_response new signature

```python
# Current:
def process_whatsapp_response(self, from_number: str, body: str, clinic_id: str | None = None):

# Fixed:
def process_whatsapp_response(self, webhook_id: str):
    webhook = WhatsAppWebhook.objects.get(id=webhook_id)
    from_number = webhook.from_number
    body = webhook.message_body
    # clinic already resolved from webhook.clinic_id
```

### Detail: Consent check in send_appointment_reminders

```python
# Before loop — add after `patient = appt.patient`:

# Check WhatsApp consent
if not patient.whatsapp_opt_in:
    logger.warning(f"Patient {patient.id} has whatsapp_opt_in=False, skipping")
    continue

from patients.models import PatientConsent
has_consent = PatientConsent.objects.filter(
    patient=patient,
    consent_type="whatsapp",
    signed=True,
).exists()
if not has_consent:
    logger.warning(f"Patient {patient.id} has no signed WhatsApp consent, skipping")
    continue
```

### Detail: Template service in reminder

```python
# Current:
body = f"Hola {patient.full_name}, te recordamos tu cita dental:\n\n..."  # f-string

# Fixed:
from notifications.services.template_service import render_template
body = render_template("appointment_reminder", {
    "nombre": patient.full_name,
    "fecha": appt.date.strftime("%d/%m/%Y"),
    "hora": appt.start_time.strftime("%H:%M"),
    "doctor": appt.dentist.get_full_name(),
})
```

### Detail: Appointment whatsapp_sent reset signal

```python
# appointments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Appointment)
def reset_whatsapp_on_reschedule(sender, instance, **kwargs):
    if not kwargs.get("update_fields"):
        return  # Only react to explicit saves
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    was_terminal = old.status in ("completed", "cancelled", "no_show")
    is_active = instance.status in ("scheduled", "confirmed")

    if was_terminal and is_active and old.whatsapp_sent:
        Appointment.objects.filter(pk=instance.pk).update(whatsapp_sent=False)
```

### Detail: Frontend WhatsApp indicators

```tsx
// In appointment detail dialog, add after status:
{detailAppointment.whatsapp_sent && (
  <div className="flex items-center gap-1 text-xs">
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${
      detailAppointment.whatsapp_response === 'confirmar' ? 'bg-green-100 text-green-800' :
      detailAppointment.whatsapp_response === 'cancelar' ? 'bg-red-100 text-red-800' :
      'bg-gray-100 text-gray-800'
    }`}>
      {detailAppointment.whatsapp_response === 'confirmar' ? '✅ Confirmada' :
       detailAppointment.whatsapp_response === 'cancelar' ? '❌ Cancelada' :
       '📤 WhatsApp enviado'}
    </span>
  </div>
)}

// In PatientDetailPage, replace raw text:
<InfoRow label="WhatsApp" value={
  patient.whatsapp_opt_in
    ? '✅ Aceptado'
    : '❌ No aceptado'
} />
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (contract) | `validate_signature` | 4 tests existentes (test_twilio_webhook.py) — deben pasar con el fix |
| Unit | `_resolve_clinic` | Test con múltiples clinics, con/sin phone, con cfdi_config |
| Unit | Consent check logic | Test dual condition (opt_in + PatientConsent) |
| Unit | `reset_whatsapp` signal | Test status transitions, test idempotencia |
| Integration | Webhook → task wiring | POST a webhook, verificar WhatsAppWebhook + task call |
| Integration | Reminder task | Mock Twilio, verify template rendering + consent skip |
| E2E | Frontend indicators | Visual: badge aparece cuando whatsapp_sent=True |

## Migration / Rollout

No migration required. Campos existentes (`whatsapp_sent`, `whatsapp_opt_in`, `PatientConsent.consent_type=whatsapp`) ya están en la DB. Rollback: revert commit, desactivar webhook en Twilio Console.

## Open Questions

None.

## Delivery Strategy

- **PR budget forecast**: ~350-400 lines (backend fixes ~250, signal + tests ~80, frontend ~50)
- **400-line budget risk**: Low (stays under 400)
- **Chained PRs recommended**: No (single PR viable)
- **Decision needed before apply**: No
