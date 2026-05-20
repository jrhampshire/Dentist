"""
Clinics app views — Onboarding & Clinic Management.

Views:
- ClinicRegistrationView: Public registration endpoint
- EmailVerificationView: Verify email with token
- ResendVerificationView: Resend verification email
- OnboardingStepsViewSet: CRUD for onboarding steps
- CompleteOnboardingView: Finish onboarding, activate clinic
- ClinicViewSet: Clinic detail and management (authenticated)
"""

import logging

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clinics.models import Clinic, OnboardingStep
from clinics.serializers import (
    ClinicRegistrationSerializer,
    ClinicSerializer,
    OnboardingStepSerializer,
)
from clinics.services.onboarding_service import OnboardingService
from core.permissions import IsClinicAdmin

logger = logging.getLogger(__name__)


class ClinicRegistrationView(APIView):
    """
    POST /api/v1/onboarding/register/

    Register a new clinic with an admin user.
    Public endpoint — no authentication required.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ClinicRegistrationSerializer

    def post(self, request):
        serializer = ClinicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            result = OnboardingService.register_clinic(
                name=data["name"],
                rfc=data["rfc"],
                email=data["email"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                password=data["password"],
                phone=data.get("phone", ""),
                address=data.get("address", {}),
                plan=data.get("plan", Clinic.Plan.FREE),
            )
        except Exception as e:
            logger.exception("Error registering clinic: %s", e)
            return Response(
                {
                    "error": "registration_failed",
                    "message": "Error al registrar la clínica.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Send verification email (dev mode: logs URL)
        OnboardingService.send_verification_email(
            result["clinic"], result["verification_token"]
        )

        return Response(
            {
                "id": str(result["clinic"].id),
                "name": result["clinic"].name,
                "email": result["clinic"].email,
                "status": result["clinic"].status,
                "plan": result["clinic"].plan,
                "verification_required": True,
                "message": "Email de verificación enviado. Revisa tu bandeja.",
            },
            status=status.HTTP_201_CREATED,
        )


class EmailVerificationView(APIView):
    """
    POST /api/v1/onboarding/verify-email/

    Verify clinic email with token.
    Public endpoint.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {
                    "error": "missing_token",
                    "message": "Token de verificación requerido.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = OnboardingService.verify_email(token)

        if result["success"]:
            return Response(
                {
                    "message": "Email verificado exitosamente.",
                    "clinic": {
                        "id": str(result["clinic"].id),
                        "name": result["clinic"].name,
                        "status": result["clinic"].status,
                        "email_verified": result["clinic"].email_verified,
                    },
                },
                status=status.HTTP_200_OK,
            )

        if result["error"] == "already_verified":
            return Response(
                {"message": "El email ya fue verificado previamente."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "error": "invalid_token",
                "message": "Token inválido o expirado. Solicita uno nuevo.",
            },
            status=status.HTTP_410_GONE,
        )


class ResendVerificationView(APIView):
    """
    POST /api/v1/onboarding/resend-verification/

    Resend email verification token.
    Public endpoint with rate limiting.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "missing_email", "message": "Email requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = OnboardingService.resend_verification(email)

        if result["success"]:
            # In dev mode, the token is logged; in prod, email is sent
            return Response(
                {"message": "Email de verificación reenviado. Revisa tu bandeja."},
                status=status.HTTP_200_OK,
            )

        if result["error"] == "already_verified":
            return Response(
                {"message": "El email ya fue verificado."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "error": "clinic_not_found",
                "message": "No se encontró una clínica con este email.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )


class OnboardingStepsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for onboarding steps.

    GET /api/v1/onboarding/steps/ — List all steps for user's clinic
    GET /api/v1/onboarding/steps/{step_name}/ — Get specific step
    PATCH /api/v1/onboarding/steps/{step_name}/ — Mark step complete
    """

    serializer_class = OnboardingStepSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "step_name"

    def get_queryset(self):
        """Only return steps for the user's clinic."""
        user = self.request.user
        if user.clinic_id:
            return OnboardingStep.objects.filter(clinic_id=user.clinic_id)
        return OnboardingStep.objects.none()

    def get_object(self):
        """Override to support lookup by step_name instead of id."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = queryset.filter(**filter_kwargs).first()
        self.check_object_permissions(self.request, obj)
        return obj

    def partial_update(self, request, *args, **kwargs):
        """Mark a step as complete."""
        step = self.get_object()
        if step is None:
            return Response(
                {
                    "error": "step_not_found",
                    "message": "Paso de onboarding no encontrado.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if step.completed:
            return Response(
                {"message": "Este paso ya fue completado."},
                status=status.HTTP_200_OK,
            )

        metadata = request.data.get("metadata", {})
        updated_step = OnboardingService.complete_onboarding_step(
            step.clinic, step.step_name, metadata
        )

        if updated_step is None:
            return Response(
                {
                    "error": "step_not_found",
                    "message": "Paso de onboarding no encontrado.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(updated_step)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def progress(self, request):
        """Get overall onboarding progress for the user's clinic."""
        user = request.user
        if not user.clinic_id:
            return Response(
                {"error": "no_clinic", "message": "Usuario sin clínica asignada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic = Clinic.objects.get(id=user.clinic_id)
        progress = OnboardingService.get_onboarding_progress(clinic)
        return Response(progress, status=status.HTTP_200_OK)


class CompleteOnboardingView(APIView):
    """
    POST /api/v1/onboarding/complete/

    Mark onboarding as complete. Activates clinic if email is verified.
    """

    permission_classes = [IsAuthenticated, IsClinicAdmin]

    def post(self, request):
        user = request.user
        if not user.clinic_id:
            return Response(
                {"error": "no_clinic", "message": "Usuario sin clínica asignada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        clinic = Clinic.objects.get(id=user.clinic_id)

        if clinic.email_verified:
            clinic.complete_onboarding()
            return Response(
                {
                    "message": "Onboarding completado. Tu clínica está activa.",
                    "clinic": ClinicSerializer(clinic).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "error": "email_not_verified",
                "message": "Debes verificar tu email antes de completar el onboarding.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class ClinicViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet for clinic management.

    GET /api/v1/clinics/ — List clinics (admin/superuser only)
    GET /api/v1/clinics/{id}/ — Get clinic detail
    PATCH /api/v1/clinics/{id}/ — Update clinic settings
    """

    serializer_class = ClinicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Users can only see their own clinic (superusers see all)."""
        user = self.request.user
        if user.is_superuser:
            return Clinic.objects.filter(is_deleted=False)
        if user.clinic_id:
            return Clinic.objects.filter(id=user.clinic_id, is_deleted=False)
        return Clinic.objects.none()
