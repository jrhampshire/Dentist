# exceptions — Test Spec

## Purpose

Unit tests for `core/exceptions.py`: `unified_exception_handler`, `_build_error_data`, and error response formatting across all Django REST Framework exception types.

## Requirements

### Requirement: unified_exception_handler MUST return structured error responses

The system MUST format all unhandled exceptions into a consistent JSON structure with `error`, `message`, and `code` fields.

#### Scenario: ValidationError produces 400

- GIVEN a `ValidationError` with field-level messages
- WHEN `unified_exception_handler(request, exc)` is called
- THEN the system SHALL return HTTP 400 with `{"error": "validation_error", "message": "...", "code": "VALIDATION_ERROR", "details": {...}}`

#### Scenario: NotAuthenticated produces 401

- GIVEN a `NotAuthenticated` exception
- WHEN `unified_exception_handler(request, exc)` is called
- THEN the system SHALL return HTTP 401 with `{"error": "not_authenticated", "message": "...", "code": "AUTH_REQUIRED"}`

#### Scenario: PermissionDenied produces 403

- GIVEN a `PermissionDenied` exception
- WHEN `unified_exception_handler(request, exc)` is called
- THEN the system SHALL return HTTP 403 with `{"error": "permission_denied", "message": "...", "code": "FORBIDDEN"}`

#### Scenario: NotFound produces 404

- GIVEN a `NotFound` exception
- WHEN `unified_exception_handler(request, exc)` is called
- THEN the system SHALL return HTTP 404 with `{"error": "not_found", "code": "NOT_FOUND"}`

#### Scenario: Unexpected exception produces 500

- GIVEN an unexpected `Exception` (non-Django exception)
- WHEN `unified_exception_handler(request, exc)` is called
- THEN the system SHALL return HTTP 500 with `{"error": "internal_error", "message": "An unexpected error occurred", "code": "INTERNAL_ERROR"}` and SHALL NOT leak exception details