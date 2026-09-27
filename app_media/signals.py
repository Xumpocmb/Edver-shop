"""Генерация превью при сохранении модели и их удаление вместе с записью."""

from django.db.models.signals import post_delete, post_save, pre_save

from . import processing
from .registry import iter_watched

PREVIOUS_NAME_ATTR = "_app_media_previous_name"


def _stored_name(model, instance, field_name):
    if not instance.pk:
        return ""
    return model.objects.filter(pk=instance.pk).values_list(field_name, flat=True).first() or ""


def _connect(model, field_name, profile):
    def remember_previous(instance, **kwargs):
        setattr(instance, PREVIOUS_NAME_ATTR, _stored_name(model, instance, field_name))

    def build_derivatives(sender, instance, created, **kwargs):
        field_file = getattr(instance, field_name)
        previous = getattr(instance, PREVIOUS_NAME_ATTR, "")
        if not field_file or created or field_file.name != previous:
            processing.generate(field_file, profile)

    def drop_derivatives(sender, instance, **kwargs):
        processing.delete_derivatives(getattr(instance, field_name, None), profile)

    label = f"{model._meta.label_lower}.{field_name}"
    pre_save.connect(remember_previous, sender=model, weak=False, dispatch_uid=f"{label}:pre_save")
    post_save.connect(build_derivatives, sender=model, weak=False, dispatch_uid=f"{label}:post_save")
    post_delete.connect(drop_derivatives, sender=model, weak=False, dispatch_uid=f"{label}:post_delete")


def connect():
    for model, field_name, profile in iter_watched():
        _connect(model, field_name, profile)
