"""Какие поля обрабатываются и каким профилем.

Модели указаны строками, чтобы не тянуть импорты моделей на старте приложения.
"""

from django.apps import apps as django_apps

WATCHED = (
    ("app_catalog", "ProductImage", "image", "product"),
    ("app_catalog", "Category", "image", "product"),
    ("app_home", "Slide", "image", "slide"),
)


def iter_watched():
    """Возвращает тройки (модель, имя поля, профиль)."""
    for app_label, model_name, field_name, profile in WATCHED:
        yield django_apps.get_model(app_label, model_name), field_name, profile
