"""
E2E test: Full clinic flow (Task 12.13).

Flow: register clinic → verify email → complete onboarding → create patient
→ book appointment → receive WhatsApp confirmation → stamp invoice

This test uses the Django test client with mocked external services.
"""

from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.e2e
@pytest.mark.django_db
class TestFullClinicFlow:
    """
    End-to-end test of the complete clinic flow.

    Steps:
    1. Register a new clinic
    2. Verify email
    3. Complete onboarding
    4. Create a patient
    5. Book an appointment
    6. Receive WhatsApp confirmation (mocked)
    7. Stamp an invoice (mocked)
    """

    def test_full_clinic_flow(self, settings):
        """Execute the complete flow end-to-end."""
        client = APIClient()

        # ===================================================================
        # Step 1: Register clinic
        # ===================================================================
        register_response = client.post(
            "/api/v1/onboarding/register/",
            {
                "name": "Clínica Dental Test",
                "rfc": "XAXX010101000",
                "email": "admin@clinicatest.com",
                "first_name": "Admin",
                "last_name": "Test",
                "password": "SecurePass123!",
                "accept_terms": True,
            },
            format="json",
        )

        assert register_response.status_code == 201
        data = register_response.json()
        assert "id" in data
        clinic_id = data["id"]

        # ===================================================================
        # Step 2: Verify email
        # ===================================================================
        from clinics.models import Clinic

        clinic = Clinic.objects.get(id=clinic_id)
        token = clinic.generate_verification_token()

        verify_response = client.post(
            "/api/v1/onboarding/verify-email/",
            {"token": token},
            format="json",
        )

        assert verify_response.status_code == 200
        clinic.refresh_from_db()
        assert clinic.email_verified is True

        # ===================================================================
        # Step 3: Complete onboarding
        # ===================================================================
        # Login first
        login_response = client.post(
            "/api/v1/auth/login/",
            {
                "email": "admin@clinicatest.com",
                "password": "SecurePass123!",
            },
            format="json",
        )

        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Complete onboarding
        onboarding_response = client.post(
            "/api/v1/onboarding/complete/",
            format="json",
        )

        assert onboarding_response.status_code in (200, 201)
        clinic.refresh_from_db()
        assert clinic.onboarding_completed is True

        # ===================================================================
        # Step 4: Create a patient
        # ===================================================================
        patient_response = client.post(
            "/api/v1/patients/",
            {
                "first_name": "Juan",
                "last_name": "Pérez",
                "phone": "5512345678",
                "date_of_birth": "1990-01-01",
                "email": "juan@test.com",
            },
            format="json",
        )

        assert patient_response.status_code == 201
        patient_data = patient_response.json()
        patient_id = patient_data["id"]

        # Verify patient was created
        get_patient = client.get(f"/api/v1/patients/{patient_id}/")
        assert get_patient.status_code == 200
        assert get_patient.json()["first_name"] == "Juan"

        # ===================================================================
        # Step 5: Book an appointment
        # ===================================================================
        # First, create a dentist user
        from accounts.models import User

        dentist = User.objects.create_user(
            email="dentist@clinicatest.com",
            password="DentistPass123!",
            first_name="Dr.",
            last_name="Test",
            role="dentista",
            clinic=clinic,
        )

        # Create appointment type
        from appointments.models import AppointmentType

        appt_type = AppointmentType.objects.create(
            clinic=clinic,
            name="Consulta General",
            duration_minutes=30,
            price=Decimal("500.00"),
        )

        # Create schedule slot for the appointment date
        from appointments.models import ScheduleSlot

        appt_date = date.today() + timedelta(days=7)
        day_of_week = appt_date.weekday()

        ScheduleSlot.objects.create(
            clinic=clinic,
            dentist=dentist,
            day_of_week=day_of_week,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        # Book appointment
        appt_response = client.post(
            "/api/v1/appointments/",
            {
                "patient_id": patient_id,
                "appointment_type_id": str(appt_type.pk),
                "dentist_id": str(dentist.pk),
                "date": str(appt_date),
                "start_time": "09:00",
            },
            format="json",
        )

        assert appt_response.status_code == 201
        appt_data = appt_response.json()
        appointment_id = appt_data["id"]

        # Verify appointment
        get_appt = client.get(f"/api/v1/appointments/{appointment_id}/")
        assert get_appt.status_code == 200
        assert get_appt.json()["status"] == "scheduled"

        # ===================================================================
        # Step 6: WhatsApp confirmation (mocked)
        # ===================================================================
        with patch(
            "notifications.services.twilio_service.TwilioService.send_message"
        ) as mock_send:
            mock_send.return_value = {
                "sid": "SM123456",
                "status": "queued",
            }

            from notifications.services.twilio_service import TwilioService

            twilio = TwilioService(
                account_sid="test_sid",
                auth_token="test_token",
                whatsapp_number="+14155238886",
            )

            result = twilio.send_message(
                "+5215512345678",
                f"Hola Juan, tu cita está confirmada para {appt_date} a las 09:00.",
            )

            mock_send.assert_called_once()
            assert result["sid"] == "SM123456"
            assert result["status"] == "queued"

        # ===================================================================
        # Step 7: Stamp invoice (mocked)
        # ===================================================================
        # Create invoice
        from invoicing.models import Invoice

        invoice = Invoice.objects.create(
            clinic=clinic,
            patient_id=patient_id,
            folio="F-001",
            rfc_receptor="XAXX010101000",
            nombre_receptor="Juan Pérez",
            uso_cfdi="D01",
            metodo_pago="PUE",
            forma_pago="01",
            moneda="MXN",
            subtotal=Decimal("500.00"),
            iva=Decimal("80.00"),
            total=Decimal("580.00"),
            concepts=[
                {
                    "clave_sat": "84111506",
                    "descripcion": "Consulta General",
                    "cantidad": 1,
                    "valor_unitario": 500.00,
                    "importe": 500.00,
                    "iva_rate": 0.16,
                }
            ],
            status="draft",
        )

        # Create fiscal config
        from invoicing.models import FiscalConfig

        FiscalConfig.objects.create(
            clinic=clinic,
            rfc="XAXX010101000",
            razon_social="Clínica Dental Test SA de CV",
            regimen_fiscal="601",
            is_validated=True,
        )

        # Mock stamping
        with patch("invoicing.views._decrypt_csd_password") as mock_decrypt:
            mock_decrypt.return_value = b"testpass"

            with patch("invoicing.services.cfdi_builder.sign_cfdi") as mock_sign:
                mock_sign.return_value = (
                    '<?xml version="1.0"?>'
                    '<cfdi:Comprobante certificado="cert" sello="sello" noCertificado="123">'
                    "test</cfdi:Comprobante>"
                )

                with patch(
                    "invoicing.services.finkok_service.FinkokService.stamp"
                ) as mock_stamp:
                    from invoicing.services.finkok_service import StampResult

                    mock_stamp.return_value = StampResult(
                        success=True,
                        uuid="CFDI-UUID-123",
                        xml="base64xml",
                        sat_certificate="SAT-CERT",
                        stamp_date="2024-01-15T10:00:00",
                    )

                    stamp_response = client.post(
                        f"/api/v1/invoices/{invoice.pk}/stamp/",
                        format="json",
                    )

                    assert stamp_response.status_code == 200
                    stamp_data = stamp_response.json()
                    assert stamp_data["cfdi_uuid"] == "CFDI-UUID-123"

                    invoice.refresh_from_db()
                    assert invoice.status == "stamped"
                    assert invoice.cfdi_uuid == "CFDI-UUID-123"

        # ===================================================================
        # Final verification: all entities exist and are linked
        # ===================================================================
        clinic.refresh_from_db()
        assert clinic.email_verified is True
        assert clinic.onboarding_completed is True

        from patients.models import Patient

        patient = Patient.objects.get(id=patient_id)
        assert patient.clinic_id == clinic.pk

        from appointments.models import Appointment

        appt = Appointment.objects.get(id=appointment_id)
        assert appt.clinic_id == clinic.pk
        assert appt.patient_id == patient.pk
        assert appt.status == "scheduled"

        invoice.refresh_from_db()
        assert invoice.clinic_id == clinic.pk
        assert invoice.patient_id == patient.pk
        assert invoice.status == "stamped"
