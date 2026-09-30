"""Поле, которое сохраняет загруженную картинку сразу в WebP.

Оригинал не остаётся JPEG: он пережимается один раз при загрузке и лежит в
``media/`` как ``<читаемое-имя>.webp``. Превью из него делает ``processing``.

Форматы, которые Pillow не берёт (svg, gif), сохраняются как есть — иначе
не отрендерились бы иконки-заглушки из ``seed_catalog``.
"""

import io
from pathlib import PurePosixPath
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from PIL import Image, ImageOps

from .naming import translit_slug
from .processing import WEBP, WEBP_QUALITY, has_alpha, is_processable

MAX_STEM_LENGTH = 60
ENCODE_METHOD = 5


def readable_stem(name):
    """``Сумка красная (2).JPG`` -> ``sumka-krasnaya-2``; нечитаемое имя -> uuid."""
    stem = translit_slug(PurePosixPath(name).stem)[:MAX_STEM_LENGTH].strip("-")
    return stem or uuid4().hex


def webp_bytes(content):
    """Данные картинки в WebP либо None, если пережать её нельзя."""
    buffer = io.BytesIO()
    for chunk in content.chunks():
        buffer.write(chunk)
    buffer.seek(0)

    try:
        with Image.open(buffer) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
    except (OSError, ValueError, Image.DecompressionBombError):
        return None

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if has_alpha(image) else "RGB")
    output = io.BytesIO()
    image.save(output, WEBP, quality=WEBP_QUALITY, method=ENCODE_METHOD)
    return output.getvalue()


class WebPFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        name = name or getattr(content, "name", "")
        payload = webp_bytes(content) if is_processable(name) else None
        if payload is None:
            return super().save(name, content, save=save)
        return super().save(f"{readable_stem(name)}.{WEBP}", ContentFile(payload), save=save)


class WebPImageField(models.ImageField):
    """``ImageField``, который кладёт в хранилище WebP с читаемым именем."""

    attr_class = WebPFieldFile
