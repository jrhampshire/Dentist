# test-config — Test Spec

## Purpose

Infrastructure tests for `pytest.ini` configuration: DJANGO_SETTINGS_MODULE, coverage config, and marker conventions.

## Requirements

### Requirement: pytest.ini MUST set DJANGO_SETTINGS_MODULE for test environment

The system SHALL configure the Django settings module to ensure consistent test environment.

#### Scenario: Default test run uses configured settings

- GIVEN `pytest.ini` with `DJANGO_SETTINGS_MODULE=config.settings.test`
- WHEN `pytest` is invoked without `--settings`
- THEN Django SHALL use `config.settings.test`

#### Scenario: DJANGO_SETTINGS_MODULE is overridable via CLI

- GIVEN `pytest.ini` with `DJANGO_SETTINGS_MODULE=config.settings.test`
- WHEN `pytest --settings=config.settings.docker` is invoked
- THEN Django SHALL use `config.settings.docker`

#### Scenario: Coverage config is applied

- GIVEN `pytest.ini` with `addopts = --cov=backend --cov-report=term-missing`
- WHEN `pytest` is invoked
- THEN coverage data SHALL be collected for the `backend` package and a term-missing report SHALL be generated

### Requirement: pytest markers MUST be correctly applied

The system SHALL enforce that `unit` marker tests do NOT use the database.

#### Scenario: unit marker test does not access database

- GIVEN a test file with `@pytest.mark.unit`
- WHEN `pytest -m unit --collect-only` is run
- THEN no collected test SHALL require a database transaction

#### Scenario: unit marker runs in isolation

- GIVEN a test file with `@pytest.mark.unit`
- WHEN `pytest -m unit` is run
- THEN the test SHALL complete in under 5 seconds

### Requirement: Coverage threshold MUST be configurable

The system SHALL support a minimum coverage threshold via pytest.ini or pytest-cov configuration.

#### Scenario: Coverage below threshold fails the run

- GIVEN `pytest.ini` with `--cov-fail-under=80`
- WHEN pytest exits with coverage below 80%
- THEN the run SHALL exit with a non-zero status code
