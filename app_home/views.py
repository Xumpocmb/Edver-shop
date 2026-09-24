from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from app_catalog.models import Product, Category
from .models import Advantage, SiteReview, Slide, StaticPage


def home(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants__images')

    popular = products.filter(is_popular=True)[:8]
    new_products = products.filter(is_new=True)[:8]
    sale = products.filter(is_sale=True)[:8]

    categories = Category.objects.filter(
        is_active=True
    ).order_by('order', 'name')[:8]

    slides = Slide.objects.filter(is_active=True)

    context = {
        'slides': slides,
        'popular_products': popular,
        'new_products': new_products,
        'sale_products': sale,
        'categories': categories,
    }
    return render(request, 'app_home/home.html', context)


def about(request):
    advantages = Advantage.objects.filter(is_active=True).values_list('icon', 'title', 'text')
    page = StaticPage.objects.filter(slug='about', is_published=True).first()

    context = {
        'advantages': advantages,
        'page': page,
    }
    return render(request, 'app_home/about.html', context)


def contacts(request):
    return render(request, 'app_home/contacts.html')


def site_reviews(request):
    reviews = SiteReview.objects.filter(is_published=True)[:20]

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        text = request.POST.get('text', '').strip()
        rating = request.POST.get('rating')

        if name and text and rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    SiteReview.objects.create(
                        name=name,
                        text=text,
                        rating=rating,
                    )
                    messages.success(request, 'Спасибо! Ваш отзыв появится после модерации.')
                    return redirect('site_reviews')
            except (ValueError, TypeError):
                pass
        messages.error(request, 'Заполните все обязательные поля.')

    context = {'reviews': reviews}
    return render(request, 'app_home/site_reviews.html', context)


def static_page(request, slug):
    page = get_object_or_404(StaticPage, slug=slug, is_published=True)
    return render(request, 'app_home/static_page.html', {'page': page})


def robots(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "Disallow: /profile/",
        "Disallow: /orders/",
        "Disallow: /catalog/search/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap(request):
    def add(path, lastmod=None, changefreq=None, priority=None):
        items.append({
            'loc': request.build_absolute_uri(path),
            'lastmod': lastmod,
            'changefreq': changefreq,
            'priority': priority,
        })

    items = []
    add('/', changefreq='daily', priority='1.0')
    add('/catalog/', changefreq='daily', priority='0.9')
    add('/about/', changefreq='monthly', priority='0.5')
    add('/contacts/', changefreq='monthly', priority='0.5')
    add('/reviews/', changefreq='weekly', priority='0.5')

    for c in Category.objects.filter(is_active=True):
        add(c.get_absolute_url(), lastmod=c.updated_at, changefreq='weekly', priority='0.8')
    for p in Product.objects.filter(is_active=True):
        add(p.get_absolute_url(), lastmod=p.updated_at, changefreq='weekly', priority='0.7')
    for page in StaticPage.objects.filter(is_published=True).exclude(slug='about'):
        add(f'/{page.slug}/', lastmod=page.updated_at, changefreq='monthly', priority='0.5')

    response = render(request, 'app_home/sitemap.xml', {'items': items})
    response['Content-Type'] = 'application/xml'
    return response
