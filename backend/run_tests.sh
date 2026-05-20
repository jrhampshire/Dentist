#!/bin/sh
# =============================================================================
# Run tests with reused test database (local development).
#
# DJANGO_SETTINGS_MODULE is set in pytest.ini — no export needed.
# pytest-django handles database creation and migrations automatically.
# =============================================================================

set -e

echo "Running tests..."
pytest --reuse-db "$@"
