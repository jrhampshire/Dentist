"""
Dental Records views for ClínicaSaaS Dental MX.

ViewSets:
- DentalRecordEntryViewSet: List + create odontogram entries (append-only)
- ToothStateViewSet: Read-only materialized tooth state
- MedicalHistoryViewSet: Retrieve + versioned upsert
- VitalSignsViewSet: List + create vital signs records
- PatientImageViewSet: Upload, list, detail, serve file, delete
- TreatmentPlanViewSet: Full CRUD for treatment plans
- TreatmentPhaseViewSet: Nested under plans (CRUD)
- TreatmentProcedureViewSet: Nested under phases (CRUD)

All views scope data by patient_id from URL and enforce
tenant isolation via the patient → clinic FK chain.
"""

from typing import Any

from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dental_records.models import (
    DentalRecordEntry,
    MedicalHistory,
    PatientImage,
    Tooth,
    TreatmentPhase,
    TreatmentPlan,
    TreatmentProcedure,
    VitalSigns,
)
from dental_records.serializers import (
    DentalRecordEntrySerializer,
    MedicalHistorySerializer,
    PatientImageListSerializer,
    PatientImageSerializer,
    PatientImageUploadSerializer,
    ToothStateSerializer,
    TreatmentPhaseSerializer,
    TreatmentPlanDetailSerializer,
    TreatmentPlanListSerializer,
    TreatmentProcedureSerializer,
    VitalSignsSerializer,
)


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _get_patient_id(kwargs: dict[str, Any]) -> str:
    """Extract patient_id from URL kwargs."""
    return kwargs.get("patient_id", "")


# ─────────────────────────────────────────────────────────────────────────
# 1. DentalRecordEntryViewSet — List + Create (append-only, no update/delete)
# ─────────────────────────────────────────────────────────────────────────


class DentalRecordEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Dental record entries for a patient.

    Endpoints:
    - GET  /api/v1/dental-records/patients/{patient_id}/teeth/entries/
    - POST /api/v1/dental-records/patients/{patient_id}/teeth/entries/
    - GET  /api/v1/dental-records/patients/{patient_id}/teeth/entries/{id}/

    Entries are append-only — no PUT, PATCH, or DELETE allowed.
    Filter by ?tooth_fdi= to view entries for a specific tooth.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DentalRecordEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "tooth_fdi"]
    ordering = ["-created_at"]

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        qs = DentalRecordEntry.objects.filter(patient_id=patient_id).select_related(
            "created_by", "patient"
        )
        tooth_fdi = self.request.query_params.get("tooth_fdi")
        if tooth_fdi:
            qs = qs.filter(tooth_fdi=tooth_fdi)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def create(self, request, *args, **kwargs):
        """
        Create a new dental record entry.

        Idempotent: if the same tooth+surface+condition already exists,
        returns 200 with the existing entry instead of 201 with a duplicate.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance = serializer.save()

        # Check if this was an idempotent return (existing record)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
            headers=headers,
        )

    def destroy(self, request, *args, **kwargs):
        """DELETE is not allowed — append-only."""
        return Response(
            {
                "error": "method_not_allowed",
                "message": "Las entradas del odontograma son inmutables.",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def update(self, request, *args, **kwargs):
        """PUT is not allowed — append-only."""
        return Response(
            {
                "error": "method_not_allowed",
                "message": "Las entradas del odontograma son inmutables.",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH is not allowed — append-only."""
        return Response(
            {
                "error": "method_not_allowed",
                "message": "Las entradas del odontograma son inmutables.",
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


# ─────────────────────────────────────────────────────────────────────────
# 2. ToothStateViewSet — Read-only materialized state
# ─────────────────────────────────────────────────────────────────────────


class ToothStateViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only materialized tooth state for a patient.

    Endpoint:
    - GET /api/v1/dental-records/patients/{patient_id}/teeth/state/

    Returns the current condition for each tooth that has been recorded,
    with nested surface-level details.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ToothStateSerializer

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        return (
            Tooth.objects.filter(patient_id=patient_id)
            .prefetch_related("surfaces")
            .order_by("tooth_fdi")
        )


# ─────────────────────────────────────────────────────────────────────────
# 3. MedicalHistoryViewSet — Retrieve active + versioned upsert
# ─────────────────────────────────────────────────────────────────────────


class MedicalHistoryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Medical history for a patient.

    Endpoints:
    - GET  /api/v1/dental-records/patients/{patient_id}/medical-history/
      Returns the current active version (or 404 if none).
    - POST /api/v1/dental-records/patients/{patient_id}/medical-history/
      Creates the first version (version=1).
    - PUT  /api/v1/dental-records/patients/{patient_id}/medical-history/{id}/
      Creates a new version (version = current.version + 1) and deactivates current.
    - GET  /api/v1/dental-records/patients/{patient_id}/medical-history/{id}/
      Retrieve a specific version.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MedicalHistorySerializer

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        return (
            MedicalHistory.objects.filter(patient_id=patient_id)
            .select_related("patient", "created_by", "updated_by")
            .order_by("-version")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def list(self, request, *args, **kwargs):
        """Return only the active medical history record."""
        patient_id = _get_patient_id(self.kwargs)
        active = (
            MedicalHistory.objects.filter(patient_id=patient_id, is_active=True)
            .select_related("patient", "created_by", "updated_by")
            .first()
        )

        if not active:
            return Response(
                {"detail": "No active medical history found for this patient."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(active)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="history")
    def list_versions(self, request, *args, **kwargs):
        """List all versions (active and historical) for the patient."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────
# 4. VitalSignsViewSet — List + Create
# ─────────────────────────────────────────────────────────────────────────


class VitalSignsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Vital signs records for a patient.

    Endpoints:
    - GET  /api/v1/dental-records/patients/{patient_id}/vital-signs/
    - POST /api/v1/dental-records/patients/{patient_id}/vital-signs/
    - GET  /api/v1/dental-records/patients/{patient_id}/vital-signs/{id}/

    Filters:
    - ?from=YYYY-MM-DD&to=YYYY-MM-DD — date range filter
    - ?appointment=<uuid> — filter by appointment
    """

    permission_classes = [IsAuthenticated]
    serializer_class = VitalSignsSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["recorded_at"]
    ordering = ["-recorded_at"]

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        qs = VitalSigns.objects.filter(patient_id=patient_id).select_related(
            "patient", "recorded_by", "appointment"
        )

        # Date range filter
        date_from = self.request.query_params.get("from")
        date_to = self.request.query_params.get("to")
        if date_from:
            qs = qs.filter(recorded_at__gte=date_from)
        if date_to:
            qs = qs.filter(recorded_at__lte=date_to)

        # Appointment filter
        appointment_id = self.request.query_params.get("appointment")
        if appointment_id:
            qs = qs.filter(appointment_id=appointment_id)

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context


# ─────────────────────────────────────────────────────────────────────────
# 5. PatientImageViewSet — Upload, list, detail, serve, delete
# ─────────────────────────────────────────────────────────────────────────


class PatientImageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Patient image management (photos, X-rays, documents).

    Endpoints:
    - GET    /api/v1/dental-records/patients/{patient_id}/images/
      List images (with proxy URLs, no raw binary).
    - POST   /api/v1/dental-records/patients/{patient_id}/images/
      Upload image (multipart: image file + image_type + optional tooth_fdi, description).
    - GET    /api/v1/dental-records/patients/{patient_id}/images/{id}/
      Image metadata (proxy URLs, no raw binary).
    - GET    /api/v1/dental-records/patients/{patient_id}/images/{id}/file/
      Serve the original image file (protected via Django view).
    - GET    /api/v1/dental-records/patients/{patient_id}/images/{id}/thumbnail/
      Serve the thumbnail.
    - DELETE /api/v1/dental-records/patients/{patient_id}/images/{id}/
      Delete the image.

    Filters:
    - ?image_type= — filter by image type
    - ?tooth_fdi= — filter by tooth
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["uploaded_at"]
    ordering = ["-uploaded_at"]

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        qs = PatientImage.objects.filter(patient_id=patient_id).select_related(
            "patient", "uploaded_by"
        )

        image_type = self.request.query_params.get("image_type")
        if image_type:
            qs = qs.filter(image_type=image_type)

        tooth_fdi = self.request.query_params.get("tooth_fdi")
        if tooth_fdi:
            qs = qs.filter(tooth_fdi=tooth_fdi)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return PatientImageUploadSerializer
        if self.action in ("list",):
            return PatientImageListSerializer
        return PatientImageSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    @action(detail=True, methods=["get"], url_path="file")
    def serve_file(self, request, patient_id=None, pk=None):
        """Serve the original image file through Django proxy."""
        instance = self.get_object()
        if not instance.image:
            raise Http404("No file associated with this image.")

        try:
            file_handle = instance.image.open("rb")
        except Exception:
            raise Http404("Image file not found in storage.")

        response = FileResponse(
            file_handle,
            content_type=instance.content_type or "application/octet-stream",
        )
        response["Content-Disposition"] = f'inline; filename="{instance.image.name}"'
        return response

    @action(detail=True, methods=["get"], url_path="thumbnail")
    def serve_thumbnail(self, request, patient_id=None, pk=None):
        """Serve the thumbnail through Django proxy."""
        instance = self.get_object()
        if not instance.thumbnail:
            raise Http404("No thumbnail available for this image.")

        try:
            file_handle = instance.thumbnail.open("rb")
        except Exception:
            raise Http404("Thumbnail file not found in storage.")

        response = FileResponse(file_handle, content_type="image/jpeg")
        response["Content-Disposition"] = f'inline; filename="thumb_{instance.id}.jpg"'
        return response


# ─────────────────────────────────────────────────────────────────────────
# 6. TreatmentPlanViewSet — Full CRUD with nested phases
# ─────────────────────────────────────────────────────────────────────────


class TreatmentPlanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Treatment plans for a patient.

    Endpoints:
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/
    - POST   /api/v1/dental-records/patients/{patient_id}/plans/
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/{id}/
    - PUT    /api/v1/dental-records/patients/{patient_id}/plans/{id}/
    - PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{id}/
    - DELETE /api/v1/dental-records/patients/{patient_id}/plans/{id}/
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        patient_id = _get_patient_id(self.kwargs)
        return (
            TreatmentPlan.objects.filter(patient_id=patient_id)
            .prefetch_related("phases__procedures")
            .select_related("patient", "created_by")
        )

    def get_serializer_class(self):
        if self.action in ("list",):
            return TreatmentPlanListSerializer
        return TreatmentPlanDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def perform_create(self, serializer):
        serializer.save()


# ─────────────────────────────────────────────────────────────────────────
# 7. TreatmentPhaseViewSet — Nested under plan
# ─────────────────────────────────────────────────────────────────────────


class TreatmentPhaseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Treatment phases nested under a plan.

    Endpoints:
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/
    - POST   /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{id}/
    - PUT    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{id}/
    - PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{id}/
    - DELETE /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TreatmentPhaseSerializer

    def get_queryset(self):
        plan_id = self.kwargs.get("plan_id", "")
        return (
            TreatmentPhase.objects.filter(plan_id=plan_id)
            .prefetch_related("procedures")
            .select_related("plan__patient")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def perform_create(self, serializer):
        plan_id = self.kwargs.get("plan_id", "")
        try:
            plan = TreatmentPlan.objects.get(
                id=plan_id,
                patient_id=self.kwargs.get("patient_id", ""),
            )
        except TreatmentPlan.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Plan de tratamiento no encontrado para este paciente.")
        serializer.save(plan=plan)


# ─────────────────────────────────────────────────────────────────────────
# 8. TreatmentProcedureViewSet — Nested under phase
# ─────────────────────────────────────────────────────────────────────────


class TreatmentProcedureViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Treatment procedures nested under a phase.

    Endpoints:
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/
    - POST   /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/
    - GET    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{id}/
    - PUT    /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{id}/
    - PATCH  /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{id}/
    - DELETE /api/v1/dental-records/patients/{patient_id}/plans/{plan_id}/phases/{phase_id}/procedures/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TreatmentProcedureSerializer

    def get_queryset(self):
        phase_id = self.kwargs.get("phase_id", "")
        return TreatmentProcedure.objects.filter(phase_id=phase_id).select_related(
            "phase__plan__patient", "appointment"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def perform_create(self, serializer):
        phase_id = self.kwargs.get("phase_id", "")
        try:
            phase = TreatmentPhase.objects.get(
                id=phase_id,
                plan_id=self.kwargs.get("plan_id", ""),
                plan__patient_id=self.kwargs.get("patient_id", ""),
            )
        except TreatmentPhase.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Fase no encontrada para este plan y paciente.")
        serializer.save(phase=phase)
