from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "appointments"
    verbose_name = "Appointment Scheduling"

    def ready(self):
        import appointments.signals  # noqa: F401
