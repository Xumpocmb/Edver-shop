"""JSON-LD разметка для поисковиков.

Магазин существует и офлайн (Барановичи), и как доставка по всей Беларуси,
поэтому разметка описывает и физическую точку (Store/Place), и зону продаж
(areaServed). Так сайт виден и в локальном поиске, и в обычном.
"""

import json

from django.conf import settings
from django.utils.safestring import mark_safe


def _abs(request, path):
    return request.build_absolute_uri(path)


def store_schema(request):
    """Организация/магазин: адрес, телефон, зона доставки.

    Возвращает JSON-строку, готовую для <script type="application/ld+json">.
    """
    from .models import PhoneNumber, SiteEmail, Instagram, TikTok

    site = settings.SITE
    data = {
        '@context': 'https://schema.org',
        '@type': 'Store',
        '@id': _abs(request, '/') + '#store',
        'name': site['name'],
        'url': _abs(request, '/'),
        'image': None,
        'priceRange': site['price_range'],
        'currenciesAccepted': settings.MERCHANT['currency'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': site['street'],
            'addressLocality': site['city'],
            'addressRegion': site['region'],
            'postalCode': site['postal_code'],
            'addressCountry': site['country'],
        },
        'location': {
            '@type': 'Place',
            'name': site['place'],
        },
        'geo': {
            '@type': 'GeoCoordinates',
            'latitude': site['latitude'],
            'longitude': site['longitude'],
        },
        # Доставляем по всей стране, а не только в Барановичи.
        'areaServed': {
            '@type': 'Country',
            'name': 'Беларусь',
            'identifier': site['area_served'],
        },
        'potentialAction': {
            '@type': 'SearchAction',
            'target': _abs(request, '/catalog/search/') + '?q={search_term_string}',
            'query-input': 'required name=search_term_string',
        },
    }

    phone = PhoneNumber.objects.first()
    if phone and phone.number:
        data['telephone'] = phone.number

    email = SiteEmail.objects.first()
    if email and email.email:
        data['email'] = email.email

    same_as = [
        obj.url for obj in (Instagram.objects.first(), TikTok.objects.first())
        if obj and obj.url
    ]
    if same_as:
        data['sameAs'] = same_as

    # Логотип сайта, если загружен.
    from .models import SiteLogo
    logo = SiteLogo.objects.first()
    if logo and logo.image:
        data['logo'] = _abs(request, logo.image.url)
        data['image'] = _abs(request, logo.image.url)

    data = {key: value for key, value in data.items() if value not in (None, '', [])}
    return mark_safe(json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'))


def breadcrumbs_schema(request, breadcrumbs):
    """BreadcrumbList из списка (label, url). url=None — текущий пункт."""
    if not breadcrumbs:
        return None

    items = []
    for position, (label, url) in enumerate(breadcrumbs, start=1):
        item = {
            '@type': 'ListItem',
            'position': position,
            'name': label,
        }
        if url:
            item['item'] = _abs(request, url)
        items.append(item)

    data = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': items,
    }
    return mark_safe(json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'))
