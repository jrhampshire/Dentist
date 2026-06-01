"""
Tests for dental_records models.

Covers:
- Model creation for all 12 models
- DentalRecordEntry append-only constraint (update/delete prevention)
- Tooth/ToothSurface materialization via signal
- Tenant isolation (two clinics, verify patient scoping)
- MedicalHistory versioning
- PatientImage upload path format
- TreatmentProcedure appointment linking
"""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from dental_records.models import (
    DentalRecordEntry,
    MedicalHistory,
    PatientImage,
    Tooth,
    ToothSurface,
    TreatmentPhase,
    TreatmentPlan,
    TreatmentProcedure,
    VitalSigns,
    validate_fdi,
)


# ─────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def clinic_a(db):
    """Create clinic A for tenant isolation tests."""
    from clinics.models import Clinic

    return Clinic.objects.create(name="Clínica A", rfc="XAXX01010100A")


@pytest.fixture
def clinic_b(db):
    """Create clinic B for tenant isolation tests."""
    from clinics.models import Clinic

    return Clinic.objects.create(name="Clínica B", rfc="XAXX01010100B")


@pytest.fixture
def user_a(db):
    """Create a dentist user for clinic A."""
    from accounts.models import User

    return User.objects.create_user(
        email="dentist_a@test.com",
        password="testpass123",
        first_name="Dentista",
        last_name="A",
        role="dentista",
    )


@pytest.fixture
def user_b(db):
    """Create a dentist user for clinic B."""
    from accounts.models import User

    return User.objects.create_user(
        email="dentist_b@test.com",
        password="testpass123",
        first_name="Dentista",
        last_name="B",
        role="dentista",
    )


@pytest.fixture
def patient_a(clinic_a):
    """Create a patient in clinic A."""
    from patients.models import Patient

    return Patient.objects.create(
        clinic=clinic_a,
        first_name="Juan",
        last_name="Pérez",
        phone="5550000001",
        date_of_birth=date(1990, 1, 1),
    )


@pytest.fixture
def patient_b(clinic_b):
    """Create a patient in clinic B."""
    from patients.models import Patient

    return Patient.objects.create(
        clinic=clinic_b,
        first_name="María",
        last_name="García",
        phone="5550000002",
        date_of_birth=date(1985, 6, 15),
    )


# ─────────────────────────────────────────────────────────────────────────
# FDI Validation
# ─────────────────────────────────────────────────────────────────────────


