"""Сборка YML-фида товаров для Яндекс Маркета."""

import re
from urllib.parse import urljoin, urlparse

import yaml
from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator, slugify

from .models import Product, ProductVariant

MAX_PICTURES = 15
MAX_DESCRIPTION = 3000
MAX_NAME = 500


def _absolute(url):
    return urljoin(settings.FEED['site_url'], url)


def _active_products():
    """Товары на витрине вместе с активными вариантами и их фото."""
    variants = (
        ProductVariant.objects
        .filter(is_active=True)
        .prefetch_related('images')
        .order_by('order', 'id')
    )
    return (
        Product.objects
        .filter(is_active=True, category__is_active=True, variants__is_active=True)
        .select_related('category')
        .prefetch_related(Prefetch('variants', queryset=variants))
        .order_by('id')
        .distinct()
    )


def _pictures(variant):
    """Картинки варианта в абсолютных URL, только в форматах Яндекса."""
    allowed = settings.FEED['picture_extensions']
    urls = []
    for image in variant.images.all():
        url = _absolute(image.image.url)
        extension = urlparse(url).path.rsplit('.', 1)[-1].lower()
        if f'.{extension}' not in allowed:
            continue
        if url not in urls:
            urls.append(url)
    return urls[:MAX_PICTURES]


def _clean_text(text, limit):
    """Текст без HTML в одну строку, обрезанный до лимита Яндекса.

    Теги заменяем пробелами, иначе соседние абзацы склеиваются
    («...хлопка</p><p>Большая» → «хлопкаБольшая»).
    """
    plain = strip_tags(re.sub(r'<[^>]+>', ' ', text or ''))
    return ' '.join(plain.split())[:limit].strip()


def _params(product, variant):
    pairs = [
        ('Материал', product.material),
        ('Пол', product.get_gender_display() if product.gender else ''),
        ('Цвет', variant.color),
        ('Размеры', product.dimensions),
    ]
    return [{'name': name, 'value': value} for name, value in pairs if value]


def _offer(product, variant):
    offer = {
        'id': str(variant.pk),
        'vendorCode': f'{product.slug}-{slugify(variant.color, allow_unicode=True)}',
        'name': Truncator(f'{product.name}, {variant.color}').chars(MAX_NAME),
        'url': _absolute(product.get_absolute_url()),
        'price': float(variant.sale_price),
        'currencyId': settings.FEED['currency'],
        'categoryId': product.category.market_category_id or product.category.slug,
        'available': variant.status != 'out_of_stock' and variant.stock > 0,
    }

    pictures = _pictures(variant)
    if pictures:
        offer['picture'] = pictures

    description = _clean_text(product.description, MAX_DESCRIPTION)
    if not description:
        description = _clean_text(product.short_description, MAX_DESCRIPTION)
    if description:
        offer['description'] = description

    if product.weight:
        offer['weight'] = float(product.weight)

    params = _params(product, variant)
    if params:
        offer['param'] = params

    return offer


def _offers(products):
    return [
        _offer(product, variant)
        for product in products
        for variant in product.variants.all()
    ]


def _categories(products):
    """Категории фида. В магазине все категории плоские, без родителей."""
    categories = {}
    for product in products:
        category = product.category
        categories.setdefault(
            category.pk,
            {'id': category.market_category_id or category.slug, 'name': category.name},
        )
    return list(categories.values())


def _catalog(products, offers):
    feed = settings.FEED
    return {
        'date': timezone.localtime(timezone.now()).isoformat(timespec='seconds'),
        'shop': {
            'name': feed['shop_name'],
            'company': feed['company_name'],
            'url': feed['site_url'],
        },
        'vendor': {
            'name': feed['vendor_name'],
            'url': feed['site_url'],
        },
        'currencies': [{'code': feed['currency'], 'rate': 1}],
        'categories': _categories(products),
        'offers': offers,
    }


def build_feed():
    """Возвращает (текст YML, статистика сборки)."""
    products = list(_active_products())
    offers = _offers(products)
    stats = {
        'products': len(products),
        'offers': len(offers),
        'offers_without_picture': sum(1 for offer in offers if not offer.get('picture')),
        'categories_without_market_id': sorted({
            product.category.name
            for product in products
            if not product.category.market_category_id
        }),
    }
    catalog = _catalog(products, offers)
    text = yaml.safe_dump(
        catalog,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )
    return text, stats
