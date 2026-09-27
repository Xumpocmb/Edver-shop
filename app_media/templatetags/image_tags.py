from django import template

from app_media import processing
from app_media.payload import variant_payload

register = template.Library()


@register.inclusion_tag("app_media/_responsive_image.html")
def responsive_image(
    field_file,
    profile,
    alt="",
    classes="",
    sizes=None,
    loading="lazy",
    fetchpriority=None,
    image_id="",
):
    """<picture> с превью и WebP; без превью отдаёт исходный <img>."""
    data = processing.describe(field_file, profile) if field_file else {}
    return {
        "src": data["src"],
        "srcset": data["srcset"],
        "webp": data["webp"],
        "alt": alt,
        "classes": classes,
        "sizes": sizes,
        "loading": loading,
        "fetchpriority": fetchpriority,
        "image_id": image_id,
    }


@register.inclusion_tag("app_media/_slide_background.html")
def slide_background(slide):
    """Фон слайдера: <picture> с превью либо исходная картинка."""
    image = slide.image
    data = processing.describe(image, "slide") if image else {"src": "", "srcset": "", "webp": ""}
    return {
        "image": image,
        "src": data["src"],
        "srcset": data["srcset"],
        "webp": data["webp"],
    }
