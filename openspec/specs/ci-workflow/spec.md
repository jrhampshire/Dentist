# ci-workflow — Test Spec

## Purpose

Infrastructure tests for `.github/workflows/ci.yml`: GitHub Actions CI pipeline behavior, job orchestration, and artifact handling.

## Requirements

### Requirement: CI workflow MUST run tests on every push and PR

The system SHALL trigger the test suite on push to main and on all PRs.

#### Scenario: Push to main triggers full test suite

- GIVEN a push to `main`
- WHEN the CI workflow runs
- THEN the full test suite SHALL execute, including unit, integration, and contract tests

#### Scenario: PR from fork triggers tests

- GIVEN a pull request from a contributor fork
- WHEN the CI workflow runs
- THEN tests SHALL execute in an isolated environment and status SHALL be reported via GitHub Checks

#### Scenario: Push to feature branch triggers unit tests only

- GIVEN a push to a feature branch `feat/my-feature`
- WHEN the CI workflow runs
- THEN `pytest -m unit` SHALL be executed to provide fast feedback

### Requirement: CI workflow MUST publish coverage reports

The system SHALL generate and publish coverage reports as a CI artifact.

#### Scenario: Coverage artifact is uploaded

- GIVEN a successful test run with `--cov`
- WHEN CI finishes
- THEN a coverage report artifact SHALL be uploaded and available in the workflow run summary

#### Scenario: Coverage threshold not met fails CI

- GIVEN `pytest --cov --cov-fail-under=80` and coverage at 65%
- WHEN CI runs
- THEN the workflow SHALL exit with status `failure`

### Requirement: CI workflow MUST isolate test environment

The system SHALL use Docker or a clean virtual environment to prevent host contamination.

#### Scenario: Tests run in Docker container

- GIVEN a Docker-based CI setup
- WHEN the CI job runs pytest
- THEN all tests SHALL execute inside the container with no access to host Python packages

#### Scenario: PostgreSQL is provisioned per job

- GIVEN CI workflow
- WHEN a test job starts
- THEN a PostgreSQL 16 instance with RLS policies SHALL be available via Docker service
