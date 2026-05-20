"""
Appointment Scheduling serializers.

Serializers:
- AppointmentTypeSerializer: Full read/write for appointment types
- AppointmentSerializer: Full appointment detail (read)
- AppointmentCreateSerializer: Appointment creation with conflict validation
- ScheduleSlotSerializer: Schedule slot read/write
"""

from datetime import datetime, time, timedelta
from typing import Any

from rest_framework import serializers

from appointments.models import Appointment, AppointmentType, ScheduleSlot


# ---------------------------------------------------------------------------
# AppointmentType Serializers
# ---------------------------------------------------------------------------


class AppointmentTypeSerializer(serializers.ModelSerializer):
    """Full serializer for appointment types."""

    class Meta:
        model = AppointmentType
        fields = [
            "id",
            "clinic",
            "name",
            "description",
            "duration_minutes",
            "price",
            "color",
            "inventory_kit",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "clinic",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "clinic": {"required": False},
        }

    def validate_name(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("El nombre es obligatorio.")
        return value.strip()

    def validate_color(self, value: str) -> str:
        """Validate hex color format."""
        if value and not value.startswith("#"):
            raise serializers.ValidationError(
                "El color debe ser un hex válido (e.g., #4A90D9)."
            )
        if value and len(value) != 7:
            raise serializers.ValidationError(
                "El color debe tener 7 caracteres (e.g., #4A90D9)."
            )
        return value

    def create(self, validated_data: dict[str, Any]) -> AppointmentType:
        """Create appointment type with clinic from JWT context."""
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

        validated_data["clinic"] = clinic
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# Appointment Serializers
# ---------------------------------------------------------------------------


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new appointment.

    Handles:
    - Clinic injection from JWT
    - End time auto-calculation from appointment type duration
    - Conflict detection (dentist double-booking)
    - Patient/dentist/type validation
    """

    patient_id = serializers.UUIDField(write_only=True)
    appointment_type_id = serializers.UUIDField(write_only=True)
    dentist_id = serializers.UUIDField(write_only=True)

    # Read-only nested info for response
    patient_name = serializers.CharField(read_only=True)
    dentist_name = serializers.CharField(read_only=True)
    appointment_type_name = serializers.CharField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient_id",
            "appointment_type_id",
            "dentist_id",
            "date",
            "start_time",
            "notes",
            "patient_name",
            "dentist_name",
            "appointment_type_name",
        ]

    def validate_date(self, value) -> Any:
        """Date cannot be in the past."""
        from datetime import date

        if isinstance(value, date) and value < date.today():
            raise serializers.ValidationError(
                "No se pueden crear citas en fechas pasadas."
            )
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cross-field validation and conflict detection."""
        from accounts.models import User
        from clinics.models import Clinic
        from patients.models import Patient

        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError("No se pudo determinar la clínica.")

        # Validate patient exists and belongs to clinic
        patient_id = data.get("patient_id")
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, clinic_id=clinic_id)
                data["_patient"] = patient
            except Patient.DoesNotExist:
                raise serializers.ValidationError(
                    {"patient_id": "Paciente no encontrado en esta clínica."}
                )

        # Validate dentist exists and belongs to clinic
        dentist_id = data.get("dentist_id")
        if dentist_id:
            try:
                dentist = User.objects.get(
                    id=dentist_id, clinic_id=clinic_id, role__in=["dentista", "admin"]
                )
                data["_dentist"] = dentist
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"dentist_id": "Dentista no encontrado en esta clínica."}
                )

        # Validate appointment type exists and belongs to clinic
        appt_type_id = data.get("appointment_type_id")
        if appt_type_id:
            try:
                appt_type = AppointmentType.objects.get(
                    id=appt_type_id, clinic_id=clinic_id
                )
                data["_appointment_type"] = appt_type
            except AppointmentType.DoesNotExist:
                raise serializers.ValidationError(
                    {"appointment_type_id": "Tipo de cita no encontrado."}
                )

        # Conflict detection: check if dentist already has an overlapping appointment
        date = data.get("date")
        start_time = data.get("start_time")
        appt_type = data.get("_appointment_type")

        if date and start_time and appt_type and data.get("_dentist"):
            # Calculate end time
            start_dt = datetime.combine(date, start_time)
            end_dt = start_dt + timedelta(minutes=appt_type.duration_minutes)
            end_time = end_dt.time()

            # Check for overlapping appointments
            # An overlap exists if: existing.start < new.end AND existing.end > new.start
            from django.db.models import Q

            conflict = (
                Appointment.objects.filter(
                    dentist=data["_dentist"],
                    date=date,
                    status__in=["scheduled", "confirmed", "in_progress"],
                )
                .filter(Q(start_time__lt=end_time) & Q(end_time__gt=start_time))
                .exists()
            )

            if conflict:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            {
                                "error": "time_slot_conflict",
                                "message": "El dentista ya tiene una cita en ese horario.",
                            }
                        ]
                    }
                )

        return data

    def create(self, validated_data: dict[str, Any]) -> Appointment:
        """Create appointment with all FKs resolved."""
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
        dentist = validated_data.pop("_dentist")
        appt_type = validated_data.pop("_appointment_type")

        # Calculate end_time
        start_time = validated_data["start_time"]
        start_dt = datetime.combine(validated_data["date"], start_time)
        end_dt = start_dt + timedelta(minutes=appt_type.duration_minutes)

        appointment = Appointment(
            clinic=clinic,
            patient=patient,
            appointment_type=appt_type,
            dentist=dentist,
            date=validated_data["date"],
            start_time=start_time,
            end_time=end_dt.time(),
            notes=validated_data.get("notes", ""),
            created_by=request.user if request and hasattr(request, "user") else None,
        )
        appointment.save()
        return appointment


