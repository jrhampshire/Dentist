"""
Serializers for dental_records app.

Provides read/write serializers for all 6 dental records capabilities:
- DentalRecordEntry (append-only odontogram entries)
- Tooth / ToothSurface (materialized state, read-only)
- MedicalHistory (versioned, upsert-on-PUT)
- VitalSigns (vital signs recording)
- PatientImage (image upload with thumbnail generation)
- TreatmentPlan / TreatmentPhase / TreatmentProcedure (nested CRUD)
"""

from typing import Any

from django.db import transaction
from rest_framework import serializers

from dental_records.choices import Surface
from dental_records.models import (
    VALID_FDI_CODES,
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
from dental_records.services import generate_thumbnail


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _validate_tooth_fdi(value: int) -> int:
    """Validate an FDI tooth number is valid."""
    if value not in VALID_FDI_CODES:
        raise serializers.ValidationError(
            f"{value} no es un código FDI válido. "
            f"Debe estar entre 11-48 (permanentes) o 51-85 (primarios)."
        )
    return value


def _validate_surface(value: str) -> str:
    """Validate surface choice is valid."""
    valid = set(Surface.values)
    if value not in valid:
        raise serializers.ValidationError(
            f"Superficie '{value}' no válida. Opciones: {', '.join(sorted(valid))}."
        )
    return value


def _get_patient_from_context(context: dict[str, Any]):
    """Get the patient ID from view context (URL kwargs)."""
    patient_id = context.get("patient_id")
    if not patient_id:
        raise serializers.ValidationError("patient_id is required in context.")
    from patients.models import Patient

    try:
        return Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        raise serializers.ValidationError("Paciente no encontrado.")


# ─────────────────────────────────────────────────────────────────────────
# 1. DentalRecordEntry Serializers
# ─────────────────────────────────────────────────────────────────────────


class DentalRecordEntrySerializer(serializers.ModelSerializer):
    """Serializer for DentalRecordEntry (read + create)."""

    surface_display = serializers.SerializerMethodField()
    condition_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DentalRecordEntry
        fields = [
            "id",
            "patient",
            "tooth_fdi",
            "surface",
            "surface_display",
            "condition",
            "condition_display",
            "notes",
            "created_by",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "created_by",
            "created_at",
        ]

    def get_surface_display(self, obj: DentalRecordEntry) -> str:
        return obj.get_surface_display()

    def get_condition_display(self, obj: DentalRecordEntry) -> str:
        return obj.get_condition_display()

    def get_created_by_name(self, obj: DentalRecordEntry) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None

    def validate_tooth_fdi(self, value: int) -> int:
        return _validate_tooth_fdi(value)

    def validate_surface(self, value: str) -> str:
        return _validate_surface(value)

    def create(self, validated_data: dict[str, Any]) -> DentalRecordEntry:
        """Create entry with patient from URL context and created_by from user."""
        request = self.context.get("request")
        patient = _get_patient_from_context(self.context)

        validated_data["patient"] = patient

        # Idempotency check: if same tooth+surface+condition exists, return it
        existing = DentalRecordEntry.objects.filter(
            patient=patient,
            tooth_fdi=validated_data["tooth_fdi"],
            surface=validated_data["surface"],
            condition=validated_data["condition"],
        ).first()

        if existing:
            # Return existing record — no duplicate created
            return existing

        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        return super().create(validated_data)


# ─────────────────────────────────────────────────────────────────────────
# 2. Tooth + ToothSurface Serializers (read-only)
# ─────────────────────────────────────────────────────────────────────────


class ToothSurfaceStateSerializer(serializers.ModelSerializer):
    """Read-only serializer for ToothSurface materialized state."""

    surface_display = serializers.SerializerMethodField()
    condition_display = serializers.SerializerMethodField()

    class Meta:
        model = ToothSurface
        fields = [
            "id",
            "surface",
            "surface_display",
            "condition",
            "condition_display",
            "updated_at",
        ]
        read_only_fields = fields

    def get_surface_display(self, obj: ToothSurface) -> str:
        return obj.get_surface_display()

    def get_condition_display(self, obj: ToothSurface) -> str:
        return obj.get_condition_display()


class ToothStateSerializer(serializers.ModelSerializer):
    """Read-only serializer for Tooth materialized state with nested surfaces."""

    condition_display = serializers.SerializerMethodField()
    surfaces = ToothSurfaceStateSerializer(many=True, read_only=True)

    class Meta:
        model = Tooth
        fields = [
            "id",
            "tooth_fdi",
            "condition",
            "condition_display",
            "surfaces",
            "updated_at",
        ]
        read_only_fields = fields

    def get_condition_display(self, obj: Tooth) -> str:
        return obj.get_condition_display()


# ─────────────────────────────────────────────────────────────────────────
# 3. MedicalHistory Serializer
# ─────────────────────────────────────────────────────────────────────────


class MedicalHistorySerializer(serializers.ModelSerializer):
    """Serializer for MedicalHistory (read + versioned upsert on PUT)."""

    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalHistory
        fields = [
            "id",
            "patient",
            "version",
            "antecedentes_patologicos",
            "antecedentes_quirurgicos",
            "antecedentes_alergicos",
            "antecedentes_farmacologicos",
            "antecedentes_familiares",
            "motivo_consulta",
            "enfermedad_actual",
            "is_active",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "version",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    _ANTECEDENT_FIELDS = [
        "antecedentes_patologicos",
        "antecedentes_quirurgicos",
        "antecedentes_alergicos",
        "antecedentes_farmacologicos",
        "antecedentes_familiares",
    ]

    _TEXT_FIELDS = [
        "motivo_consulta",
        "enfermedad_actual",
    ]

    def get_created_by_name(self, obj: MedicalHistory) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None

    def get_updated_by_name(self, obj: MedicalHistory) -> str | None:
        if obj.updated_by:
            return obj.updated_by.get_full_name()
        return None

    def update(
        self, instance: MedicalHistory, validated_data: dict[str, Any]
    ) -> MedicalHistory:
        """
        Versioned update: deactivates current, creates new version.

        1. Sets is_active=False on the current instance
        2. Creates a new instance with version = current.version + 1
        3. Carries forward any fields not provided in the update
        """
        request = self.context.get("request")

        # Merge: carry forward existing values for fields not in validated_data
        new_data: dict[str, Any] = {
            "patient": instance.patient,
            "version": instance.version + 1,
            "is_active": True,
        }

        # Antecedent fields (JSONField)
        for field in self._ANTECEDENT_FIELDS:
            new_data[field] = validated_data.get(field, getattr(instance, field))

        # Text fields
        for field in self._TEXT_FIELDS:
            new_data[field] = validated_data.get(field, getattr(instance, field))

        # Audit
        if request and hasattr(request, "user") and request.user.is_authenticated:
            new_data["created_by"] = request.user
            new_data["updated_by"] = request.user

        # Deactivate current record (within same transaction)
        with transaction.atomic():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])

            # Create new active version
            new_instance = MedicalHistory.objects.create(**new_data)

        return new_instance

    def create(self, validated_data: dict[str, Any]) -> MedicalHistory:
        """Create initial medical history entry for a patient."""
        request = self.context.get("request")
        patient = _get_patient_from_context(self.context)

        validated_data["patient"] = patient
        validated_data["version"] = 1
        validated_data["is_active"] = True

        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["created_by"] = request.user
            validated_data["updated_by"] = request.user

        return super().create(validated_data)


