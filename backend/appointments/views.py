"""
Appointment Scheduling views.

ViewSets:
- AppointmentTypeViewSet: CRUD for appointment types (admin-only for create/update)
- AppointmentViewSet: CRUD for appointments + available-slots action
- ScheduleSlotViewSet: CRUD for schedule slots (admin-only for create/update)

Custom endpoints:
- AvailabilityView: GET /api/v1/availability/ — list available slots for a dentist on a date

All views enforce tenant isolation via RLS (clinic_id from JWT).
"""

from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment, AppointmentType, ScheduleSlot
from inventory.models import InventoryItem
from inventory.services.stock_service import consume_kit
from appointments.serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AppointmentTypeSerializer,
    ScheduleSlotSerializer,
)
from appointments.services.slot_service import (
    find_available_slots,
)
from core.permissions import IsAdminOrReadOnly, IsClinicAdmin


# ---------------------------------------------------------------------------
# AppointmentTypeViewSet
# ---------------------------------------------------------------------------


class AppointmentTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for appointment types.

    Endpoints:
    - GET    /api/v1/appointment-types/          — list types
    - GET    /api/v1/appointment-types/{id}/     — get type detail
    - POST   /api/v1/appointment-types/          — create type (admin only)
    - PATCH  /api/v1/appointment-types/{id}/     — update type (admin only)
    - DELETE /api/v1/appointment-types/{id}/     — delete type (admin only)
    """

    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ["name", "duration_minutes", "price"]
    ordering = ["name"]

    def get_queryset(self):
        """Return appointment types for the current clinic (RLS handles isolation)."""
        return AppointmentType.objects.filter(is_active=True).select_related("clinic")

    def get_serializer_class(self):
        return AppointmentTypeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ---------------------------------------------------------------------------
# AppointmentViewSet
# ---------------------------------------------------------------------------


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for appointments.

    Endpoints:
    - GET    /api/v1/appointments/               — list appointments (?date=, ?status=)
    - POST   /api/v1/appointments/               — create appointment
    - GET    /api/v1/appointments/{id}/          — get appointment detail
    - PATCH  /api/v1/appointments/{id}/          — update appointment
    - DELETE /api/v1/appointments/{id}/          — cancel appointment
    - GET    /api/v1/appointments/available-slots/ — get available slots (?date=, ?dentist_id=)

    Filtering:
    - ?date=YYYY-MM-DD: Filter by date
    - ?status=scheduled: Filter by status
    - ?dentist_id=uuid: Filter by dentist
    - ?patient_id=uuid: Filter by patient
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ["date", "start_time", "created_at", "status"]
    ordering = ["date", "start_time"]

    def get_queryset(self):
        """Return appointments for the current clinic."""
        queryset = Appointment.objects.all().select_related(
            "patient",
            "dentist",
            "appointment_type",
            "created_by",
            "clinic",
        )

        # Apply filters
        date_filter = self.request.query_params.get("date")
        if date_filter:
            queryset = queryset.filter(date=date_filter)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        dentist_filter = self.request.query_params.get("dentist_id")
        if dentist_filter:
            queryset = queryset.filter(dentist_id=dentist_filter)

        patient_filter = self.request.query_params.get("patient_id")
        if patient_filter:
            queryset = queryset.filter(patient_id=patient_filter)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(detail=False, methods=["get"], url_path="available-slots")
    def available_slots(self, request, *args, **kwargs):
        """
        Get available time slots for a dentist on a specific date.

        Query params:
        - date: YYYY-MM-DD (required)
        - dentist_id: UUID (required)
        - duration: slot duration in minutes (optional, default 30)
        """
        date_str = request.query_params.get("date")
        dentist_id = request.query_params.get("dentist_id")
        duration = int(request.query_params.get("duration", 30))

        if not date_str:
            return Response(
                {
                    "error": "date_required",
                    "message": "El parámetro 'date' es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not dentist_id:
            return Response(
                {
                    "error": "dentist_id_required",
                    "message": "El parámetro 'dentist_id' es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {
                    "error": "invalid_date",
                    "message": "Formato de fecha inválido. Use YYYY-MM-DD.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic_id = getattr(request, "clinic_id", None)
        if not clinic_id:
            return Response(
                {"error": "no_clinic", "message": "No se pudo determinar la clínica."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slots = find_available_slots(
            dentist_id=dentist_id,
            date=target_date,
            clinic_id=str(clinic_id),
            slot_duration_minutes=duration,
        )

        # Format times as strings for JSON
        formatted_slots = [
            {
                "start_time": slot["start_time"].strftime("%H:%M"),
                "end_time": slot["end_time"].strftime("%H:%M"),
            }
            for slot in slots
        ]

        return Response(
            {
                "date": date_str,
                "dentist_id": dentist_id,
                "duration_minutes": duration,
                "slots": formatted_slots,
                "total_available": len(formatted_slots),
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        Complete an appointment and auto-consume its inventory kit.

        POST /api/v1/appointments/{id}/complete/

        Status must be scheduled, confirmed, or in_progress.
        Idempotent: once inventory_consumed_at is set, returns 400.
        If the appointment type has a non-empty inventory_kit,
        stock is deducted in a single atomic transaction.
        """
        appointment = self.get_object()
        appt_type = appointment.appointment_type

        # ------------------------------------------------------------------
        # 1. Idempotency check (before status — already consumed is always an error)
        # ------------------------------------------------------------------
        if appointment.inventory_consumed_at is not None:
            return Response(
                {
                    "error": "already_completed",
                    "message": (
                        "La cita ya fue completada. "
                        "Inventario consumido en: "
                        f"{appointment.inventory_consumed_at.isoformat()}"
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------------------------------
        # 2. Validate status
        # ------------------------------------------------------------------
        valid_statuses = [
            Appointment.Status.SCHEDULED,
            Appointment.Status.CONFIRMED,
            Appointment.Status.IN_PROGRESS,
        ]
        if appointment.status not in valid_statuses:
            return Response(
                {
                    "error": "invalid_status",
                    "message": (
                        "Solo se pueden completar citas en estado "
                        "'programada', 'confirmada' o 'en curso'."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------------------------------
        # 3. Pre-validate kit items (collect per-item errors)
        # ------------------------------------------------------------------
        kit = appt_type.inventory_kit or []
        pre_errors = []

        if kit:
            for kit_item in kit:
                item_id = kit_item.get("item_id")
                quantity = kit_item.get("quantity", 0)

                if (
                    not item_id
                    or not isinstance(quantity, (int, float))
                    or quantity <= 0
                ):
                    continue

                try:
                    item = InventoryItem.objects.select_for_update().get(
                        id=item_id,
                        clinic_id=str(appointment.clinic_id),
                        is_active=True,
                    )
                except InventoryItem.DoesNotExist:
                    pre_errors.append(
                        {
                            "item_id": str(item_id),
                            "item_name": "Desconocido",
                            "available": 0,
                            "required": quantity,
                            "error": "Item no encontrado",
                        }
                    )
                    continue

                if item.is_blocked:
                    pre_errors.append(
                        {
                            "item_id": str(item_id),
                            "item_name": item.name,
                            "available": int(item.stock_current),
                            "required": quantity,
                            "error": "Item bloqueado",
                        }
                    )
                    continue

                if item.is_expired:
                    pre_errors.append(
                        {
                            "item_id": str(item_id),
                            "item_name": item.name,
                            "available": int(item.stock_current),
                            "required": quantity,
                            "error": "Item expirado",
                        }
                    )
                    continue

                if item.stock_current < quantity:
                    pre_errors.append(
                        {
                            "item_id": str(item_id),
                            "item_name": item.name,
                            "available": int(item.stock_current),
                            "required": quantity,
                            "error": "Stock insuficiente",
                        }
                    )

        if pre_errors:
            return Response(
                {
                    "error": "stock_insufficient",
                    "message": "Stock insuficiente para consumir el kit de inventario.",
                    "details": pre_errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------------------------------
        # 4. Consume kit + update appointment (atomic)
        # ------------------------------------------------------------------
        with transaction.atomic():
            if kit:
                movements = consume_kit(
                    clinic_id=str(appointment.clinic_id),
                    kit=kit,
                    appointment_id=str(appointment.id),
                    user=request.user,
                )
                items_consumed = len(movements)
            else:
                items_consumed = 0

            appointment.status = Appointment.Status.COMPLETED
            appointment.inventory_consumed_at = timezone.now()
            appointment.save(
                update_fields=["status", "inventory_consumed_at", "updated_at"]
            )

        return Response(
            {
                "id": str(appointment.id),
                "status": "completed",
                "inventory_consumed_at": appointment.inventory_consumed_at.isoformat(),
                "inventory_items_consumed": items_consumed,
            },
            status=status.HTTP_200_OK,
        )

    def perform_destroy(self, instance):
        """Soft cancel — set status to cancelled instead of deleting."""
        user = self.request.user
        instance.cancel(user=user)

    def update(self, request, *args, **kwargs):
        """
        Update appointment with conflict detection.

        If date, start_time, or dentist changes, re-check for conflicts.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


# ---------------------------------------------------------------------------
# ScheduleSlotViewSet
# ---------------------------------------------------------------------------


class ScheduleSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for schedule slots (recurring weekly availability).

    Endpoints:
    - GET    /api/v1/schedule-slots/             — list schedule slots
    - GET    /api/v1/schedule-slots/{id}/        — get slot detail
    - POST   /api/v1/schedule-slots/             — create slot (admin only)
    - PATCH  /api/v1/schedule-slots/{id}/        — update slot (admin only)
    - DELETE /api/v1/schedule-slots/{id}/        — delete slot (admin only)
    """

    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [OrderingFilter]
    ordering_fields = ["day_of_week", "start_time"]
    ordering = ["day_of_week", "start_time"]

    def get_queryset(self):
        """Return schedule slots for the current clinic."""
        queryset = ScheduleSlot.objects.all().select_related("clinic", "dentist")

        # Optional filters
        day_filter = self.request.query_params.get("day_of_week")
        if day_filter:
            queryset = queryset.filter(day_of_week=int(day_filter))

        dentist_filter = self.request.query_params.get("dentist_id")
        if dentist_filter:
            queryset = queryset.filter(dentist_id=dentist_filter)

        return queryset

    def get_serializer_class(self):
        return ScheduleSlotSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ---------------------------------------------------------------------------
# AvailabilityView
# ---------------------------------------------------------------------------


class AvailabilityView(APIView):
    """
    Custom endpoint to list available slots.

    GET /api/v1/availability/?dentist_id=&date=&duration=

    This is an alternative to the available-slots action on AppointmentViewSet.
    Provides a flat endpoint for calendar widgets.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get("date")
        dentist_id = request.query_params.get("dentist_id")
        duration = int(request.query_params.get("duration", 30))

        if not date_str:
            return Response(
                {
                    "error": "date_required",
                    "message": "El parámetro 'date' es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not dentist_id:
            return Response(
                {
                    "error": "dentist_id_required",
                    "message": "El parámetro 'dentist_id' es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {
                    "error": "invalid_date",
                    "message": "Formato de fecha inválido. Use YYYY-MM-DD.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic_id = getattr(request, "clinic_id", None)
        if not clinic_id:
            return Response(
                {"error": "no_clinic", "message": "No se pudo determinar la clínica."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slots = find_available_slots(
            dentist_id=dentist_id,
            date=target_date,
            clinic_id=str(clinic_id),
            slot_duration_minutes=duration,
        )

        formatted_slots = [
            {
                "start_time": slot["start_time"].strftime("%H:%M"),
                "end_time": slot["end_time"].strftime("%H:%M"),
            }
            for slot in slots
        ]

        return Response(
            {
                "date": date_str,
                "dentist_id": dentist_id,
                "duration_minutes": duration,
                "slots": formatted_slots,
                "total_available": len(formatted_slots),
            }
        )
