"""
Patient Management serializers.

Serializers:
- PatientSerializer: Full patient detail (read/write)
- PatientListSerializer: Lightweight list representation
- PatientCreateSerializer: Patient creation with validation
- ClinicalNoteSerializer: Clinical note (read/write, sign action)
- ClinicalNoteCreateSerializer: Clinical note creation
- PatientConsentSerializer: Consent record (read/write, sign action)

Encrypted fields are automatically decrypted on read and encrypted on write.
"""

from typing import Any

from rest_framework import serializers

from patients.models import ClinicalNote, Patient, PatientConsent
from patients.services.encryption_service import decrypt, encrypt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encrypt_field(value: str) -> str:
    """Encrypt a field value if non-empty."""
    if value:
        return encrypt(value)
    return ""


def _decrypt_field(value: str) -> str:
    """Decrypt a field value if non-empty."""
    if value:
        try:
            return decrypt(value)
        except Exception:
            return "[encrypted]"
    return ""


# ---------------------------------------------------------------------------
# Patient Serializers
# ---------------------------------------------------------------------------


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for patient list view."""

    full_name = serializers.CharField(read_only=True)
    consent_status = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "date_of_birth",
            "gender",
            "consent_status",
            "created_at",
        ]

    def get_consent_status(self, obj: Patient) -> str:
        if obj.consent_signed:
            return "signed"
        return "pending"


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new patient."""

    # Encrypted fields as plain text on input
    allergies = serializers.CharField(
        required=False, allow_blank=True, default="", write_only=True
    )
    chronic_conditions = serializers.CharField(
        required=False, allow_blank=True, default="", write_only=True
    )
    current_medications = serializers.CharField(
        required=False, allow_blank=True, default="", write_only=True
    )

    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "second_last_name",
            "email",
            "phone",
            "alternate_phone",
            "curp",
            "rfc",
            "date_of_birth",
            "gender",
            "address",
            "occupation",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "blood_type",
            "allergies",
            "chronic_conditions",
            "current_medications",
            "insurance_provider",
            "insurance_policy_number",
            "whatsapp_opt_in",
            "email_opt_in",
        ]
        extra_kwargs = {
            "address": {"required": False, "default": {}},
            "occupation": {"required": False, "allow_blank": True, "default": ""},
            "emergency_contact_name": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
            "emergency_contact_phone": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
            "emergency_contact_relation": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
            "blood_type": {"required": False, "allow_blank": True, "default": ""},
            "insurance_provider": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
            "insurance_policy_number": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
        }

    def validate_phone(self, value: str) -> str:
        """Validate phone format."""
        if not value or not value.strip():
            raise serializers.ValidationError("El teléfono es obligatorio.")
        return value.strip()

    def validate_curp(self, value: str) -> str:
        """Validate CURP format (18 characters, alphanumeric)."""
        if value and len(value) != 18:
            raise serializers.ValidationError(
                "El CURP debe tener exactamente 18 caracteres."
            )
        return value.strip().upper() if value else ""

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation."""
        if not data.get("first_name", "").strip():
            raise serializers.ValidationError(
                {"first_name": "El nombre es obligatorio."}
            )
        if not data.get("last_name", "").strip():
            raise serializers.ValidationError(
                {"last_name": "El apellido es obligatorio."}
            )
        if not data.get("date_of_birth"):
            raise serializers.ValidationError(
                {"date_of_birth": "La fecha de nacimiento es obligatoria."}
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> Patient:
        """Create patient with encrypted medical fields and clinic assignment."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError(
                "No se pudo determinar la clínica. Contacte al administrador."
            )

        # Encrypt sensitive fields
        validated_data["allergies"] = _encrypt_field(
            validated_data.pop("allergies", "")
        )
        validated_data["chronic_conditions"] = _encrypt_field(
            validated_data.pop("chronic_conditions", "")
        )
        validated_data["current_medications"] = _encrypt_field(
            validated_data.pop("current_medications", "")
        )

        # Get clinic
        from clinics.models import Clinic

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError("Clínica no encontrada.")

        validated_data["clinic"] = clinic

        # Set created_by if user is available
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        return super().create(validated_data)


class PatientSerializer(serializers.ModelSerializer):
    """Full patient serializer with decrypted sensitive fields."""

    full_name = serializers.CharField(read_only=True)

    # Encrypted fields — decrypted on output, encrypted on input
    allergies = serializers.CharField(required=False, allow_blank=True, default="")
    chronic_conditions = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    current_medications = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    # Read-only metadata
    consent_status = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "clinic",
            "first_name",
            "last_name",
            "second_last_name",
            "full_name",
            "email",
            "phone",
            "alternate_phone",
            "curp",
            "rfc",
            "date_of_birth",
            "gender",
            "address",
            "occupation",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "blood_type",
            "allergies",
            "chronic_conditions",
            "current_medications",
            "insurance_provider",
            "insurance_policy_number",
            "whatsapp_opt_in",
            "email_opt_in",
            "consent_signed",
            "consent_signed_at",
            "consent_version",
            "consent_status",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "clinic",
            "consent_signed",
            "consent_signed_at",
            "consent_version",
            "created_by",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "clinic": {"required": False},
        }

    def get_consent_status(self, obj: Patient) -> str:
        if obj.consent_signed:
            return "signed"
        return "pending"

    def get_created_by_name(self, obj: Patient) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None

    def to_representation(self, instance: Patient) -> dict[str, Any]:
        """Decrypt sensitive fields on output."""
        data = super().to_representation(instance)

        # Decrypt encrypted fields
        data["allergies"] = _decrypt_field(instance.allergies)
        data["chronic_conditions"] = _decrypt_field(instance.chronic_conditions)
        data["current_medications"] = _decrypt_field(instance.current_medications)

        return data

    def update(self, instance: Patient, validated_data: dict[str, Any]) -> Patient:
        """Update patient, re-encrypting sensitive fields if changed."""
        # Re-encrypt sensitive fields if they were provided
        if "allergies" in validated_data:
            validated_data["allergies"] = _encrypt_field(
                validated_data.pop("allergies")
            )
        if "chronic_conditions" in validated_data:
            validated_data["chronic_conditions"] = _encrypt_field(
                validated_data.pop("chronic_conditions")
            )
        if "current_medications" in validated_data:
            validated_data["current_medications"] = _encrypt_field(
                validated_data.pop("current_medications")
            )

        return super().update(instance, validated_data)


