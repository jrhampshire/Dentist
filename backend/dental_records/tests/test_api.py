"""
API integration tests for dental_records app.

Covers all endpoints across 6 capabilities:
- DentalRecordEntry: create, list, filter, append-only enforcement
- ToothState: materialization verification
- MedicalHistory: create, versioned update, version history
- VitalSigns: create, list, date range filter, BP validation
- PatientImage: upload, list, serve file, delete
- TreatmentPlan: CRUD with nested phases/procedures
- Tenant isolation: cross-clinic access returns 404
- Unauthenticated: all endpoints return 401
"""

import io
import uuid
from datetime import date, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APIClient

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
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _url(patient_id, path=""):
    """Build a dental-records API URL."""
    return f"/api/v1/dental-records/patients/{patient_id}/{path}"


def _make_jpeg_bytes():
    """Generate a minimal JPEG in memory."""
    img = PILImage.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def _make_pdf_bytes():
    """Generate a minimal PDF in memory (well-formed enough for validation)."""
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )
    return io.BytesIO(content)


@pytest.fixture
def api():
    return APIClient()


# ── Fixtures (inline copies from tests/conftest.py for discoverability) ──


@pytest.fixture
def make_jwt_token():
    """Generate a JWT access token for testing."""
    import jwt as pyjwt
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    def _make(user, clinic_id=None):
        now = timezone.now()
        payload = {
            "user_id": str(user.pk),
            "clinic_id": str(clinic_id or user.clinic_id),
            "role": user.role,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        return pyjwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    return _make


@pytest.fixture
def auth_headers(make_jwt_token):
    """Generate Authorization headers for a user."""

    def _headers(user, clinic_id=None):
        token = make_jwt_token(user, clinic_id)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    return _headers


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
def clinic_users(db, create_user, create_clinic):
    """Create users for two clinics: admin + dentist per clinic."""
    clinic_a = create_clinic(name="Clinic A", rfc="XAXX01010100A")
    clinic_b = create_clinic(name="Clinic B", rfc="XAXX01010100B")

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


@pytest.fixture
def authenticated_api(api, auth_headers, create_user, create_clinic):
    """API client authenticated as a dentist in a clinic."""
    clinic = create_clinic(name="Test Dental")
    user = create_user(
        role="dentista", clinic=clinic, first_name="Dr.", last_name="Test"
    )
    headers = auth_headers(user, clinic_id=str(clinic.id))
    api.credentials(**headers)
    # Attach clinic/user for convenience
    api._clinic = clinic
    api._user = user
    return api


# ─────────────────────────────────────────────────────────────────────────
# 1. DentalRecordEntry — Odontogram Entries
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDentalRecordEntryAPI:
    """Tests for dental record entry endpoints."""

    def test_create_entry(self, authenticated_api, create_patient):
        """POST creates a new odontogram entry and returns 200 with existing (idempotent)."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {
            "tooth_fdi": 11,
            "surface": "mesial",
            "condition": "caries",
            "notes": "Caries incipiente en mesial",
        }

        response = authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            data,
            format="json",
        )
        # 200 (OK) returned for idempotent pattern
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tooth_fdi"] == 11
        assert response.data["surface"] == "mesial"
        assert response.data["condition"] == "caries"
        assert response.data["condition_display"] == "Caries"

    def test_create_entry_idempotent(self, authenticated_api, create_patient):
        """Same tooth+surface+condition returns 200 with existing record (no duplicate)."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"}

        r1 = authenticated_api.post(
            _url(patient.id, "teeth/entries/"), data, format="json"
        )
        r2 = authenticated_api.post(
            _url(patient.id, "teeth/entries/"), data, format="json"
        )

        assert r1.status_code == status.HTTP_200_OK
        assert r2.status_code == status.HTTP_200_OK
        # Same entry returned
        assert r1.data["id"] == r2.data["id"]
        # Only one entry in DB
        assert DentalRecordEntry.objects.filter(patient=patient).count() == 1

    def test_list_entries(self, authenticated_api, create_patient):
        """GET lists entries for a patient."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Create 2 entries
        for fdi, surf in [(11, "mesial"), (21, "distal")]:
            authenticated_api.post(
                _url(patient.id, "teeth/entries/"),
                {"tooth_fdi": fdi, "surface": surf, "condition": "caries"},
                format="json",
            )

        response = authenticated_api.get(_url(patient.id, "teeth/entries/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_filter_by_tooth_fdi(self, authenticated_api, create_patient):
        """GET ?tooth_fdi= filters entries to that tooth only."""
        patient = create_patient(clinic=authenticated_api._clinic)

        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )
        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 21, "surface": "distal", "condition": "healthy"},
            format="json",
        )

        response = authenticated_api.get(
            _url(patient.id, "teeth/entries/"), {"tooth_fdi": 11}
        )
        assert response.status_code == status.HTTP_200_OK
        for entry in response.data:
            assert entry["tooth_fdi"] == 11

    def test_invalid_fdi_returns_400(self, authenticated_api, create_patient):
        """POST with invalid FDI code returns 400."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {"tooth_fdi": 99, "surface": "mesial", "condition": "caries"}

        response = authenticated_api.post(
            _url(patient.id, "teeth/entries/"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_surface_returns_400(self, authenticated_api, create_patient):
        """POST with invalid surface returns 400."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {"tooth_fdi": 11, "surface": "north", "condition": "caries"}

        response = authenticated_api.post(
            _url(patient.id, "teeth/entries/"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_returns_405(self, authenticated_api, create_patient):
        """DELETE is not allowed on odontogram entries."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r = authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )

        response = authenticated_api.delete(
            _url(patient.id, f"teeth/entries/{r.data['id']}/")
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_returns_405(self, authenticated_api, create_patient):
        """PUT is not allowed on odontogram entries."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r = authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )

        response = authenticated_api.put(
            _url(patient.id, f"teeth/entries/{r.data['id']}/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "filling"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_returns_405(self, authenticated_api, create_patient):
        """PATCH is not allowed on odontogram entries."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r = authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )

        response = authenticated_api.patch(
            _url(patient.id, f"teeth/entries/{r.data['id']}/"),
            {"notes": "Updated note"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ─────────────────────────────────────────────────────────────────────────
# 2. ToothState — Materialized State
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestToothStateAPI:
    """Tests for tooth state materialization endpoint."""

    def test_state_reflects_latest_entry(self, authenticated_api, create_patient):
        """Tooth state shows the latest condition after creating entries."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Create an entry
        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "teeth/state/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        tooth_11 = next((t for t in response.data if t["tooth_fdi"] == 11), None)
        assert tooth_11 is not None
        assert tooth_11["condition"] == "caries"
        assert tooth_11["condition_display"] == "Caries"
        assert len(tooth_11["surfaces"]) >= 1
        assert tooth_11["surfaces"][0]["surface"] == "mesial"
        assert tooth_11["surfaces"][0]["condition"] == "caries"

    def test_state_empty_patient(self, authenticated_api, create_patient):
        """State returns empty list for patient with no entries."""
        patient = create_patient(clinic=authenticated_api._clinic)

        response = authenticated_api.get(_url(patient.id, "teeth/state/"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_state_multiple_surfaces(self, authenticated_api, create_patient):
        """Each surface condition is independently tracked."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Caries on mesial
        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )
        # Filling on distal
        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "distal", "condition": "filling"},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "teeth/state/"))
        tooth_11 = next((t for t in response.data if t["tooth_fdi"] == 11), None)
        assert tooth_11 is not None

        surfaces = {s["surface"]: s["condition"] for s in tooth_11["surfaces"]}
        assert surfaces.get("mesial") == "caries"
        assert surfaces.get("distal") == "filling"

    def test_state_overwrites_previous(self, authenticated_api, create_patient):
        """Creating a new entry for same surface updates the state."""
        patient = create_patient(clinic=authenticated_api._clinic)

        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )
        authenticated_api.post(
            _url(patient.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "filling"},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "teeth/state/"))
        tooth_11 = next((t for t in response.data if t["tooth_fdi"] == 11), None)
        assert tooth_11["condition"] == "filling"
        assert tooth_11["surfaces"][0]["condition"] == "filling"


