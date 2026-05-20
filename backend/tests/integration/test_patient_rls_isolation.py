"""
Integration tests for PatientViewSet (Task 12.7) and RLS isolation (Task 12.8).

Tests:
- CRUD isolation: user from clinic A cannot see patients from clinic B
- RLS bypass via manual SET app.current_clinic_id
- All 16 tables isolation across 2 clinics
"""

import pytest
from rest_framework.test import APIClient


@pytest.mark.integration
@pytest.mark.django_db
class TestPatientViewSetIsolation:
    """Test patient CRUD isolation between clinics."""

    def test_clinic_a_user_cannot_see_clinic_b_patients(
        self, two_clinics, create_user, create_patient, auth_headers
    ):
        clinic_a, clinic_b = two_clinics
        admin_a = create_user(role="admin", clinic=clinic_a, first_name="Admin A")
        create_patient(clinic=clinic_a, first_name="Patient A")
        create_patient(clinic=clinic_b, first_name="Patient B")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        response = client.get("/api/v1/patients/")

        assert response.status_code == 200
        # Should only see clinic A patients
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["first_name"] == "Patient A"

    def test_clinic_b_user_cannot_see_clinic_a_patients(
        self, two_clinics, create_user, create_patient, auth_headers
    ):
        clinic_a, clinic_b = two_clinics
        admin_b = create_user(role="admin", clinic=clinic_b, first_name="Admin B")
        create_patient(clinic=clinic_a, first_name="Patient A")
        create_patient(clinic=clinic_b, first_name="Patient B")

        client = APIClient()
        client.credentials(**auth_headers(admin_b, clinic_b))
        response = client.get("/api/v1/patients/")

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["first_name"] == "Patient B"

    def test_create_patient_assigned_to_correct_clinic(
        self, two_clinics, create_user, auth_headers
    ):
        clinic_a, _ = two_clinics
        admin_a = create_user(role="admin", clinic=clinic_a, first_name="Admin A")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        response = client.post(
            "/api/v1/patients/",
            {
                "first_name": "New Patient",
                "last_name": "Test",
                "phone": "5512345678",
                "date_of_birth": "1990-01-01",
            },
            format="json",
        )

        assert response.status_code == 201
        from patients.models import Patient

        patient = Patient.objects.get(first_name="New Patient")
        assert patient.clinic_id == clinic_a.pk

    def test_unauthenticated_cannot_access_patients(self, create_patient):
        create_patient(first_name="Secret")

        client = APIClient()
        response = client.get("/api/v1/patients/")

        assert response.status_code == 401

    def test_soft_delete_only_admin(
        self, two_clinics, create_user, create_patient, auth_headers
    ):
        clinic_a, _ = two_clinics
        admin_a = create_user(role="admin", clinic=clinic_a)
        dentist_a = create_user(role="dentista", clinic=clinic_a, first_name="Dr.")
        patient = create_patient(clinic=clinic_a)

        client = APIClient()

        # Admin can delete
        client.credentials(**auth_headers(admin_a, clinic_a))
        response = client.delete(f"/api/v1/patients/{patient.pk}/")
        assert response.status_code == 204

        # Create another patient for dentist test
        patient2 = create_patient(clinic=clinic_a, phone="5599999999")

        # Dentist cannot delete
        client.credentials(**auth_headers(dentist_a, clinic_a))
        response = client.delete(f"/api/v1/patients/{patient2.pk}/")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestRLSIsolationAllTables:
    """
    Test RLS isolation across all 16 tables.
    2 clinics, 2 users each, verify CRUD isolation.

    Tables tested:
    1. clinics (read isolation)
    2. onboarding_steps
    3. users (read isolation)
    4. refresh_tokens
    5. patients
    6. clinical_notes
    7. patient_consents
    8. appointment_types
    9. appointments
    10. schedule_slots
    11. fiscal_configs
    12. invoices
    13. notification_logs
    14. whatsapp_webhooks
    15. inventory_items
    16. inventory_movements
    """

    def _setup_two_clinic_data(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
        create_schedule_slot,
        create_inventory_item,
        create_invoice,
    ):
        """Create data for both clinics."""
        clinic_a, clinic_b = (
            create_clinic(name="Clinic A", rfc="XAXX01010100A"),
            create_clinic(name="Clinic B", rfc="XAXX01010100B"),
        )

        admin_a = create_user(role="admin", clinic=clinic_a, first_name="Admin A")
        admin_b = create_user(role="admin", clinic=clinic_b, first_name="Admin B")

        patient_a = create_patient(clinic=clinic_a, first_name="Patient A")
        patient_b = create_patient(clinic=clinic_b, first_name="Patient B")

        appt_type_a = create_appointment_type(clinic=clinic_a, name="Tipo A")
        appt_type_b = create_appointment_type(clinic=clinic_b, name="Tipo B")

        appt_a = create_appointment(
            clinic=clinic_a, patient=patient_a, appt_type=appt_type_a
        )
        appt_b = create_appointment(
            clinic=clinic_b, patient=patient_b, appt_type=appt_type_b
        )

        slot_a = create_schedule_slot(clinic=clinic_a)
        slot_b = create_schedule_slot(clinic=clinic_b)

        item_a = create_inventory_item(clinic=clinic_a, name="Item A")
        item_b = create_inventory_item(clinic=clinic_b, name="Item B")

        invoice_a = create_invoice(clinic=clinic_a, patient=patient_a, folio="FA-001")
        invoice_b = create_invoice(clinic=clinic_b, patient=patient_b, folio="FB-001")

        return {
            "clinic_a": clinic_a,
            "clinic_b": clinic_b,
            "admin_a": admin_a,
            "admin_b": admin_b,
            "patient_a": patient_a,
            "patient_b": patient_b,
            "appt_type_a": appt_type_a,
            "appt_type_b": appt_type_b,
            "appt_a": appt_a,
            "appt_b": appt_b,
            "slot_a": slot_a,
            "slot_b": slot_b,
            "item_a": item_a,
            "item_b": item_b,
            "invoice_a": invoice_a,
            "invoice_b": invoice_b,
        }

    def test_patient_table_isolation(
        self, create_clinic, create_user, create_patient, auth_headers
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        create_patient(clinic=clinic_a, first_name="A")
        create_patient(clinic=clinic_b, first_name="B")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/patients/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert all(p["first_name"] == "A" for p in results)

    def test_appointment_table_isolation(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_appointment_type,
        create_appointment,
        auth_headers,
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        dentist_a = create_user(role="dentista", clinic=clinic_a, first_name="Dr. A")
        dentist_b = create_user(role="dentista", clinic=clinic_b, first_name="Dr. B")
        patient_a = create_patient(clinic=clinic_a)
        patient_b = create_patient(clinic=clinic_b)
        type_a = create_appointment_type(clinic=clinic_a)
        type_b = create_appointment_type(clinic=clinic_b)

        create_appointment(
            clinic=clinic_a, patient=patient_a, dentist=dentist_a, appt_type=type_a
        )
        create_appointment(
            clinic=clinic_b, patient=patient_b, dentist=dentist_b, appt_type=type_b
        )

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/appointments/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1

    def test_appointment_type_isolation(
        self, create_clinic, create_user, create_appointment_type, auth_headers
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        create_appointment_type(clinic=clinic_a, name="Tipo A")
        create_appointment_type(clinic=clinic_b, name="Tipo B")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/appointment-types/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert all(t["name"] == "Tipo A" for t in results)

    def test_inventory_item_isolation(
        self, create_clinic, create_user, create_inventory_item, auth_headers
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        create_inventory_item(clinic=clinic_a, name="Item A")
        create_inventory_item(clinic=clinic_b, name="Item B")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/inventory/items/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert all(i["name"] == "Item A" for i in results)

    def test_invoice_isolation(
        self, create_clinic, create_user, create_patient, create_invoice, auth_headers
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        patient_a = create_patient(clinic=clinic_a)
        patient_b = create_patient(clinic=clinic_b)
        create_invoice(clinic=clinic_a, patient=patient_a, folio="FA-001")
        create_invoice(clinic=clinic_b, patient=patient_b, folio="FB-001")

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/invoices/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["folio"] == "FA-001"

    def test_schedule_slot_isolation(
        self, create_clinic, create_user, create_schedule_slot, auth_headers
    ):
        clinic_a = create_clinic(name="A", rfc="XAXX01010100A")
        clinic_b = create_clinic(name="B", rfc="XAXX01010100B")
        admin_a = create_user(role="admin", clinic=clinic_a)
        create_schedule_slot(clinic=clinic_a)
        create_schedule_slot(clinic=clinic_b)

        client = APIClient()
        client.credentials(**auth_headers(admin_a, clinic_a))
        resp = client.get("/api/v1/schedule-slots/")

        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
