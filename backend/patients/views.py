"""
Patient Management views.

ViewSets:
- PatientViewSet: CRUD + search for patients
- ClinicalNoteViewSet: CRUD + sign action for clinical notes (nested under patients)
- PatientConsentViewSet: CRUD for consent records (nested under patients)
- AuditTrailViewSet: Read-only audit log entries (NOM-024 compliance)

All views enforce tenant isolation via RLS (clinic_id from JWT).
"""

from typing import Any

from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import AuditLog
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

    @action(detail=True, methods=["get"], url_path="export")
    def export_patient_data(self, request, pk=None):
        """
        Export complete patient record for NOM-024 data portability.

        Returns JSON with patient info, clinical notes, consents,
        appointments, and invoices.

        Permission: IsClinicAdmin or IsOwnerOrAdmin.
        """
        patient = self.get_object()

        # Permission check
        user_role = getattr(request, "user_role", None)
        user_id = str(request.user.pk) if request.user else None

        if user_role != "admin":
            # Dentists and receptionists can export their own patients
            if str(patient.created_by_id) != user_id:
                raise PermissionDenied(
                    "Solo el administrador o el creador del expediente puede exportarlo."
                )

        # --- Patient data ---
        patient_data = PatientSerializer(patient, context={"request": request}).data

        # --- Clinical notes ---
        notes_qs = ClinicalNote.objects.filter(patient=patient).select_related("author")
        notes_data = []
        for note in notes_qs:
            note_dict = ClinicalNoteSerializer(note, context={"request": request}).data
            notes_data.append(note_dict)

        # --- Consents ---
        consents_qs = PatientConsent.objects.filter(patient=patient).select_related(
            "signed_by"
        )
        consents_data = []
        for consent in consents_qs:
            consent_dict = PatientConsentSerializer(
                consent, context={"request": request}
            ).data
            consents_data.append(consent_dict)

        # --- Appointments ---
        from appointments.models import Appointment

        appointments_qs = (
            Appointment.objects.filter(patient=patient)
            .select_related("appointment_type", "dentist")
            .order_by("-date", "-start_time")
        )
        appointments_data = []
        for appt in appointments_qs:
            appointments_data.append(
                {
                    "id": str(appt.id),
                    "date": str(appt.date),
                    "start_time": str(appt.start_time),
                    "end_time": str(appt.end_time),
                    "type": appt.appointment_type.name
                    if appt.appointment_type
                    else None,
                    "dentist": appt.dentist.get_full_name() if appt.dentist else None,
                    "status": appt.status,
                    "status_display": appt.get_status_display(),
                }
            )

        # --- Invoices ---
        from invoicing.models import Invoice

        invoices_qs = (
            Invoice.objects.filter(patient=patient)
            .select_related("appointment")
            .order_by("-created_at")
        )
        invoices_data = []
        for inv in invoices_qs:
            invoices_data.append(
                {
                    "id": str(inv.id),
                    "folio": inv.folio,
                    "total": str(inv.total),
                    "status": inv.status,
                    "status_display": inv.get_status_display(),
                    "created_at": str(inv.created_at),
                    "stamped_at": str(inv.cfdi_stamp_date)
                    if hasattr(inv, "cfdi_stamp_date") and inv.cfdi_stamp_date
                    else None,
                }
            )

        # --- Build response ---
        export_data = {
            "expediente": {
                "patient": patient_data,
                "clinical_notes": notes_data,
                "consents": consents_data,
                "appointments": appointments_data,
                "invoices": invoices_data,
            },
            "exported_at": timezone.now().isoformat(),
            "exported_by": user_id,
            "retention_policy": "NOM-024 — 5 años",
        }

        filename = f"expediente_{pk}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        response = Response(export_data, status=status.HTTP_200_OK)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

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


# ---------------------------------------------------------------------------
# AuditTrailViewSet — NOM-024 compliance
# ---------------------------------------------------------------------------


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog entries — read-only."""

    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "resource_type",
            "resource_id",
            "user",
            "user_name",
            "details",
            "result",
            "ip_address",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj: AuditLog) -> str | None:
        """Return the user's full name or email for display."""
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return None


class AuditTrailViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read-only audit trail for NOM-024 compliance.

    Endpoints:
    - GET /audit-trail/                       — list all audit entries
    - GET /audit-trail/?resource_type=X       — filter by resource type
    - GET /audit-trail/?resource_type=X&resource_id=Y — filter by resource
    - GET /audit-trail/{id}/                  — get single audit entry detail

    All entries are ordered by -created_at (most recent first).
    Uses cursor-based pagination (default: 20 per page).

    Permission: authenticated users only.

    Role-based scoping:
    - Admins: see all clinic audit entries (RLS enforces clinic isolation).
    - Dentists: restricted to audit entries about their own patients — i.e.
      patients they created (`created_by`) or treat (have an appointment with
      them as the `dentist`) — plus the appointments/notes/consents tied to
      those patients.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        """Return audit log entries filtered by query params and role."""
        qs = AuditLog.objects.select_related("user").order_by("-created_at")
        resource_type = self.request.query_params.get("resource_type")
        resource_id = self.request.query_params.get("resource_id")

        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if resource_id:
            qs = qs.filter(resource_id=resource_id)

        # ── Role-based scoping ──────────────────────────────────────────
        user_role = getattr(self.request, "user_role", None)

        # Admins see the full clinic audit trail (RLS handles tenant isolation).
        if user_role == "admin":
            return qs

        # Dentists only see audit entries about their own patients.
        if user_role == "dentista":
            from django.db.models import Q

            from appointments.models import Appointment

            user = self.request.user

            # Patients this dentist owns (created) or treats (has appointments
            # with). Uses subqueries so the IN clauses stay cheap.
            patient_ids = (
                Patient.objects.filter(
                    Q(created_by=user) | Q(appointments__dentist=user)
                )
                .values_list("id", flat=True)
                .distinct()
            )
            appointment_ids = Appointment.objects.filter(dentist=user).values_list(
                "id", flat=True
            )
            note_ids = ClinicalNote.objects.filter(
                patient_id__in=patient_ids
            ).values_list("id", flat=True)
            consent_ids = PatientConsent.objects.filter(
                patient_id__in=patient_ids
            ).values_list("id", flat=True)

            qs = qs.filter(
                Q(resource_type="Patient", resource_id__in=patient_ids)
                | Q(resource_type="Appointment", resource_id__in=appointment_ids)
                | Q(resource_type="Clinical Note", resource_id__in=note_ids)
                | Q(resource_type="Patient Consent", resource_id__in=consent_ids)
            )

        return qs
