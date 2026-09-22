from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from app_catalog.models import Product, Category
from .models import Advantage, SiteReview, StaticPage


def home(request):
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('variants__images')

    popular = products.filter(is_popular=True)[:8]
    new_products = products.filter(is_new=True)[:8]
    sale = products.filter(is_sale=True)[:8]

    categories = Category.objects.filter(
        is_active=True
    ).order_by('order', 'name')[:8]

    slides = [
        {
            'title': 'Новая коллекция 2026',
            'subtitle': 'Сумки, чемоданы, кошельки — со скидкой до 30%',
            'cta': 'Смотреть каталог',
            'href': '/catalog/',
            'bg': 'var(--color-accent)',
        },
        {
            'title': 'Бесплатная доставка',
            'subtitle': 'При заказе от 5 000 бел. руб. — бесплатная доставка',
            'cta': 'Узнать подробнее',
            'href': '/catalog/?on_sale=1',
            'bg': 'var(--color-accent-light)',
        },
        {
            'title': 'Коллекция чемоданов',
            'subtitle': 'Прочные, лёгкие, вместительные — готовы к путешествию',
            'cta': 'К чемоданам',
            'href': '/catalog/',
            'bg': '#2b5a3f',
        },
    ]

    advantages = [
        ('✓', 'Гарантия качества', 'Все товары сертифицированы и проверены перед продажей'),
        ('🚚', 'Быстрая доставка', 'Отправляем по всей России в течение 1-2 рабочих дней'),
        ('💳', 'Удобная оплата', 'Оплата картой, СБП, наличными при получении'),
        ('↩️', 'Возврат 14 дней', 'Вернём товар без вопросов в течение двух недель'),
        ('🎁', 'Бонусы и акции', 'Регулярные скидки, распродажи и акции для постоянных клиентов'),
        ('💬', 'Поддержка 24/7', 'Всегда готовы ответить на вопросы и помочь с выбором'),
    ]

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

    context = {
        'advantages': advantages,
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
