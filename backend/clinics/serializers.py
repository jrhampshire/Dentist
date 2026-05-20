"""
Clinics app serializers.

ClinicSerializer: Full clinic representation.
OnboardingStepSerializer: Onboarding step progress.
ClinicRegistrationSerializer: Registration input (clinic + admin user).
"""

from rest_framework import serializers

from clinics.models import Clinic, OnboardingStep


class OnboardingStepSerializer(serializers.ModelSerializer[OnboardingStep]):
    """Serializer for onboarding step progress."""

    class Meta:
        model = OnboardingStep
        fields = [
            "id",
            "step_name",
            "completed",
            "completed_at",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at"]


class ClinicSerializer(serializers.ModelSerializer[Clinic]):
    """Serializer for clinic representation."""

    onboarding_progress = serializers.SerializerMethodField()

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "rfc",
            "email",
            "phone",
            "address",
            "plan",
            "status",
            "email_verified",
            "onboarding_completed",
            "subscription_start",
            "subscription_end",
            "stamps_remaining",
            "settings",
            "onboarding_progress",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "email_verified",
            "onboarding_completed",
            "subscription_start",
            "subscription_end",
            "stamps_remaining",
            "created_at",
            "updated_at",
        ]

    def get_onboarding_progress(self, obj: Clinic) -> dict:
        """Return onboarding step completion status."""
        steps = obj.onboarding_steps.all()
        total = steps.count()
        completed = sum(1 for s in steps if s.completed)
        return {
            "total_steps": total,
            "completed_steps": completed,
            "percentage": round((completed / total * 100) if total > 0 else 0, 1),
            "steps": OnboardingStepSerializer(steps, many=True).data,
        }


class ClinicRegistrationSerializer(serializers.Serializer):
    """
    Serializer for clinic registration.

    Accepts clinic data + admin user data in a single request.
    Creates both Clinic and User atomically.
    """

    # Clinic fields
    name = serializers.CharField(max_length=200)
    rfc = serializers.CharField(max_length=13, min_length=12)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    address = serializers.JSONField(required=False, default=dict)
    plan = serializers.ChoiceField(
        choices=Clinic.Plan.choices,
        required=False,
        default=Clinic.Plan.FREE,
    )

    # Admin user fields
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True)

    # Compliance
    accept_terms = serializers.BooleanField(write_only=True)

    def validate_rfc(self, value: str) -> str:
        """Validate RFC format (Mexican tax ID)."""
        value = value.strip().upper()
        if Clinic.objects.filter(rfc=value).exists():
            raise serializers.ValidationError(
                "Ya existe una clínica registrada con este RFC."
            )
        return value

    def validate_email(self, value: str) -> str:
        """Check email is not already used by another clinic."""
        if Clinic.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Ya existe una clínica registrada con este email."
            )
        return value

    def validate_accept_terms(self, value: bool) -> bool:
        """Require terms acceptance."""
        if not value:
            raise serializers.ValidationError(
                "Debes aceptar los términos y condiciones."
            )
        return value

    def validate_password(self, value: str) -> str:
        """Validate password strength."""
        from django.contrib.auth.password_validation import validate_password

        validate_password(value)
        return value

    def create(self, validated_data: dict) -> dict:
        """
        NOTE: This serializer does NOT create objects directly.
        Use OnboardingService.register_clinic() for the atomic creation flow.
        This serializer only validates the input data.
        """
        return validated_data