# ─────────────────────────────────────────────────────────────────────────
# 4. VitalSigns Serializer
# ─────────────────────────────────────────────────────────────────────────


class VitalSignsSerializer(serializers.ModelSerializer):
    """Serializer for VitalSigns (read + create)."""

    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = VitalSigns
        fields = [
            "id",
            "patient",
            "appointment",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "heart_rate",
            "temperature",
            "weight",
            "height",
            "notes",
            "recorded_by",
            "recorded_by_name",
            "recorded_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "recorded_by",
            "recorded_at",
            "created_at",
        ]

    def get_recorded_by_name(self, obj: VitalSigns) -> str | None:
        if obj.recorded_by:
            return obj.recorded_by.get_full_name()
        return None

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate blood pressure: systolic > diastolic."""
        systolic = data.get("blood_pressure_systolic")
        diastolic = data.get("blood_pressure_diastolic")

        if systolic is not None and diastolic is not None:
            if systolic <= diastolic:
                raise serializers.ValidationError(
                    {
                        "blood_pressure_systolic": "La presión sistólica debe ser mayor que la diastólica."
                    }
                )

        # At least one field must be provided
        vital_fields = [
            data.get("blood_pressure_systolic"),
            data.get("blood_pressure_diastolic"),
            data.get("heart_rate"),
            data.get("temperature"),
            data.get("weight"),
            data.get("height"),
        ]
        if all(v is None for v in vital_fields):
            raise serializers.ValidationError(
                "Al menos un signo vital debe ser proporcionado."
            )

        return data

    def create(self, validated_data: dict[str, Any]) -> VitalSigns:
        """Create vital signs record with patient from URL and user from request."""
        request = self.context.get("request")
        patient = _get_patient_from_context(self.context)

        validated_data["patient"] = patient

        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["recorded_by"] = request.user

        return super().create(validated_data)


# ─────────────────────────────────────────────────────────────────────────
# 4b. TreatmentProcedure consent enforcement helper
# ─────────────────────────────────────────────────────────────────────────


def _check_treatment_consent_for_procedure(
    patient_id: str, context: dict[str, Any]
) -> None:
    """Validate that the patient has a signed treatment consent (NOM-024).

    Called before creating a TreatmentProcedure. Raises ValidationError
    if no signed treatment consent exists for the patient.
    """
    from patients.models import Patient
    from patients.services.consent_service import require_treatment_consent

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return  # Will be caught by serializer validation

    require_treatment_consent(patient)


# ─────────────────────────────────────────────────────────────────────────
# 5. PatientImage Serializers
# ─────────────────────────────────────────────────────────────────────────


class PatientImageListSerializer(serializers.ModelSerializer):
    """Serializer for PatientImage list view (no raw binary, returns proxy URLs)."""

    image_type_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientImage
        fields = [
            "id",
            "patient",
            "tooth_fdi",
            "image_type",
            "image_type_display",
            "image_url",
            "thumbnail_url",
            "description",
            "file_size",
            "content_type",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_image_type_display(self, obj: PatientImage) -> str:
        return obj.get_image_type_display()

    def get_uploaded_by_name(self, obj: PatientImage) -> str | None:
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name()
        return None

    def get_thumbnail_url(self, obj: PatientImage) -> str | None:
        """Return proxy URL for thumbnail."""
        if obj.thumbnail:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/thumbnail/"
        return None

    def get_image_url(self, obj: PatientImage) -> str | None:
        """Return proxy URL for the image file."""
        if obj.image:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/file/"
        return None


class PatientImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for PatientImage upload (handles multipart file)."""

    image = serializers.FileField(required=True)
    image_type = serializers.ChoiceField(
        choices=[
            ("photo", "Foto Clínica"),
            ("xray_periapical", "Radiografía Periapical"),
            ("xray_panoramic", "Radiografía Panorámica"),
            ("xray_cephalometric", "Radiografía Cefalométrica"),
            ("document", "Documento"),
            ("other", "Otro"),
        ]
    )
    image_type_display = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientImage
        fields = [
            "id",
            "image",
            "image_type",
            "image_type_display",
            "tooth_fdi",
            "description",
            "file_size",
            "content_type",
            "image_url",
            "thumbnail_url",
        ]
        read_only_fields = [
            "id",
            "image_type_display",
            "file_size",
            "content_type",
            "image_url",
            "thumbnail_url",
        ]

    def get_image_type_display(self, obj: PatientImage) -> str:
        return obj.get_image_type_display()

    def get_image_url(self, obj: PatientImage) -> str | None:
        if obj.image:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/file/"
        return None

    def get_thumbnail_url(self, obj: PatientImage) -> str | None:
        if obj.thumbnail:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/thumbnail/"
        return None

    def validate_image(self, value):
        """Validate file size (max 20MB) and file extension."""
        MAX_SIZE = 20 * 1024 * 1024  # 20 MB

        if value.size > MAX_SIZE:
            raise serializers.ValidationError(
                "El archivo excede el tamaño máximo de 20 MB."
            )

        # Validate extension
        valid_extensions = (".jpg", ".jpeg", ".png", ".pdf")
        name = value.name.lower()
        if not name.endswith(valid_extensions):
            raise serializers.ValidationError(
                "Tipo de archivo no permitido. Use JPEG, PNG o PDF."
            )

        return value

    def validate_tooth_fdi(self, value: int | None) -> int | None:
        if value is not None:
            return _validate_tooth_fdi(value)
        return value

    def create(self, validated_data: dict[str, Any]) -> PatientImage:
        """Create image record with thumbnail generation and metadata extraction."""
        request = self.context.get("request")
        patient = _get_patient_from_context(self.context)

        image_file = validated_data.pop("image")

        validated_data["patient"] = patient
        validated_data["file_size"] = image_file.size
        validated_data["content_type"] = getattr(
            image_file, "content_type", "application/octet-stream"
        )

        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["uploaded_by"] = request.user

        # Generate thumbnail for images (skip PDFs)
        thumbnail = generate_thumbnail(image_file)
        if thumbnail:
            validated_data["thumbnail"] = thumbnail

        # Reset file pointer and set image
        image_file.seek(0)
        validated_data["image"] = image_file

        return PatientImage.objects.create(**validated_data)


