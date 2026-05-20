# Tasks: Test Suite MVP

> [!IMPORTANT]
> 1. Tasks are ordered by dependency — Phase 1 must be complete before Phase 2.
> 2. Each task is a single file + action pair.
> 3. Verify `pytest -m unit` passes after every Phase 2 task.
> 4. Do NOT merge until all 3 phases pass the full suite.

## Phase 1: Infrastructure (5 tasks)

| # | File | Action | Details |
|---|------|--------|---------|
| 1.1 | `config/settings/test.py` | Create | [x] Extend `base.py`. Overrides: `DEBUG=False`, `PASSWORD_HASHERS=[MD5PasswordHasher]`, `EMAIL_BACKEND=locmem`, `CACHES=locmem`, deterministic `SECRET_KEY`, no Whitenoise middleware. Keep `DATABASES` from env vars. |
| 1.2 | `backend/pytest.ini` | Modify | [x] Change `DJANGO_SETTINGS_MODULE=config.settings.test`. Add coverage addopts: `--cov=backend --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-fail-under=75`. Verify markers section is intact. |
| 1.3 | `.github/workflows/ci.yml` | Create | [x] GitHub Actions workflow: trigger on push/PR to main. Postgres 16 service container. Steps: checkout, setup Python 3.12, `pip install -r backend/requirements.txt`, `pytest --cov=backend --cov-report=xml`. Upload `coverage.xml` as artifact. |
| 1.4 | `backend/run_tests.sh` | Modify | [x] Simplify to `pytest --reuse-db "$@"` with `DJANGO_SETTINGS_MODULE=config.settings.test` exported. Remove the manual Python migration script (pytest-django handles migrations). |
| 1.5 | `backend/requirements.txt` | Modify | [x] Remove `factory-boy>=3.3,<4.0` and `responses>=0.24,<1.0` (dead dependencies). |

## Phase 2: New Tests + Marker Fixes (8 tasks)

| # | File | Action | Details |
|---|------|--------|---------|
| 2.1 | `backend/tests/conftest.py` | Modify | [x] Add fixtures: `mocked_google_oauth_response` (Mock Response with `.json()`), `mocked_verify_id_token` (patch `google.oauth2.id_token.verify_oauth2_token`), `sample_invoice_data` (dict with invoice/fiscal_config fields), `mock_jwt_payload` (dict with user_id/clinic_id/role). |
| 2.2 | `backend/tests/unit/test_oauth_service.py` | Create | [x] Mock `requests.post` for token exchange + patch `google.oauth2.id_token.verify_oauth2_token`. Test: Google OAuth2 success, Apple OAuth2 with client_secret_jwt, invalid/expired code, PKCE verifier mismatch. No DB. ~150 lines. |
| 2.3 | `backend/tests/unit/test_permissions.py` | Create | [x] Direct instantiation of permission classes with mock DRF requests. Test: `IsClinicAdmin` (same/different clinic), `IsDentista`, `IsRecepcionista`, `IsOwnerOrAdmin` (owner/non-owner/admin), `IsAdminOrReadOnly` (safe/unsafe methods). No DB. ~120 lines. |
| 2.4 | `backend/tests/unit/test_authentication.py` | Create | [x] Patch `jwt.decode` to return valid payload / raise `ExpiredSignatureError` / raise `DecodeError`. Test: valid token returns (user, payload), expired returns None, malformed returns None, missing header returns None. No DB. ~80 lines. |
| 2.5 | `backend/tests/unit/test_pdf_service.py` | Create | Test `generate_invoice_pdf`: ReportLab path (verify bytes start with `%PDF-`), ImportError fallback (verify HTML contains invoice data), both paths fail (raises `PDFGenerationError`), zero line items. Mock `import` to raise ImportError for fallback. No DB. ~100 lines. |
| 2.6 | `backend/tests/unit/test_exceptions.py` | Create | Use DRF `APIRequestFactory` to create mock requests. Call `unified_exception_handler` directly. Test: ValidationError→400, NotAuthenticated→401, PermissionDenied→403, NotFound→404, unexpected Exception→500 (no leak). No DB. ~60 lines. |
| 2.7 | `backend/tests/unit/test_model_methods.py` | Create | Use existing `create_*` fixtures with `@pytest.mark.django_db`. Test: `Appointment.save()` (end_time recalc on start_time change, no recalc without change), `Patient.delete()` (soft delete sets deleted_at, excluded from queries), `Patient.hard_delete()` (permanent removal), `InventoryItem.deduct_stock()` (sufficient, insufficient→InsufficientStockError, exact zero). ~150 lines. |
| 2.8 | `backend/tests/unit/test_auth_service.py`, `test_stock_service.py`, `test_slot_service.py` | Modify | Reclassify DB-dependent tests: remove `@pytest.mark.django_db` from pure unit tests (CFDI builder, encryption, Finkok service). Move `test_auth_service.py`, `test_stock_service.py`, `test_slot_service.py` from `unit/` to `integration/` (they use DB). Update file imports accordingly. |

## Phase 3: Cleanup + Verification (2 tasks)

| # | File | Action | Details |
|---|------|--------|---------|
| 3.1 | Full test suite | Verify | Run `pytest --co` (collection succeeds), `pytest -m unit` (<10s, no DB), `pytest -m integration` (DB required), full `pytest` (all pass, coverage ≥75%). |
| 3.2 | `README.md` or `DEPLOYMENT.md` | Modify | Add test execution section: `pytest` (default), `pytest -m unit` (fast), `pytest --cov` (coverage), `./run_tests.sh` (local with reuse-db). Document marker taxonomy. |

---

## Review Workload Forecast

| Phase | Tasks | Est. Lines Changed | Files Created | Files Modified |
|-------|-------|-------------------|---------------|----------------|
| 1: Infrastructure | 5 | ~90 | 2 (test.py, ci.yml) | 3 (pytest.ini, run_tests.sh, requirements.txt) |
| 2: New Tests | 8 | ~720 | 6 (test files) | 2 (conftest.py, 3 existing tests reclassified) |
| 3: Cleanup | 2 | ~30 | 0 | 1 (README/DEPLOYMENT.md) |
| **Total** | **15** | **~840** | **8** | **6** |

**Chained PRs recommended: Yes** (840 lines > 400 threshold)

Suggested chain:
- **PR 1** (Phase 1): Infrastructure — settings, CI, deps (~90 lines)
- **PR 2** (Phase 2a): Conftest helpers + OAuth + Permissions + Auth (~370 lines)
- **PR 3** (Phase 2b): PDF + Exceptions + Model methods + Marker fixes (~350 lines)
- **PR 4** (Phase 3): Verification + docs (~30 lines)
