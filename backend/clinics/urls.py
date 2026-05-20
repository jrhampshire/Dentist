"""Onboarding & Clinic Management URL routes — /api/v1/onboarding/*"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from clinics.views import (
    ClinicRegistrationView,
    ClinicViewSet,
    CompleteOnboardingView,
    EmailVerificationView,
    OnboardingStepsViewSet,
    ResendVerificationView,
)

# Router for onboarding steps
onboarding_router = DefaultRouter()
onboarding_router.register(
    r"steps", OnboardingStepsViewSet, basename="onboarding-steps"
)

# Router for clinics (separate prefix)
clinics_router = DefaultRouter()
clinics_router.register(r"", ClinicViewSet, basename="clinics")

urlpatterns = [
    # Public endpoints (no auth required)
    path(
        "register/",
        ClinicRegistrationView.as_view(),
        name="clinic-register",
    ),
    path(
        "verify-email/",
        EmailVerificationView.as_view(),
        name="verify-email",
    ),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    # Authenticated endpoints
    path(
        "complete/",
        CompleteOnboardingView.as_view(),
        name="complete-onboarding",
    ),
    # Onboarding steps (nested under onboarding/)
    path("", include(onboarding_router.urls)),
]

# Clinics are at /api/v1/clinics/ — registered separately in config/urls.py
