"""
Auth serializers for ClínicaSaaS.

- LoginSerializer: email/password authentication
- RegisterSerializer: new user registration (with clinic)
- TokenSerializer: access/refresh token response
- UserSerializer: user profile serialization
- UserCreateSerializer: admin creates user (invite flow)
- PasswordResetRequestSerializer: forgot password
- PasswordResetConfirmSerializer: reset password with token
- ChangePasswordSerializer: change password (authenticated)
"""

import re
from typing import Any

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()

# Password requirements regex
PASSWORD_UPPER_RE = re.compile(r"[A-Z]")
PASSWORD_LOWER_RE = re.compile(r"[a-z]")
PASSWORD_DIGIT_RE = re.compile(r"\d")
PASSWORD_SPECIAL_RE = re.compile(r"[!@#$%^&*()_+\-=\[\]{};:'\"\\|,.<>\/?]")


def validate_password_strength(password: str) -> str:
    """
    Validate password meets requirements:
    - Min 8 characters
    - At least 1 uppercase
    - At least 1 lowercase
    - At least 1 digit
    - At least 1 special character
    """
    if len(password) < 8:
        raise serializers.ValidationError(
            "La contraseña debe tener al menos 8 caracteres."
        )
    if not PASSWORD_UPPER_RE.search(password):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos una letra mayúscula."
        )
    if not PASSWORD_LOWER_RE.search(password):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos una letra minúscula."
        )
    if not PASSWORD_DIGIT_RE.search(password):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos un número."
        )
    if not PASSWORD_SPECIAL_RE.search(password):
        raise serializers.ValidationError(
            "La contraseña debe tener al menos un carácter especial (!@#$%^&*...)."
        )

    # Also run Django's built-in validators
    try:
        password_validation.validate_password(password)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))

    return password


class LoginSerializer(serializers.Serializer):
    """Serializer for email/password login."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                "Se requieren email y contraseña.",
                code="missing_fields",
            )

        return attrs


class RegisterSerializer(serializers.Serializer):
    """Serializer for new user registration (via onboarding flow)."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)
    phone = serializers.CharField(required=False, max_length=15, default="")
    accept_terms = serializers.BooleanField(required=True, write_only=True)

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "Debes aceptar los términos y condiciones."
            )
        return value

    def validate_password(self, value: str) -> str:
        return validate_password_strength(value)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este email.",
                code="email_exists",
            )
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        validated_data.pop("accept_terms")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for admin to create/invite a user to the clinic."""

    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "password",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate_password(self, value: str | None) -> str | None:
        if value:
            return validate_password_strength(value)
        return value

    def validate_email(self, value: str) -> str:
        request = self.context.get("request")
        clinic = getattr(request, "clinic_id", None) if request else None
        qs = User.objects.filter(email=value, is_deleted=False)
        if clinic:
            qs = qs.filter(clinic_id=clinic)
        if qs.exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este email en esta clínica.",
                code="email_exists",
            )
        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            # Generate invitation token for user to set password
            import secrets
            from django.utils import timezone

            user.invitation_token = secrets.token_urlsafe(32)
            user.invitation_expires = timezone.now() + timezone.timedelta(hours=48)
            user.set_password(None)  # unusable password until invitation accepted
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile (read + partial update)."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "is_active",
            "is_verified",
            "clinic_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "is_active",
            "is_verified",
            "clinic_id",
            "created_at",
        ]

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(update_fields=list(validated_data.keys()))
        return instance


class TokenSerializer(serializers.Serializer):
    """Serializer for JWT token response."""

    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    token_type = serializers.CharField(default="Bearer", read_only=True)
    expires_in = serializers.IntegerField(read_only=True)

    def to_representation(self, instance: dict[str, Any]) -> dict[str, Any]:
        """
        instance should be a dict with:
        - access_token: str
        - refresh_token: str (DB token string)
        - expires_in: int (seconds)
        - user: User instance
        """
        data = super().to_representation(instance)
        user = instance.get("user")
        if user:
            serializer = UserSerializer(user, context=self.context)
            data["user"] = serializer.data
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for forgot password — sends reset email."""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for reset password with token."""

    token = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value: str) -> str:
        return validate_password_strength(value)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated user)."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Las contraseñas no coinciden."}
            )
        return attrs

    def validate_new_password(self, value: str) -> str:
        return validate_password_strength(value)