class AppointmentSerializer(serializers.ModelSerializer):
    """Full appointment serializer for reading."""

    patient_name = serializers.CharField(read_only=True)
    dentist_name = serializers.CharField(read_only=True)
    appointment_type_name = serializers.SerializerMethodField()
    appointment_type_duration = serializers.SerializerMethodField()
    appointment_type_color = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "appointment_type",
            "appointment_type_name",
            "appointment_type_duration",
            "appointment_type_color",
            "dentist",
            "dentist_name",
            "date",
            "start_time",
            "end_time",
            "status",
            "status_display",
            "notes",
            "cancellation_reason",
            "cancelled_by",
            "cancelled_at",
            "whatsapp_sent",
            "whatsapp_sent_at",
            "whatsapp_response",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_appointment_type_name(self, obj: Appointment) -> str:
        return obj.appointment_type.name

    def get_appointment_type_duration(self, obj: Appointment) -> int:
        return obj.appointment_type.duration_minutes

    def get_appointment_type_color(self, obj: Appointment) -> str:
        return obj.appointment_type.color

    def get_status_display(self, obj: Appointment) -> str:
        return obj.get_status_display()

    def get_created_by_name(self, obj: Appointment) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name()
        return None


# ---------------------------------------------------------------------------
# ScheduleSlot Serializers
# ---------------------------------------------------------------------------


class ScheduleSlotSerializer(serializers.ModelSerializer):
    """Serializer for schedule slots (recurring weekly availability)."""

    dentist_name = serializers.SerializerMethodField()
    day_of_week_display = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleSlot
        fields = [
            "id",
            "clinic",
            "dentist",
            "dentist_name",
            "day_of_week",
            "day_of_week_display",
            "start_time",
            "end_time",
            "is_active",
            "valid_from",
            "valid_until",
        ]
        read_only_fields = [
            "id",
            "clinic",
        ]
        extra_kwargs = {
            "clinic": {"required": False},
        }

    def get_dentist_name(self, obj: ScheduleSlot) -> str | None:
        if obj.dentist:
            return obj.dentist.get_full_name()
        return "Todos"

    def get_day_of_week_display(self, obj: ScheduleSlot) -> str:
        return obj.get_day_of_week_display()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure end_time is after start_time."""
        start = data.get("start_time")
        end = data.get("end_time")
        if start and end and end <= start:
            raise serializers.ValidationError(
                "La hora de fin debe ser posterior a la hora de inicio."
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> ScheduleSlot:
        """Create schedule slot with clinic from JWT context."""
        request = self.context.get("request")
        clinic_id = getattr(request, "clinic_id", None) if request else None

        if not clinic_id:
            raise serializers.ValidationError("No se pudo determinar la clínica.")

        from clinics.models import Clinic

        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            raise serializers.ValidationError("Clínica no encontrada.")

        validated_data["clinic"] = clinic
        return super().create(validated_data)
