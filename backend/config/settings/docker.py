"""
Docker/local development settings for ClínicaSaaS Dental MX.

Usage:
    docker compose up (sets DJANGO_SETTINGS_MODULE=config.settings.docker)
"""

from config.settings.base import *  # noqa: F401,F403

DEBUG = os.getenv("DOCKER_DEBUG", "false").lower() == "true"  # noqa: F405

ALLOWED_HOSTS = os.getenv(
    "DOCKER_ALLOWED_HOSTS", "localhost,127.0.0.1,django,nginx"
).split(",")  # noqa: F405

# CORS: allow local frontend
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:80"
).split(",")

# Security — DISABLED for local Docker testing
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Email backend: console for local dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Use Finkok sandbox
FINKOK_SANDBOX = os.getenv("FINKOK_SANDBOX", "true").lower() == "true"
FINKOK_USERNAME = os.getenv("FINKOK_USERNAME", "")
FINKOK_PASSWORD = os.getenv("FINKOK_PASSWORD", "")

# Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

# Sentry disabled by default in Docker local
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Logging: simple console
LOGGING = {  # noqa: F405
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "core.middleware": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "invoicing.services": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "notifications.services": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}
