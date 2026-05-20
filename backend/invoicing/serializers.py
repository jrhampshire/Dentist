"""
CFDI Invoicing serializers.

Serializers:
- FiscalConfigSerializer: Full read/write for fiscal configuration
- InvoiceSerializer: Full invoice detail (read)
- InvoiceCreateSerializer: Invoice creation with validation
- InvoiceStampSerializer: Stamping result data
"""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from invoicing.models import FiscalConfig, Invoice


# ---------------------------------------------------------------------------
# FiscalConfig Serializers
# ---------------------------------------------------------------------------


class FiscalConfigSerializer(serializers.ModelSerializer):
    """Full serializer for fiscal configuration."""

    class Meta:
        model = FiscalConfig
        fields = [
            "id",
            "clinic",
            "rfc",
            "razon_social",
            "regimen_fiscal",
            "fiscal_address",
            "csd_cert_path",
            "csd_key_path",
            "email",
            "is_validated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "clinic",
            "is_validated",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "clinic": {"required": False},
        }

    def validate_rfc(self, value: str) -> str:
        """Validate RFC format (12-13 alphanumeric characters)."""
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("El RFC es obligatorio.")
        if len(value) < 12 or len(value) > 13:
            raise serializers.ValidationError("El RFC debe tener 12 o 13 caracteres.")
        return value

    def validate_regimen_fiscal(self, value: str) -> str:
        """Validate SAT regime code (3 digits)."""
        if not value or len(value) != 3 or not value.isdigit():
            raise serializers.ValidationError(
                "El régimen fiscal debe ser una clave de 3 dígitos (e.g., 601)."
            )
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation for fiscal address."""
        fiscal_address = data.get("fiscal_address", {})
        required_fields = ["calle", "codigo_postal", "estado"]
        missing = [f for f in required_fields if not fiscal_address.get(f)]
        if missing:
            raise serializers.ValidationError(
                {
                    "fiscal_address": f"Campos obligatorios faltantes: {', '.join(missing)}"
                }
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> FiscalConfig:
        """Create fiscal config with clinic from JWT context."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError(
                "No se pudo determinar la clínica. Contacte al administrador."
            )

        from clinics.models import Clinic

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError("Clínica no encontrada.")

        # Check if fiscal config already exists for this clinic
        if FiscalConfig.objects.filter(clinic=clinic).exists():
            raise serializers.ValidationError(
                "Esta clínica ya tiene una configuración fiscal. Use PATCH para actualizar."
            )

        validated_data["clinic"] = clinic
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Invoice Serializers
# ---------------------------------------------------------------------------


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new invoice.

    Handles:
    - Clinic injection from JWT
    - Patient validation
    - Appointment validation (optional)
    - Auto-calculation of totals from concepts
    - Folio generation
    """

    patient_id = serializers.UUIDField(write_only=True)
    appointment_id = serializers.UUIDField(
        write_only=True, required=False, allow_null=True
    )

    # Read-only nested info for response
    patient_name = serializers.CharField(read_only=True)
    folio = serializers.CharField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "patient_id",
            "appointment_id",
            "rfc_receptor",
            "nombre_receptor",
            "uso_cfdi",
            "metodo_pago",
            "forma_pago",
            "moneda",
            "concepts",
            "folio",
            "patient_name",
        ]

    def validate_concepts(self, value: list[dict]) -> list[dict]:
        """Validate concepts structure and amounts."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe incluir al menos un concepto.")

        validated_concepts = []
        for i, concept in enumerate(value):
            required = ["clave_sat", "descripcion", "cantidad", "valor_unitario"]
            missing = [f for f in required if f not in concept]
            if missing:
                raise serializers.ValidationError(
                    {
                        "concepts": f"Concepto {i + 1}: campos obligatorios faltantes: {', '.join(missing)}"
                    }
                )

            # Validate numeric fields
            try:
                cantidad = Decimal(str(concept["cantidad"]))
                valor_unitario = Decimal(str(concept["valor_unitario"]))
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    {
                        "concepts": f"Concepto {i + 1}: 'cantidad' y 'valor_unitario' deben ser numéricos."
                    }
                )

            if cantidad <= 0:
                raise serializers.ValidationError(
                    {"concepts": f"Concepto {i + 1}: 'cantidad' debe ser mayor a 0."}
                )
            if valor_unitario < 0:
                raise serializers.ValidationError(
                    {
                        "concepts": f"Concepto {i + 1}: 'valor_unitario' no puede ser negativo."
                    }
                )

            # Calculate importe
            importe = round(cantidad * valor_unitario, 2)
            iva_rate = Decimal(str(concept.get("iva_rate", "0.16")))

            validated_concept = {
                "clave_sat": concept["clave_sat"].strip(),
                "descripcion": concept["descripcion"].strip(),
                "cantidad": float(cantidad),
                "unidad": concept.get("unidad", "NO APLICA"),
                "valor_unitario": float(valor_unitario),
                "importe": float(importe),
                "iva_rate": float(iva_rate),
            }
            validated_concepts.append(validated_concept)

        return validated_concepts

    def validate_rfc_receptor(self, value: str) -> str:
        """Validate receptor RFC format."""
        value = value.strip().upper()
        if not value:
            raise serializers.ValidationError("El RFC del receptor es obligatorio.")
        if len(value) < 12 or len(value) > 13:
            raise serializers.ValidationError(
                "El RFC del receptor debe tener 12 o 13 caracteres."
            )
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError("No se pudo determinar la clínica.")

        # Validate patient exists and belongs to clinic
        patient_id = data.get("patient_id")
        if patient_id:
            from patients.models import Patient

            try:
                patient = Patient.objects.get(id=patient_id, clinic_id=clinic_id)
                data["_patient"] = patient
                # Auto-fill nombre_receptor if not provided
                if not data.get("nombre_receptor"):
                    data["nombre_receptor"] = patient.full_name
            except Patient.DoesNotExist:
                raise serializers.ValidationError(
                    {"patient_id": "Paciente no encontrado en esta clínica."}
                )

        # Validate appointment if provided
        appointment_id = data.get("appointment_id")
        if appointment_id:
            from appointments.models import Appointment

            try:
                appointment = Appointment.objects.get(
                    id=appointment_id, clinic_id=clinic_id
                )
                data["_appointment"] = appointment
            except Appointment.DoesNotExist:
                raise serializers.ValidationError(
                    {"appointment_id": "Cita no encontrada en esta clínica."}
                )

        return data

    def create(self, validated_data: dict[str, Any]) -> Invoice:
        """Create invoice with all FKs resolved and totals calculated."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError("No se pudo determinar la clínica.")

        from clinics.models import Clinic

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError("Clínica no encontrada.")

        # Pop internal resolved objects
        patient = validated_data.pop("_patient")
        appointment = validated_data.pop("_appointment", None)

        # Generate folio
        last_folio = (
            Invoice.objects.filter(clinic=clinic)
            .order_by("-folio")
            .values_list("folio", flat=True)
            .first()
        )
        if last_folio:
            # Extract numeric part and increment
            try:
                num = int("".join(filter(str.isdigit, last_folio)))
                next_num = num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        folio = f"FAC-{next_num:06d}"
        validated_data["folio"] = folio

        # Calculate totals
        concepts = validated_data.get("concepts", [])
        subtotal = sum(c.get("importe", 0) for c in concepts)
        iva = sum(c.get("importe", 0) * c.get("iva_rate", 0.16) for c in concepts)
        total = round(subtotal + iva, 2)

        invoice = Invoice(
            clinic=clinic,
            patient=patient,
            appointment=appointment,
            folio=folio,
            rfc_receptor=validated_data["rfc_receptor"],
            nombre_receptor=validated_data["nombre_receptor"],
            uso_cfdi=validated_data.get("uso_cfdi", Invoice.UsoCFDI.G03),
            metodo_pago=validated_data.get("metodo_pago", Invoice.MetodoPago.PUE),
            forma_pago=validated_data.get("forma_pago", Invoice.FormaPago.EFECTIVO),
            moneda=validated_data.get("moneda", Invoice.Moneda.MXN),
            concepts=concepts,
            subtotal=round(subtotal, 2),
            iva=round(iva, 2),
            total=total,
            created_by=request.user if request and hasattr(request, "user") else None,
        )
        invoice.save()
        return invoice


class InvoiceSerializer(serializers.ModelSerializer):
    """Full invoice serializer for reading."""

    patient_name = serializers.CharField(read_only=True)
    status_display = serializers.SerializerMethodField()
    metodo_pago_display = serializers.SerializerMethodField()
    forma_pago_display = serializers.SerializerMethodField()
    moneda_display = serializers.SerializerMethodField()
    uso_cfdi_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "clinic",
            "patient",
            "patient_name",
            "appointment",
            "folio",
            "rfc_receptor",
            "nombre_receptor",
            "uso_cfdi",
            "uso_cfdi_display",
            "metodo_pago",
            "metodo_pago_display",
            "forma_pago",
            "forma_pago_display",
            "moneda",
            "moneda_display",
            "subtotal",
            "iva",
            "total",
            "concepts",
            "status",
            "status_display",
            "cfdi_uuid",
            "xml_url",
            "pdf_url",
            "cfdi_sat_certificate",
            "cfdi_stamp_date",
            "cancellation_reason",
            "cancellation_folio",
            "cancelled_at",
            "error_message",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status_display(self, obj: Invoice) -> str:
        return obj.get_status_display()

    def get_metodo_pago_display(self, obj: Invoice) -> str:
        return obj.get_metodo_pago_display()

    def get_forma_pago_display(self, obj: Invoice) -> str:
        return obj.get_forma_pago_display()

    def get_moneda_display(self, obj: Invoice) -> str:
        return obj.get_moneda_display()

    def get_uso_cfdi_display(self, obj: Invoice) -> str:
        return obj.get_uso_cfdi_display()

    def get_created_by_name(self, obj: Invoice) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


# ---------------------------------------------------------------------------
# InvoiceStamp Serializer
# ---------------------------------------------------------------------------


class InvoiceStampSerializer(serializers.Serializer):
    """Serializer for stamping an invoice via Finkok."""

    invoice_id = serializers.UUIDField(write_only=True)

    # Read-only result fields
    cfdi_uuid = serializers.CharField(read_only=True)
    xml_url = serializers.CharField(read_only=True)
    pdf_url = serializers.CharField(read_only=True)
    stamp_date = serializers.DateTimeField(read_only=True)

    def validate_invoice_id(self, value):
        """Validate invoice exists and is in draft or pending_stamp status."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        try:
            invoice = Invoice.objects.get(id=value, clinic_id=clinic_id)
        except Invoice.DoesNotExist:
            raise serializers.ValidationError("Factura no encontrada.")

        if invoice.status not in (
            Invoice.Status.DRAFT,
            Invoice.Status.PENDING_STAMP,
            Invoice.Status.ERROR,
        ):
            raise serializers.ValidationError(
                f"No se puede timbrar una factura en estado '{invoice.get_status_display()}'."
            )

        # Validate fiscal config exists for clinic
        if not hasattr(invoice.clinic, "fiscal_config"):
            raise serializers.ValidationError(
                "La clínica no tiene configuración fiscal. Configure el RFC y CSD primero."
            )

        fiscal_config = invoice.clinic.fiscal_config
        if not fiscal_config.is_validated:
            raise serializers.ValidationError(
                "La configuración fiscal no ha sido validada. Valide el CSD primero."
            )

        self._invoice = invoice
        return value
