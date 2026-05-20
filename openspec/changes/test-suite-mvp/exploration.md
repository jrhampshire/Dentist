# Exploration: Test Suite — Current State

## Current State

The Dentist project has a **mature but inconsistent test suite** with 12 test files across 4 layers (unit, integration, contract, e2e) totaling ~2,900 lines. Tests cover authentication, CFDI building, encryption, Finkok SOAP, appointment slots, inventory stock, appointment/invoicing viewsets, RLS isolation, Twilio webhooks, and a full clinic E2E flow. However, several architectural issues prevent reliable execution: marker misuse (`unit` tests hitting the DB), environment coupling (`config.settings.docker` hardcoded), dead dependencies (`factory-boy`, `responses` unused), and significant coverage gaps in OAuth, PDF generation, core permissions/authentication, and model-level business logic.

## Existing Test Files Summary

| File | Layer | Lines | DB? | What It Tests | Notable Findings |
|------|-------|-------|-----|---------------|------------------|
| `test_auth_service.py` | unit | 220 | Yes | AuthService authenticate, tokens, refresh, revoke, validate | Good coverage. Uses `@pytest.mark.django_db` despite `unit` marker claiming "no DB". |
| `test_cfdi_builder.py` | unit | 272 | No | `_fmt_decimal`, `_format_cert_serial`, `_get_receptor_regimen`, `build_cfdi_xml`, `_build_cadena_original`, `encode_for_finkok` | Clean pure unit tests. Uses `MagicMock` for invoice/config. |
| `test_encryption_service.py` | unit | 174 | No | AES-256-GCM encrypt/decrypt round-trip, unicode, tampering, key mgmt | Clean pure unit tests. `set_encryption_key` fixture (autouse) sets deterministic key. |
| `test_finkok_service.py` | unit | 275 | No | FinkokService init, SOAP envelope building, response parsing, mocked HTTP stamp/cancel/status | Good coverage. Mocks `requests.post`. Disables retry logic in timeout tests. |
| `test_slot_service.py` | unit | 371 | Yes | `check_conflict`, `generate_slots_from_schedule`, `find_available_slots` | DB-dependent. Tests conflict detection, schedule generation, available slot filtering. |
| `test_stock_service.py` | unit | 304 | Yes | `adjust_stock`, `consume_kit`, `get_low_stock_items`, `get_expiring_items`, `mark_expired_items` | DB-dependent. Tests stock adjustment, kit consumption, expiration detection. |
| `test_appointment_viewset.py` | integration | 293 | Yes | Appointment conflict (409), available-slots endpoint | Uses `APIClient`. Tests POST conflict, GET available slots with filtering. |
| `test_invoice_viewset.py` | integration | 254 | Yes | Invoice stamp flow, cancel flow | Heavy mocking (`_decrypt_csd_password`, `sign_cfdi`, `FinkokService.stamp`). Tests success, failure, and state transitions. |
| `test_patient_rls_isolation.py` | integration | 318 | Yes | Patient CRUD isolation, multi-table isolation | Tests 6 of 16 claimed tables. `_setup_two_clinic_data` helper defined but never used. |
| `test_finkok_soap.py` | contract | 223 | No | Finkok SOAP request/response schema, endpoint URLs | Pure schema validation. No HTTP calls. Good contract coverage. |
| `test_twilio_webhook.py` | contract | 200 | No | Twilio signature validation, message parsing, status callback | Tests signature HMAC, keyword parsing, status mapping. No HTTP calls. |
| `test_full_clinic_flow.py` | e2e | 321 | Yes | Full flow: register → verify → onboard → patient → appointment → WhatsApp → invoice | Heavy mocking of Twilio and Finkok. Creates entities directly in some places instead of using fixtures. |

**Total: ~2,953 lines across 12 files.**

## Dependencies & Setup

### What's Needed to Run
- **PostgreSQL 16** with RLS policies enabled (integration/e2e tests require `app.current_clinic_id` session variables)
- **Python 3.12+** with dependencies from `requirements.txt`
- **Redis** (Celery broker, though not directly exercised by tests)
- **Django settings**: `config.settings.docker` is hardcoded in `pytest.ini`
- **Test runner**: `pytest` with `--reuse-db` (per `run_tests.sh`)

