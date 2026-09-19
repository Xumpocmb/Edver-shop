from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Min, Max

from .models import Product, Category


def _apply_filters(queryset, request):
    get = request.GET
    qs = queryset.filter(variants__is_active=True)

    price_from = get.get('price_from')
    price_to = get.get('price_to')
    if price_from:
        try:
            qs = qs.filter(variants__price__gte=float(price_from))
        except (TypeError, ValueError):
            pass
    if price_to:
        try:
            qs = qs.filter(variants__price__lte=float(price_to))
        except (TypeError, ValueError):
            pass
    if price_from or price_to:
        qs = qs.distinct()

    gender = get.get('gender')
    if gender in ('M', 'F'):
        qs = qs.filter(
            Q(gender=gender) | Q(gender__isnull=True)
        )

    in_stock = get.get('in_stock')
    if in_stock == '1':
        qs = qs.filter(variants__status='in_stock', variants__stock__gt=0).distinct()

    on_sale = get.get('on_sale')
    if on_sale == '1':
        qs = qs.filter(is_sale=True)

    sort = get.get('sort', 'newest')
    if sort == 'price_asc':
        qs = qs.annotate(_display_price=Min('variants__price')).order_by('_display_price', 'id')
    elif sort == 'price_desc':
        qs = qs.annotate(_display_price=Min('variants__price')).order_by('-_display_price', 'id')
    elif sort == 'popular':
        qs = qs.order_by('-sales_count', '-views_count')
    else:
        qs = qs.order_by('-created_at')
    return qs


def _get_filter_context(request, base_qs, show_gender=True):
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    price_agg = base_qs.aggregate(min_price=Min('variants__price'), max_price=Max('variants__price'))
    return {
        'categories': categories,
        'price_min': price_agg.get('min_price') or 0,
        'price_max': price_agg.get('max_price') or 0,
        'current_sort': request.GET.get('sort', 'newest'),
        'current_price_from': request.GET.get('price_from', ''),
        'current_price_to': request.GET.get('price_to', ''),
        'current_gender': request.GET.get('gender', ''),
        'in_stock_checked': request.GET.get('in_stock') == '1',
        'on_sale_checked': request.GET.get('on_sale') == '1',
        'show_gender_filter': show_gender,
    }


def _prefetch_products(qs):
    return qs.select_related('category', 'brand').prefetch_related('variants__images')


def catalog_list(request):
    qs = _prefetch_products(Product.objects.filter(is_active=True))
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    breadcrumbs = [('Каталог', None)]
    context = {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'paginator': paginator,
        'breadcrumbs': breadcrumbs,
        'page_title': 'Каталог',
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    qs = _prefetch_products(Product.objects.filter(is_active=True, category=category))
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs, show_gender=category.has_gender)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    crumbs = [('Каталог', '/catalog/'), (category.name, None)]

    context = {
        'category': category,
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'paginator': paginator,
        'breadcrumbs': crumbs,
        'page_title': category.name,
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def search_results(request):
    query = request.GET.get('q', '').strip()
    qs = _prefetch_products(Product.objects.filter(is_active=True))
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(variants__color__icontains=query)
            | Q(material__icontains=query)
        ).distinct()
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
        'products': page_obj.object_list,
        'paginator': paginator,
        'search_query': query,
        'breadcrumbs': breadcrumbs,
        'page_title': f'Поиск: {query}' if query else 'Поиск',
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('variants__images'),
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

    variants_data = [
        {
            'id': v.id,
            'name': f'{product.name} {v.color}',
            'color': v.color,
            'hex': v.color_hex or '#cccccc',
            'price': str(v.price),
            'sale_price': str(v.sale_price),
            'discount': v.discount_percent_display,
            'stock': v.stock,
            'status': v.status,
            'images': [img.image.url for img in v.images.all()],
        }
        for v in variants
    ]

    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(id=product.id).select_related('brand').prefetch_related('variants__images')[:8]

    cross_sell = Product.objects.filter(
        is_active=True, is_popular=True
    ).exclude(id=product.id).select_related('brand').prefetch_related('variants__images')[:4]

    crumbs = [('Каталог', '/catalog/')]
    crumbs.append((product.category.name, product.category.get_absolute_url()))
    crumbs.append((product.name, None))

    context = {
        'product': product,
        'variants': variants,
        'variant': selected,
        'images': images,
        'variants_data': variants_data,
        'related_products': related,
        'cross_sell_products': cross_sell,
        'breadcrumbs': crumbs,
        'page_title': product.name,
    }
    return render(request, 'app_catalog/product_detail.html', context)