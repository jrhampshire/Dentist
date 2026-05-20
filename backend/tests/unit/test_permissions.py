"""
Unit tests for core/permissions.py.

Direct instantiation of permission classes with mock DRF requests.
No DB required.
"""

from unittest.mock import Mock

import pytest
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request

from core.permissions import (
    IsAdminOrReadOnly,
    IsClinicAdmin,
    IsDentist,
    IsOwnerOrAdmin,
    IsRecepcionista,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_request(user_role=None, method="GET", user=None, user_pk=None):
    """Build a DRF Request mock with user_role and auth state."""
    mock_django_request = Mock()
    if user is not None:
        mock_django_request.user = user
    else:
        mock_django_request.user = Mock()
        mock_django_request.user.is_authenticated = True
        mock_django_request.user.pk = user_pk or 1

    mock_request = Mock(spec=Request)
    mock_request.method = method
    mock_request.user = mock_django_request.user
    mock_request.user_role = user_role
    return mock_request


def make_mock_view():
    """Build a mock DRF view."""
    return Mock()


# ---------------------------------------------------------------------------
# IsClinicAdmin
# ---------------------------------------------------------------------------


class TestIsClinicAdmin:
    """Permission: only users with role='admin' are allowed."""

    def test_admin_has_permission(self):
        """User with role='admin' → True."""
        perm = IsClinicAdmin()
        request = make_mock_request(user_role="admin")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_admin_has_object_permission(self):
        """Object-level: admin → True (delegates to has_permission)."""
        perm = IsClinicAdmin()
        request = make_mock_request(user_role="admin")
        view = make_mock_view()
        obj = Mock()
        assert perm.has_object_permission(request, view, obj) is True

    def test_non_admin_has_permission(self):
        """User with role='dentista' → False."""
        perm = IsClinicAdmin()
        request = make_mock_request(user_role="dentista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_no_role_has_permission(self):
        """No user_role attribute → False."""
        perm = IsClinicAdmin()
        request = make_mock_request(user_role=None)
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_admin_in_any_clinic_passes(self):
        """
        NOTE: The current implementation does NOT check cross-clinic access.
        Any admin role returns True regardless of clinic. This test documents
        actual behavior — the spec expects clinic-aware checks (future enhancement).
        """
        perm = IsClinicAdmin()
        request = make_mock_request(user_role="admin")
        view = make_mock_view()
        obj = Mock()
        # Admin in any clinic passes because has_object_permission
        # only checks user_role, not clinic_id
        assert perm.has_object_permission(request, view, obj) is True


# ---------------------------------------------------------------------------
# IsDentist
# ---------------------------------------------------------------------------


class TestIsDentist:
    """Permission: dentista or admin roles are allowed."""

    def test_dentista_has_permission(self):
        perm = IsDentist()
        request = make_mock_request(user_role="dentista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_admin_has_permission(self):
        perm = IsDentist()
        request = make_mock_request(user_role="admin")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_recepcionista_does_not_have_permission(self):
        perm = IsDentist()
        request = make_mock_request(user_role="recepcionista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_no_role_has_permission(self):
        perm = IsDentist()
        request = make_mock_request(user_role=None)
        view = make_mock_view()
        assert perm.has_permission(request, view) is False


# ---------------------------------------------------------------------------
# IsRecepcionista
# ---------------------------------------------------------------------------


class TestIsRecepcionista:
    """Permission: recepcionista or admin roles are allowed."""

    def test_recepcionista_has_permission(self):
        perm = IsRecepcionista()
        request = make_mock_request(user_role="recepcionista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_admin_has_permission(self):
        perm = IsRecepcionista()
        request = make_mock_request(user_role="admin")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_dentista_does_not_have_permission(self):
        perm = IsRecepcionista()
        request = make_mock_request(user_role="dentista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_no_role_has_permission(self):
        perm = IsRecepcionista()
        request = make_mock_request(user_role=None)
        view = make_mock_view()
        assert perm.has_permission(request, view) is False


# ---------------------------------------------------------------------------
# IsOwnerOrAdmin
# ---------------------------------------------------------------------------


class TestIsOwnerOrAdmin:
    """Permission: owner or admin can access the resource."""

    def test_owner_accessing_own_resource(self):
        """Owner's user_id matches object's user_id → True."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="dentista", user_pk=42)
        view = make_mock_view()
        obj = Mock()
        obj.user_id = 42
        assert perm.has_object_permission(request, view, obj) is True

    def test_admin_accessing_non_owned_resource(self):
        """Admin role → True regardless of ownership."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="admin", user_pk=1)
        view = make_mock_view()
        obj = Mock()
        obj.user_id = 99
        assert perm.has_object_permission(request, view, obj) is True

    def test_non_owner_non_admin(self):
        """Non-owner, non-admin → False."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="dentista", user_pk=5)
        view = make_mock_view()
        obj = Mock()
        obj.user_id = 10
        assert perm.has_object_permission(request, view, obj) is False

    def test_authenticated_user_has_permission(self):
        """has_permission: any authenticated user → True."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="recepcionista")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_unauthenticated_user_no_permission(self):
        """has_permission: unauthenticated → False."""
        perm = IsOwnerOrAdmin()
        mock_django_request = Mock()
        mock_django_request.user = Mock()
        mock_django_request.user.is_authenticated = False
        request = Mock(spec=Request)
        request.user = mock_django_request.user
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_obj_with_created_by_id(self):
        """Object with created_by_id matches user → True."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="dentista", user_pk=7)
        view = make_mock_view()
        obj = Mock()
        obj.user_id = None
        obj.created_by_id = 7
        obj.author_id = None
        assert perm.has_object_permission(request, view, obj) is True

    def test_obj_with_no_ownership_fields(self):
        """Object with no ownership fields → False."""
        perm = IsOwnerOrAdmin()
        request = make_mock_request(user_role="dentista", user_pk=1)
        view = make_mock_view()
        obj = Mock()
        obj.user_id = None
        obj.created_by_id = None
        del obj.author_id  # ensure it raises AttributeError
        assert perm.has_object_permission(request, view, obj) is False


# ---------------------------------------------------------------------------
# IsAdminOrReadOnly
# ---------------------------------------------------------------------------


class TestIsAdminOrReadOnly:
    """Permission: read for all authenticated, write only for admin."""

    def test_authenticated_user_get(self):
        """Authenticated non-admin GET → True."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="dentista", method="GET")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_non_admin_post(self):
        """Non-admin POST → False."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="dentista", method="POST")
        view = make_mock_view()
        assert perm.has_permission(request, view) is False

    def test_admin_post(self):
        """Admin POST → True."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="admin", method="POST")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_authenticated_user_head(self):
        """HEAD is a SAFE_METHOD → True."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="recepcionista", method="HEAD")
        view = make_mock_view()
        assert perm.has_permission(request, view) is True

    def test_authenticated_object_permission_get(self):
        """Object-level GET → True."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="dentista", method="GET")
        view = make_mock_view()
        obj = Mock()
        assert perm.has_object_permission(request, view, obj) is True

    def test_non_admin_object_permission_post(self):
        """Object-level POST non-admin → False."""
        perm = IsAdminOrReadOnly()
        request = make_mock_request(user_role="dentista", method="POST")
        view = make_mock_view()
        obj = Mock()
        assert perm.has_object_permission(request, view, obj) is False

    def test_unauthenticated_get(self):
        """Unauthenticated GET → False (must be authenticated)."""
        perm = IsAdminOrReadOnly()
        mock_django_request = Mock()
        mock_django_request.user = Mock()
        mock_django_request.user.is_authenticated = False
        request = Mock(spec=Request)
        request.method = "GET"
        request.user = mock_django_request.user
        view = make_mock_view()
        assert perm.has_permission(request, view) is False
