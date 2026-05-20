"""
Development settings for ClínicaSaaS Dental MX.

Usage:
    python manage.py runserver --settings=config.settings.dev
"""

from config.settings.base import *  # noqa: F401,F403
from config.settings.base import INSTALLED_APPS, LOGGING

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "django"]

# CORS: allow all origins in dev
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_ALL_ORIGINS = True

# Email backend: console (no real emails in dev)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable security middleware features in dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Faster password hasher for dev
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Logging: more verbose in dev
LOGGING["loggers"]["django"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["core.middleware"]["level"] = "DEBUG"  # noqa: F405

# Disable WhiteNoise in dev (use runserver static files)
MIDDLEWARE.remove("whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# Disable production apps that aren't needed in dev
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:  # noqa: F405
    pass  # already removed
