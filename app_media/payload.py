"""Данные варианта для клиентской галереи (JSON, который разбирает main.js)."""

from . import processing

PROFILE = "product"


def image_payload(product_image):
    data = processing.describe(product_image.image, PROFILE)
    return {
        "src": data["src"],
        "srcset": data["srcset"],
        "webp": data["webp"],
        "alt": product_image.alt or f"{product_image.variant.product.name} {product_image.variant.color}",
    }


def variant_payload(variant):
    """Сериализует вариант: цвета, остатки и фотографии с srcset."""
    return {
        "id": variant.id,
        "name": f"{variant.product.name} {variant.color}",
        "color": variant.color,
        "hex": variant.color_hex or "#cccccc",
        "price": str(variant.price),
        "sale_price": str(variant.sale_price),
        "discount": variant.discount_percent_display,
        "stock": variant.stock,
        "status": variant.status,
        "images": [image_payload(image) for image in variant.images.all()],
    }
