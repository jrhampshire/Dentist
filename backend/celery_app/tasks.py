"""
Celery async tasks for ClínicaSaaS Dental MX.

Tasks:
- send_appointment_reminders: Send WhatsApp reminders for upcoming appointments
- process_whatsapp_response: Parse and act on patient WhatsApp responses
- check_expiration_alerts: Alert admin about items expiring soon
- check_low_stock_alerts: Alert admin about low stock items
- mark_expired_items: Auto-mark expired inventory items
- send_stamp_reminder: Weekly reminder about CFDI stamp balance
- consume_inventory_kit: Deduct inventory kit items on appointment completion
- send_password_reset_email: Send password reset email to user
- send_verification_email_task: Send clinic email verification

Queue mapping:
- high: send_appointment_reminders, process_whatsapp_response
- default: check_expiration_alerts, check_low_stock_alerts, consume_inventory_kit
- low: mark_expired_items, send_stamp_reminder, send_password_reset_email, send_verification_email_task
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger("notifications.services")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_notification(
    clinic,
    patient=None,
    appointment=None,
    channel="whatsapp",
    notification_type=None,
    recipient="",
    content="",
    twilio_result=None,
):
    """Create a NotificationLog entry from a TwilioService result dict."""
    from notifications.models import NotificationLog

    status_map = {
        "queued": NotificationLog.Status.QUEUED,
        "sent": NotificationLog.Status.SENT,
        "delivered": NotificationLog.Status.DELIVERED,
        "read": NotificationLog.Status.READ,
        "failed": NotificationLog.Status.FAILED,
        "undelivered": NotificationLog.Status.UNDELIVERED,
    }

    twilio_status = twilio_result.get("status", "failed") if twilio_result else "failed"
    log_status = status_map.get(twilio_status, NotificationLog.Status.FAILED)

    return NotificationLog.objects.create(
        clinic=clinic,
        patient=patient,
        appointment=appointment,
        channel=channel,
        template=notification_type or "",
        status=log_status,
        recipient=recipient,
        content=content,
        provider_id=twilio_result.get("sid", "") if twilio_result else "",
        provider_response=twilio_result or {},
        error_message=twilio_result.get("error_message", "") if twilio_result else "",
        sent_at=timezone.now()
        if twilio_status in ("sent", "delivered", "read")
        else None,
    )


def _send_twilio(twilio, to_number: str, body: str) -> dict:
    """Send a WhatsApp message, catching exceptions and returning a result dict."""
    from notifications.services.twilio_service import TwilioServiceError

    try:
        result = twilio.send_message(to_number=to_number, body=body)
        return result
    except TwilioServiceError as e:
        logger.error(f"Twilio send failed to {to_number}: {e}")
        return {"status": "failed", "sid": "", "error_message": str(e)}


# ---------------------------------------------------------------------------
# Task 9.1: Send Appointment Reminders
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high",
)
def send_appointment_reminders(self):
    """
    Find appointments in the next 24 hours and send WhatsApp reminders.

    Runs every 15 minutes via Celery Beat.
    Only sends to appointments that haven't been sent a reminder yet.
    """
    from appointments.models import Appointment
    from notifications.models import NotificationLog
    from notifications.services.template_service import render_template
    from notifications.services.twilio_service import TwilioService
    from patients.models import PatientConsent

    now = timezone.now()
    tomorrow = now + timedelta(hours=24)

    # Find scheduled/confirmed appointments in next 24h without reminder sent
    appointments = (
        Appointment.objects.filter(
            Q(status=Appointment.Status.SCHEDULED)
            | Q(status=Appointment.Status.CONFIRMED),
            date__gte=now.date(),
            date__lt=tomorrow.date() + timedelta(days=1),
            whatsapp_sent=False,
            patient__phone__isnull=False,
        )
        .exclude(patient__phone="")
        .select_related("patient", "clinic", "appointment_type", "dentist")
    )

    twilio = TwilioService()
    sent_count = 0
    failed_count = 0

    for appt in appointments:
        try:
            patient = appt.patient
            phone = patient.phone

            # Consent check: opt_in flag + signed PatientConsent record
            if (
                not patient.whatsapp_opt_in
                or not PatientConsent.objects.filter(
                    patient=patient, consent_type="whatsapp", signed=True
                ).exists()
            ):
                logger.warning(
                    "WhatsApp consent not confirmed for patient %s", patient.id
                )
                continue

            # Build reminder via pre-approved template (Twilio TOS compliance)
            appointment_date = appt.date.strftime("%d/%m/%Y")
            appointment_time = appt.start_time.strftime("%H:%M")
            dentist_name = appt.dentist.get_full_name()

            body = render_template(
                "appointment_reminder",
                {
                    "nombre": patient.full_name,
                    "fecha": appointment_date,
                    "hora": appointment_time,
                    "doctor": dentist_name,
                },
            )

            result = _send_twilio(twilio, to_number=phone, body=body)

            # Log the notification
            _log_notification(
                clinic=appt.clinic,
                patient=patient,
                appointment=appt,
                channel=NotificationLog.Channel.WHATSAPP,
                notification_type="appointment_reminder",
                recipient=phone,
                content=body,
                twilio_result=result,
            )

            if result.get("status") not in ("failed", "undelivered"):
                appt.whatsapp_sent = True
                appt.whatsapp_sent_at = timezone.now()
                appt.save(
                    update_fields=["whatsapp_sent", "whatsapp_sent_at", "updated_at"]
                )
                sent_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.exception(f"Failed to send reminder for appointment {appt.id}: {e}")
            failed_count += 1

    logger.info(
        f"Appointment reminders: {sent_count} sent, {failed_count} failed "
        f"(total: {appointments.count()})"
    )

    return {"sent": sent_count, "failed": failed_count}


# ---------------------------------------------------------------------------
# Task 9.2: Process WhatsApp Response
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="high",
)
def process_whatsapp_response(self, webhook_id: str):
    """
    Parse a patient's WhatsApp response and take appropriate action.

    Supported commands:
    - CONFIRMAR: Mark appointment as confirmed
    - CANCELAR: Cancel the appointment
    - BAJA: Opt-out from future notifications

    Args:
        webhook_id: UUID string of the WhatsAppWebhook record to process
    """
    from appointments.models import Appointment
    from notifications.models import NotificationLog, WhatsAppWebhook
    from notifications.services.twilio_service import TwilioService
    from patients.models import Patient

    # Resolve webhook record
    try:
        webhook = WhatsAppWebhook.objects.select_related("clinic").get(id=webhook_id)
    except WhatsAppWebhook.DoesNotExist:
        logger.error(f"WhatsAppWebhook {webhook_id} not found")
        return {"status": "error", "reason": "webhook_not_found"}

    from_number = webhook.from_number
    body = webhook.message_body
    clinic = webhook.clinic

    command = TwilioService.parse_response(body)

    if command is None:
        logger.info(f"Unrecognized WhatsApp command from {from_number}: {body[:50]}")
        return {"command": None, "action": "none"}

    # Find the patient by phone
    patient_filter = {"phone": from_number}
    if clinic:
        patient_filter["clinic_id"] = clinic.id

    try:
        patient = Patient.objects.get(**patient_filter)
    except Patient.DoesNotExist:
        logger.warning(f"Patient not found for phone {from_number}")
        return {"command": command, "action": "patient_not_found"}

    # Find the patient's next upcoming appointment
    upcoming_appt = (
        Appointment.objects.filter(
            patient=patient,
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
            date__gte=date.today(),
        )
        .order_by("date", "start_time")
        .first()
    )

    action = command
    twilio = TwilioService()

    if command == "confirmar":
        if upcoming_appt:
            upcoming_appt.status = Appointment.Status.CONFIRMED
            upcoming_appt.whatsapp_response = "confirmar"
            upcoming_appt.save(
                update_fields=["status", "whatsapp_response", "updated_at"]
            )

            # Send confirmation reply
            _send_twilio(
                twilio,
                to_number=from_number,
                body=(
                    f"✅ Tu cita del {upcoming_appt.date.strftime('%d/%m')} a las "
                    f"{upcoming_appt.start_time.strftime('%H:%M')} ha sido confirmada. "
                    f"¡Te esperamos!"
                ),
            )
            action = "appointment_confirmed"
        else:
            _send_twilio(
                twilio,
                to_number=from_number,
                body=(
                    "No tienes citas programadas próximas. Si necesitas agendar una, "
                    "contacta a tu clínica."
                ),
            )
            action = "no_upcoming_appointment"

    elif command == "cancelar":
        if upcoming_appt:
            with transaction.atomic():
                upcoming_appt.status = Appointment.Status.CANCELLED
                upcoming_appt.whatsapp_response = "cancelar"
                upcoming_appt.cancellation_reason = "Cancelada por WhatsApp"
                upcoming_appt.cancelled_at = timezone.now()
                upcoming_appt.save(
                    update_fields=[
                        "status",
                        "whatsapp_response",
                        "cancellation_reason",
                        "cancelled_at",
                        "updated_at",
                    ]
                )

            # Log the cancellation notification
            NotificationLog.objects.create(
                clinic=upcoming_appt.clinic,
                patient=patient,
                appointment=upcoming_appt,
                channel=NotificationLog.Channel.WHATSAPP,
                template="appointment_cancellation",
                status=NotificationLog.Status.SENT,
                recipient=from_number,
                content=f"Cita cancelada por WhatsApp: {upcoming_appt.date}",
            )

            # Send cancellation reply
            _send_twilio(
                twilio,
                to_number=from_number,
                body=(
                    f"❌ Tu cita del {upcoming_appt.date.strftime('%d/%m')} ha sido cancelada. "
                    f"Si deseas reprogramar, contacta a tu clínica."
                ),
            )
            action = "appointment_cancelled"
        else:
            _send_twilio(
                twilio,
                to_number=from_number,
                body="No tienes citas programadas próximas para cancelar.",
            )
            action = "no_upcoming_appointment"

    elif command == "baja":
        # Opt-out: log the request
        NotificationLog.objects.create(
            clinic=clinic,
            patient=patient,
            channel=NotificationLog.Channel.WHATSAPP,
            template="opt_out",
            status=NotificationLog.Status.SENT,
            recipient=from_number,
            content=f"Opt-out solicitado por {patient.full_name}",
        )

        _send_twilio(
            twilio,
            to_number=from_number,
            body=(
                "Has sido dado de baja de las notificaciones por WhatsApp. "
                "Si deseas volver a recibirlas, contacta a tu clínica."
            ),
        )
        action = "opt_out"

    logger.info(f"WhatsApp response processed: {command} from {from_number} → {action}")

    return {"command": command, "action": action, "patient_id": str(patient.id)}


# ---------------------------------------------------------------------------
# Task 9.3: Check Expiration Alerts
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="default",
)
def check_expiration_alerts(self):
    """
    Find inventory items expiring within 30 days and notify admin.

    Runs daily at 8:00 AM via Celery Beat.
    """
    from clinics.models import Clinic
    from inventory.services.stock_service import get_items_expiring_within
    from notifications.models import NotificationLog
    from notifications.services.twilio_service import TwilioService

    clinics = Clinic.objects.filter(status=Clinic.Status.ACTIVE)
    total_alerts = 0
    clinics_notified = 0

    for clinic in clinics:
        expiring_items = get_items_expiring_within(days=30, clinic=clinic)

        if not expiring_items.exists():
            continue

        # Build alert message
        items_list = "\n".join(
            f"• {item.name}: {item.stock_current} unidades — "
            f"vence {item.expiration_date.strftime('%d/%m/%Y')}"
            for item in expiring_items[:10]  # Limit to 10 items
        )

        more_text = (
            f"\n... y {expiring_items.count() - 10} más"
            if expiring_items.count() > 10
            else ""
        )

        body = (
            f"⚠️ Alerta de expiración — {clinic.name}\n\n"
            f"Los siguientes productos vencen en los próximos 30 días:\n\n"
            f"{items_list}{more_text}\n\n"
            f"Total: {expiring_items.count()} productos por vencer."
        )

        # Send to clinic admin (use clinic phone or a configured admin number)
        admin_phone = clinic.settings.get("admin_phone", clinic.phone)
        if admin_phone:
            twilio = TwilioService()
            result = _send_twilio(twilio, to_number=admin_phone, body=body)

            _log_notification(
                clinic=clinic,
                channel=NotificationLog.Channel.WHATSAPP,
                notification_type=NotificationLog.Type.EXPIRATION_ALERT,
                recipient=admin_phone,
                content=body,
                twilio_result=result,
            )
            clinics_notified += 1

        total_alerts += expiring_items.count()
        logger.info(
            f"Expiration alert for {clinic.name}: {expiring_items.count()} items"
        )

    return {"total_expiring": total_alerts, "clinics_notified": clinics_notified}


# ---------------------------------------------------------------------------
# Task 9.4: Check Low Stock Alerts
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="default",
)
def check_low_stock_alerts(self):
    """
    Find inventory items below their minimum stock threshold and notify admin.

    Runs daily at 8:30 AM via Celery Beat.
    """
    from clinics.models import Clinic
    from inventory.services.stock_service import get_items_below_minimum
    from notifications.models import NotificationLog
    from notifications.services.twilio_service import TwilioService

    clinics = Clinic.objects.filter(status=Clinic.Status.ACTIVE)
    total_alerts = 0
    clinics_notified = 0

    for clinic in clinics:
        low_items = get_items_below_minimum(clinic=clinic)

        if not low_items.exists():
            continue

        # Build alert message
        items_list = "\n".join(
            f"• {item.name}: {item.stock_current}/{item.stock_minimum} {item.unit}"
            for item in low_items[:10]
        )

        more_text = (
            f"\n... y {low_items.count() - 10} más" if low_items.count() > 10 else ""
        )

        body = (
            f"📦 Alerta de stock bajo — {clinic.name}\n\n"
            f"Los siguientes productos están por debajo del mínimo:\n\n"
            f"{items_list}{more_text}\n\n"
            f"Total: {low_items.count()} productos con stock bajo."
        )

        admin_phone = clinic.settings.get("admin_phone", clinic.phone)
        if admin_phone:
            twilio = TwilioService()
            result = _send_twilio(twilio, to_number=admin_phone, body=body)

            _log_notification(
                clinic=clinic,
                channel=NotificationLog.Channel.WHATSAPP,
                notification_type=NotificationLog.Type.LOW_STOCK_ALERT,
                recipient=admin_phone,
                content=body,
                twilio_result=result,
            )
            clinics_notified += 1

        total_alerts += low_items.count()
        logger.info(f"Low stock alert for {clinic.name}: {low_items.count()} items")

    return {"total_low_stock": total_alerts, "clinics_notified": clinics_notified}


# ---------------------------------------------------------------------------
# Task 9.5: Mark Expired Items
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="low",
)
def mark_expired_items(self):
    """
    Set is_expired=True and is_blocked=True for items past their expiration date.

    Runs daily at midnight via Celery Beat.
    """
    from inventory.services.stock_service import mark_expired_items as _mark_expired

    count = _mark_expired()

    logger.info(f"Marked {count} inventory items as expired")

    return {"expired_count": count}


# ---------------------------------------------------------------------------
# Task 9.6: Send Stamp Reminder
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="low",
)
def send_stamp_reminder(self):
    """
    Notify clinics when their CFDI stamp balance is below 20.

    Runs weekly on Monday at 9:00 AM via Celery Beat.
    """
    from clinics.models import Clinic
    from notifications.models import NotificationLog
    from notifications.services.twilio_service import TwilioService

    threshold = 20
    clinics_low_stamps = Clinic.objects.filter(
        stamps_remaining__lt=threshold,
        status=Clinic.Status.ACTIVE,
    )

    twilio = TwilioService()
    notified = 0

    for clinic in clinics_low_stamps:
        body = (
            f"🧾 Recordatorio de timbres CFDI — {clinic.name}\n\n"
            f"Te quedan {clinic.stamps_remaining} timbres disponibles.\n"
            f"Te recomendamos recargar pronto para evitar interrupciones "
            f"en la facturación."
        )

        admin_phone = clinic.settings.get("admin_phone", clinic.phone)
        if admin_phone:
            result = _send_twilio(twilio, to_number=admin_phone, body=body)

            _log_notification(
                clinic=clinic,
                channel=NotificationLog.Channel.WHATSAPP,
                notification_type=NotificationLog.Type.STAMP_REMINDER,
                recipient=admin_phone,
                content=body,
                twilio_result=result,
            )

            notified += 1

    logger.info(f"Stamp reminder sent to {notified} clinics")

    return {"notified": notified, "total_low": clinics_low_stamps.count()}


# ---------------------------------------------------------------------------
# Task 9.7: Consume Inventory Kit
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="default",
)
def consume_inventory_kit(self, appointment_id: str):
    """
    On appointment completion, deduct inventory_kit items from stock.

    Args:
        appointment_id: UUID of the completed appointment

    This task is triggered when an appointment transitions to 'completed' status.
    It reads the inventory_kit from the AppointmentType and consumes each item.
    """
    from appointments.models import Appointment
    from inventory.services.stock_service import consume_kit

    try:
        appt = Appointment.objects.select_related("appointment_type").get(
            id=appointment_id
        )
    except Appointment.DoesNotExist:
        logger.error(
            f"Appointment {appointment_id} not found for inventory consumption"
        )
        return {"status": "error", "reason": "appointment_not_found"}

    kit = appt.appointment_type.inventory_kit

    if not kit:
        logger.info(f"No inventory kit for appointment {appointment_id}")
        return {"status": "skipped", "reason": "no_kit"}

    try:
        movements = consume_kit(
            clinic_id=str(appt.clinic_id),
            kit=kit,
            appointment_id=str(appt.id),
            user=None,
        )

        logger.info(
            f"Inventory kit consumed for appointment {appointment_id}: "
            f"{len(movements)} items"
        )

        return {"status": "success", "items_consumed": len(movements)}

    except ValueError as e:
        logger.error(f"Inventory consumption failed for {appointment_id}: {e}")
        return {"status": "error", "reason": str(e)}
    except Exception as e:
        logger.exception(
            f"Unexpected error consuming inventory for {appointment_id}: {e}"
        )
        return {"status": "error", "reason": str(e)}


# ---------------------------------------------------------------------------
# Email Tasks
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=180,
    queue="low",
)
def send_password_reset_email(self, user_id: str):
    """
    Send password reset email to a user.

    Triggered by ForgotPasswordView after generating a reset token.
    In development mode, logs the reset URL. In production, integrate with
    an email provider (SendGrid, AWS SES, etc.).

    Args:
        user_id: UUID of the User who requested password reset.
    """
    from django.conf import settings

    from accounts.models import User

    try:
        user = User.objects.select_related("clinic").get(id=user_id, is_deleted=False)
    except User.DoesNotExist:
        logger.error(f"Password reset: user {user_id} not found")
        return {"status": "error", "reason": "user_not_found"}

    if not user.invitation_token:
        logger.warning(f"Password reset: user {user_id} has no reset token")
        return {"status": "skipped", "reason": "no_token"}

    reset_url = (
        f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}"
        f"/reset-password?token={user.invitation_token}&email={user.email}"
    )

    # In dev mode, log the reset link. In production, send via email provider.
    if getattr(settings, "DEBUG", True):
        logger.info(
            "PASSWORD RESET EMAIL (dev mode):\n"
            "  To: %s\n"
            "  URL: %s\n"
            "  Token expires: %s",
            user.email,
            reset_url,
            user.invitation_expires,
        )
    else:
        _send_email(
            to_email=user.email,
            subject="Restablecer contraseña — ClínicaSaaS",
            html_body=(
                f"<p>Hola {user.first_name},</p>"
                f"<p>Hemos recibido una solicitud para restablecer tu contraseña.</p>"
                f"<p><a href='{reset_url}'>Haz clic aquí</a> para crear una nueva "
                f"contraseña. Este enlace expira en 1 hora.</p>"
                f"<p>Si no solicitaste este cambio, ignora este correo.</p>"
            ),
        )

    logger.info(f"Password reset email sent for user {user.email}")

    return {"status": "sent", "user_id": str(user.id)}


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=180,
    queue="low",
)
def send_verification_email_task(self, clinic_id: str, token: str):
    """
    Send email verification link to a newly registered clinic admin.

    Triggered by OnboardingService.send_verification_email() after clinic registration.
    In development mode, logs the verification URL. In production, integrate with
    an email provider (SendGrid, AWS SES, etc.).

    Args:
        clinic_id: UUID of the Clinic.
        token: Email verification token.
    """
    from django.conf import settings

    from clinics.models import Clinic

    try:
        clinic = Clinic.objects.get(id=clinic_id, is_deleted=False)
    except Clinic.DoesNotExist:
        logger.error(f"Verification email: clinic {clinic_id} not found")
        return {"status": "error", "reason": "clinic_not_found"}

    if clinic.email_verified:
        logger.info(f"Verification email: clinic {clinic_id} already verified")
        return {"status": "skipped", "reason": "already_verified"}

    verification_url = (
        f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}"
        f"/verify-email?token={token}&email={clinic.email}"
    )

    # In dev mode, log the verification link. In production, send via email provider.
    if getattr(settings, "DEBUG", True):
        logger.info(
            "VERIFICATION EMAIL (dev mode):\n"
            "  To: %s\n"
            "  URL: %s\n"
            "  Token expires: %s",
            clinic.email,
            verification_url,
            clinic.email_verification_expires,
        )
    else:
        _send_email(
            to_email=clinic.email,
            subject="Verifica tu cuenta — ClínicaSaaS",
            html_body=(
                f"<p>Bienvenido a ClínicaSaaS,</p>"
                f"<p>Tu clínica <strong>{clinic.name}</strong> ha sido registrada.</p>"
                f"<p><a href='{verification_url}'>Verifica tu dirección de email</a> "
                f"para activar tu cuenta.</p>"
            ),
        )

    logger.info(f"Verification email sent for clinic {clinic.email}")

    return {"status": "sent", "clinic_id": str(clinic.id)}


def _send_email(*, to_email: str, subject: str, html_body: str) -> bool:
    """
    Stub for sending emails through a provider (SendGrid, AWS SES, etc.).

    Replace this with your actual email provider integration.
    """
    logger.info(
        "EMAIL STUB (production mode):\n" "  To: %s\n" "  Subject: %s\n" "  Body: %s",
        to_email,
        subject,
        html_body[:200],
    )
    return True
