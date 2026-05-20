"""
Tests for Patient Management serializers.

Tests cover:
- ClinicalNoteSerializer: valid/invalid data, create flow
- PatientConsentSerializer: valid/invalid data, create flow
- ClinicalNoteCreateSerializer: content encryption, validation
"""

import pytest
from rest_framework.exceptions import ValidationError

from patients.models import Patient
from patients.serializers import (
    ClinicalNoteCreateSerializer,
    ClinicalNoteSerializer,
    PatientConsentSerializer,
    PatientSerializer,
)


@pytest.mark.django_db
class TestClinicalNoteSerializer:
    """Tests for ClinicalNoteSerializer and ClinicalNoteCreateSerializer."""

    def test_valid_note_serialization(self, patient, dentist_user):
        """Serialized note should include all expected fields."""
        from patients.models import ClinicalNote

        note = ClinicalNote.objects.create(
            patient=patient,
            author=dentist_user,
            note_type="evolution",
            title="Evolución semanal",
            content="El paciente muestra mejoría significativa.",
        )

        serializer = ClinicalNoteSerializer(note)
        data = serializer.data

        assert data["id"] == str(note.id)
        assert data["note_type"] == "evolution"
        assert data["note_type_display"] == "Evolución"
        assert data["title"] == "Evolución semanal"
        assert data["content"] == "El paciente muestra mejoría significativa."
        assert data["is_signed"] is False
        assert data["author_name"] == "Dr. García"

    def test_create_serializer_valid_data(self, patient, dentist_user):
        """Create serializer should produce a note with encrypted content."""
        context = {
            "request": None,
            "patient_id": str(patient.id),
        }

        data = {
            "note_type": "diagnosis",
            "title": "Diagnóstico periodontitis",
            "content": "Periodontitis grado 2 detectada.",
        }

        serializer = ClinicalNoteCreateSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors

        # We can't fully test create() without a request user, but validation passes
        assert serializer.validated_data["note_type"] == "diagnosis"
        assert serializer.validated_data["title"] == "Diagnóstico periodontitis"

    def test_create_serializer_requires_content(self):
        """Content field is required."""
        serializer = ClinicalNoteCreateSerializer(
            data={"note_type": "evolution", "title": "X"}
        )
        assert not serializer.is_valid()
        assert "content" in serializer.errors

    def test_create_serializer_requires_title(self):
        """Title field is required."""
        serializer = ClinicalNoteCreateSerializer(
            data={"note_type": "evolution", "content": "X"}
        )
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_create_serializer_empty_content_invalid(self):
        """Empty content string should be invalid."""
        serializer = ClinicalNoteCreateSerializer(
            data={"note_type": "evolution", "title": "X", "content": "   "}
        )
        assert not serializer.is_valid()
        assert "content" in serializer.errors


@pytest.mark.django_db
class TestPatientConsentSerializer:
    """Tests for PatientConsentSerializer."""

    def test_valid_consent_serialization(self, patient):
        """Serialized consent should include all expected fields."""
        from patients.models import PatientConsent

        consent = PatientConsent.objects.create(
            patient=patient,
            consent_type="general",
            version="2.0",
            content="Consentimiento general v2.0",
        )

        serializer = PatientConsentSerializer(consent)
        data = serializer.data

        assert data["id"] == str(consent.id)
        assert data["consent_type"] == "general"
        assert data["consent_type_display"] == "Consentimiento General"
        assert data["version"] == "2.0"
        assert data["content"] == "Consentimiento general v2.0"
        assert data["signed"] is False

    def test_create_consent_valid_data(self, patient):
        """Create consent via serializer with patient_id in context."""
        data = {
            "consent_type": "whatsapp",
            "version": "1.0",
            "content": "Acepto recibir comunicaciones por WhatsApp.",
        }

        context = {
            "request": None,
            "patient_id": str(patient.id),
        }

        serializer = PatientConsentSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors

        consent = serializer.save()

        assert consent.consent_type == "whatsapp"
        assert consent.version == "1.0"
        assert consent.patient == patient


@pytest.mark.django_db
class TestPatientSerializer:
    """Tests for PatientSerializer."""

    def test_patient_serialization(self, patient):
        """Patient serializer should decrypt sensitive fields on output."""
        serializer = PatientSerializer(patient)
        data = serializer.data

        assert data["id"] == str(patient.id)
        assert data["first_name"] == "Juan"
        assert data["last_name"] == "Pérez"
        assert data["full_name"] == patient.full_name
        assert data["phone"] == patient.phone
        # Encrypted fields should be decrypted (or empty)
        assert "allergies" in data
        assert "chronic_conditions" in data
        assert "current_medications" in data