# ─────────────────────────────────────────────────────────────────────────
# 3. MedicalHistory — Versioned History
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMedicalHistoryAPI:
    """Tests for medical history versioned endpoints."""

    def test_create_initial(self, authenticated_api, create_patient):
        """POST creates version 1 medical history."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {
            "motivo_consulta": "Dolor dental",
            "enfermedad_actual": "Caries múltiples",
            "antecedentes_patologicos": [{"enfermedad": "Diabetes", "notas": "Tipo 2"}],
        }

        response = authenticated_api.post(
            _url(patient.id, "medical-history/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["version"] == 1
        assert response.data["is_active"] is True
        assert response.data["motivo_consulta"] == "Dolor dental"

    def test_get_active_returns_current(self, authenticated_api, create_patient):
        """GET returns the active medical history."""
        patient = create_patient(clinic=authenticated_api._clinic)
        authenticated_api.post(
            _url(patient.id, "medical-history/"),
            {"motivo_consulta": "Revision", "enfermedad_actual": ""},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "medical-history/"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["version"] == 1
        assert response.data["is_active"] is True

    def test_get_active_not_found(self, authenticated_api, create_patient):
        """GET returns 404 when no active history exists."""
        patient = create_patient(clinic=authenticated_api._clinic)

        response = authenticated_api.get(_url(patient.id, "medical-history/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_creates_new_version(self, authenticated_api, create_patient):
        """PUT deactivates current, creates version 2."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r = authenticated_api.post(
            _url(patient.id, "medical-history/"),
            {"motivo_consulta": "Primera consulta", "enfermedad_actual": ""},
            format="json",
        )
        instance_id = r.data["id"]

        response = authenticated_api.put(
            _url(patient.id, f"medical-history/{instance_id}/"),
            {"motivo_consulta": "Segunda consulta", "enfermedad_actual": "Caries"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["version"] == 2
        assert response.data["is_active"] is True
        assert response.data["id"] != instance_id

        # Old version is now inactive
        old = MedicalHistory.objects.get(id=instance_id)
        assert old.is_active is False

    def test_list_versions(self, authenticated_api, create_patient):
        """GET /history/ returns all versions."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r1 = authenticated_api.post(
            _url(patient.id, "medical-history/"),
            {"motivo_consulta": "V1", "enfermedad_actual": ""},
            format="json",
        )
        authenticated_api.put(
            _url(patient.id, f"medical-history/{r1.data['id']}/"),
            {"motivo_consulta": "V2", "enfermedad_actual": ""},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "medical-history/history/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_put_preserves_antecedents(self, authenticated_api, create_patient):
        """PUT carries forward antecedent fields not provided."""
        patient = create_patient(clinic=authenticated_api._clinic)
        r = authenticated_api.post(
            _url(patient.id, "medical-history/"),
            {
                "motivo_consulta": "V1",
                "enfermedad_actual": "",
                "antecedentes_patologicos": [
                    {"enfermedad": "Diabetes", "notas": "Tipo 2"}
                ],
            },
            format="json",
        )

        # Update without antecedentes
        r2 = authenticated_api.put(
            _url(patient.id, f"medical-history/{r.data['id']}/"),
            {"motivo_consulta": "V2 updated"},
            format="json",
        )
        assert r2.status_code == status.HTTP_200_OK
        assert len(r2.data["antecedentes_patologicos"]) == 1
        assert r2.data["antecedentes_patologicos"][0]["enfermedad"] == "Diabetes"


# ─────────────────────────────────────────────────────────────────────────
# 4. VitalSigns
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestVitalSignsAPI:
    """Tests for vital signs endpoints."""

    def test_create_vital_signs(self, authenticated_api, create_patient):
        """POST creates a vital signs record."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "heart_rate": 72,
            "temperature": "36.5",
        }

        response = authenticated_api.post(
            _url(patient.id, "vital-signs/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["blood_pressure_systolic"] == 120
        assert response.data["blood_pressure_diastolic"] == 80

    def test_list_vital_signs(self, authenticated_api, create_patient):
        """GET lists vital signs records."""
        patient = create_patient(clinic=authenticated_api._clinic)

        authenticated_api.post(
            _url(patient.id, "vital-signs/"),
            {"blood_pressure_systolic": 120, "blood_pressure_diastolic": 80},
            format="json",
        )
        authenticated_api.post(
            _url(patient.id, "vital-signs/"),
            {"blood_pressure_systolic": 130, "blood_pressure_diastolic": 85},
            format="json",
        )

        response = authenticated_api.get(_url(patient.id, "vital-signs/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_filter_by_date_range(self, authenticated_api, create_patient):
        """GET with ?from=&to= filters by date range."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Create record with specific date
        from django.utils import timezone

        vs = VitalSigns.objects.create(
            patient=patient,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            recorded_by=authenticated_api._user,
            recorded_at=timezone.now() - timedelta(days=30),
        )

        today = timezone.now().date()
        last_week = today - timedelta(days=7)

        # Filter for last week — should NOT include the old record
        response = authenticated_api.get(
            _url(patient.id, "vital-signs/"),
            {"from": str(last_week), "to": str(today)},
        )
        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data]
        # Old record should not be in results
        assert str(vs.id) not in ids

    def test_validation_systolic_greater_than_diastolic(
        self, authenticated_api, create_patient
    ):
        """BP validation: systolic must be > diastolic."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {"blood_pressure_systolic": 80, "blood_pressure_diastolic": 120}

        response = authenticated_api.post(
            _url(patient.id, "vital-signs/"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validation_at_least_one_field(self, authenticated_api, create_patient):
        """At least one vital sign field must be provided."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {"notes": "No readings"}

        response = authenticated_api.post(
            _url(patient.id, "vital-signs/"), data, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_single(self, authenticated_api, create_patient):
        """GET by ID returns single record."""
        patient = create_patient(clinic=authenticated_api._clinic)
        vs = VitalSigns.objects.create(
            patient=patient,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80,
            recorded_by=authenticated_api._user,
        )

        response = authenticated_api.get(_url(patient.id, f"vital-signs/{vs.id}/"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["blood_pressure_systolic"] == 120


# ─────────────────────────────────────────────────────────────────────────
# 5. PatientImage — Upload, list, serve
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPatientImageAPI:
    """Tests for patient image endpoints."""

    def test_upload_image(self, authenticated_api, create_patient):
        """POST uploads a JPEG image with thumbnail generated."""
        patient = create_patient(clinic=authenticated_api._clinic)
        img_bytes = _make_jpeg_bytes()
        file = SimpleUploadedFile(
            "test.jpg",
            img_bytes.read(),
            content_type="image/jpeg",
        )

        response = authenticated_api.post(
            _url(patient.id, "images/"),
            {
                "image": file,
                "image_type": "photo",
                "tooth_fdi": 11,
                "description": "Test photo",
            },
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["image_type"] == "photo"
        assert response.data["image_type_display"] == "Foto Clínica"
        assert response.data["tooth_fdi"] == 11
        assert response.data["file_size"] is not None
        assert response.data["content_type"] == "image/jpeg"
        assert response.data["thumbnail_url"] is not None
        assert response.data["image_url"] is not None

    def test_upload_pdf_no_thumbnail(self, authenticated_api, create_patient):
        """POST uploads a PDF — no thumbnail generated."""
        patient = create_patient(clinic=authenticated_api._clinic)
        pdf_bytes = _make_pdf_bytes()
        file = SimpleUploadedFile(
            "doc.pdf",
            pdf_bytes.read(),
            content_type="application/pdf",
        )

        response = authenticated_api.post(
            _url(patient.id, "images/"),
            {"image": file, "image_type": "document"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["thumbnail_url"] is None

    def test_list_images(self, authenticated_api, create_patient):
        """GET lists images for a patient."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Create 2 images via API
        for i in range(2):
            buf = _make_jpeg_bytes()
            file = SimpleUploadedFile(
                f"test_{i}.jpg", buf.read(), content_type="image/jpeg"
            )
            authenticated_api.post(
                _url(patient.id, "images/"),
                {"image": file, "image_type": "photo"},
                format="multipart",
            )

        response = authenticated_api.get(_url(patient.id, "images/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_filter_images_by_type(self, authenticated_api, create_patient):
        """GET ?image_type= filters by type."""
        patient = create_patient(clinic=authenticated_api._clinic)

        # Photo
        buf1 = _make_jpeg_bytes()
        authenticated_api.post(
            _url(patient.id, "images/"),
            {
                "image": SimpleUploadedFile(
                    "p.jpg", buf1.read(), content_type="image/jpeg"
                ),
                "image_type": "photo",
            },
            format="multipart",
        )
        # X-ray
        buf2 = _make_jpeg_bytes()
        authenticated_api.post(
            _url(patient.id, "images/"),
            {
                "image": SimpleUploadedFile(
                    "x.jpg", buf2.read(), content_type="image/jpeg"
                ),
                "image_type": "xray_periapical",
            },
            format="multipart",
        )

        response = authenticated_api.get(
            _url(patient.id, "images/"), {"image_type": "photo"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["image_type"] == "photo"

    def test_serve_file(self, authenticated_api, create_patient):
        """GET /file/ serves the original image."""
        patient = create_patient(clinic=authenticated_api._clinic)
        buf = _make_jpeg_bytes()
        file = SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")

        r = authenticated_api.post(
            _url(patient.id, "images/"),
            {"image": file, "image_type": "photo"},
            format="multipart",
        )

        response = authenticated_api.get(
            _url(patient.id, f"images/{r.data['id']}/file/")
        )
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/jpeg"

    def test_serve_thumbnail(self, authenticated_api, create_patient):
        """GET /thumbnail/ serves the generated thumbnail."""
        patient = create_patient(clinic=authenticated_api._clinic)
        buf = _make_jpeg_bytes()
        file = SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")

        r = authenticated_api.post(
            _url(patient.id, "images/"),
            {"image": file, "image_type": "photo"},
            format="multipart",
        )

        response = authenticated_api.get(
            _url(patient.id, f"images/{r.data['id']}/thumbnail/")
        )
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/jpeg"

    def test_delete_image(self, authenticated_api, create_patient):
        """DELETE removes the image record."""
        patient = create_patient(clinic=authenticated_api._clinic)
        buf = _make_jpeg_bytes()
        file = SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")

        r = authenticated_api.post(
            _url(patient.id, "images/"),
            {"image": file, "image_type": "photo"},
            format="multipart",
        )

        response = authenticated_api.delete(_url(patient.id, f"images/{r.data['id']}/"))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert PatientImage.objects.filter(id=r.data["id"]).count() == 0

    def test_upload_wrong_type_returns_400(self, authenticated_api, create_patient):
        """Upload of unsupported file type returns 400."""
        patient = create_patient(clinic=authenticated_api._clinic)
        file = SimpleUploadedFile(
            "script.txt", b"malicious content", content_type="text/plain"
        )

        response = authenticated_api.post(
            _url(patient.id, "images/"),
            {"image": file, "image_type": "photo"},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────
# 6. TreatmentPlan — Nested CRUD
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTreatmentPlanAPI:
    """Tests for treatment plan endpoints."""

    def test_create_plan(self, authenticated_api, create_patient):
        """POST creates a treatment plan."""
        patient = create_patient(clinic=authenticated_api._clinic)
        data = {
            "name": "Plan de Ortodoncia",
            "description": "Tratamiento de 18 meses",
            "status": "active",
        }

        response = authenticated_api.post(
            _url(patient.id, "plans/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Plan de Ortodoncia"
        assert response.data["status"] == "active"
        assert response.data["phases"] == []

    def test_list_plans(self, authenticated_api, create_patient):
        """GET lists plans for a patient."""
        patient = create_patient(clinic=authenticated_api._clinic)

        for name in ["Plan A", "Plan B"]:
            authenticated_api.post(
                _url(patient.id, "plans/"),
                {"name": name, "description": "", "status": "active"},
                format="json",
            )

        response = authenticated_api.get(_url(patient.id, "plans/"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2

    def test_get_plan_detail_with_phases(self, authenticated_api, create_patient):
        """GET plan detail returns nested phases and procedures."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient,
            name="Plan Completo",
            created_by=authenticated_api._user,
        )
        phase1 = TreatmentPhase.objects.create(plan=plan, name="Fase 1", order=1)
        phase2 = TreatmentPhase.objects.create(plan=plan, name="Fase 2", order=2)
        TreatmentProcedure.objects.create(
            phase=phase1, description="Limpieza", cost=500.00
        )
        TreatmentProcedure.objects.create(
            phase=phase2, description="Ortodoncia", tooth_fdi=11, cost=3000.00
        )

        response = authenticated_api.get(_url(patient.id, f"plans/{plan.id}/"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Plan Completo"
        assert len(response.data["phases"]) == 2
        assert len(response.data["phases"][0]["procedures"]) == 1

    def test_create_phase(self, authenticated_api, create_patient):
        """POST creates a phase nested under a plan."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient,
            name="Plan Test",
            created_by=authenticated_api._user,
        )

        data = {"name": "Fase Inicial", "description": "Primera fase", "order": 1}
        response = authenticated_api.post(
            _url(patient.id, f"plans/{plan.id}/phases/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Fase Inicial"
        assert response.data["order"] == 1

    def test_create_procedure(self, authenticated_api, create_patient):
        """POST creates a procedure nested under a phase."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient,
            name="Plan Test",
            created_by=authenticated_api._user,
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase 1", order=1)

        data = {
            "description": "Extracción",
            "tooth_fdi": 48,
            "cost": "1500.00",
            "status": "planned",
        }
        response = authenticated_api.post(
            _url(patient.id, f"plans/{plan.id}/phases/{phase.id}/procedures/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["description"] == "Extracción"
        assert response.data["tooth_fdi"] == 48
        assert response.data["cost"] == "1500.00"

    def test_delete_plan_cascades(self, authenticated_api, create_patient):
        """Deleting a plan cascades to phases and procedures."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient,
            name="Plan a Eliminar",
            created_by=authenticated_api._user,
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase", order=1)
        TreatmentProcedure.objects.create(phase=phase, description="Proc")

        response = authenticated_api.delete(_url(patient.id, f"plans/{plan.id}/"))
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert TreatmentPlan.objects.filter(id=plan.id).count() == 0
        assert TreatmentPhase.objects.filter(id=phase.id).count() == 0

    def test_delete_phase_cascades_procedures(self, authenticated_api, create_patient):
        """Deleting a phase cascades to procedures."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient,
            name="Plan",
            created_by=authenticated_api._user,
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase", order=1)
        proc = TreatmentProcedure.objects.create(phase=phase, description="Proc")

        response = authenticated_api.delete(
            _url(patient.id, f"plans/{plan.id}/phases/{phase.id}/")
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert TreatmentPhase.objects.filter(id=phase.id).count() == 0
        assert TreatmentProcedure.objects.filter(id=proc.id).count() == 0

    def test_procedure_invalid_fdi(self, authenticated_api, create_patient):
        """Procedure with invalid FDI returns 400."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient, name="Plan", created_by=authenticated_api._user
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase 1", order=1)

        data = {"description": "Test", "tooth_fdi": 99}
        response = authenticated_api.post(
            _url(patient.id, f"plans/{plan.id}/phases/{phase.id}/procedures/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_procedure_negative_cost(self, authenticated_api, create_patient):
        """Procedure with negative cost returns 400."""
        patient = create_patient(clinic=authenticated_api._clinic)
        plan = TreatmentPlan.objects.create(
            patient=patient, name="Plan", created_by=authenticated_api._user
        )
        phase = TreatmentPhase.objects.create(plan=plan, name="Fase 1", order=1)

        data = {"description": "Test", "cost": -100}
        response = authenticated_api.post(
            _url(patient.id, f"plans/{plan.id}/phases/{phase.id}/procedures/"),
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────
# 7. Tenant Isolation — Cross-clinic enforcement
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTenantIsolation:
    """Tests that clinic B cannot access clinic A's data."""

    def test_cross_clinic_dental_entry(
        self, clinic_users, auth_headers, create_patient, api
    ):
        """Clinic B cannot see entries from clinic A."""
        patient_a = create_patient(clinic=clinic_users["clinic_a"])

        # Create entry as clinic A user
        headers_a = auth_headers(
            clinic_users["dentist_a"], clinic_id=str(clinic_users["clinic_a"].id)
        )
        api.credentials(**headers_a)
        api.post(
            _url(patient_a.id, "teeth/entries/"),
            {"tooth_fdi": 11, "surface": "mesial", "condition": "caries"},
            format="json",
        )

        # Clinic B tries to access
        headers_b = auth_headers(
            clinic_users["dentist_b"], clinic_id=str(clinic_users["clinic_b"].id)
        )
        api.credentials(**headers_b)
        response = api.get(_url(patient_a.id, "teeth/entries/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND or response.data == []

    def test_cross_clinic_medical_history(
        self, clinic_users, auth_headers, create_patient, api
    ):
        """Clinic B cannot see clinic A's medical history."""
        patient_a = create_patient(clinic=clinic_users["clinic_a"])

        headers_a = auth_headers(
            clinic_users["dentist_a"], clinic_id=str(clinic_users["clinic_a"].id)
        )
        api.credentials(**headers_a)
        api.post(
            _url(patient_a.id, "medical-history/"),
            {"motivo_consulta": "Test", "enfermedad_actual": ""},
            format="json",
        )

        headers_b = auth_headers(
            clinic_users["dentist_b"], clinic_id=str(clinic_users["clinic_b"].id)
        )
        api.credentials(**headers_b)
        response = api.get(_url(patient_a.id, "medical-history/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_clinic_vital_signs(
        self, clinic_users, auth_headers, create_patient, api
    ):
        """Clinic B cannot see clinic A's vital signs."""
        patient_a = create_patient(clinic=clinic_users["clinic_a"])

        headers_a = auth_headers(
            clinic_users["dentist_a"], clinic_id=str(clinic_users["clinic_a"].id)
        )
        api.credentials(**headers_a)
        api.post(
            _url(patient_a.id, "vital-signs/"),
            {"blood_pressure_systolic": 120, "blood_pressure_diastolic": 80},
            format="json",
        )

        headers_b = auth_headers(
            clinic_users["dentist_b"], clinic_id=str(clinic_users["clinic_b"].id)
        )
        api.credentials(**headers_b)
        response = api.get(_url(patient_a.id, "vital-signs/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND or response.data == []

    def test_cross_clinic_images(self, clinic_users, auth_headers, create_patient, api):
        """Clinic B cannot see clinic A's images."""
        patient_a = create_patient(clinic=clinic_users["clinic_a"])

        headers_a = auth_headers(
            clinic_users["dentist_a"], clinic_id=str(clinic_users["clinic_a"].id)
        )
        api.credentials(**headers_a)

        buf = _make_jpeg_bytes()
        file = SimpleUploadedFile("test.jpg", buf.read(), content_type="image/jpeg")
        api.post(
            _url(patient_a.id, "images/"),
            {"image": file, "image_type": "photo"},
            format="multipart",
        )

        headers_b = auth_headers(
            clinic_users["dentist_b"], clinic_id=str(clinic_users["clinic_b"].id)
        )
        api.credentials(**headers_b)
        response = api.get(_url(patient_a.id, "images/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND or response.data == []

    def test_cross_clinic_treatment_plan(
        self, clinic_users, auth_headers, create_patient, api
    ):
        """Clinic B cannot see clinic A's treatment plans."""
        patient_a = create_patient(clinic=clinic_users["clinic_a"])

        headers_a = auth_headers(
            clinic_users["dentist_a"], clinic_id=str(clinic_users["clinic_a"].id)
        )
        api.credentials(**headers_a)
        api.post(
            _url(patient_a.id, "plans/"),
            {"name": "Plan A", "description": "", "status": "active"},
            format="json",
        )

        headers_b = auth_headers(
            clinic_users["dentist_b"], clinic_id=str(clinic_users["clinic_b"].id)
        )
        api.credentials(**headers_b)
        response = api.get(_url(patient_a.id, "plans/"))
        assert response.status_code == status.HTTP_404_NOT_FOUND or response.data == []


# ─────────────────────────────────────────────────────────────────────────
# 8. Unauthenticated — 401 on all endpoints
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUnauthenticated:
    """All endpoints require authentication."""

    ENDPOINTS = [
        # (method, url_template)
        ("get", "teeth/entries/"),
        ("post", "teeth/entries/"),
        ("get", "teeth/state/"),
        ("get", "medical-history/"),
        ("post", "medical-history/"),
        ("get", "vital-signs/"),
        ("post", "vital-signs/"),
        ("get", "images/"),
        ("get", "plans/"),
        ("post", "plans/"),
    ]

    def test_unauthenticated_returns_401(self, api):
        """All endpoints return 401 without auth."""
        # Use a dummy UUID since we won't reach DB anyway
        dummy_id = "00000000-0000-0000-0000-000000000001"

        for method, url_template in self.ENDPOINTS:
            url = _url(dummy_id, url_template)
            if method == "get":
                response = api.get(url)
            elif method == "post":
                response = api.post(url, {}, format="json")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{method.upper()} {url} returned {response.status_code}, expected 401"
            )