### Environment Notes
- The current environment **cannot run tests** — `pytest --co` fails with `ModuleNotFoundError: No module named 'django'` because dependencies are not installed in the host environment.
- Tests are designed to run inside the Docker container where Django/PostgreSQL are available.
- `run_tests.sh` manually creates a test database named `test_clinica_dental` and runs migrations before pytest. This is redundant with `pytest-django`'s built-in behavior but ensures RLS policies are applied.

### Mocking Strategy
- **External APIs fully mocked**: Finkok SOAP (unit + integration), Twilio REST API (e2e only)
- **CSD signing mocked**: `_decrypt_csd_password` and `sign_cfdi` are patched in integration tests
- **No VCR/recording**: All external API tests use hand-crafted XML/JSON strings
- **No HTTP-level contract tests for Twilio**: Only signature validation and message parsing are tested; actual HTTP sending is not contract-tested

## Issues Found

### Critical
1. **Marker misuse**: `pytest.ini` defines `unit: Unit tests (fast, no DB)`, but 4 of 6 unit test files use `@pytest.mark.django_db`. This violates the marker contract and prevents running "fast" unit tests in isolation.
2. **Environment coupling**: `pytest.ini` hardcodes `DJANGO_SETTINGS_MODULE = config.settings.docker`. Running tests outside Docker requires overriding this or creating a local settings file.
3. **Missing dependencies in host env**: Django, pytest-django, and other test deps are listed in `requirements.txt` but not installed in the current environment, making local test execution impossible without Docker or a virtualenv.

### Warning
4. **Dead dependencies**: `factory-boy>=3.3` and `responses>=0.24` are in `requirements.txt` but unused anywhere in the test suite. `conftest.py` uses hand-rolled inline factories.
5. **Incomplete RLS coverage**: `test_patient_rls_isolation.py` claims to test 16 tables but only tests 6 (patients, appointments, appointment_types, inventory_items, invoices, schedule_slots). Missing: clinics, onboarding_steps, users, refresh_tokens, clinical_notes, patient_consents, fiscal_configs, notification_logs, whatsapp_webhooks, inventory_movements.
6. **Unused helper**: `_setup_two_clinic_data` in `test_patient_rls_isolation.py` (lines 137–196) is defined but never called by any test.
7. **Twilio contract tests don't test HTTP**: `test_twilio_webhook.py` tests signature validation and parsing but never exercises the actual `TwilioService.send_message()` HTTP call. Only the e2e test mocks it.
8. **Import inconsistency**: Several test files import models inside test methods (e.g., `from appointments.models import Appointment`) instead of at module level. This is a minor anti-pattern.
9. **E2E test mixes fixture and direct creation**: `test_full_clinic_flow.py` creates the dentist user via `User.objects.create_user()` directly instead of using the `create_user` fixture, making it inconsistent with other tests.

### Suggestion
10. **No CI configuration**: No `.github/workflows/` or similar found to automate test execution.
11. **No coverage threshold**: `pytest-cov` is in requirements but no coverage config or threshold is set.
12. **No test for `Appointment.save()` auto-calculate `end_time`**: The model has logic to auto-calculate `end_time` from `appointment_type.duration_minutes`, but this is not directly tested.
13. **Missing `__init__.py` check**: All test package `__init__.py` files exist, which is good.

## Gaps in Coverage

The following modules have **zero dedicated tests**:

