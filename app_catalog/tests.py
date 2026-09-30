import re

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.formats import number_format
import yaml

from app_catalog import yml_feed
from app_catalog.views import _category_meta
from .models import Category, Product, ProductImage, ProductVariant


def price(variant):
    """Цена так, как её выводит шаблон: с локальным разделителем дробной части."""
    return number_format(variant.price)


def make_product(category, name, slug):
    product = Product.objects.create(name=name, slug=slug, category=category)
    ProductVariant.objects.create(product=product, color='Чёрный', price='100.00')
    return product


class CatalogCardsTests(TestCase):
    """Карточка каталога — это вариант (цвет), а не модель."""

    def setUp(self):
        self.category = Category.objects.create(name='Сумки', slug='sumki')
        self.product = Product.objects.create(
            name='Сумка-шопер', slug='sumka-shopper', category=self.category,
        )
        self.bordovy = self.variant('Бордовый', '100.00')
        self.siniy = self.variant('Синий', '300.00')
        self.cherny = self.variant('Чёрный', '200.00')

    def variant(self, color, price, **kwargs):
        return ProductVariant.objects.create(
            product=self.product, color=color, price=price, **kwargs
        )

    def cards(self, url='/catalog/'):
        """Подписи цветов и id вариантов из отрендеренных карточек."""
        html = self.client.get(url).content.decode()
        return html

    def variant_ids_in_order(self, html):
        return re.findall(r'data-variant-id="(\d+)"', html)

    def test_one_card_per_color(self):
        html = self.cards()

        self.assertEqual(html.count('class="product-card"'), 3)
        self.assertEqual(
            set(self.variant_ids_in_order(html)),
            {str(self.bordovy.id), str(self.siniy.id), str(self.cherny.id)},
        )

    def test_each_card_shows_its_own_price(self):
        html = self.cards()

        for variant in (self.bordovy, self.siniy, self.cherny):
            self.assertIn(f'{price(variant)} BYN', html)

    def test_each_card_shows_its_own_color(self):
        html = self.cards()

        for color in ('Бордовый', 'Синий', 'Чёрный'):
            self.assertIn(f'>{color}</span>', html)

    def test_card_links_to_its_own_color(self):
        html = self.cards()

        for variant in (self.bordovy, self.siniy, self.cherny):
            self.assertIn(f'{self.product.get_absolute_url()}?variant={variant.id}', html)

    def test_variant_param_selects_color_on_product_page(self):
        html = self.client.get(f'{self.product.get_absolute_url()}?variant={self.siniy.id}').content.decode()

        self.assertIn(f'Сумка-шопер {self.siniy.color}', html)
        self.assertIn(f'id="currentPrice">{price(self.siniy)} BYN', html)

    def test_inactive_variant_is_hidden(self):
        self.bordovy.is_active = False
        self.bordovy.save()

        html = self.cards()

        self.assertEqual(html.count('class="product-card"'), 2)
        self.assertNotIn(str(self.bordovy.id), self.variant_ids_in_order(html))

    def test_inactive_product_hides_all_its_cards(self):
        self.product.is_active = False
        self.product.save()

        html = self.cards()

        self.assertEqual(html.count('class="product-card"'), 0)

    def test_price_filter_applies_to_cards(self):
        html = self.cards('/catalog/?price_from=150')

        self.assertEqual(set(self.variant_ids_in_order(html)), {
            str(self.siniy.id), str(self.cherny.id),
        })

    def test_color_filter_returns_only_that_color(self):
        html = self.cards('/catalog/?color=Синий')

        self.assertEqual(self.variant_ids_in_order(html), [str(self.siniy.id)])

    def test_sort_by_price_orders_cards_by_own_price(self):
        html = self.cards('/catalog/?sort=price_asc')

        self.assertEqual(self.variant_ids_in_order(html), [
            str(self.bordovy.id), str(self.cherny.id), str(self.siniy.id),
        ])

    def test_search_page_also_lists_one_card_per_color(self):
        html = self.cards('/catalog/search/')

        self.assertEqual(html.count('class="product-card"'), 3)

    def test_pagination_counts_colorways(self):
        # В setUp уже 3 варианта — до 12 не хватает 10 моделей по одному цвету.
        for index in range(10):
            make_product(self.category, f'Сумка {index}', f'sumka-{index}')

        first = self.cards('/catalog/?sort=price_asc')
        second = self.cards('/catalog/?sort=price_asc&page=2')

        self.assertEqual(first.count('class="product-card"'), 12)
        self.assertEqual(second.count('class="product-card"'), 1)

    def test_category_page_lists_every_color(self):
        html = self.cards(self.category.get_absolute_url())

        self.assertEqual(html.count('class="product-card"'), 3)

    def test_single_color_product_has_one_card(self):
        only = Category.objects.create(name='Кошельки', slug='koshelki')
        product = Product.objects.create(name='Кошелок', slug='koshelok', category=only)
        ProductVariant.objects.create(product=product, color='Чёрный', price='90.00')

        html = self.cards()

        self.assertEqual(html.count('class="product-card"'), 4)


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


class YmlFeedTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Сумки', slug='sumki', market_category_id='17028922',
        )
        self.product = Product.objects.create(
            name='Сумка-шопер',
            slug='sumka-shopper',
            category=self.category,
            gender='F',
            short_description='Шопер из хлопка',
            description='<p>Сумка из <b>хлопка</b></p><p>Большая</p>',
            weight='0.450',
            material='Хлопок',
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color='Бордовый',
            price='200.00',
            discount_percent=10,
            stock=3,
        )

    def feed(self):
        text, stats = yml_feed.build_feed()
        return yaml.safe_load(text), stats

    def test_offer_uses_sale_price(self):
        catalog, _ = self.feed()

        offer = catalog['offers'][0]

        self.assertEqual(offer['price'], 180.0)
        self.assertEqual(offer['currencyId'], 'BYN')
        self.assertEqual(offer['weight'], 0.45)

    def test_offer_fields(self):
        catalog, _ = self.feed()

        offer = catalog['offers'][0]

        self.assertEqual(offer['name'], 'Сумка-шопер, Бордовый')
        self.assertEqual(offer['url'], 'https://edvershop.by/catalog/product/sumka-shopper/')
        self.assertEqual(offer['categoryId'], '17028922')
        self.assertEqual(offer['vendorCode'], 'sumka-shopper-бордовый')
        self.assertIs(offer['available'], True)

    def test_offer_description_is_plain_text(self):
        catalog, _ = self.feed()

        self.assertEqual(catalog['offers'][0]['description'], 'Сумка из хлопка Большая')

    def test_offer_params(self):
        catalog, _ = self.feed()

        params = {p['name']: p['value'] for p in catalog['offers'][0]['param']}

        self.assertEqual(params['Материал'], 'Хлопок')
        self.assertEqual(params['Пол'], 'Женский')
        self.assertEqual(params['Цвет'], 'Бордовый')

    def test_falls_back_to_short_description(self):
        self.product.description = ''
        self.product.save()

        catalog, _ = self.feed()

        self.assertEqual(catalog['offers'][0]['description'], 'Шопер из хлопка')

    def test_svg_pictures_are_skipped(self):
        ProductImage.objects.create(
            variant=self.variant, image='products/test.svg', is_main=True,
        )

        catalog, stats = self.feed()

        self.assertNotIn('picture', catalog['offers'][0])
        self.assertEqual(stats['offers_without_picture'], 1)

    def test_pictures_are_absolute_urls(self):
        ProductImage.objects.create(
            variant=self.variant, image='products/test.jpg', is_main=True,
        )
        ProductImage.objects.create(variant=self.variant, image='products/second.png')

        catalog, stats = self.feed()

        self.assertEqual(
            catalog['offers'][0]['picture'],
            [
                'https://edvershop.by/media/products/test.jpg',
                'https://edvershop.by/media/products/second.png',
            ],
        )
        self.assertEqual(stats['offers_without_picture'], 0)

    def test_out_of_stock_variant_is_not_available(self):
        ProductVariant.objects.filter(pk=self.variant.pk).update(stock=0)

        catalog, _ = self.feed()

        self.assertIs(catalog['offers'][0]['available'], False)

    def test_preorder_variant_is_available(self):
        ProductVariant.objects.filter(pk=self.variant.pk).update(status='preorder')

        catalog, _ = self.feed()

        self.assertIs(catalog['offers'][0]['available'], True)

    def test_inactive_product_and_variant_are_skipped(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)
        ProductVariant.objects.filter(pk=self.variant.pk).update(is_active=False)

        catalog, stats = self.feed()

        self.assertEqual(catalog['offers'], [])
        self.assertEqual(stats['products'], 0)

    def test_inactive_category_is_skipped(self):
        Category.objects.filter(pk=self.category.pk).update(is_active=False)

        catalog, _ = self.feed()

        self.assertEqual(catalog['offers'], [])

    def test_category_id_falls_back_to_slug(self):
        self.category.market_category_id = ''
        self.category.save()

        catalog, stats = self.feed()

        self.assertEqual(catalog['categories'][0]['id'], 'sumki')
        self.assertEqual(stats['categories_without_market_id'], ['Сумки'])

    def test_category_tree_lists_used_categories(self):
        other = Category.objects.create(name='Кошельки', slug='koshelki')
        make_product(other, 'Кошелок', 'koshelok')

        catalog, _ = self.feed()

        self.assertEqual([c['name'] for c in catalog['categories']], ['Сумки', 'Кошельки'])

    def test_feed_header(self):
        catalog, _ = self.feed()

        self.assertEqual(catalog['shop']['url'], 'https://edvershop.by')
        self.assertEqual(catalog['vendor']['name'], 'EDVER Shop')
        self.assertEqual(catalog['currencies'], [{'code': 'BYN', 'rate': 1}])
        self.assertIn('+03:00', catalog['date'])

    def test_one_offer_per_variant(self):
        ProductVariant.objects.create(
            product=self.product, color='Чёрный', price='210.00', stock=1,
        )

        catalog, stats = self.feed()

        self.assertEqual(stats['offers'], 2)
        self.assertEqual(
            [offer['name'] for offer in catalog['offers']],
            ['Сумка-шопер, Бордовый', 'Сумка-шопер, Чёрный'],
        )

    def test_vendor_codes_are_unique(self):
        ProductVariant.objects.create(
            product=self.product, color='Чёрный', price='210.00', stock=1,
        )

        catalog, _ = self.feed()

        codes = [offer['vendorCode'] for offer in catalog['offers']]
        self.assertEqual(len(set(codes)), len(codes))


