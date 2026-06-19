"""
Integration tests for InvoiceViewSet (Task 12.10).

Tests:
- Stamp flow (pending → stamped)
- Cancel flow (admin only)
"""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.mark.integration
@pytest.mark.django_db
class TestInvoiceStampFlow:
    """Test invoice stamping flow."""

    @patch("invoicing.views._decrypt_csd_password")
    @patch("invoicing.services.cfdi_builder.sign_cfdi")
    @patch("invoicing.services.finkok_service.FinkokService.stamp")
    def test_stamp_draft_invoice_success(
        self,
        mock_stamp,
        mock_sign,
        mock_decrypt,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")
        fiscal_config = create_fiscal_config(clinic=clinic)

        # Mock the CSD password decryption
        mock_decrypt.return_value = "testpass"

        # Mock the CSD signing (returns XML with sello/certificado)
        mock_sign.return_value = '<?xml version="1.0"?><cfdi:Comprobante certificado="cert" sello="sello" noCertificado="123">test</cfdi:Comprobante>'

        # Mock Finkok stamp response
        from invoicing.services.finkok_service import StampResult

        mock_stamp.return_value = StampResult(
            success=True,
            uuid="TEST-UUID-123",
            xml="base64xml",
            sat_certificate="SAT-CERT",
            stamp_date="2024-01-15T10:00:00",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(f"/api/v1/invoices/{invoice.pk}/stamp/")

        assert response.status_code == 200
        data = response.json()
        assert "cfdi_uuid" in data
        assert data["cfdi_uuid"] == "TEST-UUID-123"

        invoice.refresh_from_db()
        assert invoice.status == "stamped"
        assert invoice.cfdi_uuid == "TEST-UUID-123"

    @patch("invoicing.views._decrypt_csd_password")
    @patch("invoicing.services.cfdi_builder.sign_cfdi")
    @patch("invoicing.services.finkok_service.FinkokService.stamp")
    def test_stamp_failed_invoice(
        self,
        mock_stamp,
        mock_sign,
        mock_decrypt,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")
        create_fiscal_config(clinic=clinic)

        mock_decrypt.return_value = "testpass"
        mock_sign.return_value = (
            '<?xml version="1.0"?><cfdi:Comprobante>test</cfdi:Comprobante>'
        )

        from invoicing.services.finkok_service import StampResult

        mock_stamp.return_value = StampResult(
            success=False,
            error="CSD expirado",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(f"/api/v1/invoices/{invoice.pk}/stamp/")

        assert response.status_code == 502
        assert "CSD expirado" in response.json()["message"]

        invoice.refresh_from_db()
        assert invoice.status == "error"

    def test_stamp_already_stamped_fails(
        self, create_clinic, create_user, create_patient, create_invoice, auth_headers
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(
            clinic=clinic, patient=patient, status="stamped", folio="F-001"
        )
        invoice.cfdi_uuid = "EXISTING-UUID"
        invoice.save()

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(f"/api/v1/invoices/{invoice.pk}/stamp/")

        assert response.status_code == 400
        assert "invalid_status" in response.json()["error"]

    def test_stamp_no_fiscal_config_fails(
        self, create_clinic, create_user, create_patient, create_invoice, auth_headers
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")

        # No fiscal config created

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(f"/api/v1/invoices/{invoice.pk}/stamp/")

        assert response.status_code == 400
        assert "no_fiscal_config" in response.json()["error"]

    def test_stamp_no_stamps_remaining_fails(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic(stamps_remaining=0)
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")
        create_fiscal_config(clinic=clinic)

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(f"/api/v1/invoices/{invoice.pk}/stamp/")

        assert response.status_code == 402
        data = response.json()
        assert data["error"] == "no_stamps"
        assert data["stamps_remaining"] == 0


@pytest.mark.integration
@pytest.mark.django_db
class TestInvoiceCancelFlow:
    """Test invoice cancellation flow."""

    @patch("invoicing.services.finkok_service.FinkokService.cancel")
    def test_cancel_stamped_invoice(
        self,
        mock_cancel,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="stamped")
        invoice.cfdi_uuid = "TEST-UUID"
        invoice.save()
        create_fiscal_config(clinic=clinic)

        from invoicing.services.finkok_service import CancelResult

        mock_cancel.return_value = CancelResult(
            success=True,
            status="Cancelado",
        )

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            f"/api/v1/invoices/{invoice.pk}/cancel/",
            {"reason": "02"},
            format="json",
        )

        assert response.status_code == 200
        assert "Cancelación solicitada" in response.json()["message"]

        invoice.refresh_from_db()
        assert invoice.status == "cancelled"

    @patch("invoicing.services.finkok_service.FinkokService.cancel")
    def test_cancel_draft_invoice_fails(
        self,
        mock_cancel,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            f"/api/v1/invoices/{invoice.pk}/cancel/",
            {"reason": "02"},
            format="json",
        )

        assert response.status_code == 400
        assert "invalid_status" in response.json()["error"]

    def test_cancel_requires_reason_01_folio(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="stamped")
        invoice.cfdi_uuid = "TEST-UUID"
        invoice.save()

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.post(
            f"/api/v1/invoices/{invoice.pk}/cancel/",
            {"reason": "01"},  # Requires folio_sustitucion
            format="json",
        )

        assert response.status_code == 400
        assert "missing_folio" in response.json()["error"]


@pytest.mark.integration
@pytest.mark.django_db
class TestXmlDownload:
    """Test XML download endpoint."""

    def test_download_xml_returns_xml_content(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        create_fiscal_config,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="stamped")
        invoice.cfdi_uuid = "TEST-UUID-123"
        invoice.xml_content = '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0"><cfdi:Emisor Rfc="XAXX010101000"/></cfdi:Comprobante>'
        invoice.save()

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(f"/api/v1/invoices/{invoice.pk}/xml/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/xml"
        assert "cfdi:Comprobante" in response.content.decode("utf-8")
        assert 'filename="factura_' in response["Content-Disposition"]

    def test_download_xml_not_stamped_returns_400(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="draft")

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(f"/api/v1/invoices/{invoice.pk}/xml/")

        assert response.status_code == 400
        assert "not_stamped" in response.json()["error"]

    def test_download_xml_no_content_returns_404(
        self,
        create_clinic,
        create_user,
        create_patient,
        create_invoice,
        auth_headers,
    ):
        clinic = create_clinic()
        admin = create_user(role="admin", clinic=clinic)
        patient = create_patient(clinic=clinic)
        invoice = create_invoice(clinic=clinic, patient=patient, status="stamped")
        invoice.cfdi_uuid = "TEST-UUID-456"
        invoice.xml_content = ""
        invoice.save()

        client = APIClient()
        client.credentials(**auth_headers(admin, clinic))

        response = client.get(f"/api/v1/invoices/{invoice.pk}/xml/")

        assert response.status_code == 404
        assert "no_xml" in response.json()["error"]