class TestFDIValidation:
    """Test FDI tooth code validation."""

    @pytest.mark.parametrize(
        "valid_code",
        [
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            18,  # upper right permanent
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,  # upper left permanent
            31,
            32,
            33,
            34,
            35,
            36,
            37,
            38,  # lower left permanent
            41,
            42,
            43,
            44,
            45,
            46,
            47,
            48,  # lower right permanent
            51,
            52,
            53,
            54,
            55,  # upper right primary
            61,
            62,
            63,
            64,
            65,  # upper left primary
            71,
            72,
            73,
            74,
            75,  # lower left primary
            81,
            82,
            83,
            84,
            85,  # lower right primary
        ],
    )
    def test_valid_fdi_codes(self, valid_code):
        """Valid FDI codes should pass validation."""
        # Should not raise
        validate_fdi(valid_code)

    @pytest.mark.parametrize(
        "invalid_code",
        [
            0,
            10,
            19,
            20,
            49,
            50,
            86,
            90,
            99,
            100,
            -1,
            200,
        ],
    )
    def test_invalid_fdi_codes(self, invalid_code):
        """Invalid FDI codes should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_fdi(invalid_code)


# ─────────────────────────────────────────────────────────────────────────
# DentalRecordEntry — Append-only constraint
# ─────────────────────────────────────────────────────────────────────────


class TestDentalRecordEntry:
    """Test DentalRecordEntry append-only behavior and creation."""

    def test_create_entry(self, patient_a, user_a):
        """Should create a DentalRecordEntry successfully."""
        entry = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            notes="Caries en oclusal del 11",
            created_by=user_a,
        )
        assert entry.pk is not None
        assert entry.tooth_fdi == 11
        assert entry.surface == "occlusal"
        assert entry.condition == "caries"

    def test_update_entry_raises(self, patient_a, user_a):
        """Updating an existing entry should raise ValidationError."""
        entry = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        entry.condition = "filling"
        with pytest.raises(ValidationError, match="inmutables"):
            entry.save()

    def test_delete_entry_raises(self, patient_a, user_a):
        """Deleting an existing entry should raise ValidationError."""
        entry = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        with pytest.raises(ValidationError, match="inmutables"):
            entry.delete()

    def test_entry_ordering(self, patient_a, user_a):
        """Entries should be ordered by -created_at."""
        entry1 = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        entry2 = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="mesial",
            condition="filling",
            created_by=user_a,
        )
        entries = list(DentalRecordEntry.objects.filter(patient=patient_a))
        assert entries[0].pk == entry2.pk  # newest first
        assert entries[1].pk == entry1.pk


# ─────────────────────────────────────────────────────────────────────────
# Tooth / ToothSurface — Materialized state via signal
# ─────────────────────────────────────────────────────────────────────────


class TestToothMaterialization:
    """Test that Tooth and ToothSurface are materialized on entry creation."""

    def test_entry_creates_tooth(self, patient_a, user_a):
        """Creating an entry should create a Tooth."""
        entry = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        tooth = Tooth.objects.get(patient=patient_a, tooth_fdi=11)
        assert tooth.condition == "caries"
        assert tooth.last_entry == entry

    def test_entry_creates_tooth_surface(self, patient_a, user_a):
        """Creating an entry should create a ToothSurface."""
        entry = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        tooth = Tooth.objects.get(patient=patient_a, tooth_fdi=11)
        surface_entry = ToothSurface.objects.get(tooth=tooth, surface="occlusal")
        assert surface_entry.condition == "caries"
        assert surface_entry.last_entry == entry

    def test_second_entry_updates_state(self, patient_a, user_a):
        """A second entry should update the existing Tooth and ToothSurface."""
        entry1 = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        entry2 = DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="filling",
            created_by=user_a,
        )
        # Tooth should reflect the latest condition
        tooth = Tooth.objects.get(patient=patient_a, tooth_fdi=11)
        assert tooth.condition == "filling"
        assert tooth.last_entry == entry2

        # ToothSurface should reflect the latest condition
        surface_entry = ToothSurface.objects.get(tooth=tooth, surface="occlusal")
        assert surface_entry.condition == "filling"
        assert surface_entry.last_entry == entry2

    def test_multiple_surfaces_same_tooth(self, patient_a, user_a):
        """Multiple surfaces on the same tooth should each have entries."""
        DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="mesial",
            condition="filling",
            created_by=user_a,
        )
        tooth = Tooth.objects.get(patient=patient_a, tooth_fdi=11)
        surfaces = ToothSurface.objects.filter(tooth=tooth)
        assert surfaces.count() == 2
        assert surfaces.filter(surface="occlusal").exists()
        assert surfaces.filter(surface="mesial").exists()


# ─────────────────────────────────────────────────────────────────────────
# Tenant Isolation
# ─────────────────────────────────────────────────────────────────────────


class TestTenantIsolation:
    """Verify that patients from different clinics are isolated."""

    def test_patients_isolated_by_clinic(self, patient_a, patient_b, user_a):
        """Entries for patient_a should not affect patient_b."""
        # Create entry for patient_a (clinic A)
        DentalRecordEntry.objects.create(
            patient=patient_a,
            tooth_fdi=11,
            surface="occlusal",
            condition="caries",
            created_by=user_a,
        )
        # patient_b (clinic B) should NOT have any entries
        assert DentalRecordEntry.objects.filter(patient=patient_b).count() == 0
        # patient_b should NOT have a Tooth for FDI 11
        assert not Tooth.objects.filter(patient=patient_b, tooth_fdi=11).exists()

    def test_medical_history_isolated(self, patient_a, patient_b, user_a):
        """MedicalHistory for patient_a should not be visible on patient_b."""
        MedicalHistory.objects.create(
            patient=patient_a,
            version=1,
            motivo_consulta="Dolor dental",
            created_by=user_a,
        )
        assert MedicalHistory.objects.filter(patient=patient_b).count() == 0


# ─────────────────────────────────────────────────────────────────────────
# MedicalHistory — Versioning
# ─────────────────────────────────────────────────────────────────────────


class TestMedicalHistory:
    """Test MedicalHistory versioning and creation."""

    def test_create_medical_history(self, patient_a, user_a):
        """Should create a MedicalHistory record."""
        mh = MedicalHistory.objects.create(
            patient=patient_a,
            version=1,
            motivo_consulta="Dolor en molar inferior",
            enfermedad_actual="Dolor pulsátil de 3 días",
            created_by=user_a,
        )
        assert mh.pk is not None
        assert mh.version == 1
        assert mh.is_active is True

    def test_version_increment(self, patient_a, user_a):
        """Should allow multiple versions for the same patient."""
        v1 = MedicalHistory.objects.create(
            patient=patient_a,
            version=1,
            motivo_consulta="Dolor dental",
            created_by=user_a,
        )
        v2 = MedicalHistory.objects.create(
            patient=patient_a,
            version=2,
            motivo_consulta="Revisión",
            created_by=user_a,
            is_active=True,
        )
        # Deactivate v1
        v1.is_active = False
        v1.save()

        versions = MedicalHistory.objects.filter(patient=patient_a)
        assert versions.count() == 2
        assert versions.filter(version=1, is_active=False).exists()
        assert versions.filter(version=2, is_active=True).exists()

    def test_unique_patient_version(self, patient_a, user_a):
        """Duplicate patient+version should be rejected."""
        MedicalHistory.objects.create(
            patient=patient_a,
            version=1,
            created_by=user_a,
        )
        with pytest.raises(Exception):  # IntegrityError from PostgreSQL
            MedicalHistory.objects.create(
                patient=patient_a,
                version=1,
                created_by=user_a,
            )

    def test_ordering_by_version_desc(self, patient_a, user_a):
        """Should order by -version (newest first)."""
        for v in range(1, 4):
            MedicalHistory.objects.create(
                patient=patient_a,
                version=v,
                created_by=user_a,
            )
        versions = list(MedicalHistory.objects.filter(patient=patient_a))
        assert versions[0].version == 3
        assert versions[2].version == 1

    def test_antecedentes_json_fields(self, patient_a, user_a):
        """JSON fields should store structured data."""
        mh = MedicalHistory.objects.create(
            patient=patient_a,
            version=1,
            antecedentes_patologicos=[
                {"enfermedad": "Diabetes tipo 2", "notas": "Diagnosticado 2019"}
            ],
            antecedentes_alergicos=[
                {"alergeno": "Penicilina", "reaccion": "Urticaria", "notas": ""}
            ],
            created_by=user_a,
        )
        assert len(mh.antecedentes_patologicos) == 1
        assert mh.antecedentes_patologicos[0]["enfermedad"] == "Diabetes tipo 2"
        assert len(mh.antecedentes_alergicos) == 1
        assert mh.antecedentes_alergicos[0]["alergeno"] == "Penicilina"


# ─────────────────────────────────────────────────────────────────────────
# VitalSigns
# ─────────────────────────────────────────────────────────────────────────


class TestVitalSigns:
    """Test VitalSigns creation and validation."""

    def test_create_vital_signs(self, patient_a, user_a):
        """Should create a VitalSigns record."""
        vs = VitalSigns.objects.create(
            patient=patient_a,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            heart_rate=72,
            temperature=36.5,
            recorded_by=user_a,
        )
        assert vs.pk is not None
        assert vs.blood_pressure_systolic == 120
        assert vs.blood_pressure_diastolic == 80

    def test_bp_validation_systolic_greater_than_diastolic(self, patient_a, user_a):
        """Systolic <= diastolic should raise ValidationError."""
        vs = VitalSigns(
            patient=patient_a,
            blood_pressure_systolic=80,
            blood_pressure_diastolic=120,  # systolic < diastolic
            recorded_by=user_a,
        )
        with pytest.raises(ValidationError, match="sistólica"):
            vs.full_clean()

    def test_vital_signs_without_bp(self, patient_a, user_a):
        """Should allow creating vital signs without BP."""
        vs = VitalSigns.objects.create(
            patient=patient_a,
            heart_rate=72,
            weight=70.5,
            recorded_by=user_a,
        )
        assert vs.blood_pressure_systolic is None
        assert vs.blood_pressure_diastolic is None

    def test_vital_signs_optional_fields_null(self, patient_a, user_a):
        """Optional fields should default to None/null."""
        vs = VitalSigns.objects.create(
            patient=patient_a,
            recorded_by=user_a,
        )
        assert vs.blood_pressure_systolic is None
        assert vs.heart_rate is None
        assert vs.temperature is None
        assert vs.weight is None
        assert vs.height is None


# ─────────────────────────────────────────────────────────────────────────
# PatientImage
# ─────────────────────────────────────────────────────────────────────────


class TestPatientImage:
    """Test PatientImage model and upload path."""

    def test_get_image_path_format(self, patient_a):
        """The upload path should follow the expected format."""
        instance = PatientImage(
            id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            patient=patient_a,
            image_type="xray_periapical",
        )
        from dental_records.models import get_image_path

        path = get_image_path(instance, "radiografia.jpg")
        expected = (
            "patients/{}/images/xray_periapical/"
            "12345678-1234-5678-1234-567812345678_radiografia.jpg"
        ).format(patient_a.pk)
        assert path == expected

    def test_sanitize_filename(self):
        """Filenames with spaces and paths should be sanitized."""
        from dental_records.models import sanitize_filename

        assert sanitize_filename("my photo.jpg") == "my_photo.jpg"
        assert sanitize_filename("/etc/passwd/hack.jpg") == "hack.jpg"


# ─────────────────────────────────────────────────────────────────────────
# TreatmentPlan / TreatmentPhase / TreatmentProcedure
# ─────────────────────────────────────────────────────────────────────────


class TestTreatmentPlan:
    """Test TreatmentPlan hierarchy creation."""

    def test_create_treatment_plan(self, patient_a, user_a):
        """Should create a TreatmentPlan."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Ortodoncia completa",
            description="Brackets + retenedores",
            created_by=user_a,
        )
        assert plan.pk is not None
        assert plan.status == "active"
        assert plan.name == "Ortodoncia completa"

    def test_create_phase(self, patient_a, user_a):
        """Should create a TreatmentPhase under a plan."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan de prueba",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(
            plan=plan,
            name="Fase 1: Alineación",
            order=0,
            status="pending",
        )
        assert phase.plan == plan
        assert phase.order == 0
        assert phase.status == "pending"

    def test_create_procedure(self, patient_a, user_a):
        """Should create a TreatmentProcedure under a phase."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan de prueba",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(
            plan=plan,
            name="Fase 1",
            order=0,
        )
        procedure = TreatmentProcedure.objects.create(
            phase=phase,
            tooth_fdi=11,
            description="Obturación composite en 11",
            cost=800.00,
            status="planned",
        )
        assert procedure.phase == phase
        assert procedure.description == "Obturación composite en 11"
        assert procedure.cost == 800.00

    def test_cascade_delete_plan_deletes_phases(self, patient_a, user_a):
        """Deleting a plan should cascade-delete its phases."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan a eliminar",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(
            plan=plan,
            name="Fase",
            order=0,
        )
        plan_pk = plan.pk
        plan.delete()
        assert not TreatmentPlan.objects.filter(pk=plan_pk).exists()
        assert not TreatmentPhase.objects.filter(plan_id=plan_pk).exists()

    def test_cascade_delete_phase_deletes_procedures(self, patient_a, user_a):
        """Deleting a phase should cascade-delete its procedures."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan de prueba",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(
            plan=plan,
            name="Fase",
            order=0,
        )
        procedure = TreatmentProcedure.objects.create(
            phase=phase,
            description="Procedimiento de prueba",
        )
        phase_pk = phase.pk
        phase.delete()
        assert not TreatmentPhase.objects.filter(pk=phase_pk).exists()
        assert not TreatmentProcedure.objects.filter(phase_id=phase_pk).exists()

    def test_procedure_with_invalid_fdi(self, patient_a, user_a):
        """Procedure with invalid FDI should raise ValidationError."""
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase", order=0)
        with pytest.raises(ValidationError):
            procedure = TreatmentProcedure(
                phase=phase,
                tooth_fdi=99,  # invalid
                description="Test",
            )
            procedure.full_clean()

    def test_procedure_appointment_linking(self, patient_a, user_a, clinic_a):
        """Should link a procedure to an appointment."""
        from datetime import time

        from appointments.models import Appointment, AppointmentType

        appt_type = AppointmentType.objects.create(
            clinic=clinic_a, name="Consulta", duration_minutes=30
        )
        appointment = Appointment.objects.create(
            clinic=clinic_a,
            patient=patient_a,
            appointment_type=appt_type,
            dentist=user_a,
            date=date(2026, 6, 1),
            start_time=time(9, 0),
            created_by=user_a,
        )
        plan = TreatmentPlan.objects.create(
            patient=patient_a,
            name="Plan con cita",
            created_by=user_a,
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase", order=0)
        procedure = TreatmentProcedure.objects.create(
            phase=phase,
            appointment=appointment,
            description="Procedimiento vinculado a cita",
        )
        assert procedure.appointment == appointment
        assert appointment.treatment_procedures.count() == 1
