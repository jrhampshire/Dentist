"""
Test settings for ClínicaSaaS Dental MX.

Extends base.py with overrides optimized for fast test execution:
- MD5 password hasher (faster than bcrypt/argon2)
- In-memory email backend
- In-memory cache backend
- Deterministic SECRET_KEY
- No Whitenoise (static file handling not needed for tests)

Usage:
    pytest  (reads DJANGO_SETTINGS_MODULE from pytest.ini)
"""

from config.settings.base import *  # noqa: F401,F403

# ---------------------------------------------------------------------------
# Test-specific overrides
# ---------------------------------------------------------------------------

# Deterministic secret key for reproducible test runs
SECRET_KEY = "test-secret-key-not-for-production"

# Keep DEBUG off — tests should run as close to production as possible
DEBUG = False

# Fast password hasher — MD5 is instant, no cost factor
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Capture emails in memory instead of sending them
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# In-memory cache — fastest option, no external dependency
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Middleware: remove Whitenoise (not needed for tests)
# ---------------------------------------------------------------------------

# noqa: F405 — MIDDLEWARE is imported from base.py
MIDDLEWARE = [
    m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"
]

# ---------------------------------------------------------------------------
# Static files: use default storage (Whitenoise is removed)
# ---------------------------------------------------------------------------

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
