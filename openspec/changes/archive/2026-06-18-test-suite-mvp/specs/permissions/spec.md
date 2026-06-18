# permissions — Test Spec

## Purpose

Unit tests for `core/permissions.py`: IsClinicAdmin, IsDentista, IsRecepcionista, IsOwnerOrAdmin, IsAdminOrReadOnly.

## Requirements

### Requirement: IsClinicAdmin MUST grant access to clinic staff only

The system MUST grant object-level access to users whose `role` is `admin` within the same clinic.

#### Scenario: Admin accessing own clinic resource

- GIVEN a user with role `admin` in clinic A, and a resource belonging to clinic A
- WHEN `IsClinicAdmin.has_object_permission(request, view, resource)` is called
- THEN the system SHALL return `True`

#### Scenario: Admin accessing different clinic resource

- GIVEN a user with role `admin` in clinic A, and a resource belonging to clinic B
- WHEN `IsClinicAdmin.has_object_permission(request, view, resource)` is called
- THEN the system SHALL return `False`

### Requirement: IsOwnerOrAdmin MUST verify object ownership or admin role

The system SHALL allow access when the requesting user owns the resource OR has an admin role in the resource's clinic.

#### Scenario: Owner accessing own resource

- GIVEN a user owns resource X, and `request.user.clinic_id` matches the resource's clinic
- WHEN `IsOwnerOrAdmin.has_object_permission(request, view, X)` is called
- THEN the system SHALL return `True`

#### Scenario: Admin accessing non-owned resource

- GIVEN an admin user with `role=admin` in the resource's clinic
- WHEN `IsOwnerOrAdmin.has_object_permission(request, view, resource)` is called
- THEN the system SHALL return `True`

### Requirement: IsAdminOrReadOnly MUST allow safe HTTP methods without admin role

The system SHALL grant read-only access (`GET`, `HEAD`, `OPTIONS`) to any authenticated user, and write access only to admin roles.

#### Scenario: Authenticated user reading

- GIVEN an authenticated user with no admin role
- WHEN a `GET` request is made to a view protected by `IsAdminOrReadOnly`
- THEN the system SHALL return `True`

#### Scenario: Non-admin writing

- GIVEN an authenticated user with no admin role
- WHEN a `POST` request is made to a view protected by `IsAdminOrReadOnly`
- THEN the system SHALL return `False`