- **`accounts/services/oauth_service.py`** — Google/Apple OAuth2 exchange, PKCE, ID token verification, `handle_oauth_login`. Completely untested.
- **`invoicing/services/pdf_service.py`** — `generate_invoice_pdf`, `_generate_with_reportlab`, `_generate_html_fallback`. Completely untested.
- **`core/authentication.py`** — `JWTAuthentication.authenticate()`. Only exercised indirectly via integration tests; no direct unit tests.
- **`core/permissions.py`** — `IsClinicAdmin`, `IsDentist`, `IsRecepcionista`, `IsOwnerOrAdmin`, `IsAdminOrReadOnly`. Completely untested.
- **`core/exceptions.py`** — `unified_exception_handler`, `_build_error_data`. Completely untested.
- **`patients/models.py`** — `ClinicalNote.sign()`, `PatientConsent.sign()`, `Patient.delete()` (soft delete), `Patient.hard_delete()`. Not directly tested.
- **`appointments/models.py`** — `Appointment.cancel()`, `Appointment.save()` (auto-calculate `end_time`), `ScheduleSlot.clean()`. Not directly tested.
- **`invoicing/models.py`** — `Invoice.cancel()`, `Invoice.mark_cancelled()`, `Invoice.mark_stamped()`, `Invoice.mark_error()`, `Invoice.calculate_totals()`. Only exercised indirectly.
- **`inventory/models.py`** — `InventoryItem.deduct_stock()`, `InventoryItem.add_stock()`, `InventoryItem.mark_expired()`, `InventoryItem.save()` (auto-expiration), `InventoryMovement.save()` (quantity sign enforcement). Only exercised indirectly via stock_service.
- **`clinics/models.py`** — `Clinic.verify_email()`, `Clinic.generate_verification_token()`, `Clinic.complete_onboarding()`, `OnboardingStep.mark_complete()`. Only partially exercised in E2E.
- **`notifications/services/twilio_service.py`** — `TwilioService.send_message()` retry logic, HTTP error handling. Only mocked in E2E; no unit tests for the actual HTTP interaction.

## Approaches to Fix

### Approach 1: Fix Runner + True Unit Tests Split
**Description**: Fix `pytest.ini` and markers so `unit` tests are truly DB-free. Split DB-dependent tests into `integration` or create a new `db_unit` marker. Add missing pure unit tests for uncovered services.
- **Pros**: Fast feedback loop (unit tests run in <5s), clear test taxonomy, aligns with pytest-django best practices
- **Cons**: Requires refactoring some existing tests to use mocks instead of DB fixtures; moderate effort
- **Effort**: Medium

### Approach 2: Docker-First Test Environment + CI
**Description**: Keep the current Docker-centric setup, add a `pytest.ini` override for local dev (`config.settings.test`), add GitHub Actions CI that runs tests in Docker Compose, and install deps in the host environment.
- **Pros**: Minimal test code changes, ensures RLS policies are always applied, consistent with production environment
- **Cons**: Slower feedback (Docker boot time), doesn't address marker misuse or coverage gaps
- **Effort**: Low

### Approach 3: Comprehensive Coverage Push
**Description**: In addition to fixing the runner (Approach 1), write dedicated unit tests for all uncovered services (OAuth, PDF, permissions, auth, model methods) and complete the RLS isolation tests for all 16 tables.
- **Pros**: Maximizes confidence, documents behavior, prevents regressions
- **Cons**: Large effort (~800–1200 new lines of test code), may require refactoring some code to be more testable
- **Effort**: High

## Recommendation

**Combine Approach 1 + 2 as the immediate fix, then Approach 3 as follow-up.**

1. **Immediate (Low effort, high impact)**:
   - Fix `pytest.ini`: create `config.settings.test` for local dev, keep `docker` as fallback.
   - Fix markers: remove `@pytest.mark.django_db` from tests that claim to be `unit` but don't need the DB, or reclassify them.
   - Remove dead dependencies (`factory-boy`, `responses`) from `requirements.txt`.
   - Add GitHub Actions CI to run tests in Docker Compose.

2. **Short-term (Medium effort)**:
   - Add unit tests for `oauth_service.py`, `pdf_service.py`, `core/permissions.py`, `core/authentication.py`, and model methods.
   - Complete RLS isolation tests for the remaining 10 tables.
   - Add a coverage threshold (e.g., 80%) with `pytest-cov`.

3. **Long-term (High effort)**:
   - Add contract tests for `TwilioService.send_message()` using `responses` or `VCR.py`.
   - Add integration tests for notification endpoints.
   - Add performance tests for slot generation with large schedules.

## Ready for Proposal

Yes. The next phase should be `sdd-propose` to define the scope of getting the test suite passing reliably and addressing the critical marker/environment issues.
