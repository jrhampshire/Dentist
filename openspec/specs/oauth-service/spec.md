# oauth-service — Test Spec

## Purpose

Unit tests for `accounts/services/oauth_service.py`: Google/Apple OAuth2 exchange, PKCE validation, ID token verification, and `handle_oauth_login`.

## Requirements

### Requirement: OAuth2 token exchange SHALL validate provider response

The system SHALL validate Google/Apple OAuth2 token exchange responses before establishing sessions.

#### Scenario: Google OAuth2 success flow

- GIVEN valid Google OAuth data (email, oauth_id)
- WHEN `GoogleOAuthService.exchange_code(code, code_verifier, redirect_uri)` is called
- THEN the system exchanges the code for tokens, verifies the ID token via `verify_id_token`, and returns the token response

- GIVEN a verified Google user
- WHEN `handle_oauth_login("google", email, oauth_id, first_name, last_name)` is called
- THEN the system finds or creates the user, links OAuth credentials, and returns JWT tokens

#### Scenario: Apple OAuth2 with client_secret_jwt

- GIVEN valid Apple OAuth data (email, oauth_id)
- WHEN `AppleOAuthService.exchange_code(code, code_verifier, redirect_uri)` is called
- THEN the system exchanges the code using client_secret_jwt assertion and returns the token response

- GIVEN a verified Apple user
- WHEN `handle_oauth_login("apple", email, oauth_id, first_name, last_name)` is called
- THEN the system finds or creates the user, links OAuth credentials, and returns JWT tokens

#### Scenario: Invalid or expired authorization code

- GIVEN an expired or malformed authorization code
- WHEN `GoogleOAuthService.exchange_code()` or `AppleOAuthService.exchange_code()` is called
- THEN the system SHALL raise `ValueError` with a descriptive message and SHALL NOT create a session

### Requirement: PKCE verification MUST be enforced

The system MUST verify PKCE challenge/verifier for all OAuth2 flows to prevent authorization code interception.

#### Scenario: PKCE verifier mismatch

- GIVEN a code_verifier that does not match the originally sent code_challenge
- WHEN `handle_oauth_login` is called
- THEN the system SHALL raise `ValueError` and SHALL NOT complete the exchange
