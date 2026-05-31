"""
Signal receivers for dental_records app.

Handles materialization of Tooth and ToothSurface state from
DentalRecordEntry post_save events. Uses select_for_update on
Tooth to prevent race conditions in concurrent writes.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from dental_records.models import DentalRecordEntry, Tooth, ToothSurface


@receiver(post_save, sender=DentalRecordEntry)
def materialize_tooth_state(
    sender: type[DentalRecordEntry],
    instance: DentalRecordEntry,
    created: bool,
    **kwargs: object,
) -> None:
    """
    Materialize the current tooth and surface state after a new entry.

    Only fires on creation (created=True), not on updates (which are
    blocked by the append-only constraint anyway).

    Wraps the materialization in transaction.atomic() with
    select_for_update on Tooth to prevent race conditions.
    """
    if not created:
        return

    with transaction.atomic():
        # 1. Get or create Tooth for this patient+tooth_fdi
        #    select_for_update prevents concurrent modifications
        tooth, _ = Tooth.objects.select_for_update().get_or_create(
            patient=instance.patient,
            tooth_fdi=instance.tooth_fdi,
            defaults={
                "condition": instance.condition,
                "last_entry": instance,
            },
        )

        # If tooth already existed, update its condition and last_entry
        if tooth.condition != instance.condition or tooth.last_entry_id != instance.pk:
            tooth.condition = instance.condition
            tooth.last_entry = instance
            tooth.save(update_fields=["condition", "last_entry", "updated_at"])

        # 2. Get or create ToothSurface for this tooth+surface
        surface_entry, _ = ToothSurface.objects.get_or_create(
            tooth=tooth,
            surface=instance.surface,
            defaults={
                "condition": instance.condition,
                "last_entry": instance,
            },
        )

        # If surface already existed, update its condition and last_entry
        if (
            surface_entry.condition != instance.condition
            or surface_entry.last_entry_id != instance.pk
        ):
            surface_entry.condition = instance.condition
            surface_entry.last_entry = instance
            surface_entry.save(update_fields=["condition", "last_entry", "updated_at"])
