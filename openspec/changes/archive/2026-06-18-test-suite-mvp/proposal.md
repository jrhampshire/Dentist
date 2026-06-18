# Test Suite MVP — Proposal

**Change ID**: `test-suite-mvp`  
**Project**: `dentist`  
**Phase**: `sdd-propose`  
**Date**: 2026-05-19  
**Status**: Ready for spec

---

## Executive Summary

This proposal defines the scope to get the Dentist project's test suite into a **reliable, runnable state** with clear execution paths for both local development and CI/CD. The work addresses critical issues identified in the exploration phase: marker misuse, environment coupling, dead dependencies, and coverage gaps.

**Goal**: Enable developers to run tests confidently with fast feedback for unit tests and reliable execution for integration/e2e tests in Docker.

---

## Problem Statement

The current test suite (12 files, ~2,900 lines) has architectural issues preventing reliable execution:

1. **Marker misuse**: `unit` tests claim "no DB" but 4 of 6 use `@pytest.mark.django_db`
2. **Environment coupling**: `pytest.ini` hardcodes `config.settings.docker` — no local dev option
3. **Dead dependencies**: `factory-boy` and `responses` listed but unused
4. **No CI workflow**: No GitHub Actions or automated test execution
5. **Coverage gaps**: OAuth, PDF generation, permissions, authentication have zero dedicated tests
6. **No coverage threshold**: `pytest-cov` installed but not configured

---

## In Scope

### 1. Fix `pytest.ini` Configuration

**Current state**:
```ini
DJANGO_SETTINGS_MODULE = config.settings.docker
```

**Proposed fix**:
```ini
DJANGO_SETTINGS_MODULE = config.settings.test
```

**Actions**:
- Create `config/settings/test.py` extending `dev.py` with test-specific overrides
- Keep `docker.py` as fallback for Docker Compose execution
- Add pytest-cov configuration with thresholds

**Test settings should include**:
- `DEBUG = False` (catch template/permission issues)
- `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]` (faster tests)
- `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` (no console spam)
- `CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}`
- Coverage configuration: `--cov=backend --cov-report=term-missing --cov-fail-under=75`

### 2. Fix Test Markers

**Current issue**: Tests marked as `unit` but use database.

**Proposed taxonomy**:
- `unit`: Pure unit tests (no DB) — e.g., `test_cfdi_builder.py`, `test_encryption_service.py`, `test_finkok_service.py`
- `integration`: DB-dependent tests — e.g., `test_auth_service.py`, `test_slot_service.py`, `test_stock_service.py`
- `contract`: External API schema validation — e.g., `test_finkok_soap.py`, `test_twilio_webhook.py`
- `e2e`: Full flow tests — e.g., `test_full_clinic_flow.py`

**Actions**:
- Remove `@pytest.mark.django_db` from true unit tests (CFDI builder, encryption, Finkok service)
- Reclassify DB-dependent "unit" tests to `integration` layer
- Update docstrings and comments to reflect correct layer

### 3. Create GitHub Actions CI Workflow

**File**: `.github/workflows/ci.yml`

**Workflow should**:
- Trigger on: `push: main`, `pull_request: main`
- Run in Docker Compose (consistent with production)
- Build backend container
- Run migrations
- Execute pytest with coverage
- Upload coverage artifact to GitHub Actions
- Fail if coverage < 75%

**Example structure**:
```yaml
name: Test Suite
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_clinica_dental
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker Compose
        run: docker compose build backend
      - name: Run migrations
        run: docker compose run backend python manage.py migrate
      - name: Run tests
        run: docker compose run backend pytest --cov --cov-fail-under=75
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: backend/coverage.xml
```

### 4. Add Unit Tests for Coverage Gaps

**Priority modules** (zero test coverage):

| Module | Priority | Estimated Lines | What to Test |
|--------|----------|----------------|--------------|
| `accounts/services/oauth_service.py` | High | ~150 | Google/Apple OAuth2 exchange, PKCE, ID token verification, `handle_oauth_login` |
| `core/permissions.py` | High | ~120 | `IsClinicAdmin`, `IsDentista`, `IsRecepcionista`, `IsOwnerOrAdmin`, `IsAdminOrReadOnly` |
| `core/authentication.py` | High | ~80 | `JWTAuthentication.authenticate()` with valid/invalid/expired tokens |
| `invoicing/services/pdf_service.py` | Medium | ~100 | `generate_invoice_pdf`, fallback to HTML generation |
| `core/exceptions.py` | Medium | ~60 | `unified_exception_handler`, error response formatting |
| Model methods | Medium | ~150 | `Appointment.save()` (auto end_time), `Patient.delete()` (soft delete), `InventoryItem.deduct_stock()` |

**Total estimated**: ~660 new lines of test code across 6 new test files.

### 5. Configure pytest-cov with Threshold

**In `pytest.ini`**:
```ini
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=backend
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=75
```

**Initial threshold**: 75% (realistic given current gaps)  
**Future target**: 85% (after RLS isolation tests added)

### 6. Remove Dead Dependencies

**Remove from `requirements.txt`**:
- `factory-boy>=3.3,<4.0` — unused (inline factories in `conftest.py`)
- `responses>=0.24,<1.0` — unused (manual mocking with `MagicMock`)

