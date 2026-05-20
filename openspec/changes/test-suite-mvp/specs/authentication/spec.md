# authentication — Test Spec

## Purpose

Unit tests for `core/authentication.py`: JWTAuthentication.authenticate() with valid, invalid, and expired tokens.

## Requirements

### Requirement: JWTAuthentication MUST validate token signature and expiry

The system MUST verify JWT signature using the configured secret/key and SHALL reject expired or malformed tokens.

#### Scenario: Valid JWT token

- GIVEN a valid, non-expired JWT with correct signature
- WHEN `JWTAuthentication.authenticate(request)` is called
- THEN the system SHALL return a `(user, token_payload)` tuple

#### Scenario: Expired JWT token

- GIVEN a JWT with `exp` timestamp in the past
- WHEN `JWTAuthentication.authenticate(request)` is called
- THEN the system SHALL return `None` and SHALL NOT set `request.user`

#### Scenario: Malformed JWT

- GIVEN a base64-decoded but structurally invalid JWT
- WHEN `JWTAuthentication.authenticate(request)` is called
- THEN the system SHALL return `None` and SHALL NOT raise an exception

#### Scenario: Missing Authorization header

- GIVEN a request without `Authorization` header
- WHEN `JWTAuthentication.authenticate(request)` is called
- THEN the system SHALL return `None` and SHALL NOT set `request.user`