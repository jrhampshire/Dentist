"""
Custom DRF permission classes for role-based access control.

Permissions:
- IsClinicAdmin: Only users with role='admin'
- IsDentist: Users with role='dentista' or 'admin'
- IsRecepcionista: Users with role='recepcionista' or 'admin'
- IsOwnerOrAdmin: User owns the resource or is an admin
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsClinicAdmin(BasePermission):
    """Permission class that only allows clinic administrators."""

    def has_permission(self, request, view):
        user_role = getattr(request, "user_role", None)
        return user_role == "admin"

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsDentist(BasePermission):
    """Permission class that allows dentists and admins."""

    def has_permission(self, request, view):
        user_role = getattr(request, "user_role", None)
        return user_role in ("dentista", "admin")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsRecepcionista(BasePermission):
    """Permission class that allows receptionists and admins."""

    def has_permission(self, request, view):
        user_role = getattr(request, "user_role", None)
        return user_role in ("recepcionista", "admin")

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsOwnerOrAdmin(BasePermission):
    """
    Permission class that allows the resource owner or an admin.

    The resource must have a user_id, created_by_id, or author_id attribute
    that matches the current user's ID.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user_role = getattr(request, "user_role", None)
        if user_role == "admin":
            return True

        user_id = str(request.user.pk) if request.user else None
        if not user_id:
            return False

        # Check various ownership fields
        owner_id = getattr(obj, "user_id", None) or getattr(obj, "created_by_id", None)
        if hasattr(obj, "author_id"):
            owner_id = owner_id or obj.author_id

        if owner_id:
            return str(owner_id) == user_id

        return False


class IsAdminOrReadOnly(BasePermission):
    """Admins can do everything; authenticated users can only read."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return getattr(request, "user_role", None) == "admin"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return getattr(request, "user_role", None) == "admin"
