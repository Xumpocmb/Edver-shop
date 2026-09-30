from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Min, Max
from django.utils.html import strip_tags
from django.utils.text import Truncator

from app_media.payload import image_payload, variant_payload

from .models import Product, ProductVariant, Category


# Карточка каталога — это вариант (цвет), а не модель: у товара с тремя
# цветами выводятся три карточки. Поэтому список строится на ProductVariant,
# и ни один фильтр не джойнит многозначную связь — иначе строка размножалась бы
# по числу вариантов и товар показывался бы несколько раз.
def _variant_queryset():
    return (
        ProductVariant.objects
        .filter(is_active=True, product__is_active=True, product__category__is_active=True)
        .select_related('product', 'product__category')
        .prefetch_related('images')
    )


def _apply_filters(queryset, request):
    get = request.GET
    qs = queryset

    price_from = get.get('price_from')
    price_to = get.get('price_to')
    if price_from:
        try:
            qs = qs.filter(price__gte=float(price_from))
        except (TypeError, ValueError):
            pass
    if price_to:
        try:
            qs = qs.filter(price__lte=float(price_to))
        except (TypeError, ValueError):
            pass

    gender = get.get('gender')
    if gender in ('M', 'F'):
        qs = qs.filter(
            Q(product__gender=gender) | Q(product__gender__isnull=True)
        )

    colors = get.getlist('color')
    if colors:
        qs = qs.filter(color__in=colors)

    materials = get.getlist('material')
    if materials:
        qs = qs.filter(product__material__in=materials)

    in_stock = get.get('in_stock')
    if in_stock == '1':
        qs = qs.filter(status='in_stock', stock__gt=0)

    on_sale = get.get('on_sale')
    if on_sale == '1':
        qs = qs.filter(product__is_sale=True)

    sort = get.get('sort', 'newest')
    if sort == 'price_asc':
        qs = qs.order_by('price', 'id')
    elif sort == 'price_desc':
        qs = qs.order_by('-price', 'id')
    else:
        qs = qs.order_by('-product__created_at', 'id')
    return qs


def _get_filter_context(request, base_qs, show_gender=True):
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    price_agg = base_qs.aggregate(min_price=Min('price'), max_price=Max('price'))
    return {
        'categories': categories,
        'price_min': price_agg.get('min_price') or 0,
        'price_max': price_agg.get('max_price') or 0,
        'current_sort': request.GET.get('sort', 'newest'),
        'current_price_from': request.GET.get('price_from', ''),
        'current_price_to': request.GET.get('price_to', ''),
        'current_gender': request.GET.get('gender', ''),
        'current_colors': request.GET.getlist('color'),
        'current_materials': request.GET.getlist('material'),
        'in_stock_checked': request.GET.get('in_stock') == '1',
        'on_sale_checked': request.GET.get('on_sale') == '1',
        'show_gender_filter': show_gender,
    }


def _get_filter_options(qs):
    """Доступные для фильтрации цвета и материалы (в контексте набора товаров)."""
    colors = list(
        qs.values_list('color', flat=True)
          .distinct()
          .order_by('color')
    )
    materials = list(
        qs.exclude(product__material__isnull=True).exclude(product__material='')
          .values_list('product__material', flat=True)
          .distinct()
          .order_by('product__material')
    )
    return colors, materials


def _prefetch_products(qs):
    return qs.select_related('category').prefetch_related('variants__images')