class PatientImageSerializer(serializers.ModelSerializer):
    """Full serializer for PatientImage detail view."""

    image_type_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PatientImage
        fields = [
            "id",
            "patient",
            "tooth_fdi",
            "image_type",
            "image_type_display",
            "image_url",
            "thumbnail_url",
            "description",
            "file_size",
            "content_type",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
        ]
        read_only_fields = fields

    def get_image_type_display(self, obj: PatientImage) -> str:
        return obj.get_image_type_display()

    def get_uploaded_by_name(self, obj: PatientImage) -> str | None:
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name()
        return None

    def get_thumbnail_url(self, obj: PatientImage) -> str | None:
        if obj.thumbnail:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/thumbnail/"
        return None

    def get_image_url(self, obj: PatientImage) -> str | None:
        if obj.image:
            return f"/api/v1/dental-records/patients/{obj.patient_id}/images/{obj.id}/file/"
        return None


# ─────────────────────────────────────────────────────────────────────────
# 6. TreatmentPlan Serializers
# ─────────────────────────────────────────────────────────────────────────


class TreatmentProcedureSerializer(serializers.ModelSerializer):
    """Serializer for TreatmentProcedure."""

    status_display = serializers.SerializerMethodField()

    class Meta:
        model = TreatmentProcedure
        fields = [
            "id",
            "phase",
            "appointment",
            "tooth_fdi",
            "description",
            "cost",
            "status",
            "status_display",
            "notes",
        ]
        read_only_fields = ["id", "phase"]

    def get_status_display(self, obj: TreatmentProcedure) -> str:
        return obj.get_status_display()

    def validate_tooth_fdi(self, value: int | None) -> int | None:
        if value is not None:
            return _validate_tooth_fdi(value)
        return value

    def validate_cost(self, value) -> Any:
        if value < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return value

    def create(self, validated_data: dict[str, Any]) -> TreatmentProcedure:
        """Create procedure with NOM-024 treatment consent enforcement."""
        patient_id = self.context.get("patient_id")
        if patient_id:
            _check_treatment_consent_for_procedure(patient_id, self.context)
        return super().create(validated_data)


