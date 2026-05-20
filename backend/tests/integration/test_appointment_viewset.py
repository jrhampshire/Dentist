"""
Integration tests for AppointmentViewSet (Task 12.9).

Tests:
- Time slot conflict (409 response)
- Available slots endpoint
"""

from datetime import date, time, timedelta

import pytest
from rest_framework.test import APIClient


@pytest.mark.integration
@pytest.mark.django_db
class TestAppointmentConflict:
    """Test appointment time slot conflict detection."""

    def test_conflicting_appointment_returns_409(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        # Book 9:00-10:00
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

        # Try to book 9:15-9:45 for same dentist
        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            "/api/v1/appointments/",
            {
                "patient_id": str(patient.pk),
                "appointment_type_id": str(appt_type.pk),
                "dentist_id": str(dentist.pk),
                "date": str(date.today()),
                "start_time": "09:15",
            },
            format="json",
        )

        # Should get 409 Conflict
        assert response.status_code == 409

    def test_non_conflicting_appointment_succeeds(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        # Book 9:00-10:00
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

        # Book 10:00-11:00 — should succeed (no overlap)
        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            "/api/v1/appointments/",
            {
                "patient_id": str(patient.pk),
                "appointment_type_id": str(appt_type.pk),
                "dentist_id": str(dentist.pk),
                "date": str(date.today()),
                "start_time": "10:00",
            },
            format="json",
        )

        assert response.status_code == 201

    def test_different_dentist_no_conflict(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        dentist_a = create_user(role="dentista", clinic=clinic, first_name="Dr. A")
        dentist_b = create_user(role="dentista", clinic=clinic, first_name="Dr. B")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        from appointments.models import Appointment

        # Book dentist A at 9:00
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

        # Book dentist B at same time — should succeed
        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            "/api/v1/appointments/",
            {
                "patient_id": str(patient.pk),
                "appointment_type_id": str(appt_type.pk),
                "dentist_id": str(dentist_b.pk),
                "date": str(date.today()),
                "start_time": "09:00",
            },
            format="json",
        )

        assert response.status_code == 201


@pytest.mark.integration
@pytest.mark.django_db
class TestAvailableSlotsEndpoint:
    """Test the available-slots endpoint."""

    def test_available_slots_returns_slots(
        self, create_clinic, create_user, create_schedule_slot, auth_headers
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")

        # Set up Monday 9:00-11:00 schedule
        create_schedule_slot(
            clinic=clinic,
            dentist=dentist,
            day_of_week=0,  # Monday
            start=time(9, 0),
            end=time(11, 0),
        )

        # Calculate next Monday
        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(
            "/api/v1/appointments/available-slots/",
            {
                "date": str(next_monday),
                "dentist_id": str(dentist.pk),
                "duration": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        assert data["total_available"] == 4  # 9:00, 9:30, 10:00, 10:30

    def test_available_slots_requires_date(
        self, create_clinic, create_user, auth_headers
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(
            "/api/v1/appointments/available-slots/",
            {"dentist_id": "00000000-0000-0000-0000-000000000000"},
        )

        assert response.status_code == 400
        assert "date" in response.json()["error"]

    def test_available_slots_requires_dentist_id(
        self, create_clinic, create_user, auth_headers
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(
            "/api/v1/appointments/available-slots/",
            {"date": str(date.today())},
        )

        assert response.status_code == 400
        assert "dentist_id" in response.json()["error"]

    def test_available_slots_filters_booked(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_schedule_slot,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")
        patient = create_patient(clinic=clinic)
        appt_type = create_appointment_type(clinic=clinic)

        # Set up Monday 9:00-10:00 schedule
        create_schedule_slot(
            clinic=clinic,
            dentist=dentist,
            day_of_week=0,
            start=time(9, 0),
            end=time(10, 0),
        )

        today = date.today()
        next_monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        # Book the 9:00-9:30 slot
        from appointments.models import Appointment

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

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(
            "/api/v1/appointments/available-slots/",
            {
                "date": str(next_monday),
                "dentist_id": str(dentist.pk),
                "duration": 30,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_available"] == 1  # Only 9:30-10:00 remains
        assert data["slots"][0]["start_time"] == "09:30"
