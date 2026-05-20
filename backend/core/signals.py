"""
Signals for automatic audit logging.

Connects to post_save and post_delete signals to capture
AuditLog entries for all model changes.
"""

import logging
from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.middleware.audit import get_audit_context

logger = logging.getLogger(__name__)

# Models to exclude from audit logging (avoid infinite loops)
EXCLUDED_MODELS = {"auditlog", "session", "contenttype"}


def _should_audit_model(sender: Any) -> bool:
    """Check if the model should be audited."""
    model_name = sender._meta.model_name
    return model_name not in EXCLUDED_MODELS


def _build_action_string(sender: Any, created: bool = False) -> str:
    """Build a dot-notation action string from the model."""
    app_label = sender._meta.app_label
    model_name = sender._meta.model_name
    action = "created" if created else "updated"
    return f"{app_label}.{model_name}.{action}"


def _build_delete_action_string(sender: Any) -> str:
    """Build a dot-notation action string for deletes."""
    app_label = sender._meta.app_label
    model_name = sender._meta.model_name
    return f"{app_label}.{model_name}.deleted"


def _create_audit_log_entry(
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict,
    result: str = "success",
) -> None:
    """Create an AuditLog entry from the current audit context."""
    from core.models import AuditLog

    context = get_audit_context()
    clinic_id = context.get("clinic_id")

    if not clinic_id:
        # Can't log without clinic context — this shouldn't happen in normal flow
        logger.warning(
            "Audit log skipped: no clinic_id in context for action=%s", action
        )
        return

    # Import here to avoid circular imports
    from accounts.models import User
    from clinics.models import Clinic

    user_id = context.get("user_id")
    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            pass

    try:
        clinic = Clinic.objects.get(pk=clinic_id)
    except Clinic.DoesNotExist:
        logger.warning("Audit log skipped: clinic_id=%s not found", clinic_id)
        return

    AuditLog.objects.create(
        clinic=clinic,
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        result=result,
        ip_address=context.get("ip_address"),
        user_agent=context.get("user_agent"),
        request_id=context.get("request_id"),
    )


@receiver(post_save, dispatch_uid="audit_post_save")
def audit_post_save(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Capture create/update events for audit logging."""
    if not _should_audit_model(sender):
        return

    action = _build_action_string(sender, created)
    resource_type = sender._meta.verbose_name.title()
    resource_id = str(instance.pk)

    # Build details based on create vs update
    if created:
        details = {"new": _get_serializable_fields(instance)}
    else:
        # For updates, try to capture what changed
        details = {"resource_id": resource_id}

    _create_audit_log_entry(action, resource_type, resource_id, details)


@receiver(post_delete, dispatch_uid="audit_post_delete")
def audit_post_delete(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Capture delete events for audit logging."""
    if not _should_audit_model(sender):
        return

    action = _build_delete_action_string(sender)
    resource_type = sender._meta.verbose_name.title()
    resource_id = str(instance.pk)
    details = {"old": _get_serializable_fields(instance)}

    _create_audit_log_entry(action, resource_type, resource_id, details)


def _get_serializable_fields(instance: Any) -> dict:
    """Get a serializable dict of model fields (excluding sensitive/binary fields)."""
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.attname, None)
        # Skip binary fields, passwords, and large text
        if field.get_internal_type() in ("BinaryField", "TextField"):
            if field.name in ("password", "content", "signature_blob"):
                continue
        if value is not None:
            data[field.name] = (
                str(value)
                if not isinstance(value, (str, int, float, bool, dict, list))
                else value
            )
    return data
