"""
Shared test fixtures for ClínicaSaaS Dental MX.

Provides:
- Factory fixtures for all models
- Auth helpers (JWT token generation)
- RLS bypass helpers for integration tests
- Common test data builders
"""

import uuid
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def make_jwt_token():
    """Generate a JWT access token for testing."""

    def _make(user, clinic_id=None):
        import jwt

        now = timezone.now()
        payload = {
            "user_id": str(user.pk),
            "clinic_id": str(clinic_id or user.clinic_id),
            "role": user.role,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return _make


@pytest.fixture
def auth_headers(make_jwt_token):
    """Generate Authorization headers for a user."""

    def _headers(user, clinic_id=None):
        token = make_jwt_token(user, clinic_id)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    return _headers


# ---------------------------------------------------------------------------
# RLS bypass helper
# ---------------------------------------------------------------------------


@pytest.fixture
def set_rls_context():
    """
    Manually set PostgreSQL RLS session variables.
    Use this to bypass TenantMiddleware in integration tests.
    """

    def _set(clinic_id: str, user_id: str, user_role: str):
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SET app.current_clinic_id = %s", [clinic_id])
            cursor.execute("SET app.current_user_id = %s", [user_id])
            cursor.execute("SET app.current_user_role = %s", [user_role])

    return _set


# ---------------------------------------------------------------------------
# Model factories (inline — no factory-boy dependency for speed)
# ---------------------------------------------------------------------------


@pytest.fixture
def create_clinic(db):
    """Create a Clinic instance."""

    def _create(name="Test Clinic", rfc=None, status="active", email_verified=True):
        from clinics.models import Clinic

        return Clinic.objects.create(
            name=name,
            rfc=rfc or f"XAXX{uuid.uuid4().hex[:6].upper()}",
            email=f"{name.lower().replace(' ', '.')}@test.com",
            phone="+5215512345678",
            status=status,
            email_verified=email_verified,
        )

    return _create


@pytest.fixture
def create_user(db, create_clinic):
    """Create a User instance."""

    def _create(
        email=None,
        password="testpass123",
        role="admin",
        clinic=None,
        first_name="Test",
        last_name="User",
        is_active=True,
    ):
        from accounts.models import User

        if clinic is None:
            clinic = create_clinic()

        return User.objects.create_user(
            email=email or f"{role}_{uuid.uuid4().hex[:6]}@test.com",
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            clinic=clinic,
            is_active=is_active,
        )

    return _create


@pytest.fixture
def create_patient(db, create_clinic):
    """Create a Patient instance."""

    def _create(clinic=None, first_name="Juan", last_name="Pérez", phone=None):
        from patients.models import Patient

        if clinic is None:
            clinic = create_clinic()

        return Patient.objects.create(
            clinic=clinic,
            first_name=first_name,
            last_name=last_name,
            second_last_name="García",
            email=f"{first_name.lower()}.{last_name.lower()}@test.com",
            phone=phone or f"55{uuid.uuid4().hex[:8]}",
            date_of_birth=date(1990, 1, 1),
        )

    return _create


@pytest.fixture
def create_appointment_type(db, create_clinic):
    """Create an AppointmentType instance."""

    def _create(
        clinic=None,
        name="Consulta General",
        duration=30,
        price=Decimal("500.00"),
        color="#4A90D9",
        inventory_kit=None,
    ):
        from appointments.models import AppointmentType

        if clinic is None:
            clinic = create_clinic()

        return AppointmentType.objects.create(
            clinic=clinic,
            name=name,
            duration_minutes=duration,
            price=price,
            color=color,
            inventory_kit=inventory_kit or [],
        )

    return _create


@pytest.fixture
def create_appointment(
    db, create_clinic, create_patient, create_appointment_type, create_user
):
    """Create an Appointment instance."""

    def _create(
        clinic=None,
        patient=None,
        dentist=None,
        appt_type=None,
        date_val=None,
        start=time(9, 0),
        end=time(9, 30),
        status="scheduled",
    ):
        from appointments.models import Appointment

        if clinic is None:
            clinic = create_clinic()
        if patient is None:
            patient = create_patient(clinic=clinic)
        if appt_type is None:
            appt_type = create_appointment_type(clinic=clinic)
        if dentist is None:
            dentist = create_user(role="dentista", clinic=clinic, first_name="Dr.")

        return Appointment.objects.create(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=date_val or date.today(),
            start_time=start,
            end_time=end,
            status=status,
        )

    return _create


@pytest.fixture
def create_schedule_slot(db, create_clinic):
    """Create a ScheduleSlot instance."""

    def _create(
        clinic=None,
        dentist=None,
        day_of_week=0,  # Monday
        start=time(9, 0),
        end=time(17, 0),
        is_active=True,
    ):
        from appointments.models import ScheduleSlot

        if clinic is None:
            clinic = create_clinic()

        return ScheduleSlot.objects.create(
            clinic=clinic,
            dentist=dentist,
            day_of_week=day_of_week,
            start_time=start,
            end_time=end,
            is_active=is_active,
        )

    return _create


@pytest.fixture
def create_inventory_item(db, create_clinic):
    """Create an InventoryItem instance."""

    def _create(
        clinic=None,
        name="Guantes de látex",
        category="supply",
        stock_current=Decimal("100.00"),
        stock_minimum=Decimal("20.00"),
        stock_maximum=Decimal("500.00"),
        unit="caja",
        unit_price=Decimal("50.00"),
        is_active=True,
    ):
        from inventory.models import InventoryItem

        if clinic is None:
            clinic = create_clinic()

        return InventoryItem.objects.create(
            clinic=clinic,
            name=name,
            category=category,
            stock_current=stock_current,
            stock_minimum=stock_minimum,
            stock_maximum=stock_maximum,
            unit=unit,
            unit_price=unit_price,
            is_active=is_active,
        )

    return _create


@pytest.fixture
def create_invoice(db, create_clinic, create_patient):
    """Create an Invoice instance."""

    def _create(
        clinic=None,
        patient=None,
        status="draft",
        folio=None,
        rfc_receptor="XAXX010101000",
        nombre_receptor="Público General",
        subtotal=Decimal("1000.00"),
        iva=Decimal("160.00"),
        total=Decimal("1160.00"),
        concepts=None,
    ):
        from invoicing.models import Invoice

        if clinic is None:
            clinic = create_clinic()
        if patient is None:
            patient = create_patient(clinic=clinic)

        return Invoice.objects.create(
            clinic=clinic,
            patient=patient,
            folio=folio or f"F-{uuid.uuid4().hex[:6].upper()}",
            rfc_receptor=rfc_receptor,
            nombre_receptor=nombre_receptor,
            uso_cfdi="G03",
            metodo_pago="PUE",
            forma_pago="01",
            moneda="MXN",
            subtotal=subtotal,
            iva=iva,
            total=total,
            concepts=concepts
            or [
                {
                    "clave_sat": "84111506",
                    "descripcion": "Consulta dental",
                    "cantidad": 1,
                    "valor_unitario": 1000.00,
                    "importe": 1000.00,
                    "iva_rate": 0.16,
                }
            ],
            status=status,
        )

    return _create


@pytest.fixture
def create_fiscal_config(db, create_clinic):
    """Create a FiscalConfig instance."""

    def _create(clinic=None, rfc="XAXX010101000", razon_social="Test Clinic SA de CV"):
        from invoicing.models import FiscalConfig

        if clinic is None:
            clinic = create_clinic()

        return FiscalConfig.objects.create(
            clinic=clinic,
            rfc=rfc,
            razon_social=razon_social,
            regimen_fiscal="601",
            fiscal_address={"codigo_postal": "06300"},
            is_validated=True,
        )

    return _create


# ---------------------------------------------------------------------------
# Encryption key fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def set_encryption_key(settings):
    """Set a deterministic encryption key for all tests."""
    import base64
    import os

    key = base64.b64encode(os.urandom(32)).decode()
    settings.ENCRYPTION_KEY = key

    # Reset the encryption service key cache
    from patients.services.encryption_service import reset_key

    reset_key()


# ---------------------------------------------------------------------------
# Two-clinic isolation fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_clinics(db, create_clinic):
    """Create two separate clinics for RLS isolation tests."""
    clinic_a = create_clinic(name="Clinic A", rfc="XAXX01010100A")
    clinic_b = create_clinic(name="Clinic B", rfc="XAXX01010100B")
    return clinic_a, clinic_b


@pytest.fixture
def clinic_users(db, create_user, two_clinics):
    """Create users for two clinics: admin + dentist per clinic."""
    clinic_a, clinic_b = two_clinics

    admin_a = create_user(
        email="admin_a@test.com",
        role="admin",
        clinic=clinic_a,
        first_name="Admin",
        last_name="A",
    )
    dentist_a = create_user(
        email="dentist_a@test.com",
        role="dentista",
        clinic=clinic_a,
        first_name="Dr.",
        last_name="A",
    )
    admin_b = create_user(
        email="admin_b@test.com",
        role="admin",
        clinic=clinic_b,
        first_name="Admin",
        last_name="B",
    )
    dentist_b = create_user(
        email="dentist_b@test.com",
        role="dentista",
        clinic=clinic_b,
        first_name="Dr.",
        last_name="B",
    )

    return {
        "clinic_a": clinic_a,
        "clinic_b": clinic_b,
        "admin_a": admin_a,
        "dentist_a": dentist_a,
        "admin_b": admin_b,
        "dentist_b": dentist_b,
    }
