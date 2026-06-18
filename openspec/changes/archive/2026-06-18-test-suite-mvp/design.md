# Design: Test Suite MVP

## Technical Approach

Fix the test runner to support both CI and local execution, then write 6 missing test files for uncovered modules. Settings split: `config.settings.docker` → `config.settings.test` as pytest default. CI via GitHub Actions with Docker Compose. Tests are pure unit (no DB) except model methods which need `@pytest.mark.django_db`.

References: proposal (approach 1+2), spec (6 domains + test-config + CI).

## Architecture Decisions

### Decision: Test Settings File

| Option | Tradeoff |
|--------|----------|
| Reuse `config.settings.docker` | Coupled to Docker env vars; breaks outside Docker |
| **Create `config/settings/test.py`** | Clean separation; extends base + overrides for fast test execution |

**Choice**: New `config/settings/test.py` extending `base.py`.
**Rationale**: Decouples test config from Docker. Overrides: MD5 hasher (faster), console email, DEBUG=False, no Whitenoise, deterministic SECRET_KEY. Keeps DATABASES from env vars so both Docker and local Postgres work.

### Decision: OAuth Mocking

| Option | Tradeoff |
|--------|----------|
| Mock at `google.auth` / `apple.auth` lib level | Tests library internals; misses `requests.post` path |
| Mock at HTTP level (`responses` lib) | Tests full code path; dead dep needs reinstating |
| **Mock `requests.post` + `google.oauth2.id_token` with `unittest.mock`** | No new deps; covers both token exchange and ID token verification |

**Choice**: Patch `requests.post` for token exchange, patch `google.oauth2.id_token.verify_oauth2_token` for ID verification.
**Rationale**: `responses` is a dead dependency slated for removal. `unittest.mock.patch` is stdlib, zero install cost, and covers both branches (success + HTTP error). The `google-auth` import is inside `verify_id_token`, so patching the module at the right scope is clean.

### Decision: PDF Testing Strategy

| Option | Tradeoff |
|--------|----------|
| Parse PDF content with PyPDF2 | Fragile; PDF layout changes break tests |
| Check PDF magic bytes + string content | Validates output without layout coupling |
| **Mock ReportLab, test HTML fallback content directly** | Fastest; spec requires both branches |

**Choice**: Verify PDF bytes start with `%PDF-` for ReportLab path; verify HTML contains invoice data for fallback path. Mock is `import`-level: patch `reportlab` import to raise `ImportError` to trigger fallback.
**Rationale**: Spec requires testing both ReportLab success and HTML fallback. Magic bytes confirm valid PDF without parsing. HTML string matching confirms fallback content. No new dependencies.

### Decision: Model Method Tests — DB Strategy

| Option | Tradeoff |
|--------|----------|
| Pure mocks (no DB) | Brittle; models have signal/save logic that mocks miss |
| **Fixtures via `tests/conftest.py`** | Consistent with existing pattern; tests real save/query behavior |

**Choice**: Use existing `create_*` fixtures from `tests/conftest.py` with `@pytest.mark.django_db`.
**Rationale**: Methods like `Appointment.save()` override `super().save()`, so they need a real DB to exercise the full code path. The conftest fixtures are already designed for this. RLS is NOT needed — these tests operate on a single clinic context within a single test transaction.

### Decision: RLS in Model Method Tests

**Choice**: Do NOT set RLS context in model method unit tests.
**Rationale**: RLS only applies to multi-tenant isolation testing (already covered by `test_patient_rls_isolation.py`). These model method tests create 1-2 objects within a single transaction — no cross-clinic data to isolate. Setting RLS would add unnecessary coupling.

### Decision: Test DB Strategy

| Option | Tradeoff |
|--------|----------|
| `--reuse-db` via `run_tests.sh` | Existing pattern; avoids re-migrating every run |
| CI-only (fresh DB each run) | Cleaner but slower; Docker Compose already handles this |
| **Both: `--reuse-db` for local, fresh DB for CI** | Best of both |

**Choice**: Keep `run_tests.sh` pattern but simplify it — just call `pytest --reuse-db` with the correct `DJANGO_SETTINGS_MODULE` set via `pytest.ini`. Remove the manual Python migration script (pytest-django handles migrations). In CI, use a fresh Postgres service + `--create-db`.

### Decision: `factory-boy` and `responses` Removal

