"""
Celery application configuration for ClínicaSaaS Dental MX.

Usage:
    celery -A config.celery worker --loglevel=info --queues=high,default,low
    celery -A config.celery beat --loglevel=info
"""

import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("clinica_dental")

# Using a string here means the worker doesn't have to serialize the config object
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Beat Schedule
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    # High priority — every 15 minutes
    "send-appointment-reminders": {
        "task": "celery_app.tasks.send_appointment_reminders",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "high"},
    },
    # Default priority — daily at 8:00 AM (Mexico City)
    "check-expiration-alerts": {
        "task": "celery_app.tasks.check_expiration_alerts",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "default"},
    },
    # Default priority — daily at 8:30 AM (Mexico City)
    "check-low-stock-alerts": {
        "task": "celery_app.tasks.check_low_stock_alerts",
        "schedule": crontab(hour=8, minute=30),
        "options": {"queue": "default"},
    },
    # Low priority — daily at midnight (Mexico City)
    "mark-expired-items": {
        "task": "celery_app.tasks.mark_expired_items",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "low"},
    },
    # Low priority — weekly Monday 9:00 AM (Mexico City)
    "send-stamp-reminder": {
        "task": "celery_app.tasks.send_stamp_reminder",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
        "options": {"queue": "low"},
    },
}

app.conf.timezone = "America/Mexico_City"
