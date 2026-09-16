from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Min, Max
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Product, Category, Brand, ProductReview, ProductVariant


def _apply_filters(queryset, request):
    get = request.GET
    price_from = get.get('price_from')
    price_to = get.get('price_to')
    if price_from:
        try:
            queryset = queryset.filter(price__gte=float(price_from))
        except (TypeError, ValueError):
            pass
    if price_to:
        try:
            queryset = queryset.filter(price__lte=float(price_to))
        except (TypeError, ValueError):
            pass

    brands = get.getlist('brands')
    if brands:
        queryset = queryset.filter(brand__slug__in=brands)

    in_stock = get.get('in_stock')
    if in_stock == '1':
        queryset = queryset.filter(status='in_stock', stock__gt=0)

    on_sale = get.get('on_sale')
    if on_sale == '1':
        queryset = queryset.filter(is_sale=True)

    colors = get.getlist('colors')
    if colors:
        q_colors = Q()
        for c in colors:
            q_colors |= Q(color__iexact=c)
        queryset = queryset.filter(q_colors)

    sort = get.get('sort', 'newest')
    if sort == 'price_asc':
        queryset = queryset.order_by('price')
    elif sort == 'price_desc':
        queryset = queryset.order_by('-price')
    elif sort == 'popular':
        queryset = queryset.order_by('-sales_count', '-views_count')
    else:
        queryset = queryset.order_by('-created_at')
    return queryset


def _get_filter_context(request, base_qs):
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True, parent=None).prefetch_related('children')
    price_agg = base_qs.aggregate(min_p=Avg('price') * 0, max_p=Avg('price') * 0)
    if base_qs.exists():
        price_agg = base_qs.aggregate(Min('price'), Max('price'))
    colors = sorted(
        [c for c in base_qs.values_list('color', flat=True).distinct() if c]
    )
    return {
        'brands': brands,
        'categories': categories,
        'price_min': price_agg.get('price__min', 0) or 0,
        'price_max': price_agg.get('price__max', 0) or 0,
        'colors': colors,
        'current_sort': request.GET.get('sort', 'newest'),
        'current_price_from': request.GET.get('price_from', ''),
        'current_price_to': request.GET.get('price_to', ''),
        'current_brands': request.GET.getlist('brands'),
        'current_colors': request.GET.getlist('colors'),
        'in_stock_checked': request.GET.get('in_stock') == '1',
        'on_sale_checked': request.GET.get('on_sale') == '1',
    }


def catalog_list(request):
    qs = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
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
        'total_count': paginator.count,
        'breadcrumbs': breadcrumbs,
        'page_title': 'Каталог',
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    cat_ids = category.get_descendants_ids()
    qs = Product.objects.filter(
        is_active=True, category_id__in=cat_ids
    ).select_related('category', 'brand').prefetch_related('images')
    qs = _apply_filters(qs, request)
    ctx = _get_filter_context(request, qs)

    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    crumbs = [('Каталог', '/catalog/')]
    c = category
    chain = []
    while c:
        chain.append(c)
        c = c.parent
    for cat in reversed(chain):
        crumbs.append((cat.name, cat.get_absolute_url()))

    context = {
        'category': category,
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'paginator': paginator,
        'total_count': paginator.count,
        'breadcrumbs': crumbs,
        'page_title': category.name,
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def search_results(request):
    query = request.GET.get('q', '').strip()
    qs = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__name__icontains=query)
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
        'total_count': paginator.count,
        'search_query': query,
        'breadcrumbs': breadcrumbs,
        'page_title': f'Поиск: {query}' if query else 'Поиск',
    }
    context.update(ctx)
    return render(request, 'app_catalog/catalog.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('images', 'variants'),
        slug=slug, is_active=True
    )

    product.views_count += 1
    product.save(update_fields=['views_count'])

    reviews = product.reviews.filter(is_approved=True)[:10]
    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(id=product.id).select_related('brand').prefetch_related('images')[:8]

    cross_sell = Product.objects.filter(
        is_active=True, is_popular=True
    ).exclude(id=product.id).select_related('brand').prefetch_related('images')[:4]

    variants = product.variants.filter(is_active=True).prefetch_related(
        'attribute_values__attribute'
    )

    variant_attrs = {}
    for v in variants:
        for av in v.attribute_values.select_related('attribute'):
            attr_name = av.attribute.name
            if attr_name not in variant_attrs:
                variant_attrs[attr_name] = []
            if av.value not in [x['value'] for x in variant_attrs[attr_name]]:
                variant_attrs[attr_name].append({
                    'value': av.value,
                    'variant_ids': [],
                })
            for item in variant_attrs[attr_name]:
                if item['value'] == av.value:
                    item['variant_ids'].append(v.id)

    crumbs = [('Каталог', '/catalog/')]
    c = product.category
    chain = []
    while c:
        chain.append(c)
        c = c.parent
    for cat in reversed(chain):
        crumbs.append((cat.name, cat.get_absolute_url()))
    crumbs.append((product.name, None))

    review_form_data = None

    context = {
        'product': product,
        'images': product.images.all(),
        'reviews': reviews,
        'related_products': related,
        'cross_sell_products': cross_sell,
        'breadcrumbs': crumbs,
        'page_title': product.name,
        'variants': variants,
        'variant_attrs': variant_attrs,
    }
    return render(request, 'app_catalog/product_detail.html', context)


@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    rating = request.POST.get('rating', 5)
    title = request.POST.get('title', '').strip()
    text = request.POST.get('text', '').strip()
    pros = request.POST.get('pros', '').strip()
    cons = request.POST.get('cons', '').strip()

    errors = []
    if not name:
        errors.append('Введите ваше имя.')
    if not email:
        errors.append('Введите email.')
    if not text:
        errors.append('Напишите текст отзыва.')

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except (TypeError, ValueError):
        rating = 5

    if errors:
        messages.error(request, ' '.join(errors))
        return redirect(product.get_absolute_url() + '#reviews')

    ProductReview.objects.create(
        product=product,
        name=name,
        email=email,
        rating=rating,
        title=title,
        text=text,
        pros=pros,
        cons=cons,
        is_approved=False,
    )
    messages.success(request, 'Спасибо! Ваш отзыв отправлен на модерацию.')
    return redirect(product.get_absolute_url() + '#reviews')