def catalog_list(request):
    qs = _variant_queryset()
    color_options, material_options = _get_filter_options(qs)
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [('Каталог', None)]
    context = {
        'page_obj': page_obj,
        'variants': page_obj.object_list,
        'paginator': paginator,
        'breadcrumbs': breadcrumbs,
        'page_title': 'Каталог',
        'color_options': color_options,
        'material_options': material_options,
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


# Короткое описание (в т.ч. копия названия) в meta бесполезно — Google
# покажет его вместо осмысленного текста. Тогда собираем описание сами.
MIN_DESCRIPTION_LENGTH = 40
META_DESCRIPTION_LIMIT = 158


def _models_word(count):
    if count % 10 == 1 and count % 100 != 11:
        return 'модель'
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return 'модели'
    return 'моделей'


def _category_meta(category, products_count):
    """Текст для meta description страницы категории."""
    description = strip_tags(category.description).strip()
    from_admin = (
        len(description) >= MIN_DESCRIPTION_LENGTH
        and description.lower() != category.name.lower()
    )
    if from_admin:
        return Truncator(description).chars(META_DESCRIPTION_LIMIT)

    if products_count:
        tail = f'{products_count} {_models_word(products_count)} с фото и ценами'
    else:
        tail = 'модели с фото и ценами'
    return f'{category.name} в интернет-магазине EDVER Shop: {tail}, доставка по Беларуси.'


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    qs = _variant_queryset().filter(product__category=category)
    color_options, material_options = _get_filter_options(qs)
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs, show_gender=category.has_gender)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    crumbs = [('Каталог', '/catalog/'), (category.name, None)]
    products_count = Product.objects.filter(is_active=True, category=category).count()

    context = {
        'category': category,
        'page_obj': page_obj,
        'variants': page_obj.object_list,
        'paginator': paginator,
        'breadcrumbs': crumbs,
        'page_title': category.name,
        'color_options': color_options,
        'material_options': material_options,
        'meta_description': _category_meta(category, products_count),
        'og_title': f'{category.name} — EDVER Shop',
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def search_results(request):
    query = request.GET.get('q', '').strip()
    qs = _variant_queryset()
    if query:
        qs = qs.filter(
            Q(product__name__icontains=query)
            | Q(product__short_description__icontains=query)
            | Q(product__description__icontains=query)
            | Q(product__category__name__icontains=query)
            | Q(color__icontains=query)
            | Q(product__material__icontains=query)
        )
    color_options, material_options = _get_filter_options(qs)
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [
        ('Каталог', '/catalog/'),
        (f'Поиск: «{query}»' if query else 'Поиск', None),
    ]
    context = {
        'page_obj': page_obj,
        'variants': page_obj.object_list,
        'paginator': paginator,
        'search_query': query,
        'breadcrumbs': breadcrumbs,
        'page_title': f'Поиск: {query}' if query else 'Поиск',
        'color_options': color_options,
        'material_options': material_options,
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('variants__images'),
        slug=slug, is_active=True
    )

    product.views_count += 1
    product.save(update_fields=['views_count'])

    variants = [v for v in product.variants.all() if v.is_active]

    selected = None
    variant_param = request.GET.get('variant')
    if variant_param:
        for v in variants:
            if str(v.id) == variant_param:
                selected = v
                break
    if selected is None:
        selected = product.main_variant

    images = list(selected.images.all()) if selected else []

    variants_data = [variant_payload(v) for v in variants]

    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(id=product.id).prefetch_related('variants__images')[:8]

    cross_sell = Product.objects.filter(
        is_active=True, is_popular=True
    ).exclude(id=product.id).prefetch_related('variants__images')[:4]

    crumbs = [('Каталог', '/catalog/')]
    crumbs.append((product.category.name, product.category.get_absolute_url()))
    crumbs.append((product.name, None))

    context = {
        'product': product,
        'variants': variants,
        'variant': selected,
        'images': images,
        'gallery_images': [image_payload(img) for img in images],
        'variants_data': variants_data,
        'related_products': related,
        'cross_sell_products': cross_sell,
        'breadcrumbs': crumbs,
        'page_title': product.name,
        'schema_price': f'{selected.sale_price:.2f}' if selected else None,
        'has_discount': any(v.discount_percent > 0 for v in variants),
    }
    return render(request, 'app_catalog/product_detail.html', context)