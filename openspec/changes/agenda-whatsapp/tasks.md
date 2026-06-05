# Tasks: Agenda con WhatsApp

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~350-400 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | auto-chain |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend security fixes + webhook wiring | Single PR | Critical path: signature fix, clinic resolution, task wiring |
| 2 | Backend compliance + reliability | Single PR | Consent checks, signal, template service |
| 3 | Frontend indicators + tests | Single PR | UI badges + test coverage |

## Phase 1: Backend Security Fixes

- [x] 1.1 Fix `validate_signature` in `backend/notifications/services/twilio_service.py`: replace `b64decode(expected)` with `base64.b64encode(expected).decode("utf-8")` and compare against raw `signature` string using `hmac.compare_digest()`
- [x] 1.2 Fix `_resolve_clinic` in `backend/notifications/views.py`: replace `Clinic.objects.first()` with iteration over `Clinic.objects.filter(is_deleted=False)`, matching `clinic.phone` or `clinic.cfdi_config.get("phone")` against the webhook's `to_number`
- [x] 1.3 Wire `process_whatsapp_response.delay(webhook_id)` in `_handle_inbound_message` in `backend/notifications/views.py`: replace TODO comment with actual Celery task call passing the created `WhatsAppWebhook.id`
- [x] 1.4 Update `process_whatsapp_response` signature in `backend/celery_app/tasks.py`: change params from `(from_number, body, clinic_id)` to `(webhook_id: str)`, resolve `WhatsAppWebhook` inside the task

## Phase 2: Backend Compliance + Reliability

- [x] 2.1 Add dual consent check in `send_appointment_reminders` in `backend/celery_app/tasks.py`: verify `patient.whatsapp_opt_in` AND `PatientConsent.objects.filter(patient=patient, consent_type="whatsapp", signed=True).exists()` before sending; skip with warning log if either fails
- [x] 2.2 Create `backend/appointments/signals.py`: implement `post_save` signal `reset_whatsapp_on_reschedule` that detects status transition from `completed/cancelled/no_show` → `scheduled/confirmed` and resets `whatsapp_sent=False` via `.update()`
- [x] 2.3 Update `backend/appointments/apps.py`: import signals module in `AppConfig.ready()` method to register the signal
- [x] 2.4 Replace f-string reminder body in `send_appointment_reminders` in `backend/celery_app/tasks.py`: use `render_template("appointment_reminder", {"nombre", "fecha", "hora", "doctor"})` from `notifications.services.template_service`

## Phase 3: Frontend + Tests

- [x] 3.1 Add WhatsApp status badge in `frontend/src/pages/AppointmentsPage.tsx` appointment detail dialog: show colored badge based on `whatsapp_sent` and `whatsapp_response` values (green=confirmed, red=cancelled, gray=sent)
- [x] 3.2 Replace raw `whatsapp_opt_in` text with colored badge in `frontend/src/pages/Patients/PatientDetailPage.tsx` Consent Status card: show "✅ Aceptado" or "❌ No aceptado"
- [x] 3.3 Fix 4 pre-existing Twilio signature tests in `test_twilio_webhook.py`: verify tests pass after `validate_signature` base64 fix; update test assertions if needed to match new string comparison behavior
- [x] 3.4 Add unit test for `_resolve_clinic`: test with multiple clinics, with/without phone, with `cfdi_config` phone mapping
- [x] 3.5 Add unit test for consent check logic in `send_appointment_reminders`: test dual condition (opt_in + PatientConsent) skips reminder when either is missing
- [x] 3.6 Add unit test for `reset_whatsapp_on_reschedule` signal: test status transitions (completed→scheduled resets, scheduled→confirmed does not reset) and idempotency
- [x] 3.7 Add integration test for webhook → task wiring: POST to webhook endpoint, verify `WhatsAppWebhook` is created and `process_whatsapp_response` task is called with correct `webhook_id`