**Choice**: Remove both from `requirements.txt`.
**Rationale**: Both are dead dependencies — zero usage in the entire test suite. Removing them cleans up the install footprint and avoids confusion.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `config/settings/test.py` | Create | Test settings: extends base, MD5 hasher, console email, deterministic SECRET_KEY |
| `pytest.ini` | Modify | `DJANGO_SETTINGS_MODULE=config.settings.test`, add coverage addopts, fix markers |
| `requirements.txt` | Modify | Remove `factory-boy`, `responses` |
| `run_tests.sh` | Modify | Simplify to `pytest --reuse-db "$@"` (remove manual migration) |
| `tests/conftest.py` | Modify | Add `mocked_google_oauth`, `mocked_reportlab_import`, `sample_invoice` helpers |
| `tests/unit/test_oauth_service.py` | Create | Mock HTTP + google-auth; test exchange, verify, PKCE, fallback |
| `tests/unit/test_permissions.py` | Create | Direct instantiation; test all 5 permission classes with mock requests |
| `tests/unit/test_authentication.py` | Create | Mock `jwt.decode`; test valid/expired/malformed/no-header |
| `tests/unit/test_pdf_service.py` | Create | Test ReportLab output (magic bytes) + ImportError fallback (HTML content) |
| `tests/unit/test_exceptions.py` | Create | Call handler directly with DRF's `APIRequestFactory`; test all exception types |
| `tests/unit/test_model_methods.py` | Create | DB fixtures; test Appointment.save, Patient.delete, InventoryItem.deduct_stock/add_stock/mark_expired, Invoice.cancel/mark_*, ClinicalNote.sign |
| `.github/workflows/ci.yml` | Create | Docker Compose CI: postgres + pytest service, coverage artifact, matrix Python 3.12 |

## Data Flow

```
[pytest] ──reads──→ pytest.ini (DJANGO_SETTINGS_MODULE=config.settings.test)
                       │
                       ▼
              config/settings/test.py ──extends──→ base.py
                       │
                       ▼
              Database: PostgreSQL (env-configured)
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
  unit (no DB)   unit (DB)     integration/e2e
  oauth_svc      model_methods existing tests
  permissions    
  authentication
  pdf_svc
  exceptions
```

## Mocking Strategy Map

| External Dependency | Mock Target | Scope |
|---------------------|-------------|-------|
| Google OAuth2 token exchange | `requests.post` → return fake JSON | Per test |
| Google ID token verification | `google.oauth2.id_token.verify_oauth2_token` → return fake claims | Per test |
| Apple token exchange | `requests.post` → return fake JSON | Per test |
| ReportLab (PDF) | `builtins.__import__` or `unittest.mock.patch('reportlab...')` raise ImportError | Per test |
| JWT decode (auth tests) | `jwt.decode` → return fake payload / raise exceptions | Per test |
| Twilio / Finkok | Not needed — no new tests touch them | N/A |

## Test Helpers (conftest.py additions)

- **`mocked_google_oauth_response`**: returns `Mock(spec=Response)` with `.json()` returning fake token/userinfo data
- **`mocked_verify_id_token`**: patches `google.oauth2.id_token.verify_oauth2_token` to return known claims dict
- **`sample_invoice_data`**: returns a dict with minimal invoice/fiscal_config fields for PDF tests (no DB needed)
- **`mock_jwt_payload`**: returns a dict with `user_id`, `clinic_id`, `role` for auth tests

Existing `create_*` fixtures in `tests/conftest.py` are reused for model method tests.

## CI Workflow

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_DB: test_db, POSTGRES_USER: dentist, POSTGRES_PASSWORD: dentist }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements.txt
      - run: pytest --cov=backend --cov-report=xml
      - uses: actions/upload-artifact@v4
        with: { name: coverage, path: coverage.xml }
```

Service containers for postgres replace Docker Compose overhead. Redis is not needed — no test exercises Celery.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (no DB) | OAuth service, permissions, authentication, exceptions, PDF service | Pure mock + assert, no DB |
| Unit (DB) | Model methods: save hooks, soft delete, stock deduction, invoice state machine | DB fixtures via conftest.py |
| CI | Full pipeline | pytest with coverage, artifact upload |

## Migration / Rollout

No migration required. Existing tests continue passing unchanged. New `config/settings/test.py` is a net addition — doesn't affect `docker.py` or `base.py`.

## Open Questions

- None. All specs are covered, all decisions have rationale.
