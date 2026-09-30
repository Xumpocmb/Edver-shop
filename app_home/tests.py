from django.test import TestCase

from app_catalog.models import Category, Product, ProductVariant


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
