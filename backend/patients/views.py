"""
Patient Management views.

ViewSets:
- PatientViewSet: CRUD + search for patients
- ClinicalNoteViewSet: CRUD + sign action for clinical notes (nested under patients)
- PatientConsentViewSet: CRUD for consent records (nested under patients)

All views enforce tenant isolation via RLS (clinic_id from JWT).
"""

from typing import Any

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsClinicAdmin, IsDentist
from patients.filters import (
    ClinicalNoteFilter,
    PatientConsentFilter,
    PatientSearchFilter,
)
from patients.models import ClinicalNote, Patient, PatientConsent
from patients.serializers import (
    ClinicalNoteCreateSerializer,
    ClinicalNoteSerializer,
    PatientConsentSerializer,
    PatientCreateSerializer,
    PatientListSerializer,
    PatientSerializer,
)


# ---------------------------------------------------------------------------
# PatientViewSet
# ---------------------------------------------------------------------------


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for patient CRUD operations.

    Endpoints:
    - GET    /api/v1/patients/          — list patients
    - POST   /api/v1/patients/          — create patient
    - GET    /api/v1/patients/{id}/     — get patient detail
    - PATCH  /api/v1/patients/{id}/     — update patient
    - DELETE /api/v1/patients/{id}/     — soft delete (admin only)
    - GET    /api/v1/patients/search/   — search patients (?q=)

    Search: ?q=name/phone/CURP, ?phone=, ?curp=, ?gender=, ?consent_signed=
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PatientSearchFilter
    ordering_fields = ["created_at", "last_name", "first_name", "phone"]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        """Return patients for the current clinic (RLS handles isolation)."""
        return Patient.objects.all().select_related("created_by", "clinic")

    def get_serializer_class(self):
        if self.action == "list":
            return PatientListSerializer
        if self.action == "create":
            return PatientCreateSerializer
        return PatientSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        """Create patient with clinic from JWT context."""
        serializer.save()

    def perform_destroy(self, instance):
        """Soft delete — only admins can delete patients."""
        user_role = getattr(self.request, "user_role", None)
        if user_role != "admin":
            raise PermissionDenied(
                "Solo los administradores pueden eliminar pacientes."
            )
        instance.delete()  # Soft delete via model override

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request, *args, **kwargs):
        """
        Search patients by query string.

        Query params:
        - q: search across name, phone, CURP, email
        - phone: exact phone match
        - curp: exact CURP match
        """
        queryset = self.filter_queryset(self.get_queryset())

        # If no filters applied, return empty or all
        if not request.query_params:
            queryset = queryset.none()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PatientListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PatientListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create patient with duplicate phone check."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check for duplicate phone in clinic
        clinic_id = getattr(request, "clinic_id", None)
        phone = serializer.validated_data.get("phone", "")

        if clinic_id and phone:
            existing = Patient.objects.filter(
                clinic_id=clinic_id, phone=phone, is_deleted=False
            ).first()

            if existing:
                return Response(
                    {
                        "error": "duplicate_patient",
                        "message": "Ya existe un paciente con este teléfono en esta clínica.",
                        "existing_patient_id": str(existing.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


# ---------------------------------------------------------------------------
# ClinicalNoteViewSet (nested under patients)
# ---------------------------------------------------------------------------


class ClinicalNoteViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for clinical notes, nested under patients.

    Endpoints:
    - GET    /api/v1/patients/{patient_id}/notes/          — list notes
    - POST   /api/v1/patients/{patient_id}/notes/          — create note
    - GET    /api/v1/patients/{patient_id}/notes/{id}/     — get note detail
    - POST   /api/v1/patients/{patient_id}/notes/{id}/sign/ — sign note

    Permissions:
    - Dentists and admins can create/view notes
    - Recepcionistas are blocked from notes
    - Only the author (or admin) can sign a note
    - Signed notes cannot be modified
    """

    permission_classes = [IsAuthenticated, IsDentist]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ClinicalNoteFilter
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return notes for the specified patient."""
        patient_id = self.kwargs.get("patient_id")
        return ClinicalNote.objects.filter(patient_id=patient_id).select_related(
            "author", "patient"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ClinicalNoteCreateSerializer
        return ClinicalNoteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def perform_create(self, serializer):
        """Create note with author from request user."""
        serializer.save()

    @action(detail=True, methods=["post"])
    def sign(self, request, patient_id=None, pk=None):
        """
        Sign a clinical note, making it immutable.

        Only the author or an admin can sign.
        """
        note = self.get_object()

        if note.is_signed:
            return Response(
                {
                    "error": "already_signed",
                    "message": "Esta nota ya está firmada.",
                    "signed_at": note.signed_at,
                    "signature_hash": note.signature_hash,
                },
                status=status.HTTP_409_CONFLICT,
            )

        user_role = getattr(request, "user_role", None)
        user_id = str(request.user.pk) if request.user else None

        # Only author or admin can sign
        if user_role != "admin" and str(note.author_id) != user_id:
            raise PermissionDenied(
                "Solo el autor de la nota o un administrador puede firmarla."
            )

        note.sign(user=request.user)

        serializer = ClinicalNoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# PatientConsentViewSet (nested under patients)
# ---------------------------------------------------------------------------


class PatientConsentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for patient consent records, nested under patients.

    Endpoints:
    - GET    /api/v1/patients/{patient_id}/consents/      — list consents
    - POST   /api/v1/patients/{patient_id}/consents/      — create consent
    - GET    /api/v1/patients/{patient_id}/consents/{id}/ — get consent detail
    - POST   /api/v1/patients/{patient_id}/consents/{id}/sign/ — sign consent

    All authenticated users can view and create consent records.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PatientConsentFilter
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return consents for the specified patient."""
        patient_id = self.kwargs.get("patient_id")
        return PatientConsent.objects.filter(patient_id=patient_id).select_related(
            "patient", "signed_by"
        )

    def get_serializer_class(self):
        return PatientConsentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        context["patient_id"] = self.kwargs.get("patient_id")
        return context

    def perform_create(self, serializer):
        """Create consent record."""
        serializer.save()

    @action(detail=True, methods=["post"])
    def sign(self, request, patient_id=None, pk=None):
        """
        Sign a consent record.

        Records the signature blob (if provided), IP address, and timestamp.
        """
        consent = self.get_object()

        if consent.signed:
            return Response(
                {
                    "error": "already_signed",
                    "message": "Este consentimiento ya está firmado.",
                    "signed_at": consent.signed_at,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Get signature blob from request (optional — could be base64 image)
        signature_blob = None
        if request.data.get("signature_blob"):
            import base64

            try:
                signature_blob = base64.b64decode(request.data["signature_blob"])
            except Exception:
                raise ValidationError(
                    {"signature_blob": "El signature_blob debe ser base64 válido."}
                )

        consent.sign(
            signature_blob=signature_blob,
            ip_address=request.META.get("REMOTE_ADDR"),
            user=request.user,
        )

        serializer = PatientConsentSerializer(consent)
        return Response(serializer.data, status=status.HTTP_200_OK)