class YmlExportAdminTests(TestCase):
    url = '/admin/app_catalog/product/export-yml/'

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@a.by', 'pass')

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_admin_downloads_yml(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment; filename="edver-shop-yml-', response['Content-Disposition'])
        self.assertTrue(response['Content-Disposition'].endswith('.yml"'))
        self.assertIn('application/x-yaml', response['Content-Type'])
        catalog = yaml.safe_load(response.content.decode())
        self.assertIn('offers', catalog)

    def test_button_on_product_changelist(self):
        self.client.force_login(self.admin)

        html = self.client.get('/admin/app_catalog/product/').content.decode()

        self.assertIn('Скачать YML для Яндекс Маркета', html)
        self.assertIn(self.url, html)


class AdminCrossLinksTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser('admin', 'a@a.by', 'pass'))
        self.category = Category.objects.create(name='Сумки', slug='sumki')
        self.product = Product.objects.create(
            name='Сумка-шопер', slug='sumka-shopper', category=self.category,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, color='Бордовый', price='200.00',
        )

    def test_variant_row_links_to_variant_page(self):
        html = self.client.get(
            f'/admin/app_catalog/product/{self.product.pk}/change/'
        ).content.decode()

        self.assertIn(f'/admin/app_catalog/productvariant/{self.variant.pk}/change/', html)

    def test_variant_page_links_to_parent_product(self):
        html = self.client.get(
            f'/admin/app_catalog/productvariant/{self.variant.pk}/change/'
        ).content.decode()

        self.assertIn(f'/admin/app_catalog/product/{self.product.pk}/change/', html)

    def test_variant_add_page_renders_without_product(self):
        response = self.client.get('/admin/app_catalog/productvariant/add/')

        self.assertEqual(response.status_code, 200)


class ExportYmlCommandTests(TestCase):
    def test_command_writes_file(self):
        from django.core.management import call_command
        from pathlib import Path
        import tempfile

        category = Category.objects.create(name='Сумки', slug='sumki')
        make_product(category, 'Сумка', 'sumka')

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'feed.yml'
            call_command('export_yml', output=str(path))

            self.assertIn('offers', yaml.safe_load(path.read_text(encoding='utf-8')))

