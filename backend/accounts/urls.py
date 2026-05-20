"""
Auth & RBAC URL routes — /api/v1/auth/*
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import (
    AppleOAuthView,
    ChangePasswordView,
    ForgotPasswordView,
    GoogleOAuthView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    ResetPasswordView,
    UserViewSet,
)

# Router for user CRUD (admin only)
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="auth-users")

urlpatterns = [
    # Authentication
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    # Password management
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    # Current user profile
    path("me/", MeView.as_view(), name="auth-me"),
    # OAuth
    path("oauth/google/", GoogleOAuthView.as_view(), name="auth-oauth-google"),
    path("oauth/apple/", AppleOAuthView.as_view(), name="auth-oauth-apple"),
    # User CRUD (admin only) — via router
    path("", include(router.urls)),
]
