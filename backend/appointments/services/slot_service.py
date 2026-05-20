"""
Appointment Scheduling — Slot Service.

Provides:
- find_available_slots: Find open 30-min (or type-specific) slots for a dentist on a date
- check_conflict: Check if a dentist has an overlapping appointment
- generate_slots_from_schedule: Generate time slots from ScheduleSlot config
"""

from datetime import datetime, time, timedelta
from typing import Optional

from django.db.models import Q

from appointments.models import Appointment, ScheduleSlot


def check_conflict(
    dentist_id: str,
    date,
    start_time: time,
    end_time: time,
    exclude_appointment_id: Optional[str] = None,
) -> bool:
    """
    Check if a dentist has an overlapping appointment on the given date/time.

    Args:
        dentist_id: UUID of the dentist
        date: The date to check
        start_time: Proposed start time
        end_time: Proposed end time
        exclude_appointment_id: Optional appointment ID to exclude (for updates)

    Returns:
        True if there IS a conflict, False if the slot is available.
    """
    query = Appointment.objects.filter(
        dentist_id=dentist_id,
        date=date,
        status__in=["scheduled", "confirmed", "in_progress"],
    ).filter(Q(start_time__lt=end_time) & Q(end_time__gt=start_time))

    if exclude_appointment_id:
        query = query.exclude(id=exclude_appointment_id)

    return query.exists()


def generate_slots_from_schedule(
    dentist_id: Optional[str],
    date,
    clinic_id: str,
    slot_duration_minutes: int = 30,
) -> list[dict]:
    """
    Generate available time slots from ScheduleSlot configuration.

    Looks up the ScheduleSlot for the given day_of_week and generates
    individual bookable slots of the specified duration.

    Args:
        dentist_id: UUID of the dentist (or None for clinic-wide slots)
        date: The date to generate slots for
        clinic_id: UUID of the clinic
        slot_duration_minutes: Duration of each slot (default 30)

    Returns:
        List of dicts: [{"start_time": "09:00", "end_time": "09:30"}, ...]
    """
    day_of_week = date.weekday()  # 0=Monday, 6=Sunday

    # Get schedule slots for this day
    # Prefer dentist-specific slots, fall back to clinic-wide (dentist=None)
    slots = ScheduleSlot.objects.filter(
        clinic_id=clinic_id,
        day_of_week=day_of_week,
        is_active=True,
    ).filter(Q(dentist_id=dentist_id) | Q(dentist_id__isnull=True))

    # Filter by valid date range if set
    if slots:
        dated_slots = []
        for slot in slots:
            if slot.valid_from and date < slot.valid_from:
                continue
            if slot.valid_until and date > slot.valid_until:
                continue
            dated_slots.append(slot)
        slots = dated_slots

    if not slots:
        return []

    # Generate individual time slots
    available = []
    for schedule in slots:
        current = datetime.combine(date, schedule.start_time)
        end = datetime.combine(date, schedule.end_time)

        while current + timedelta(minutes=slot_duration_minutes) <= end:
            slot_end = current + timedelta(minutes=slot_duration_minutes)
            available.append(
                {
                    "start_time": current.time(),
                    "end_time": slot_end.time(),
                }
            )
            current = slot_end

    return available


def find_available_slots(
    dentist_id: str,
    date,
    clinic_id: str,
    slot_duration_minutes: int = 30,
) -> list[dict]:
    """
    Find all available (non-conflicting) time slots for a dentist on a date.

    Combines schedule configuration with existing appointments to return
    only slots that are actually bookable.

    Args:
        dentist_id: UUID of the dentist
        date: The date to check
        clinic_id: UUID of the clinic
        slot_duration_minutes: Duration of each slot (default 30)

    Returns:
        List of dicts: [
            {"start_time": "09:00", "end_time": "09:30"},
            {"start_time": "09:30", "end_time": "10:00"},
            ...
        ]
    """
    # Get all potential slots from schedule
    potential_slots = generate_slots_from_schedule(
        dentist_id=dentist_id,
        date=date,
        clinic_id=clinic_id,
        slot_duration_minutes=slot_duration_minutes,
    )

    if not potential_slots:
        return []

    # Get existing appointments for this dentist on this date
    booked = Appointment.objects.filter(
        dentist_id=dentist_id,
        date=date,
        status__in=["scheduled", "confirmed", "in_progress"],
    ).values_list("start_time", "end_time")

    booked_ranges = [(bt, et) for bt, et in booked]

    # Filter out slots that conflict with existing appointments
    available = []
    for slot in potential_slots:
        slot_start = slot["start_time"]
        slot_end = slot["end_time"]

        has_conflict = False
        for booked_start, booked_end in booked_ranges:
            # Overlap: existing.start < new.end AND existing.end > new.start
            if booked_start < slot_end and booked_end > slot_start:
                has_conflict = True
                break

        if not has_conflict:
            available.append(slot)

    return available
