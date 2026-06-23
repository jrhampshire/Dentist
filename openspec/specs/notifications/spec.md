# notifications — WhatsApp Notifications Specification

## Purpose

WhatsApp messaging via Twilio: appointment reminders, confirmations, inbound message processing, consent management, template rendering, and webhook security.

## Requirements

### Requirement: Twilio signature validation MUST protect webhook endpoint

The system SHALL validate the `X-Twilio-Signature` header on every inbound webhook request using HMAC-SHA1 with sorted POST parameters.

#### Scenario: Valid signature accepted

- GIVEN a Twilio webhook POST with correct `X-Twilio-Signature`
- WHEN the webhook is received at `POST /api/v1/whatsapp/webhook/`
- THEN the system SHALL validate the signature using the configured `TWILIO_AUTH_TOKEN`
- AND the request SHALL be processed

#### Scenario: Invalid signature rejected

- GIVEN a webhook POST with an incorrect `X-Twilio-Signature`
- WHEN the webhook is received
- THEN the system SHALL return status `403` with error `"invalid_signature"`
- AND the request body SHALL NOT be processed

#### Scenario: Missing signature in dev mode allowed through

- GIVEN a webhook POST without `X-Twilio-Signature` and Twilio not fully configured
- WHEN the webhook is received
- THEN the system SHALL process the request (development fallback)

### Requirement: Inbound WhatsApp messages MUST be processed via Celery

Inbound messages from patients SHALL be persisted as `WhatsAppWebhook` records and dispatched to a Celery task for processing (confirmation, cancellation, opt-out).

#### Scenario: Inbound message creates webhook record

- GIVEN a patient sends "Confirmo" to the clinic's WhatsApp number
- WHEN the Twilio webhook delivers the message
- THEN a `WhatsAppWebhook` SHALL be created with `direction=inbound`
- AND `from_number`, `to_number`, `message_body`, and `twilio_sid` SHALL be populated
- AND a Celery task `process_whatsapp_response` SHALL be dispatched with the webhook ID

#### Scenario: Clinic resolved from destination number

- GIVEN a webhook with `to_number="+5215512345678"`
- WHEN `_resolve_clinic` is called with the cleaned number
- THEN the system SHALL find the clinic whose `phone` or `cfdi_config.phone` matches
- AND the webhook `clinic_id` SHALL be set

#### Scenario: Confirmación keyword triggers confirmation

- GIVEN an inbound message body "confirmo" and a pending appointment
- WHEN the Celery task processes the webhook
- THEN the appointment status SHALL be updated to `confirmed`
- AND a confirmation response SHALL be sent via WhatsApp

#### Scenario: Cancel keyword triggers cancellation

- GIVEN an inbound message body "cancelar" and a pending appointment
- WHEN the Celery task processes the webhook
- THEN the appointment SHALL be cancelled
- AND a cancellation acknowledgment SHALL be sent

#### Scenario: Baja keyword triggers opt-out

- GIVEN an inbound message body "baja" or "no quiero"
- WHEN the Celery task processes the webhook
- THEN the patient's `whatsapp_opt_in` SHALL be set to `False`
- AND no further WhatsApp messages SHALL be sent to this patient

### Requirement: Message sending MUST use exponential backoff retry

Outbound WhatsApp messages via Twilio SHALL be retried up to 3 times with exponential backoff (1s, 2s, 4s) on server errors or timeouts. Client errors (4xx) SHALL NOT be retried.

#### Scenario: Server error triggers retry

- GIVEN Twilio returns a `500 Internal Server Error`
- WHEN `TwilioService.send_message()` is called
- THEN the system SHALL retry up to 3 times with backoff
- AND if all retries fail, `TwilioServiceError` SHALL be raised

#### Scenario: Client error does not retry

- GIVEN Twilio returns a `400 Bad Request` (e.g., invalid phone number)
- WHEN `TwilioService.send_message()` is called
- THEN the system SHALL NOT retry
- AND `TwilioServiceError` SHALL be raised immediately with the response body

### Requirement: Templates MUST support variable substitution

The system SHALL support pre-approved WhatsApp templates with variable substitution for patient name, date, time, and clinic info.

#### Scenario: Appointment reminder template renders correctly

- GIVEN the `appointment_reminder` template with variables `{paciente}`, `{fecha}`, `{hora}`, `{clinica}`, `{tipo}`
- WHEN `render_template("appointment_reminder", {paciente: "Juan", fecha: "22/06/2026", hora: "09:00", clinica: "Dental MX", tipo: "Limpieza"})`
- THEN the rendered message SHALL contain all substituted values
- AND SHALL include a confirmation/cancellation instruction

#### Scenario: Missing variable raises error

- GIVEN a template requiring `{paciente}` but `paciente` is not provided
- WHEN `render_template()` is called without the required variable
- THEN `TemplateVariableError` SHALL be raised

#### Scenario: Unknown template raises error

- GIVEN a template name that does not exist
- WHEN `render_template("nonexistent_template", {})` is called
- THEN `TemplateNotFoundError` SHALL be raised

### Requirement: Notification log MUST track full message lifecycle

The system SHALL track every outbound notification in `NotificationLog` with status transitions: `queued → sent → delivered → read` or `queued → failed`.

#### Scenario: Status callback updates notification log

- GIVEN a notification log entry with provider_id matching a Twilio SID
- WHEN Twilio sends a status callback with `MessageStatus=delivered`
- THEN the `NotificationLog` status SHALL be updated to `delivered`
- AND `delivered_at` SHALL be set

#### Scenario: Failed delivery records error

- GIVEN a notification log entry
- WHEN Twilio sends a status callback with `MessageStatus=failed` and `ErrorCode=30003`
- THEN the `NotificationLog` status SHALL be `failed`
- AND `error_message` SHALL contain the failure reason

### Requirement: WhatsApp consent MUST be tracked per patient

The system SHALL track WhatsApp consent via `PatientConsent` records. Patients who have opted out SHALL NOT receive WhatsApp messages.

#### Scenario: Dual consent check before sending

- GIVEN a patient with `whatsapp_opt_in=True` and a signed WhatsApp `PatientConsent`
- WHEN an appointment reminder is triggered
- THEN the system SHALL allow the message to be sent

#### Scenario: Opted-out patient receives no messages

- GIVEN a patient with `whatsapp_opt_in=False`
- WHEN an appointment reminder is triggered
- THEN the system SHALL NOT send the WhatsApp message
- AND no `NotificationLog` entry SHALL be created