class TreatmentPhaseSerializer(serializers.ModelSerializer):
    """Serializer for TreatmentPhase with nested procedures."""

    status_display = serializers.SerializerMethodField()
    procedures = TreatmentProcedureSerializer(many=True, read_only=True)

    class Meta:
        model = TreatmentPhase
        fields = [
            "id",
            "plan",
            "name",
            "description",
            "order",
            "status",
            "status_display",
            "procedures",
        ]
        read_only_fields = ["id", "plan"]

    def get_status_display(self, obj: TreatmentPhase) -> str:
        return obj.get_status_display()


class TreatmentPlanListSerializer(serializers.ModelSerializer):
    """Serializer for TreatmentPlan list view (without nested phases)."""

    status_display = serializers.SerializerMethodField()
    phases_count = serializers.SerializerMethodField()

    class Meta:
        model = TreatmentPlan
        fields = [
            "id",
            "patient",
            "name",
            "description",
            "status",
            "status_display",
            "phases_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_status_display(self, obj: TreatmentPlan) -> str:
        return obj.get_status_display()

    def get_phases_count(self, obj: TreatmentPlan) -> int:
        return obj.phases.count()


class TreatmentPlanDetailSerializer(serializers.ModelSerializer):
    """Serializer for TreatmentPlan detail view with nested phases + procedures."""

    status_display = serializers.SerializerMethodField()
    phases = TreatmentPhaseSerializer(many=True, read_only=True)

    class Meta:
        model = TreatmentPlan
        fields = [
            "id",
            "patient",
            "name",
            "description",
            "status",
            "status_display",
            "phases",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "patient",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_status_display(self, obj: TreatmentPlan) -> str:
        return obj.get_status_display()

    def create(self, validated_data: dict[str, Any]) -> TreatmentPlan:
        """Create treatment plan with patient from URL context."""
        request = self.context.get("request")
        patient = _get_patient_from_context(self.context)

        validated_data["patient"] = patient

        if request and hasattr(request, "user") and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        return super().create(validated_data)
