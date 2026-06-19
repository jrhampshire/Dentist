"""
Onboarding service — Clinic registration flow and email verification.

Handles:
- Atomic clinic + admin user creation
- Email verification token generation
- Onboarding step initialization and tracking
- Clinic activation
"""

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from clinics.models import Clinic, OnboardingStep

logger = logging.getLogger(__name__)

# Standard onboarding steps
STANDARD_ONBOARDING_STEPS = [
    OnboardingStep.StepName.CLINIC_INFO,
    OnboardingStep.StepName.TEAM_SETUP,
    OnboardingStep.StepName.SCHEDULE_CONFIG,
    OnboardingStep.StepName.PATIENT_IMPORT,
    OnboardingStep.StepName.FISCAL_CONFIG,
    OnboardingStep.StepName.WHATSAPP_CONFIG,
]


class OnboardingService:
    """Service for clinic registration and onboarding management."""

    @staticmethod
    @transaction.atomic
    def register_clinic(
        name: str,
        rfc: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        phone: str = "",
        address: dict | None = None,
        plan: str = Clinic.Plan.FREE,
    ) -> dict[str, Any]:
        """
        Register a new clinic with an admin user atomically.

        Returns:
            dict with clinic, user, verification_token, and onboarding_steps.
        """
        from accounts.models import User

        # 1. Create clinic
        clinic = Clinic.objects.create(
            name=name,
            rfc=rfc.upper().strip(),
            email=email,
            phone=phone,
            address=address or {},
            plan=plan,
            status=Clinic.Status.PENDING,
        )

        # 2. Create admin user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.ADMIN,
            clinic=clinic,
            is_verified=False,
        )

        # 3. Generate email verification token
        verification_token = clinic.generate_verification_token()

        # 4. Initialize onboarding steps
        onboarding_steps = OnboardingService._initialize_onboarding_steps(clinic)

        logger.info(
            "New clinic registered: %s (id=%s, admin=%s)",
            clinic.name,
            clinic.id,
            user.email,
        )

        return {
            "clinic": clinic,
            "user": user,
            "verification_token": verification_token,
            "onboarding_steps": onboarding_steps,
        }

    @staticmethod
    def _initialize_onboarding_steps(clinic: Clinic) -> list[OnboardingStep]:
        """Create standard onboarding steps for a new clinic."""
        steps = []
        for step_name in STANDARD_ONBOARDING_STEPS:
            step, _ = OnboardingStep.objects.get_or_create(
                clinic=clinic,
                step_name=step_name,
                defaults={"completed": False},
            )
            steps.append(step)
        return steps

    @staticmethod
    def verify_email(token: str) -> dict[str, Any]:
        """
        Verify clinic email with token.

        Returns:
            dict with success status and clinic (if successful).
        """
        try:
            clinic = Clinic.objects.get(
                email_verification_token=token,
                email_verification_expires__gt=timezone.now(),
            )
        except Clinic.DoesNotExist:
            return {"success": False, "error": "invalid_token"}

        if clinic.email_verified:
            return {"success": False, "error": "already_verified"}

        clinic.email_verified = True
        clinic.email_verification_token = ""
        clinic.email_verification_expires = None

        # Auto-activate if onboarding is also complete
        if clinic.onboarding_completed and clinic.status == Clinic.Status.PENDING:
            clinic.status = Clinic.Status.ACTIVE

        clinic.save(
            update_fields=[
                "email_verified",
                "email_verification_token",
                "email_verification_expires",
                "status",
                "updated_at",
            ]
        )

        logger.info("Email verified for clinic: %s (id=%s)", clinic.name, clinic.id)

        return {"success": True, "clinic": clinic}

    @staticmethod
    def resend_verification(email: str) -> dict[str, Any]:
        """
        Resend email verification token.

        Returns:
            dict with success status and new token (if successful).
        """
        try:
            clinic = Clinic.objects.get(email=email, is_deleted=False)
        except Clinic.DoesNotExist:
            return {"success": False, "error": "clinic_not_found"}

        if clinic.email_verified:
            return {"success": False, "error": "already_verified"}

        token = clinic.generate_verification_token()

        logger.info(
            "Verification email resent for clinic: %s (id=%s)", clinic.name, clinic.id
        )

        return {"success": True, "token": token}

    @staticmethod
    def complete_onboarding_step(
        clinic: Clinic, step_name: str, metadata: dict | None = None
    ) -> OnboardingStep | None:
        """
        Mark an onboarding step as complete.

        Returns:
            The updated OnboardingStep, or None if step not found.
        """
        try:
            step = OnboardingStep.objects.get(clinic=clinic, step_name=step_name)
        except OnboardingStep.DoesNotExist:
            return None

        step.mark_complete(metadata=metadata)

        # Check if all steps are complete
        all_complete = not OnboardingStep.objects.filter(
            clinic=clinic, completed=False
        ).exists()

        if all_complete:
            clinic.complete_onboarding()
            logger.info(
                "Onboarding completed for clinic: %s (id=%s)", clinic.name, clinic.id
            )

        return step

    @staticmethod
    def get_onboarding_progress(clinic: Clinic) -> dict[str, Any]:
        """Get onboarding progress for a clinic."""
        steps = OnboardingStep.objects.filter(clinic=clinic)
        total = steps.count()
        completed = sum(1 for s in steps if s.completed)

        return {
            "clinic_id": str(clinic.id),
            "clinic_name": clinic.name,
            "onboarding_completed": clinic.onboarding_completed,
            "email_verified": clinic.email_verified,
            "status": clinic.status,
            "total_steps": total,
            "completed_steps": completed,
            "percentage": round((completed / total * 100) if total > 0 else 0, 1),
            "steps": [
                {
                    "step_name": s.step_name,
                    "completed": s.completed,
                    "completed_at": s.completed_at,
                    "metadata": s.metadata,
                }
                for s in steps
            ],
        }

    @staticmethod
    def send_verification_email(clinic: Clinic, token: str) -> bool:
        """
        Send verification email to clinic admin.

        NOTE: This is a stub. In production, integrate with your email provider
        (SendGrid, AWS SES, etc.) via Celery async task.

        For now, logs the verification URL for development.
        """
        verification_url = (
            f"{getattr(clinic, '_base_url', 'http://localhost:3000')}"
            f"/verify-email?token={token}&email={clinic.email}"
        )

        logger.info(
            "VERIFICATION EMAIL (dev mode):\n  To: %s\n  URL: %s\n  Token expires: %s",
            clinic.email,
            verification_url,
            clinic.email_verification_expires,
        )

        # Send verification email via Celery task
        from celery_app.tasks import send_verification_email_task

        send_verification_email_task.delay(str(clinic.id), token)

        return True
