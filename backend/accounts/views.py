"""
Auth & RBAC views for ClínicaSaaS.

Views:
- LoginView: POST /auth/login/ — email/password login
- RefreshView: POST /auth/refresh/ — refresh access token
- LogoutView: POST /auth/logout/ — revoke refresh token
- RegisterView: POST /auth/register/ — new user registration
- ForgotPasswordView: POST /auth/forgot-password/ — request password reset
- ResetPasswordView: POST /auth/reset-password/ — reset with token
- ChangePasswordView: POST /auth/change-password/ — change password (auth required)
- MeView: GET/PATCH /auth/me/ — current user profile
- GoogleOAuthView: POST /auth/oauth/google/ — Google OAuth login
- AppleOAuthView: POST /auth/oauth/apple/ — Apple OAuth login
- UserViewSet: CRUD for clinic users (admin only)
"""

import logging
import secrets
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import RefreshToken
from accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TokenSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from accounts.services.auth_service import AuthService
from accounts.services.oauth_service import (
    AppleOAuthService,
    GoogleOAuthService,
    handle_oauth_login,
)
from core.permissions import IsClinicAdmin

logger = logging.getLogger(__name__)

User = get_user_model()


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticate with email and password, return JWT pair.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = AuthService.authenticate(email, password)
        except ValueError as exc:
            return Response(
                {"error": "invalid_credentials", "message": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = AuthService.generate_tokens(user)
        token_serializer = TokenSerializer(tokens, context={"request": request})

        return Response(token_serializer.data, status=status.HTTP_200_OK)


class RefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    Rotate refresh token, return new JWT pair.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "missing_token", "message": "Se requiere refresh_token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            tokens = AuthService.refresh_access_token(
                refresh_token,
                ip=ip,
                user_agent=user_agent,
            )
        except ValueError as exc:
            return Response(
                {"error": "invalid_token", "message": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_serializer = TokenSerializer(tokens, context={"request": request})
        return Response(token_serializer.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Revoke refresh token (logout).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh_token")
        if refresh_token:
            AuthService.revoke_token(refresh_token)

        # Also revoke ALL tokens for this user (force full logout)
        AuthService.revoke_all_user_tokens(request.user)

        return Response(
            {"message": "Sesión cerrada exitosamente."},
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Register a new user (used in onboarding flow).
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        tokens = AuthService.generate_tokens(user)
        token_serializer = TokenSerializer(tokens, context={"request": request})

        return Response(
            {
                **token_serializer.data,
                "message": "Registro exitoso. Revisa tu email para verificar tu cuenta.",
            },
            status=status.HTTP_201_CREATED,
        )


class ForgotPasswordView(APIView):
    """
    POST /api/v1/auth/forgot-password/
    Request password reset — generates token and sends email.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        # Always return 200 to prevent email enumeration
        try:
            user = User.objects.get(email=email, is_deleted=False, is_active=True)
            # Generate reset token
            user.invitation_token = secrets.token_urlsafe(32)
            user.invitation_expires = timezone.now() + timezone.timedelta(hours=1)
            user.save(
                update_fields=["invitation_token", "invitation_expires", "updated_at"]
            )

            # TODO: Send reset email via Celery task
            logger.info("Password reset requested for: %s", email)
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists

        return Response(
            {
                "message": "Si el email existe, recibirás un link para restablecer tu contraseña."
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /api/v1/auth/reset-password/
    Reset password with token.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(
                invitation_token=token,
                invitation_expires__gt=timezone.now(),
                is_deleted=False,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "invalid_token", "message": "Token inválido o expirado."},
                status=status.HTTP_410_GONE,
            )

        # Set new password and invalidate token
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.invitation_token = ""
        user.invitation_expires = None
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save()

        # Revoke all existing tokens
        AuthService.revoke_all_user_tokens(user)

        return Response(
            {"message": "Contraseña restablecida exitosamente."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Change password (authenticated user).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        # Verify current password
        if not user.check_password(current_password):
            return Response(
                {
                    "error": "wrong_password",
                    "message": "La contraseña actual es incorrecta.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.save()

        # Revoke all existing tokens (force re-login)
        AuthService.revoke_all_user_tokens(user)

        return Response(
            {"message": "Contraseña cambiada exitosamente. Inicia sesión nuevamente."},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/ — Get current user profile
    PATCH /api/v1/auth/me/ — Update current user profile
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self) -> User:
        return self.request.user


class GoogleOAuthView(APIView):
    """
    POST /api/v1/auth/oauth/google/
    Google OAuth2 login with ID token.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        id_token = request.data.get("id_token")
        if not id_token:
            return Response(
                {
                    "error": "missing_token",
                    "message": "Se requiere id_token de Google.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Verify and decode Google ID token
            claims = GoogleOAuthService.verify_id_token(id_token)

            email = claims.get("email", "")
            oauth_id = claims.get("sub", "")
            first_name = claims.get("given_name", "")
            last_name = claims.get("family_name", "")

            if not email:
                return Response(
                    {
                        "error": "missing_email",
                        "message": "Google no proporcionó un email.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            tokens = handle_oauth_login(
                provider="google",
                email=email,
                oauth_id=oauth_id,
                first_name=first_name,
                last_name=last_name,
            )

        except ValueError as exc:
            return Response(
                {"error": "oauth_error", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_serializer = TokenSerializer(tokens, context={"request": request})
        return Response(token_serializer.data, status=status.HTTP_200_OK)


class AppleOAuthView(APIView):
    """
    POST /api/v1/auth/oauth/apple/
    Apple Sign-In with ID token.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        id_token = request.data.get("id_token")
        if not id_token:
            return Response(
                {"error": "missing_token", "message": "Se requiere id_token de Apple."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Decode Apple ID token
            claims = AppleOAuthService.decode_id_token(id_token)

            email = claims.get("email", "")
            oauth_id = claims.get("sub", "")
            name = claims.get("name", {})
            first_name = name.get("firstName", "") if isinstance(name, dict) else ""
            last_name = name.get("lastName", "") if isinstance(name, dict) else ""

            if not oauth_id:
                return Response(
                    {"error": "missing_sub", "message": "Token de Apple inválido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            tokens = handle_oauth_login(
                provider="apple",
                email=email,
                oauth_id=oauth_id,
                first_name=first_name,
                last_name=last_name,
            )

        except ValueError as exc:
            return Response(
                {"error": "oauth_error", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_serializer = TokenSerializer(tokens, context={"request": request})
        return Response(token_serializer.data, status=status.HTTP_200_OK)


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD for clinic users (admin only).

    GET    /api/v1/auth/users/       — List clinic users
    GET    /api/v1/auth/users/{id}/  — Get user detail
    POST   /api/v1/auth/users/       — Invite/create user
    PATCH  /api/v1/auth/users/{id}/  — Update user
    DELETE /api/v1/auth/users/{id}/  — Deactivate user (soft delete)
    """

    permission_classes = [IsAuthenticated, IsClinicAdmin]

    def get_queryset(self):
        """Only return users from the current user's clinic."""
        user = self.request.user
        return User.objects.filter(
            clinic_id=user.clinic_id,
            is_deleted=False,
        ).select_related("clinic")

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        """Auto-inject clinic_id when creating a user."""
        serializer.save(clinic_id=self.request.user.clinic_id)

    @action(detail=True, methods=["delete"])
    def deactivate(self, request, pk=None):
        """Soft delete (deactivate) a user."""
        user = self.get_object()

        # Prevent self-deactivation
        if user.pk == request.user.pk:
            return Response(
                {
                    "error": "self_deactivate",
                    "message": "No puedes desactivar tu propia cuenta.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.soft_delete()
        AuthService.revoke_all_user_tokens(user)

        return Response(
            {"message": f"Usuario {user.email} desactivado."},
            status=status.HTTP_204_NO_CONTENT,
        )

    def destroy(self, request, *args, **kwargs):
        """Alias to deactivate for DELETE method."""
        return self.deactivate(request, pk=kwargs.get("pk"))
