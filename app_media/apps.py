from django.apps import AppConfig


class AppMediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_media"
    verbose_name = "Обработка изображений"

    def ready(self):
        from . import signals  # noqa: F401

        signals.connect()
