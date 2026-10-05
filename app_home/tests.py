from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path

from _settings import urls as site_urls
from app_catalog.models import Category, Product, ProductVariant
from app_home import error_views


def make_product(slug, **flags):
    category, _ = Category.objects.get_or_create(
        slug='sumki', defaults={'name': 'Сумки'},
    )
    product = Product.objects.create(
        name=slug, slug=slug, category=category, is_active=True, **flags
    )
    ProductVariant.objects.create(
        product=product, color='Чёрный', price='100.00', stock=3, is_active=True,
    )
    return product


class HomeSectionsTests(TestCase):
    """Пустые секции главной не должны рендериться."""

    def get_home(self):
        return self.client.get('/').content.decode()

    def headings(self, html):
        return {
            'new': 'Новинки' in html,
            'popular': 'Популярные товары' in html,
            'sale': 'Скидки и акции' in html,
            'categories': 'Категории каталога' in html,
        }

    def test_all_sections_shown_when_everything_present(self):
        make_product('tovar-1', is_new=True, is_popular=True, is_sale=True)
        html = self.get_home()
        self.assertEqual(
            self.headings(html),
            {'new': True, 'popular': True, 'sale': True, 'categories': True},
        )

    def test_empty_sections_are_hidden(self):
        make_product('tovar-1', is_popular=True)
        headings = self.headings(self.get_home())
        self.assertTrue(headings['popular'])
        self.assertFalse(headings['new'], 'секция «Новинки» показана без товаров')
        self.assertFalse(headings['sale'], 'секция «Скидки и акции» показана без товаров')

    def test_inactive_products_do_not_fill_sections(self):
        make_product('tovar-1', is_new=True, is_popular=True, is_sale=True)
        Product.objects.all().update(is_active=False)
        headings = self.headings(self.get_home())
        self.assertFalse(headings['new'])
        self.assertFalse(headings['popular'])
        self.assertFalse(headings['sale'])

    def test_categories_hidden_when_none_active(self):
        make_product('tovar-1', is_new=True)
        Category.objects.all().update(is_active=False)
        html = self.get_home()
        self.assertFalse(self.headings(html)['categories'])
        self.assertTrue(self.headings(html)['new'])

    def test_fully_empty_home_shows_empty_state(self):
        html = self.get_home()
        self.assertEqual(
            self.headings(html),
            {'new': False, 'popular': False, 'sale': False, 'categories': False},
        )
        self.assertIn('empty-state', html)

    def test_card_shows_name_price_and_variant_id(self):
        make_product('tovar-1', is_new=True)
        html = self.get_home()
        variant = ProductVariant.objects.get(product__slug='tovar-1')
        self.assertIn('>tovar-1</a>', html)
        self.assertIn('100,00 BYN', html)
        self.assertIn(f'data-variant-id="{variant.id}"', html)
        self.assertIn(f'?variant={variant.id}"', html)

    def test_products_without_active_variants_are_hidden(self):
        product = make_product('tovar-1', is_new=True)
        ProductVariant.objects.filter(product=product).update(is_active=False)
        self.assertFalse(
            self.headings(self.get_home())['new'],
            'товар без активного варианта попал в секцию — карточка будет пустой',
        )

    def test_product_with_several_variants_is_shown_once(self):
        product = make_product('tovar-1', is_new=True)
        ProductVariant.objects.create(
            product=product, color='Белый', price='120.00', stock=1, is_active=True,
        )
        html = self.get_home()
        self.assertEqual(html.count('data-product-name="tovar-1'), 1)


def _boom(request):
    raise RuntimeError('Шлюз оплаты вернул 502')


def _forbidden(request):
    raise PermissionDenied('Нужен доступ администратора')


handler403 = 'app_home.error_views.permission_denied'
handler404 = 'app_home.error_views.page_not_found'
handler500 = 'app_home.error_views.server_error'

urlpatterns = [
    *site_urls.urlpatterns,
    path('boom/', _boom),
    path('forbidden/', _forbidden),
]


@override_settings(ROOT_URLCONF=__name__, DEBUG=False, SECURE_SSL_REDIRECT=False)
class ErrorPagesTests(TestCase):
    """403/404/500 отдают собственные страницы, детали ошибки — только суперпользователю."""

    def get(self, path):
        self.client.raise_request_exception = False
        response = self.client.get(path)
        self.assertIn(response.status_code, [403, 404, 500])
        return response.content.decode()

    def login(self, **kwargs):
        user = get_user_model().objects.create_user(**kwargs)
        self.client.login(username=kwargs['username'], password=kwargs['password'])
        return user

    def test_404_page(self):
        html = self.get('/net-takoy-stranicy/')
        self.assertIn('Страница не найдена', html)
        self.assertIn('error-page', html)

    def test_403_page(self):
        html = self.get('/forbidden/')
        self.assertIn('Доступ закрыт', html)

    def test_500_page(self):
        self.assertIn('Что-то пошло не так', self.get('/boom/'))

    def test_error_pages_are_not_indexed(self):
        for path_ in ['/net-takoy-stranicy/', '/forbidden/', '/boom/']:
            with self.subTest(path=path_):
                self.assertIn('noindex, nofollow', self.get(path_))

    def test_500_hides_details_from_anonymous(self):
        html = self.get('/boom/')
        self.assertNotIn('Технические детали', html)
        self.assertNotIn('Шлюз оплаты вернул 502', html)

    def test_500_hides_details_from_regular_user(self):
        self.login(username='klient', password='test-password-1')
        self.assertNotIn('Технические детали', self.get('/boom/'))

    def test_500_shows_details_to_superuser(self):
        get_user_model().objects.create_superuser(
            username='boss', email='boss@example.com', password='test-password-1',
        )
        self.client.login(username='boss', password='test-password-1')

        html = self.get('/boom/')
        self.assertIn('Технические детали', html)
        self.assertIn('builtins.RuntimeError', html)
        self.assertIn('Шлюз оплаты вернул 502', html)
        self.assertIn('GET /boom/', html)

    def test_500_falls_back_if_page_cannot_be_rendered(self):
        request = RequestFactory().get('/boom/')
        request.user = AnonymousUser()

        response = error_views.server_error(request, template_name='app_home/net-takogo.html')
        self.assertEqual(response.status_code, 500)
        self.assertIn('серверная ошибка', response.content.decode())
