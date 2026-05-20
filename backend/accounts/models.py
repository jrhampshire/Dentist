"""
Accounts app — User model, RefreshToken, and supporting models.

User: Custom AbstractBaseUser with role-based access, OAuth fields, account lockout.
RefreshToken: Single-use JWT rotation tokens with revocation support.
"""

import uuid
from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    """Custom manager for the User model."""

    def create_user(
        self,
        email: str,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        role: str = "recepcionista",
        clinic: Any = None,
        **extra_fields: Any,
    ) -> "User":
        """Create and return a regular user."""
        if not email:
            raise ValueError("El email es obligatorio.")
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            clinic=clinic,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str,
        first_name: str = "Admin",
        last_name: str = "System",
        **extra_fields: Any,
    ) -> "User":
        """Create and return a superuser (no clinic bound)."""
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        user = self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            clinic=None,
            **extra_fields,
        )
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for ClínicaSaaS.

    Extends AbstractBaseUser (NOT AbstractUser) to have full control
    over fields and behavior.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        DENTISTA = "dentista", "Dentista"
        RECEPCIONISTA = "recepcionista", "Recepcionista"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    invitation_token = models.CharField(max_length=128, blank=True, null=True)
    invitation_expires = models.DateTimeField(blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    password_changed_at = models.DateTimeField(blank=True, null=True)
    oauth_provider = models.CharField(max_length=20, blank=True, null=True)
    oauth_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "role"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["email"], name="idx_users_email"),
            models.Index(fields=["clinic", "role"], name="idx_users_clinic_role"),
            models.Index(
                fields=["clinic", "is_active"], name="idx_users_clinic_active"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self) -> str:
        """Return the user's full name (Django convention)."""
        return self.full_name

    def is_locked(self) -> bool:
        """Check if the account is currently locked out."""
        if self.locked_until and self.is_active:
            return timezone.now() < self.locked_until
        return False

    def record_failed_attempt(self) -> None:
        """Increment failed login attempts and lock if threshold reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=15)
        self.save(update_fields=["failed_login_attempts", "locked_until", "updated_at"])

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts after successful login."""
        if self.failed_login_attempts > 0 or self.locked_until:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save(
                update_fields=["failed_login_attempts", "locked_until", "updated_at"]
            )

    def soft_delete(self) -> None:
        """Soft delete the user."""
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=["is_deleted", "is_active", "updated_at"])


class RefreshToken(models.Model):
    """
    Single-use refresh token for JWT rotation.

    Each refresh token is revoked after use and a new one is issued.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = "refresh_tokens"
        indexes = [
            models.Index(fields=["token"], name="idx_refresh_token"),
            models.Index(fields=["user", "revoked"], name="idx_refresh_user_revoked"),
        ]

    def __str__(self) -> str:
        return f"RefreshToken for {self.user.email} (revoked={self.revoked})"

    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return timezone.now() > self.expires_at

    def revoke(self) -> None:
        """Mark this token as revoked."""
        self.revoked = True
        self.save(update_fields=["revoked"])
