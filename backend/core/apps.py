from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core Infrastructure"

    def ready(self):
        """Register signals when the app is ready."""
        import core.signals  # noqa: F401
