"""
Fixtures for Patient Management tests.

Provides convenient shorthand fixtures (clinic, users, patient instances)
that compose the global factory fixtures from tests/conftest.py.
"""

import pytest

from accounts.models import User
from clinics.models import Clinic


@pytest.fixture
def clinic(db, create_clinic):
    """Shorthand: a single test clinic."""
    return create_clinic(name="Test Dental Clinic")


@pytest.fixture
def admin_user(db, create_user, clinic):
    """Shorthand: an admin user in the test clinic."""
    return create_user(
        email="admin@testclinic.com",
        role="admin",
        clinic=clinic,
        first_name="Admin",
        last_name="Principal",
    )


@pytest.fixture
def dentist_user(db, create_user, clinic):
    """Shorthand: a dentist user in the test clinic."""
    return create_user(
        email="dentist@testclinic.com",
        role="dentista",
        clinic=clinic,
        first_name="Dr.",
        last_name="García",
    )


@pytest.fixture
def receptionist_user(db, create_user, clinic):
    """Shorthand: a receptionist user in the test clinic."""
    return create_user(
        email="recepcionista@testclinic.com",
        role="recepcionista",
        clinic=clinic,
        first_name="Ana",
        last_name="López",
    )


@pytest.fixture
def patient(db, create_patient, clinic):
    """Shorthand: a test patient in the test clinic."""
    return create_patient(
        clinic=clinic,
        first_name="Juan",
        last_name="Pérez",
        phone="5512345678",
    )


@pytest.fixture
def clinical_note(db, patient, dentist_user):
    """Shorthand: an unsigned clinical note for the test patient."""
    from patients.models import ClinicalNote

    return ClinicalNote.objects.create(
        patient=patient,
        author=dentist_user,
        note_type="evolution",
        title="Nota de evolución",
        content="Paciente evoluciona favorablemente",
    )


@pytest.fixture
def signed_note(db, patient, dentist_user):
    """Shorthand: a signed clinical note."""
    from patients.models import ClinicalNote

    note = ClinicalNote.objects.create(
        patient=patient,
        author=dentist_user,
        note_type="diagnosis",
        title="Diagnóstico inicial",
        content="Caries profunda detectada en molar 16",
    )
    note.sign(user=dentist_user)
    return note


@pytest.fixture
def consent(db, patient):
    """Shorthand: an unsigned consent record."""
    from patients.models import PatientConsent

    return PatientConsent.objects.create(
        patient=patient,
        consent_type="general",
        version="1.0",
        content="Consentimiento general para tratamiento dental",
    )


@pytest.fixture
def signed_consent(db, patient, dentist_user):
    """Shorthand: a signed consent record."""
    from patients.models import PatientConsent

    consent = PatientConsent.objects.create(
        patient=patient,
        consent_type="treatment",
        version="1.0",
        content="Consentimiento para extracción dental",
    )
    consent.sign(user=dentist_user, ip_address="192.168.1.1")
    return consent
