#!/bin/sh
# =============================================================================
# Run tests with test database setup
# =============================================================================

set -e

# Create and migrate test database
echo "Setting up test database..."
python -c "
from django.conf import settings
settings.DATABASES['default']['NAME'] = 'test_clinica_dental'
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=1)
"

# Run pytest with reused database
echo "Running tests..."
pytest "$@" --reuse-db
