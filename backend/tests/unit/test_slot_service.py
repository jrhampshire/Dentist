"""
Unit tests for slot_service.py (Task 12.3).

Tests:
- Conflict detection
- Available slots generation
- Schedule slot filtering
"""

from datetime import date, time

import pytest

from appointments.services.slot_service import (
    check_conflict,
    find_available_slots,
    generate_slots_from_schedule,
)


@pytest.mark.unit
@pytest.mark.django_db
class TestCheckConflict:
    """Test the conflict detection function."""

    def test_no_conflict_when_no_appointments(self, create_clinic, create_user):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)

        has_conflict = check_conflict(
            dentist_id=str(dentist.pk),
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        assert has_conflict is False

    def test_conflict_with_overlapping_appointment(
        self, create_clinic, create_user, create_patient, create_appointment_type
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        # Create an appointment from 9:00 to 10:00
        from appointments.models import Appointment

        Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="scheduled",
        )

        # Try to book 9:15 to 9:45 — should conflict
        has_conflict = check_conflict(
            dentist_id=str(dentist.pk),
            date=date.today(),
            start_time=time(9, 15),
            end_time=time(9, 45),
        )
        assert has_conflict is True

    def test_no_conflict_when_adjacent(
        self, create_clinic, create_user, create_patient, create_appointment_type
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status="scheduled",
        )

        # 9:30 to 10:00 — should NOT conflict (adjacent, not overlapping)
        has_conflict = check_conflict(
            dentist_id=str(dentist.pk),
            date=date.today(),
            start_time=time(9, 30),
            end_time=time(10, 0),
        )
        assert has_conflict is False

    def test_no_conflict_with_cancelled_appointment(
        self, create_clinic, create_user, create_patient, create_appointment_type
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="cancelled",  # Cancelled shouldn't cause conflict
        )

        has_conflict = check_conflict(
            dentist_id=str(dentist.pk),
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        assert has_conflict is False

    def test_exclude_appointment_for_updates(
        self, create_clinic, create_user, create_patient, create_appointment_type
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        appt = Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status="scheduled",
        )

        # When excluding this appointment, no conflict
        has_conflict = check_conflict(
            dentist_id=str(dentist.pk),
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
            exclude_appointment_id=str(appt.pk),
        )
        assert has_conflict is False

    def test_conflict_with_different_dentist_no_conflict(
        self, create_clinic, create_user, create_patient, create_appointment_type
    ):
        clinic = create_clinic()
        dentist_a = create_user(role="dentista", clinic=clinic, first_name="Dr. A")
        dentist_b = create_user(role="dentista", clinic=clinic, first_name="Dr. B")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist_a,
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            status="scheduled",
        )

        # Dentist B should have no conflict
        has_conflict = check_conflict(
            dentist_id=str(dentist_b.pk),
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        assert has_conflict is False


@pytest.mark.unit
@pytest.mark.django_db
class TestGenerateSlotsFromSchedule:
    """Test schedule slot generation."""

    def test_generates_slots_from_schedule(
        self, create_clinic, create_user, create_schedule_slot
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)

        # Monday 9:00-10:00
        create_schedule_slot(
            clinic=clinic,
            dentist=dentist,
            day_of_week=0,  # Monday
            start=time(9, 0),
            end=time(10, 0),
        )

        # Next Monday
        from datetime import timedelta

        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        slots = generate_slots_from_schedule(
            dentist_id=str(dentist.pk),
            date=next_monday,
            clinic_id=str(clinic.pk),
            slot_duration_minutes=30,
        )

        assert len(slots) == 2  # 9:00-9:30, 9:30-10:00
        assert slots[0]["start_time"] == time(9, 0)
        assert slots[0]["end_time"] == time(9, 30)
        assert slots[1]["start_time"] == time(9, 30)
        assert slots[1]["end_time"] == time(10, 0)

    def test_empty_when_no_schedule(self, create_clinic, create_user):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)

        slots = generate_slots_from_schedule(
            dentist_id=str(dentist.pk),
            date=date.today(),
            clinic_id=str(clinic.pk),
        )
        assert slots == []

    def test_falls_back_to_clinic_wide_schedule(
        self, create_clinic, create_schedule_slot
    ):
        clinic = create_clinic()

        # Clinic-wide schedule (no dentist)
        create_schedule_slot(
            clinic=clinic,
            dentist=None,
            day_of_week=0,
            start=time(9, 0),
            end=time(10, 0),
        )

        from datetime import timedelta

        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        dentist_id = "00000000-0000-0000-0000-000000000000"
        slots = generate_slots_from_schedule(
            dentist_id=dentist_id,
            date=next_monday,
            clinic_id=str(clinic.pk),
        )

        assert len(slots) == 2

    def test_respects_valid_from_valid_until(self, create_clinic, create_schedule_slot):
        clinic = create_clinic()

        from appointments.models import ScheduleSlot

        ScheduleSlot.objects.create(
            clinic=clinic,
            dentist=None,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_active=True,
            valid_from=date.today().replace(year=date.today().year + 1),  # Next year
        )

        slots = generate_slots_from_schedule(
            dentist_id=None,
            date=date.today(),
            clinic_id=str(clinic.pk),
        )
        assert slots == []  # Not yet valid


@pytest.mark.unit
@pytest.mark.django_db
class TestFindAvailableSlots:
    """Test the combined available slots function."""

    def test_all_slots_available_when_no_appointments(
        self, create_clinic, create_user, create_schedule_slot
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)

        create_schedule_slot(
            clinic=clinic,
            dentist=dentist,
            day_of_week=0,
            start=time(9, 0),
            end=time(10, 0),
        )

        from datetime import timedelta

        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        slots = find_available_slots(
            dentist_id=str(dentist.pk),
            date=next_monday,
            clinic_id=str(clinic.pk),
        )

        assert len(slots) == 2

    def test_booked_slots_filtered_out(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_schedule_slot,
    ):
        clinic = create_clinic()
        dentist = create_user(role="dentista", clinic=clinic)
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        create_schedule_slot(
            clinic=clinic,
            dentist=dentist,
            day_of_week=0,
            start=time(9, 0),
            end=time(11, 0),
        )

        from appointments.models import Appointment
        from datetime import timedelta

        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        # Book the 9:00-9:30 slot
        Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=next_monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status="scheduled",
        )

        slots = find_available_slots(
            dentist_id=str(dentist.pk),
            date=next_monday,
            clinic_id=str(clinic.pk),
        )

        # Should have 3 slots (9:30-10:00, 10:00-10:30, 10:30-11:00) minus the booked one
        assert len(slots) == 3
        assert slots[0]["start_time"] == time(9, 30)
