# oauth-service — Test Spec

## Purpose

Unit tests for `accounts/services/oauth_service.py`: Google/Apple OAuth2 exchange, PKCE validation, ID token verification, and `handle_oauth_login`.

## Requirements

### Requirement: OAuth2 token exchange SHALL validate provider response

The system SHALL validate Google/Apple OAuth2 token exchange responses before establishing sessions.

#### Scenario: Google OAuth2 success flow

- GIVEN a valid Google authorization code and PKCE verifier
- WHEN `handle_oauth_login("google", code, code_verifier)` is called
- THEN the system exchanges the code for tokens, verifies the ID token signature using Google's JWKS endpoint, extracts the user email, and creates/returns a valid JWT session

#### Scenario: Apple OAuth2 with client_secret_jwt

- GIVEN a valid Apple authorization code and a signed client_secret_jwt
- WHEN `handle_oauth_login("apple", code, code_verifier)` is called
- THEN the system exchanges the code using client_secret_jwt assertion, verifies the ID token against Apple's /auth-keys endpoint, and returns a valid session

#### Scenario: Invalid or expired authorization code

- GIVEN an expired or malformed authorization code
- WHEN `handle_oauth_login` is called
- THEN the system SHALL raise `AuthenticationError` with a descriptive message and SHALL NOT create a session

### Requirement: PKCE verification MUST be enforced

The system MUST verify PKCE challenge/verifier for all OAuth2 flows to prevent authorization code interception.

#### Scenario: PKCE verifier mismatch

- GIVEN a code_verifier that does not match the originally sent code_challenge
- WHEN `handle_oauth_login` is called
- THEN the system SHALL raise `AuthenticationError` and SHALL NOT complete the exchange