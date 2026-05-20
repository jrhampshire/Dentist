"""
Production settings for ClínicaSaaS Dental MX.

Usage:
    gunicorn config.wsgi:application --settings=config.settings.production
"""

from config.settings.base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = os.getenv(
    "PRODUCTION_ALLOWED_HOSTS", "clinica-dental.mx,www.clinica-dental.mx"
).split(",")  # noqa: F405

# CORS: production frontend only
CORS_ALLOWED_ORIGINS = [
    os.getenv("PRODUCTION_FRONTEND_URL", "https://clinica-dental.mx"),
]

# Security — all the things
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Email backend: SMTP for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True

# Use Finkok production (no sandbox)
FINKOK_SANDBOX = False
FINKOK_USERNAME = os.getenv("FINKOK_USERNAME", "")
FINKOK_PASSWORD = os.getenv("FINKOK_PASSWORD", "")

# Twilio production
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

# Sentry for error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        environment="production",
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# Production logging: JSON structured
LOGGING = {  # noqa: F405
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
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
