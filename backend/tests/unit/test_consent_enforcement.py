"""
Tests for NOM-024 treatment consent enforcement.

Covers:
- TreatmentProcedure creation blocked without signed treatment consent
- TreatmentProcedure creation allowed with signed treatment consent
- ClinicalNote with note_type=treatment blocked without consent
- ClinicalNote with note_type=treatment allowed with consent
- Other note types not affected by consent check
"""

import pytest
from rest_framework.test import APIClient

from patients.models import PatientConsent


@pytest.mark.django_db
class TestTreatmentConsentEnforcement:
    """NOM-024: treatment operations require signed treatment consent."""

    # ── TreatmentProcedure ───────────────────────────────────────────

    def test_procedure_creation_blocked_without_consent(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """Creating a TreatmentProcedure without signed consent is rejected."""
        clinic = create_clinic(name="Consent Test Clinic")
        patient = create_patient(clinic=clinic, first_name="No", last_name="Consent")
        dentist = create_user(role="dentista", clinic=clinic)

        # Create a treatment plan and phase first
        from dental_records.models import TreatmentPhase, TreatmentPlan

        plan = TreatmentPlan.objects.create(
            patient=patient, name="Test Plan", created_by=dentist
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Phase 1", order=0)

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        response = client.post(
            f"/api/v1/dental-records/patients/{patient.id}/plans/{plan.id}/phases/{phase.id}/procedures/",
            {
                "description": "Extracción simple",
                "cost": "500.00",
                "tooth_fdi": 11,
            },
            format="json",
        )

        assert response.status_code == 400
        assert "consent_required" in str(response.data)

    def test_procedure_creation_allowed_with_consent(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """Creating a TreatmentProcedure with signed consent succeeds."""
        clinic = create_clinic(name="Consented Clinic")
        patient = create_patient(clinic=clinic, first_name="Has", last_name="Consent")
        dentist = create_user(role="dentista", clinic=clinic)

        # Create signed treatment consent
        PatientConsent.objects.create(
            patient=patient,
            consent_type=PatientConsent.ConsentType.TREATMENT,
            content="Consentimiento de tratamiento de prueba",
            signed=True,
        )

        # Create treatment plan and phase
        from dental_records.models import TreatmentPhase, TreatmentPlan

        plan = TreatmentPlan.objects.create(
            patient=patient, name="Test Plan", created_by=dentist
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Phase 1", order=0)

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        response = client.post(
            f"/api/v1/dental-records/patients/{patient.id}/plans/{plan.id}/phases/{phase.id}/procedures/",
            {
                "description": "Limpieza dental",
                "cost": "300.00",
                "tooth_fdi": 21,
            },
            format="json",
        )

        assert response.status_code == 201

    # ── ClinicalNote treatment type ──────────────────────────────────

    def test_treatment_note_blocked_without_consent(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """Creating a ClinicalNote with note_type=treatment without consent is rejected."""
        clinic = create_clinic(name="Note Test Clinic")
        patient = create_patient(
            clinic=clinic, first_name="No", last_name="ConsentNote"
        )
        dentist = create_user(role="dentista", clinic=clinic)

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        response = client.post(
            f"/api/v1/patients/{patient.id}/notes/",
            {
                "note_type": "treatment",
                "title": "Tratamiento sin consentimiento",
                "content": "Se realizó procedimiento sin consentimiento previo.",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "consent_required" in str(response.data)

    def test_treatment_note_allowed_with_consent(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """Creating a ClinicalNote with note_type=treatment with signed consent succeeds."""
        clinic = create_clinic(name="Note Consented Clinic")
        patient = create_patient(
            clinic=clinic, first_name="Has", last_name="ConsentNote"
        )
        dentist = create_user(role="dentista", clinic=clinic)

        # Create signed treatment consent
        PatientConsent.objects.create(
            patient=patient,
            consent_type=PatientConsent.ConsentType.TREATMENT,
            content="Consentimiento informado firmado",
            signed=True,
        )

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        response = client.post(
            f"/api/v1/patients/{patient.id}/notes/",
            {
                "note_type": "treatment",
                "title": "Tratamiento con consentimiento",
                "content": "Se realizó procedimiento con consentimiento previo firmado.",
            },
            format="json",
        )

        assert response.status_code == 201

    def test_other_note_types_not_blocked(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """ClinicalNotes with note_type!=treatment are NOT blocked by consent check."""
        clinic = create_clinic(name="Other Note Clinic")
        patient = create_patient(
            clinic=clinic, first_name="Other", last_name="NotePatient"
        )
        dentist = create_user(role="dentista", clinic=clinic)

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        # Evolution note — should work without consent
        response = client.post(
            f"/api/v1/patients/{patient.id}/notes/",
            {
                "note_type": "evolution",
                "title": "Evolución clínica",
                "content": "Paciente presenta evolución favorable.",
            },
            format="json",
        )
        assert response.status_code == 201

        # Diagnosis note — should work without consent
        response = client.post(
            f"/api/v1/patients/{patient.id}/notes/",
            {
                "note_type": "diagnosis",
                "title": "Diagnóstico",
                "content": "Caries oclusal en molar 36.",
            },
            format="json",
        )
        assert response.status_code == 201

    # ── Consent type specificity ─────────────────────────────────────

    def test_wrong_consent_type_does_not_satisfy(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        """A signed WhatsApp or general consent does NOT satisfy treatment consent."""
        clinic = create_clinic(name="Wrong Consent Clinic")
        patient = create_patient(
            clinic=clinic, first_name="Wrong", last_name="ConsentType"
        )
        dentist = create_user(role="dentista", clinic=clinic)

        # Create WhatsApp consent (wrong type for treatment)
        PatientConsent.objects.create(
            patient=patient,
            consent_type=PatientConsent.ConsentType.WHATSAPP,
            content="Consentimiento WhatsApp",
            signed=True,
        )

        from dental_records.models import TreatmentPhase, TreatmentPlan

        plan = TreatmentPlan.objects.create(
            patient=patient, name="Test Plan", created_by=dentist
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Phase 1", order=0)

        client = APIClient()
        client.credentials(**auth_headers(dentist, clinic))

        response = client.post(
            f"/api/v1/dental-records/patients/{patient.id}/plans/{plan.id}/phases/{phase.id}/procedures/",
            {
                "description": "Procedimiento sin consentimiento de tratamiento",
                "cost": "200.00",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "consent_required" in str(response.data)
