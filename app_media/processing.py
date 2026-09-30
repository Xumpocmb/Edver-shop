"""Превью и WebP-версии для загруженных изображений.

Оригиналы не переписываются: рядом с ними, в каталоге ``thumbs/``, создаются
уменьшенные копии нужных ширин в JPEG (или PNG, если у исходника есть
прозрачность) и в WebP. Шаблоны отдают их через ``srcset``/``<picture>``.

Имена производных: ``<исходник>_320.jpg``, ``<исходник>_320.webp`` — ширина
зашита в имя, чтобы в шаблонах не открывать файл через Pillow.
"""

import io
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

THUMBS_DIR = "thumbs"

WEBP_QUALITY = 88
JPEG_QUALITY = 90

WEBP = "webp"
JPEG = "jpg"
PNG = "png"

# Расширения, которые Pillow умеет пережать. Остальные (svg, gif) отдаём как есть.
PROCESSABLE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Профили — наборы ширин (в px) под конкретное место на сайте.
PROFILES = {
    # Карточки товаров, галерея, категории.
    "product": (320, 640, 1200, 2000),
    # Полноэкранный слайдер на главной.
    "slide": (768, 1280, 1920),
}

FALLBACK_FORMATS = (JPEG, PNG)


def is_processable(name):
    return bool(name) and PurePosixPath(name).suffix.lower() in PROCESSABLE_EXTENSIONS


def thumb_name(name, width, fmt):
    """Путь производной версии: ``thumbs/products/photo_320.webp``."""
    path = PurePosixPath(name)
    stem = f"{path.stem}_{width}.{fmt}"
    parent = str(path.parent)
    relative = f"{parent}/{stem}" if parent != "." else stem
    return f"{THUMBS_DIR}/{relative}"


def has_alpha(image):
    return image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)


def _load_resized(field_file, width):
    """Открывает исходник, уменьшает до ``width`` по большей стороне."""
    with Image.open(field_file) as source:
        # Полная декодировка без draft(): scaled-IDCT заметно размывает мелкие
        # детали, а превью генерируются один раз и весят немного.
        image = ImageOps.exif_transpose(source)
        image.thumbnail((width, width), Image.Resampling.LANCZOS)
        return image


def _encode(image, fmt):
    buffer = io.BytesIO()
    if fmt == WEBP:
        image.save(buffer, "WEBP", quality=WEBP_QUALITY, method=4)
    elif fmt == PNG:
        image.save(buffer, "PNG", optimize=True)
    else:
        image.convert("RGB").save(
            buffer, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True
        )
    return buffer.getvalue()


def _fallback_format(image):
    return PNG if has_alpha(image) else JPEG


def generate(field_file, profile, force=False):
    """Создаёт недостающие превью. Возвращает True, если файлы записаны."""
    name = getattr(field_file, "name", "")
    if not is_processable(name) or not field_file.storage.exists(name):
        return False

    with Image.open(field_file) as image:
        source_width = image.width
        fallback = _fallback_format(image)

    written = False
    for width in PROFILES[profile]:
        if width >= source_width:
            break  # меньшие исходники не растягиваем
        resized = _load_resized(field_file, width)
        for fmt in (fallback, WEBP):
            target = thumb_name(name, width, fmt)
            if field_file.storage.exists(target):
                if not force:
                    continue
                field_file.storage.delete(target)
            field_file.storage.save(target, ContentFile(_encode(resized, fmt)))
            written = True
        resized.close()
    return written


def delete_derivatives(field_file, profile):
    """Удаляет все превью файла (оригинал не трогаем)."""
    name = getattr(field_file, "name", "")
    if not is_processable(name):
        return
    for width in PROFILES[profile]:
        for fmt in (*FALLBACK_FORMATS, WEBP):
            target = thumb_name(name, width, fmt)
            if field_file.storage.exists(target):
                field_file.storage.delete(target)


def delete_files(field_file, profile):
    """Удаляет превью и сам оригинал.

    Оригинал общий на несколько записей, если файл привязан к ним напрямую,
    поэтому удалять его можно только когда ссылок не осталось — эту проверку
    делает вызывающий (app_media.signals).
    """
    delete_derivatives(field_file, profile)
    name = getattr(field_file, "name", "")
    if name:
        field_file.storage.delete(name)


def describe(field_file, profile):
    """URL-ы для шаблона. Ничего не генерирует — только читает существующие файлы.

    Возвращает ``src`` (самая большая fallback-версия или оригинал), ``srcset``,
    ``webp`` и список ``variants`` по возрастанию ширины.
    """
    name = getattr(field_file, "name", "")
    if not name:
        return {"src": "", "srcset": "", "webp": "", "variants": []}

    storage = field_file.storage
    result = {"src": storage.url(name), "srcset": "", "webp": "", "variants": []}
    if not is_processable(name):
        return result

    variants, webp = [], []
    for width in PROFILES[profile]:
        for fmt in FALLBACK_FORMATS:
            candidate = thumb_name(name, width, fmt)
            if storage.exists(candidate):
                variants.append(f"{storage.url(candidate)} {width}w")
                break
        candidate = thumb_name(name, width, WEBP)
        if storage.exists(candidate):
            webp.append(f"{storage.url(candidate)} {width}w")

    if not variants and not webp:
        return result
    if variants:
        result["srcset"] = ", ".join(variants)
        result["variants"] = [entry.rsplit(" ", 1)[0] for entry in variants]
        result["src"] = result["variants"][-1]
    result["webp"] = ", ".join(webp)
    return result


def preview_url(field_file, profile="product"):
    """URL самого маленького превью — для списков в админке."""
    data = describe(field_file, profile)
    variants = data.get("variants") or []
    return variants[0] if variants else data["src"]
