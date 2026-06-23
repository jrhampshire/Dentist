"""
Consent enforcement service for NOM-024 compliance.

Provides:
- require_treatment_consent(patient): Raises ValidationError if patient
  lacks a signed treatment consent.
"""

from rest_framework import serializers

from patients.models import Patient, PatientConsent


def require_treatment_consent(patient: Patient) -> None:
    """
    Verify the patient has a signed treatment consent.

    NOM-024-SSA3-2012 requires informed consent before any dental
    treatment is administered. This function blocks treatment-related
    operations (TreatmentProcedure creation, ClinicalNote with
    note_type=treatment) if no signed treatment consent exists.

    Raises:
        serializers.ValidationError: If no signed treatment consent found.
    """
    has_consent = PatientConsent.objects.filter(
        patient=patient,
        consent_type=PatientConsent.ConsentType.TREATMENT,
        signed=True,
    ).exists()

    if not has_consent:
        raise serializers.ValidationError(
            {
                "consent_required": (
                    "NOM-024: Se requiere consentimiento informado de tratamiento "
                    "firmado antes de realizar cualquier procedimiento. "
                    "Por favor, genere y firme el consentimiento en la sección "
                    "de Consentimientos del expediente del paciente."
                )
            }
        )
