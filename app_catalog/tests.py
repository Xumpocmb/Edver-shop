from django.test import TestCase

from app_catalog.views import _category_meta
from .models import Category, Product, ProductVariant


def make_product(category, name, slug):
    product = Product.objects.create(name=name, slug=slug, category=category)
    ProductVariant.objects.create(product=product, color='Чёрный', price='100.00')
    return product


class CategoryMetaTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Сумки', slug='sumki')

    def meta_in_page(self, url):
        html = self.client.get(url).content.decode()
        start = html.index('<meta name="description"')
        return html[start:html.index('>', start)]

    def test_description_from_admin_is_used(self):
        self.category.description = (
            'Женские сумки из натуральной кожи и текстиля: шоперы, кроссовки, '
            'клатчи и сумки через плечо с фото и ценами.'
        )
        self.category.save()

        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertIn('Женские сумки из натуральной кожи', content)
        self.assertNotIn('интернет-магазине EDVER Shop', content)

    def test_long_description_is_truncated(self):
        self.category.description = 'Сумки. ' * 60
        self.category.save()

        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertLess(len(content), 300)
        self.assertIn('…', content)

    def test_description_equal_to_name_is_replaced(self):
        self.category.description = 'Сумки'
        self.category.save()

        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertIn('Сумки в интернет-магазине EDVER Shop', content)
        self.assertIn('доставка по Беларуси', content)

    def test_fallback_includes_product_count(self):
        for index in range(3):
            make_product(self.category, f'Сумка {index}', f'sumka-{index}')

        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertIn('3 модели с фото и ценами', content)

    def test_fallback_without_products_has_no_count(self):
        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertIn('модели с фото и ценами', content)
        self.assertNotIn('0 модел', content)

    def test_inactive_products_are_not_counted(self):
        product = make_product(self.category, 'Сумка', 'sumka')
        Product.objects.filter(pk=product.pk).update(is_active=False)

        content = self.meta_in_page(self.category.get_absolute_url())

        self.assertIn('модели с фото и ценами', content)
        self.assertNotIn('1 модель', content)

    def test_og_tags_match_meta_description(self):
        make_product(self.category, 'Сумка', 'sumka')

        html = self.client.get(self.category.get_absolute_url()).content.decode()

        expected = _category_meta(self.category, 1)
        self.assertIn(f'<meta property="og:description" content="{expected}">', html)
        self.assertIn('<meta property="og:title" content="Сумки — EDVER Shop">', html)

    def test_catalog_keeps_default_description(self):
        make_product(self.category, 'Сумка', 'sumka')

        html = self.client.get('/catalog/').content.decode()

        self.assertIn('name="description" content="EDVER Shop — интернет-магазин сумок', html)
        self.assertIn('<meta property="og:title" content="EDVER Shop">', html)
