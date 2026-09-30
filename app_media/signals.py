"""Генерация превью при сохранении модели и удаление файлов вместе с записью."""

from django.db.models.fields.files import FieldFile
from django.db.models.signals import post_delete, post_save, pre_save

from . import processing
from .registry import iter_watched

PREVIOUS_NAME_ATTR = "_app_media_previous_name"


def _stored_name(model, instance, field_name):
    if not instance.pk:
        return ""
    return model.objects.filter(pk=instance.pk).values_list(field_name, flat=True).first() or ""


def _is_referenced(model, field_name, name):
    """Файл могли привязать к нескольким записям напрямую, минуя загрузку."""
    return model._default_manager.filter(**{field_name: name}).exists()


def _drop_unused(model, field_name, profile, field_file):
    """Удаляет оригинал с превью, если ссылок на него не осталось."""
    name = getattr(field_file, "name", "")
    if not name or _is_referenced(model, field_name, name):
        return
    processing.delete_files(field_file, profile)


def _file_named(instance, field_name, name):
    """FieldFile на указанное имя — чтобы удалить файл, уже отсоединённый от поля."""
    return FieldFile(instance, instance._meta.get_field(field_name), name)


def _connect(model, field_name, profile):
    def remember_previous(instance, **kwargs):
        setattr(instance, PREVIOUS_NAME_ATTR, _stored_name(model, instance, field_name))

    def build_derivatives(sender, instance, created, **kwargs):
        field_file = getattr(instance, field_name)
        previous = getattr(instance, PREVIOUS_NAME_ATTR, "")
        if not field_file or created or field_file.name != previous:
            processing.generate(field_file, profile)
        # При замене файла старый путь уже нигде не записан, но сам он и его
        # превью остались бы на диске навсегда.
        if previous and previous != field_file.name:
            _drop_unused(model, field_name, profile, _file_named(instance, field_name, previous))

    def drop_files(sender, instance, **kwargs):
        _drop_unused(model, field_name, profile, getattr(instance, field_name, None))

    label = f"{model._meta.label_lower}.{field_name}"
    pre_save.connect(remember_previous, sender=model, weak=False, dispatch_uid=f"{label}:pre_save")
    post_save.connect(build_derivatives, sender=model, weak=False, dispatch_uid=f"{label}:post_save")
    post_delete.connect(drop_files, sender=model, weak=False, dispatch_uid=f"{label}:post_delete")


def connect():
    for model, field_name, profile in iter_watched():
        _connect(model, field_name, profile)
