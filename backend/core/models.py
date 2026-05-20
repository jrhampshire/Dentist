"""
Core models for ClínicaSaaS Dental MX.

Contains cross-cutting models used across all apps.
"""

import uuid

from django.db import models


class AuditLog(models.Model):
    """
    Append-only audit log for NOM-024 compliance.

    Records every create, update, and delete operation across all models.
    This table is IMMUTABLE — PostgreSQL triggers prevent UPDATE and DELETE.

    Fields:
    - clinic_id: Tenant isolation (RLS)
    - user_id: Who performed the action
    - action: Dot-notation action string (e.g., "patient.created")
    - resource_type: Model name (e.g., "Patient", "Appointment")
    - resource_id: UUID of the affected record
    - details: JSON with old/new values
    - result: "success" or "failure"
    - ip_address, user_agent: Request context
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_index=True,
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)  # e.g. "patient.created"
    resource_type = models.CharField(max_length=50, db_index=True)  # e.g. "Patient"
    resource_id = models.UUIDField(db_index=True)
    details = models.JSONField(default=dict, blank=True)
    result = models.CharField(
        max_length=20,
        default="success",
        choices=[("success", "Success"), ("failure", "Failure")],
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=36, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["clinic", "created_at"], name="idx_audit_clinic_date"),
            models.Index(
                fields=["clinic", "resource_type"], name="idx_audit_clinic_type"
            ),
            models.Index(fields=["user", "created_at"], name="idx_audit_user_date"),
            models.Index(fields=["action"], name="idx_audit_action"),
        ]

    def __str__(self) -> str:
        return f"AuditLog({self.action} - {self.resource_type}:{self.resource_id})"

    def save(self, *args, **kwargs):
        """Prevent updates to existing audit log entries (append-only)."""
        if self.pk:
            raise RuntimeError(
                "AuditLog entries are immutable. Cannot update existing records."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit log entries (append-only)."""
        raise RuntimeError("AuditLog entries are immutable. Cannot delete records.")
