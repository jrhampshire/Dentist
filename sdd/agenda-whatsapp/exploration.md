# SDD Exploration: Agenda con WhatsApp

## Topic
Integrate WhatsApp reminders, 2-way confirmation/cancel, and consent management into the existing appointment scheduling system.

## Current State

### WhatsApp Infrastructure
- **Twilio service** (`backend/notifications/services/twilio_service.py`): `TwilioService` handles sending messages, signature validation, message parsing, and status callbacks. It has a critical bug in `validate_signature` (base64 decode on raw bytes instead of base64 string), causing 4 failing contract tests.
- **Template service** (`backend/notifications/services/template_service.py`): 5 pre-approved templates exist (reminder, confirmation, cancellation, rescheduled, test) but are completely unused by the reminder task.
- **Models** (`backend/notifications/models.py`): `NotificationLog` and `WhatsAppWebhook` are well-designed with tenant isolation, indexes, and lifecycle tracking (queued → sent → delivered → read/failed).
- **Webhook view** (`backend/notifications/views.py`): `WebhookView` receives inbound messages and status callbacks. Status callbacks update `NotificationLog`. Inbound messages are logged to `WhatsAppWebhook` but **never processed** — the view has a TODO to call `process_whatsapp_response` but doesn't.
- **URLs** (`backend/notifications/urls.py`): Public webhook at `/api/v1/whatsapp/webhook/`, logs, templates, and test-send endpoints exist.

### Appointment Reminder Automation
- **Celery task** `send_appointment_reminders` (`backend/celery_app/tasks.py`): Runs every 15 minutes via Celery Beat (`config/celery.py`).
- Finds scheduled/confirmed appointments in the next 24h where `whatsapp_sent=False`.
- Sends raw concatenated strings (not templates) via Twilio.
- **Does NOT check** `Patient.whatsapp_opt_in` or `PatientConsent.whatsapp`.
- Sets `whatsapp_sent=True` on the appointment after sending; this is never reset, so rescheduling won't trigger a new reminder.
- Does not pass `status_callback_url`, so delivery tracking depends on Twilio default behavior.

### 2-way WhatsApp (Confirm/Cancel)
- **Parser** (`TwilioService.parse_response`): Supports `confirmar`, `cancelar`, `baja` with keyword normalization and priority logic (baja wins).
- **Task** `process_whatsapp_response` (`backend/celery_app/tasks.py`): Fully implements:
  - Finding patient by phone and next upcoming appointment.
  - Confirming → status `confirmed`, sends confirmation reply.
  - Cancelling → status `cancelled`, sets `cancellation_reason`, sends cancellation reply.
  - Baja → logs opt-out, sends unsubscribe reply.
- **BUT** this task is orphaned — the webhook view never calls it. The inbound path is dead code.

### Consent Management
- **Model** (`backend/patients/models.py`):
  - `Patient.whatsapp_opt_in` (boolean, default True).
  - `PatientConsent` with `ConsentType.WHATSAPP` exists, supports signature tracking.
- **Frontend** (`frontend/src/pages/Patients/ConsentsTab.tsx`):
  - Users can create and sign consentimientos including `whatsapp`.
  - `PatientDetailPage` shows `whatsapp_opt_in` status in the Info tab.
- **Gap**: Neither the reminder task nor any backend logic checks consent before sending.

### Frontend
- **AppointmentsPage**: Shows appointment status, allows creation/completion. Does NOT show `whatsapp_sent`, `whatsapp_response`, or notification logs.
- **PatientDetailPage**: Shows `whatsapp_opt_in` as a boolean label. Consents tab is functional.
- No hooks or UI for notification logs per patient/appointment.

### Tests
- `tests/contract/test_twilio_webhook.py`: 8 tests — 4 parsing/callback tests pass, 4 signature validation tests fail due to the base64 padding bug in `validate_signature`.

## Affected Areas

