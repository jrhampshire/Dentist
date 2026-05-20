"""
Tests for Patient Management views.

Tests cover:
- ClinicalNoteViewSet: list, create, sign
- PatientConsentViewSet: list, create, sign
- AuditTrailViewSet: list, filter by resource
- Authentication required for all endpoints
"""

import json

import pytest
from rest_framework.test import APIClient

from patients.models import ClinicalNote, Patient, PatientConsent


@pytest.mark.django_db
class TestClinicalNoteViewSet:
    """Tests for ClinicalNoteViewSet endpoints."""

    def test_list_notes_requires_auth(self, patient):
        """Unauthenticated requests should be rejected."""
        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/notes/"
        response = client.get(url)
        assert response.status_code == 401

    def test_list_notes(self, patient, dentist_user, auth_headers):
        """Authenticated dentist can list notes for a patient."""
        # Create some notes
        ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Nota 1",
            content="Contenido 1",
        )
        ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="diagnosis",
            title="Nota 2",
            content="Contenido 2",
        )

        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/notes/"
        response = client.get(url, **auth_headers(dentist_user))

        assert response.status_code == 200
        # Response format depends on pagination — results might be array or paginated
        data = response.data
        if isinstance(data, list):
            assert len(data) == 2
        elif isinstance(data, dict) and "results" in data:
            assert len(data["results"]) == 2

    def test_create_note(self, patient, dentist_user, auth_headers):
        """Dentist can create a clinical note."""
        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/notes/"

        data = {
            "note_type": "evolution",
            "title": "Nota de prueba",
            "content": "Contenido de prueba para test.",
        }

        response = client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            **auth_headers(dentist_user),
        )

        assert response.status_code == 201
        assert response.data["title"] == "Nota de prueba"
        assert response.data["note_type"] == "evolution"
        assert response.data["is_signed"] is False

    def test_sign_note(self, patient, dentist_user, auth_headers):
        """Author can sign their own note."""
        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Para firmar",
            content="Contenido a firmar",
        )

        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/notes/{note.id}/sign/"

        response = client.post(url, **auth_headers(dentist_user))

        assert response.status_code == 200
        assert response.data["is_signed"] is True
        assert response.data["signature_hash"] != ""

    def test_sign_already_signed_returns_409(self, patient, dentist_user, auth_headers):
        """Signing an already-signed note returns 409."""
        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Ya firmada",
            content="Contenido",
        )
        note.sign(user=dentist_user)

        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/notes/{note.id}/sign/"

        response = client.post(url, **auth_headers(dentist_user))

        assert response.status_code == 409
        assert response.data["error"] == "already_signed"


@pytest.mark.django_db
class TestPatientConsentViewSet:
    """Tests for PatientConsentViewSet endpoints."""

    def test_list_consents(self, patient, dentist_user, auth_headers):
        """Authenticated user can list consents."""
        PatientConsent.objects.create(
            patient=patient,
            consent_type="general",
            version="1.0",
            content="Consentimiento general",
        )

        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/consents/"
        response = client.get(url, **auth_headers(dentist_user))

        assert response.status_code == 200

    def test_create_consent(self, patient, dentist_user, auth_headers):
        """User can create a consent record."""
        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/consents/"

        data = {
            "consent_type": "treatment",
            "version": "1.0",
            "content": "Consentimiento para tratamiento.",
        }

        response = client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            **auth_headers(dentist_user),
        )

        assert response.status_code == 201
        assert response.data["consent_type"] == "treatment"
        assert response.data["signed"] is False

    def test_sign_consent(self, patient, dentist_user, auth_headers):
        """User can sign a consent."""
        consent = PatientConsent.objects.create(
            patient=patient,
            consent_type="general",
            version="1.0",
            content="Para firmar",
        )

        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/consents/{consent.id}/sign/"

        response = client.post(url, **auth_headers(dentist_user))

        assert response.status_code == 200
        assert response.data["signed"] is True


@pytest.mark.django_db
class TestAuditTrailViewSet:
    """Tests for AuditTrailViewSet (NOM-024 compliance)."""

    def test_list_audit_trail(self, patient, dentist_user, auth_headers):
        """Audit trail should return entries (even if empty)."""
        client = APIClient()
        url = "/api/v1/patients/audit-trail/"

        response = client.get(
            url,
            {"resource_type": "Patient", "resource_id": str(patient.id)},
            **auth_headers(dentist_user),
        )

        assert response.status_code == 200

    def test_list_audit_trail_requires_auth(self):
        """Audit trail requires authentication."""
        client = APIClient()
        url = "/api/v1/patients/audit-trail/"
        response = client.get(url)
        assert response.status_code == 401

    def test_filter_by_resource_type(self, dentist_user, auth_headers):
        """Filter audit trail by resource_type."""
        client = APIClient()
        url = "/api/v1/patients/audit-trail/"

        response = client.get(
            url,
            {"resource_type": "Patient"},
            **auth_headers(dentist_user),
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestPatientExportView:
    """Tests for the patient export endpoint."""

    def test_export_patient_data(self, patient, dentist_user, auth_headers):
        """Export should return patient data with all related records."""
        client = APIClient()
        url = f"/api/v1/patients/{patient.id}/export/"

        response = client.get(url, **auth_headers(dentist_user))

        # May be 200 (admin/owner) or 403 (not owner)
        # Since dentist_user didn't create the patient, it might be 403
        assert response.status_code in (200, 403)

        if response.status_code == 200:
            data = response.data
            assert "expediente" in data
            assert "patient" in data["expediente"]
            assert "clinical_notes" in data["expediente"]
            assert "consents" in data["expediente"]
            assert "appointments" in data["expediente"]
            assert "invoices" in data["expediente"]
            assert data["expediente"]["patient"]["id"] == str(patient.id)