# ---------------------------------------------------------------------------
# ClinicalNote Serializers
# ---------------------------------------------------------------------------


class ClinicalNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a clinical note."""

    appointment_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = ClinicalNote
        fields = [
            "note_type",
            "title",
            "content",
            "appointment_id",
        ]

    def validate_content(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("El contenido de la nota es obligatorio.")
        return value.strip()

    def validate_title(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("El título de la nota es obligatorio.")
        return value.strip()

    def create(self, validated_data: dict[str, Any]) -> ClinicalNote:
        """Create clinical note with encrypted content and NOM-024 consent check."""
        request = self.context.get("request")

        # Get patient from URL kwargs
        patient_id = self.context.get("patient_id")
        if not patient_id:
            raise serializers.ValidationError("patient_id is required in context.")

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Paciente no encontrado.")

        # NOM-024: treatment notes require signed treatment consent
        note_type = validated_data.get("note_type", "")
        if note_type == ClinicalNote.NoteType.TREATMENT:
            from patients.services.consent_service import require_treatment_consent

            require_treatment_consent(patient)

        # Encrypt content
        validated_data["content"] = _encrypt_field(validated_data.pop("content"))

        # Set patient
        validated_data["patient"] = patient

        # Set author from request user
        if request and hasattr(request, "user"):
            validated_data["author"] = request.user

        # Handle appointment_id
        appointment_id = validated_data.pop("appointment_id", None)
        if appointment_id:
            from appointments.models import Appointment

            try:
                validated_data["appointment"] = Appointment.objects.get(
                    id=appointment_id
                )
            except Appointment.DoesNotExist:
                raise serializers.ValidationError("Cita no encontrada.")

        return super().create(validated_data)


class ClinicalNoteSerializer(serializers.ModelSerializer):
    """Full clinical note serializer with decrypted content."""

    author_name = serializers.SerializerMethodField()
    note_type_display = serializers.SerializerMethodField()

    class Meta:
        model = ClinicalNote
        fields = [
            "id",
            "patient",
            "appointment",
            "author",
            "author_name",
            "note_type",
            "note_type_display",
            "title",
            "content",
            "is_signed",
            "signed_at",
            "signature_hash",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "author",
            "is_signed",
            "signed_at",
            "signature_hash",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj: ClinicalNote) -> str | None:
        if obj.author:
            return obj.author.get_full_name()
        return None

    def get_note_type_display(self, obj: ClinicalNote) -> str:
        return obj.get_note_type_display()

    def to_representation(self, instance: ClinicalNote) -> dict[str, Any]:
        """Decrypt content on output."""
        data = super().to_representation(instance)
        data["content"] = _decrypt_field(instance.content)
        return data

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Prevent modification of signed notes."""
        if self.instance and self.instance.is_signed:
            raise serializers.ValidationError(
                "No se puede modificar una nota clínica firmada."
            )
        return data


# ---------------------------------------------------------------------------
# PatientConsent Serializers
# ---------------------------------------------------------------------------


class PatientConsentSerializer(serializers.ModelSerializer):
    """Consent record serializer."""

    consent_type_display = serializers.SerializerMethodField()
    signed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientConsent
        fields = [
            "id",
            "patient",
            "consent_type",
            "consent_type_display",
            "version",
            "content",
            "signed",
            "signed_at",
            "signature_hash",
            "signed_by",
            "signed_by_name",
            "ip_address",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "signed",
            "signed_at",
            "signature_hash",
            "signed_by",
            "created_at",
        ]

    def get_consent_type_display(self, obj: PatientConsent) -> str:
        return obj.get_consent_type_display()

    def get_signed_by_name(self, obj: PatientConsent) -> str | None:
        if obj.signed_by:
            return obj.signed_by.get_full_name()
        return None

    def create(self, validated_data: dict[str, Any]) -> PatientConsent:
        """Create consent record with patient from context."""
        request = self.context.get("request")
        patient_id = self.context.get("patient_id")

        if not patient_id:
            raise serializers.ValidationError("patient_id is required in context.")

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Paciente no encontrado.")

        validated_data["patient"] = patient

        # Auto-fill IP from request
        if request:
            validated_data["ip_address"] = request.META.get(
                "HTTP_X_FORWARDED_FOR", ""
            ).split(",")[0].strip() or request.META.get("REMOTE_ADDR")

        return super().create(validated_data)
