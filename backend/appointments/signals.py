"""
Appointment signals.

Handlers:
- reset_whatsapp_on_reschedule: Resets whatsapp_sent when a terminal appointment
  (completed / cancelled / no_show) is moved back to scheduled / confirmed.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from appointments.models import Appointment

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Appointment)
def capture_previous_status(sender, instance, **kwargs):
    """Store the pre-save status so post_save can detect transitions."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._pre_save_status = old.status
        except sender.DoesNotExist:
            instance._pre_save_status = None
    else:
        instance._pre_save_status = None


@receiver(post_save, sender=Appointment)
def reset_whatsapp_on_reschedule(sender, instance, created, **kwargs):
    """
    Reset whatsapp_sent when status transitions from a terminal state
    (completed, cancelled, no_show) back to an active state
    (scheduled, confirmed) — e.g. when a cancelled appointment is rescheduled.
    """
    if created:
        return

    old_status = getattr(instance, "_pre_save_status", None)
    if old_status is None:
        return

    terminal_statuses = {"completed", "cancelled", "no_show"}
    active_statuses = {"scheduled", "confirmed"}

    if old_status in terminal_statuses and instance.status in active_statuses:
        # Use .update() to avoid re-triggering post_save signal
        Appointment.objects.filter(pk=instance.pk).update(whatsapp_sent=False)
        logger.info(
            "WhatsApp flag reset for appointment %s: %s → %s",
            instance.pk,
            old_status,
            instance.status,
        )
