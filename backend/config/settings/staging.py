"""
Staging settings for ClínicaSaaS Dental MX.

Usage:
    gunicorn config.wsgi:application --settings=config.settings.staging
"""

from config.settings.base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = os.getenv("STAGING_ALLOWED_HOSTS", "staging.clinica-dental.mx").split(
    ","
)  # noqa: F405

# CORS: staging frontend only
CORS_ALLOWED_ORIGINS = [
    os.getenv("STAGING_FRONTEND_URL", "https://staging.clinica-dental.mx"),
]

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email backend: SMTP for staging
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True

# Use Finkok sandbox in staging
FINKOK_SANDBOX = True
FINKOK_USERNAME = os.getenv("FINKOK_USERNAME", "")
FINKOK_PASSWORD = os.getenv("FINKOK_PASSWORD", "")

# Twilio sandbox
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

# Sentry for error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment="staging",
        traces_sample_rate=0.5,
        send_default_pii=False,
    )