| File | Why affected |
|------|--------------|
| `backend/notifications/services/twilio_service.py` | Fix `validate_signature` bug; base64 decode on raw bytes instead of signature string. |
| `backend/notifications/views.py` | Wire `process_whatsapp_response` into `_handle_inbound_message`; fix clinic resolution. |
| `backend/celery_app/tasks.py` | Reminder task must check consent, use templates, pass status callback, reset `whatsapp_sent` on reschedule. |
| `backend/appointments/models.py` | `whatsapp_sent` field needs logic to reset when appointment is rescheduled. |
| `backend/appointments/serializers.py` | `AppointmentSerializer` already exposes WhatsApp fields; may need new fields for consent check. |
| `backend/patients/models.py` | `whatsapp_opt_in` logic needs to be enforced; consider soft opt-out tracking. |
| `backend/config/celery.py` | Beat schedule is fine; may need queue adjustments for high-volume clinics. |
| `frontend/src/pages/AppointmentsPage.tsx` | Add WhatsApp indicators (sent, response) and manual trigger. |
| `frontend/src/pages/Patients/ConsentsTab.tsx` | Already functional; may need to link consent status to send eligibility. |

## Approaches

### Approach A: Minimal Fix + Wire Existing Code
- Fix `validate_signature` base64 bug.
- Wire `process_whatsapp_response` into `WebhookView._handle_inbound_message`.
- Add `patient__whatsapp_opt_in=True` to the reminder query.
- Add `status_callback_url` to the reminder task.
- **Pros**: Fastest, uses existing (good) code, low risk.
- **Cons**: Doesn't use templates, doesn't handle rescheduling reminders, doesn't check `PatientConsent.whatsapp`, clinic resolution is still a hack.
- **Effort**: Low

### Approach B: Full Integration (Recommended)
- Fix `validate_signature`.
- Refactor reminder task to use `template_service.py` (`appointment_reminder` template).
- Check BOTH `Patient.whatsapp_opt_in` AND `PatientConsent.whatsapp` before sending.
- Wire webhook to `process_whatsapp_response`.
- Reset `whatsapp_sent` when appointment date/time changes (in `Appointment.save` or serializer).
- Implement proper clinic→phone mapping table for multi-tenant webhook routing.
- Add frontend indicators: `whatsapp_sent`, `whatsapp_response` in appointment cards; notification log mini-view.
- **Pros**: Uses existing architecture correctly, legally compliant (consent-aware), multi-tenant safe, consistent user experience.
- **Cons**: More files touched, requires new clinic-phone mapping model/migration.
- **Effort**: Medium

### Approach C: Advanced Automation
- Everything in B, plus:
  - Smart retry logic for failed reminders (retry after X hours).
  - Additional templates: rescheduled, day-before reminder, no-show follow-up.
  - Admin dashboard for template management (move templates from Python dict to DB model).
  - Bulk WhatsApp actions from the frontend (send to all tomorrow's appointments).
- **Pros**: Most complete, future-proof.
- **Cons**: High effort, over-engineering for current scope.
- **Effort**: High

## Recommendation

**Approach B (Full Integration)**.

The codebase already has 80% of the needed pieces — they're just not wired together. The biggest risks are legal (sending without consent) and security (broken signature validation + fake clinic resolution). Approach B fixes these foundational issues while keeping the scope tight. Approach C can be a follow-up change.

## Risks

1. **Legal/Compliance**: Sending WhatsApp messages without explicit consent violates Mexican LFPDPPP and can trigger Twilio account suspension. The current code ignores both `whatsapp_opt_in` and `PatientConsent.whatsapp`.
2. **Security**: `validate_signature` bug means anyone can spoof Twilio webhooks. The `_resolve_clinic` hack routes all webhooks to the first clinic, breaking multi-tenant isolation.
3. **Data Integrity**: `whatsapp_sent` is a one-way flag. If a patient reschedules, no new reminder is sent.
4. **Dead Code**: `process_whatsapp_response` and `template_service.py` look maintained but are unreachable, creating a false sense of completion.
5. **Frontend Staleness**: Staff can't see if a reminder was sent or if a patient confirmed/cancelled via WhatsApp, leading to double-calling patients.

## Ready for Proposal

**Yes**.

The orchestrator should tell the user:
- The existing WhatsApp integration is partially built but has critical gaps: broken signature validation, no consent enforcement, and the 2-way reply system is disconnected.
- The recommended path is to wire the existing pieces together, fix the signature bug, enforce consent checks, and add frontend visibility.
- We should proceed to the **Proposal** phase for `agenda-whatsapp`.
