"""
CFDI Invoicing views.

ViewSets:
- FiscalConfigViewSet: CRUD for fiscal configuration + validate-csd action
- InvoiceViewSet: CRUD for invoices + stamp, cancel, pdf/xml download actions

All views enforce tenant isolation via RLS (clinic_id from JWT).
"""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from invoicing.models import FiscalConfig, Invoice
from invoicing.serializers import (
    FiscalConfigSerializer,
    InvoiceCreateSerializer,
    InvoiceSerializer,
)
from core.permissions import IsAdminOrReadOnly

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FiscalConfigViewSet
# ---------------------------------------------------------------------------


class FiscalConfigViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for fiscal configuration.

    Endpoints:
    - GET    /api/v1/fiscal-config/              — list configs (one per clinic)
    - GET    /api/v1/fiscal-config/{id}/         — get config detail
    - POST   /api/v1/fiscal-config/              — create config (admin only)
    - PATCH  /api/v1/fiscal-config/{id}/         — update config (admin only)
    - POST   /api/v1/fiscal-config/{id}/validate-csd/ — validate CSD certificate
    """

    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """Return fiscal configs for the current clinic."""
        return FiscalConfig.objects.all().select_related("clinic")

    def get_serializer_class(self):
        return FiscalConfigSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=True, methods=["post"], url_path="validate-csd")
    def validate_csd(self, request, pk=None):
        """
        Validate the CSD certificate and key pair.

        Checks that:
        1. The .cer file exists and is a valid X.509 certificate
        2. The .key file exists and can be loaded with the provided password
        3. The certificate and key match (same public key)
        4. The certificate is not expired

        Body:
        {
            "csd_password": "string"  // Plain text password for the .key file
        }
        """
        config = self.get_object()

        csd_password = request.data.get("csd_password")
        if not csd_password:
            return Response(
                {
                    "error": "missing_password",
                    "message": "Se requiere la contraseña del CSD.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate paths exist
        if not config.csd_cert_path or not config.csd_key_path:
            return Response(
                {
                    "error": "missing_files",
                    "message": "Los paths del CSD (.cer y .key) no están configurados.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Load and validate certificate
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization

            with open(config.csd_cert_path, "rb") as f:
                cert_data = f.read()
            cert = x509.load_der_x509_certificate(cert_data)

            # Check expiration
            import datetime

            now = datetime.datetime.now(datetime.timezone.utc)
            if cert.not_valid_after_utc < now:
                return Response(
                    {
                        "error": "expired_cert",
                        "message": "El certificado CSD está expirado.",
                        "expired_at": cert.not_valid_after_utc.isoformat(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Load and validate key
            with open(config.csd_key_path, "rb") as f:
                key_data = f.read()

            private_key = serialization.load_der_private_key(
                key_data,
                password=csd_password.encode("utf-8"),
            )

            # Verify certificate and key match
            cert_public_key = cert.public_key()
            key_public_key = private_key.public_key()

            if cert_public_key.public_numbers() != key_public_key.public_numbers():
                return Response(
                    {
                        "error": "key_mismatch",
                        "message": "El certificado y la clave no coinciden.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark as validated
            config.is_validated = True
            config.save(update_fields=["is_validated", "updated_at"])

            return Response(
                {
                    "message": "CSD validado exitosamente.",
                    "rfc": config.rfc,
                    "razon_social": config.razon_social,
                    "cert_serial": f"{cert.serial_number:020X}",
                    "cert_valid_until": cert.not_valid_after_utc.isoformat(),
                    "is_validated": True,
                }
            )

        except FileNotFoundError:
            return Response(
                {
                    "error": "file_not_found",
                    "message": "No se encontró el archivo del CSD.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as e:
            return Response(
                {
                    "error": "invalid_password",
                    "message": f"Contraseña incorrecta: {str(e)}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("CSD validation error: %s", e)
            return Response(
                {
                    "error": "validation_failed",
                    "message": f"Error validando el CSD: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# InvoiceViewSet
# ---------------------------------------------------------------------------


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for invoices.

    Endpoints:
    - GET    /api/v1/invoices/                   — list invoices (?status=, ?patient_id=)
    - POST   /api/v1/invoices/                   — create invoice
    - GET    /api/v1/invoices/{id}/              — get invoice detail
    - PATCH  /api/v1/invoices/{id}/              — update invoice (draft only)
    - DELETE /api/v1/invoices/{id}/              — delete invoice (draft only)
    - POST   /api/v1/invoices/{id}/stamp/        — stamp invoice via Finkok
    - POST   /api/v1/invoices/{id}/cancel/       — cancel stamped invoice
    - GET    /api/v1/invoices/{id}/pdf/          — download PDF
    - GET    /api/v1/invoices/{id}/xml/          — download XML

    Filtering:
    - ?status=draft: Filter by status
    - ?patient_id=uuid: Filter by patient
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return invoices for the current clinic."""
        queryset = Invoice.objects.all().select_related(
            "patient",
            "clinic",
            "appointment",
            "created_by",
        )

        # Apply filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        patient_filter = self.request.query_params.get("patient_id")
        if patient_filter:
            queryset = queryset.filter(patient_id=patient_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_destroy(self, instance):
        """Only allow deletion of draft invoices."""
        if instance.status != Invoice.Status.DRAFT:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                "Solo se pueden eliminar facturas en estado borrador."
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def stamp(self, request, pk=None):
        """
        Stamp an invoice via Finkok PAC.

        Flow:
        1. Build CFDI 4.0 XML from invoice data
        2. Sign XML with CSD certificate
        3. Encode as base64
        4. Send to Finkok for stamping
        5. Save UUID, XML URL, and stamp date

        Returns the stamping result.
        """
        invoice = self.get_object()

        # Validate stamping eligibility
        if invoice.status not in (
            Invoice.Status.DRAFT,
            Invoice.Status.PENDING_STAMP,
            Invoice.Status.ERROR,
        ):
            return Response(
                {
                    "error": "invalid_status",
                    "message": f"No se puede timbrar una factura en estado '{invoice.get_status_display()}'.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get fiscal config
        try:
            fiscal_config = request.user.clinic.fiscal_config
        except FiscalConfig.DoesNotExist:
            return Response(
                {
                    "error": "no_fiscal_config",
                    "message": "La clínica no tiene configuración fiscal.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not fiscal_config.is_validated:
            return Response(
                {
                    "error": "csd_not_validated",
                    "message": "El CSD no ha sido validado.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check stamp balance before attempting to stamp
        clinic = request.user.clinic
        if clinic.stamps_remaining < 1:
            return Response(
                {
                    "error": "no_stamps",
                    "message": (
                        "No tienes timbres disponibles. "
                        "Recarga tu saldo de timbres CFDI para continuar facturando."
                    ),
                    "stamps_remaining": 0,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Mark as pending
        invoice.status = Invoice.Status.PENDING_STAMP
        invoice.save(update_fields=["status", "updated_at"])

        try:
            # Build CFDI XML
            from invoicing.services.cfdi_builder import (
                build_cfdi_xml,
                encode_for_finkok,
                sign_cfdi,
            )

            xml_string = build_cfdi_xml(invoice, fiscal_config)

            # Sign the XML
            signed_xml = sign_cfdi(
                xml_string,
                fiscal_config.csd_cert_path,
                fiscal_config.csd_key_path,
                _decrypt_csd_password(fiscal_config),
            )

            # Encode for Finkok
            xml_base64 = encode_for_finkok(signed_xml)

            # Send to Finkok
            from invoicing.services.finkok_service import FinkokService

            finkok = FinkokService(
                username=getattr(settings, "FINKOK_USERNAME", "demo"),
                password=getattr(settings, "FINKOK_PASSWORD", "demo123"),
                sandbox=getattr(settings, "FINKOK_SANDBOX", True),
            )

            result = finkok.stamp(xml_base64)

            if result.success:
                # Decode signed XML from Finkok (base64) to store for download
                xml_content = ""
                if result.xml:
                    try:
                        import base64 as b64

                        xml_content = b64.b64decode(result.xml).decode("utf-8")
                    except Exception as decode_err:
                        logger.warning("Failed to decode Finkok XML: %s", decode_err)

                invoice.mark_stamped(
                    uuid=result.uuid,
                    sat_certificate=result.sat_certificate,
                    stamp_date=_parse_stamp_date(result.stamp_date),
                    xml_url=f"/api/v1/invoices/{invoice.id}/xml/",
                    pdf_url=f"/api/v1/invoices/{invoice.id}/pdf/",
                    xml_content=xml_content,
                )

                # Decrement stamp balance (stamps_remaining >= 1 was checked above)
                clinic.stamps_remaining -= 1
                clinic.save(update_fields=["stamps_remaining", "updated_at"])

                return Response(
                    {
                        "message": "Factura timbrada exitosamente.",
                        "cfdi_uuid": result.uuid,
                        "stamp_date": result.stamp_date,
                        "xml_url": invoice.xml_url,
                        "pdf_url": invoice.pdf_url,
                        "stamps_remaining": clinic.stamps_remaining,
                    }
                )
            else:
                invoice.mark_error(result.error)
                return Response(
                    {
                        "error": "stamp_failed",
                        "message": result.error,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        except Exception as e:
            logger.error("Stamping error for invoice %s: %s", invoice.id, e)
            invoice.mark_error(str(e))
            return Response(
                {
                    "error": "stamp_error",
                    "message": f"Error al timbrar: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        Request cancellation of a stamped invoice.

        Body:
        {
            "reason": "02",            // SAT reason: 01, 02, 03, 04
            "folio_sustitucion": ""    // Required for reason 01
        }
        """
        invoice = self.get_object()

        if invoice.status not in (
            Invoice.Status.STAMPED,
            Invoice.Status.SENT,
            Invoice.Status.PAID,
        ):
            return Response(
                {
                    "error": "invalid_status",
                    "message": "Solo se pueden cancelar facturas timbradas.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "02")
        folio_sustitucion = request.data.get("folio_sustitucion", "")

        if reason == "01" and not folio_sustitucion:
            return Response(
                {
                    "error": "missing_folio",
                    "message": "El folio de sustitución es obligatorio para el motivo 01.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Send cancellation to Finkok
            from invoicing.services.finkok_service import FinkokService

            finkok = FinkokService(
                username=getattr(settings, "FINKOK_USERNAME", "demo"),
                password=getattr(settings, "FINKOK_PASSWORD", "demo123"),
                sandbox=getattr(settings, "FINKOK_SANDBOX", True),
            )

            cancel_result = finkok.cancel(
                uuid=invoice.cfdi_uuid,
                rfc_emisor=invoice.clinic.fiscal_config.rfc,
                reason=reason,
                folio_sustitucion=folio_sustitucion,
            )

            if cancel_result.success:
                invoice.cancel(
                    reason=reason,
                    folio_sustitucion=folio_sustitucion,
                    user=request.user,
                )

                # If SAT confirms immediately, mark as cancelled
                if cancel_result.status == "Cancelado":
                    invoice.mark_cancelled()

                return Response(
                    {
                        "message": "Cancelación solicitada exitosamente.",
                        "sat_status": cancel_result.status,
                    }
                )
            else:
                return Response(
                    {
                        "error": "cancel_failed",
                        "message": cancel_result.error,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        except Exception as e:
            logger.error("Cancellation error for invoice %s: %s", invoice.id, e)
            return Response(
                {
                    "error": "cancel_error",
                    "message": f"Error al cancelar: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pk=None):
        """Download the PDF representation of the invoice."""
        invoice = self.get_object()

        if not invoice.cfdi_uuid:
            return Response(
                {"error": "not_stamped", "message": "La factura no ha sido timbrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from invoicing.services.pdf_service import generate_invoice_pdf

            pdf_bytes = generate_invoice_pdf(invoice, invoice.clinic.fiscal_config)

            from django.http import HttpResponse

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="factura_{invoice.folio}.pdf"'
            )
            return response

        except Exception as e:
            logger.error("PDF generation error: %s", e)
            return Response(
                {"error": "pdf_error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="xml")
    def download_xml(self, request, pk=None):
        """Download the CFDI XML file."""
        invoice = self.get_object()

        if not invoice.cfdi_uuid:
            return Response(
                {"error": "not_stamped", "message": "La factura no ha sido timbrada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not invoice.xml_content:
            return Response(
                {"error": "no_xml", "message": "El XML timbrado no está disponible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from django.http import HttpResponse

        response = HttpResponse(
            invoice.xml_content.encode("utf-8"),
            content_type="application/xml",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="factura_{invoice.folio}.xml"'
        )
        return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decrypt_csd_password(fiscal_config: FiscalConfig) -> str:
    """
    Decrypt the CSD password from the database.

    Uses the AES-256-GCM encryption service to decrypt the stored password.
    The password is stored as encrypted BinaryField bytes (base64-encoded ciphertext).
    """
    if not fiscal_config.csd_password_encrypted:
        raise ValueError("CSD password not configured.")

    try:
        from patients.services.encryption_service import decrypt

        # BinaryField stores raw bytes of the base64-encoded ciphertext
        encrypted_str = (
            fiscal_config.csd_password_encrypted.decode("utf-8")
            if isinstance(fiscal_config.csd_password_encrypted, (bytes, memoryview))
            else str(fiscal_config.csd_password_encrypted)
        )
        return decrypt(encrypted_str)
    except Exception as e:
        logger.warning("Failed to decrypt CSD password: %s. Using placeholder.", e)
        return "placeholder"


def _parse_stamp_date(stamp_date_str: str):
    """Parse Finkok stamp date string to datetime."""
    if not stamp_date_str:
        return timezone.now()

    try:
        from datetime import datetime as dt

        # Handle ISO 8601 format
        return dt.fromisoformat(stamp_date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return timezone.now()
