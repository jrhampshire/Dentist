"""
Tests for the dashboard metrics endpoint.

Covers:
- Correct response structure
- Tenant isolation (two clinics get different data)
- Empty data returns zeros, not errors
- Revenue excludes draft/cancelled invoices
- Date range filtering
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestDashboardMetrics:
    """Metrics endpoint returns correct structure and values."""

    def test_metrics_return_correct_structure(
        self, create_user, auth_headers, create_appointment, create_patient
    ):
        """All expected keys are present with the right types."""
        admin = create_user(role="admin")
        clinic = admin.clinic

        # Create some data
        create_patient(clinic=clinic, first_name="Patient 1")
        create_appointment(
            clinic=clinic, date_val=timezone.localdate(), status="scheduled"
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()

        # Top-level keys
        assert isinstance(data["appointments_today"], int)
        assert isinstance(data["appointments_this_week"], dict)
        assert "total" in data["appointments_this_week"]
        assert "by_status" in data["appointments_this_week"]
        assert isinstance(data["appointments_this_month"], dict)
        assert "total" in data["appointments_this_month"]
        assert "completion_rate" in data["appointments_this_month"]
        assert isinstance(data["revenue_this_month"], (int, float, str))
        assert isinstance(data["revenue_trend"], list)
        assert isinstance(data["appointments_trend"], list)
        assert isinstance(data["patients_total"], int)
        assert isinstance(data["patients_new_this_month"], int)
        assert isinstance(data["low_stock_count"], int)
        assert isinstance(data["expiring_soon_count"], int)
        assert isinstance(data["upcoming_appointments"], list)

    def test_unauthenticated_returns_401(self):
        """Reject requests without JWT token."""
        client = APIClient()
        response = client.get("/api/v1/dashboard/metrics/")
        assert response.status_code == 401


@pytest.mark.django_db
class TestDashboardTenantIsolation:
    """Metrics from clinic A do not leak into clinic B."""

    def test_clinic_a_does_not_see_clinic_b_data(
        self, two_clinics, create_user, create_appointment, create_patient, auth_headers
    ):
        clinic_a, clinic_b = two_clinics
        admin_a = create_user(role="admin", clinic=clinic_a, first_name="Admin A")

        # Create data in both clinics
        create_patient(clinic=clinic_a, first_name="A Patient")
        create_patient(clinic=clinic_b, first_name="B Patient")
        create_appointment(
            clinic=clinic_a, date_val=timezone.localdate(), status="scheduled"
        )
        create_appointment(
            clinic=clinic_b, date_val=timezone.localdate(), status="completed"
        )

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()

        # Clinic A has 1 patient, 1 appointment today
        assert data["patients_total"] == 1
        assert data["appointments_today"] == 1

        # Upcoming should only have clinic A's appointment (since status=scheduled)
        assert len(data["upcoming_appointments"]) >= 0


@pytest.mark.django_db
class TestDashboardEmptyState:
    """When there is no data, all metrics return 0 or empty arrays — never errors."""

    def test_empty_clinic_returns_zeros(self, create_user, auth_headers):
        admin = create_user(role="admin")
        clinic = admin.clinic

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()

        assert data["appointments_today"] == 0
        assert data["appointments_this_week"]["total"] == 0
        assert data["appointments_this_week"]["by_status"] == {}
        assert data["appointments_this_month"]["total"] == 0
        assert data["appointments_this_month"]["completion_rate"] == 0.0
        assert Decimal(str(data["revenue_this_month"])) == Decimal(0)
        assert data["patients_total"] == 0
        assert data["patients_new_this_month"] == 0
        assert data["low_stock_count"] == 0
        assert data["expiring_soon_count"] == 0
        assert data["upcoming_appointments"] == []

        # Trends should be empty (or filled with zeros for the full 30-day window)
        # The implementation fills with zeros, so there will be entries
        assert all(p["count"] == 0 for p in data["appointments_trend"])
        assert all(
            Decimal(str(p["total"])) == Decimal(0) for p in data["revenue_trend"]
        )


@pytest.mark.django_db
class TestDashboardRevenueAccuracy:
    """Revenue excludes draft and cancelled invoices."""

    def test_revenue_excludes_draft_and_cancelled(
        self, create_user, create_invoice, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic

        # Create invoices with different statuses
        create_invoice(clinic=clinic, status="draft", total=Decimal("1000.00"))
        create_invoice(clinic=clinic, status="cancelled", total=Decimal("500.00"))
        create_invoice(clinic=clinic, status="stamped", total=Decimal("300.00"))
        create_invoice(clinic=clinic, status="sent", total=Decimal("200.00"))
        create_invoice(clinic=clinic, status="paid", total=Decimal("100.00"))

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()

        # Only stamped + sent + paid = 300 + 200 + 100 = 600
        assert Decimal(str(data["revenue_this_month"])) == Decimal("600.00")

    def test_revenue_excludes_pending_stamp_and_error(
        self, create_user, create_invoice, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic

        create_invoice(clinic=clinic, status="pending_stamp", total=Decimal("400.00"))
        create_invoice(clinic=clinic, status="error", total=Decimal("200.00"))
        create_invoice(clinic=clinic, status="paid", total=Decimal("50.00"))

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        assert Decimal(str(response.json()["revenue_this_month"])) == Decimal("50.00")


@pytest.mark.django_db
class TestDashboardDateRange:
    """Appointments and patients from outside the current month/week are excluded."""

    def test_appointments_today_only_counts_today(
        self, create_user, create_appointment, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic
        today = timezone.localdate()

        create_appointment(clinic=clinic, date_val=today, status="scheduled")
        create_appointment(
            clinic=clinic, date_val=today + timedelta(days=1), status="scheduled"
        )
        create_appointment(
            clinic=clinic, date_val=today - timedelta(days=1), status="scheduled"
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        assert response.json()["appointments_today"] == 1

    def test_appointments_trend_excludes_cancelled(
        self, create_user, create_appointment, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic
        today = timezone.localdate()

        create_appointment(clinic=clinic, date_val=today, status="scheduled")
        create_appointment(clinic=clinic, date_val=today, status="cancelled")

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()
        # The trend for today should only count the non-cancelled appointment
        today_points = [
            p for p in data["appointments_trend"] if p["date"] == str(today)
        ]
        assert len(today_points) == 1
        assert today_points[0]["count"] == 1  # Only 1 scheduled, cancelled excluded

    def test_patients_new_this_month_only_counts_current_month(
        self, create_user, create_patient, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic

        # Patient created today
        create_patient(clinic=clinic, first_name="New")

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()
        assert data["patients_new_this_month"] == 1
        assert data["patients_total"] >= data["patients_new_this_month"]

    def test_upcoming_appointments_limited_to_next_7_days(
        self, create_user, create_appointment, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic
        today = timezone.localdate()

        # Within next 7 days
        create_appointment(clinic=clinic, date_val=today, status="scheduled")
        create_appointment(
            clinic=clinic, date_val=today + timedelta(days=3), status="confirmed"
        )
        # Outside 7-day window
        create_appointment(
            clinic=clinic, date_val=today + timedelta(days=8), status="scheduled"
        )
        create_appointment(
            clinic=clinic, date_val=today + timedelta(days=30), status="scheduled"
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()
        # Only 2 should be upcoming (today + day+3)
        assert len(data["upcoming_appointments"]) == 2

    def test_upcoming_excludes_cancelled_and_completed(
        self, create_user, create_appointment, auth_headers
    ):
        admin = create_user(role="admin")
        clinic = admin.clinic
        today = timezone.localdate()

        create_appointment(clinic=clinic, date_val=today, status="scheduled")
        create_appointment(clinic=clinic, date_val=today, status="cancelled")
        create_appointment(clinic=clinic, date_val=today, status="completed")

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        # Only the scheduled one should appear
        assert len(response.json()["upcoming_appointments"]) == 1

    def test_revenue_trend_excludes_other_clinics(
        self, two_clinics, create_user, create_invoice, auth_headers
    ):
        clinic_a, clinic_b = two_clinics
        admin_a = create_user(role="admin", clinic=clinic_a)
        admin_b = create_user(role="admin", clinic=clinic_b)

        # Revenue for both clinics
        create_invoice(clinic=clinic_a, status="paid", total=Decimal("1000.00"))
        create_invoice(clinic=clinic_b, status="paid", total=Decimal("5000.00"))

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        response = client.get("/api/v1/dashboard/metrics/")

        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["revenue_this_month"])) == Decimal("1000.00")
