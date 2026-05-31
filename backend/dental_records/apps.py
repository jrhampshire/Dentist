from django.apps import AppConfig


class DentalRecordsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dental_records"
    verbose_name = "Expediente Clínico (Odontograma)"

    def ready(self):
        import dental_records.signals  # noqa: F401