**Add to `requirements.txt`** (if not present):
- `pytest-xdist>=3.5` — optional: parallel test execution for faster CI

---

## Out of Scope

Explicitly **deferred** to keep this MVP focused:

1. **Full RLS isolation tests for all 16 tables** — Current tests cover 6 tables; remaining 10 tables (clinics, onboarding_steps, users, refresh_tokens, clinical_notes, patient_consents, fiscal_configs, notification_logs, whatsapp_webhooks, inventory_movements) deferred to `test-suite-rls-complete` change.

2. **Contract tests for Twilio HTTP sending** — Current tests validate signature and parsing; actual HTTP call testing deferred to `test-suite-contract` change.

3. **Performance tests** — Slot generation with large schedules, deferred to `test-suite-performance` change.

4. **VCR.py integration** — HTTP recording/playback, deferred until contract tests are in scope.

---

## Deliverables

### Files to Create

| File | Purpose | Layer |
|------|---------|-------|
| `config/settings/test.py` | Test-specific Django settings | Config |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow | CI/CD |
| `tests/unit/test_oauth_service.py` | OAuth service unit tests | Unit |
| `tests/unit/test_permissions.py` | Permission classes unit tests | Unit |
| `tests/unit/test_authentication.py` | JWT authentication unit tests | Unit |
| `tests/unit/test_pdf_service.py` | PDF generation unit tests | Unit |
| `tests/unit/test_exceptions.py` | Exception handler unit tests | Unit |
| `tests/unit/test_model_methods.py` | Model method unit tests | Unit |

### Files to Modify

| File | Change | Reason |
|------|--------|--------|
| `pytest.ini` | Change `DJANGO_SETTINGS_MODULE` to `config.settings.test`; add coverage config | Fix environment coupling, add coverage |
| `requirements.txt` | Remove `factory-boy`, `responses` | Dead dependencies |
| `tests/unit/test_auth_service.py` | Remove `@pytest.mark.django_db` if pure unit, or reclassify to integration | Fix marker misuse |
| `tests/unit/test_slot_service.py` | Reclassify to integration (DB-dependent) | Fix marker misuse |
| `tests/unit/test_stock_service.py` | Reclassify to integration (DB-dependent) | Fix marker misuse |

---

## Acceptance Criteria

- [ ] `pytest --co` runs successfully without `ModuleNotFoundError`
- [ ] `pytest -m unit` runs in <10 seconds with no DB access
- [ ] `pytest -m integration` runs with full DB access and RLS policies
- [ ] CI workflow executes on PR to `main` and blocks merge if tests fail
- [ ] Coverage report shows ≥75% overall coverage
- [ ] All 12 existing test files pass
- [ ] 6 new unit test files added for coverage gaps
- [ ] Dead dependencies removed from `requirements.txt`
- [ ] Documentation updated: `README.md` or `DEPLOYMENT.md` includes test execution instructions

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| RLS policies not applied in CI | Integration tests fail | Use Docker Compose with PostgreSQL 16, run migrations before tests |
| Coverage threshold too high initially | CI fails on first run | Start at 75%, adjust after baseline established |
| OAuth tests require external setup | Tests flaky or fail | Fully mock Google/Apple OAuth2 responses; no real HTTP calls |
| PDF generation tests platform-dependent | Font/path issues | Use ReportLab's built-in fonts; mock file system writes |

---

## Effort Estimate

| Task | Effort | Notes |
|------|--------|-------|
| Create `test.py` settings | 0.5 hours | Extend `dev.py`, add test-specific overrides |
| Fix `pytest.ini` + markers | 1 hour | Update config, reclassify 3-4 test files |
| Create GitHub Actions workflow | 1 hour | Docker Compose setup, coverage upload |
| Write OAuth service tests | 2 hours | Mock OAuth2 flow, token verification |
| Write permissions tests | 1.5 hours | Test each permission class with various user roles |
| Write authentication tests | 1 hour | JWT encode/decode, expiration, invalid tokens |
| Write PDF service tests | 1.5 hours | Mock ReportLab, verify PDF generation |
| Write exception handler tests | 0.5 hours | Test error response formatting |
| Write model method tests | 2 hours | Test 5-6 key model methods |
| Remove dead dependencies | 0.5 hours | Update `requirements.txt`, verify no breakage |
| **Total** | **~11 hours** | ~1.5 working days |

---

## Success Metrics

1. **Developer experience**: `pytest` runs out-of-the-box with no manual config
2. **CI reliability**: Tests pass/fail deterministically in GitHub Actions
3. **Coverage visibility**: Coverage report generated on every run
4. **Fast feedback**: Unit tests complete in <10 seconds
5. **Documentation**: Clear test execution instructions in README

---

## Next Phase

**Recommended**: `sdd-spec` to write detailed test scenarios and acceptance tests for each new unit test file.

**Alternative**: `sdd-design` if architectural decisions need deeper exploration (e.g., mocking strategy for OAuth2, PDF generation testing approach).

---

## References

- Exploration artifact: `sdd/test-suite-mvp/explore` (observation #683)
- Existing test suite: `backend/tests/` (12 files, ~2,900 lines)
- Django testing best practices: https://docs.djangoproject.com/en/5.0/topics/testing/
- pytest-django documentation: https://pytest-django.readthedocs.io/

---

*Generated by SDD propose phase for change `test-suite-mvp`*
