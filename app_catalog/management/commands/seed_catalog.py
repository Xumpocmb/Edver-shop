import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify

from app_catalog.models import (
    Brand, Category, Product, ProductImage, ProductReview,
    ProductVariant, VariantAttribute, VariantAttributeValue
)


SVG_PLACEHOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="{w}" height="{h}" fill="url(#g)"/>
  <text x="50%" y="52%" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="20" fill="#ffffff" font-weight="bold" opacity="0.9">{label}</text>
</svg>"""

GRADIENTS = [
    ('#1b4332', '#2d6a4f'),
    ('#415a77', '#778da9'),
    ('#9b2226', '#bb3e03'),
    ('#003566', '#0077b6'),
    ('#370617', '#6a040f'),
    ('#1d3557', '#457b9d'),
    ('#386641', '#6a994e'),
    ('#22223b', '#4a4e69'),
    ('#283618', '#606c38'),
    ('#001219', '#005f73'),
]


def _svg(name, color_idx=0):
    c1, c2 = GRADIENTS[color_idx % len(GRADIENTS)]
    return SVG_PLACEHOLDER.format(w=800, h=800, c1=c1, c2=c2, label=name[:20])


class Command(BaseCommand):
    help = "Seed demo data for catalog, categories, brands, products, images, reviews"

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Clear catalog data first')

    def handle(self, *args, **options):
        if options.get('flush'):
            VariantAttributeValue.objects.all().delete()
            ProductVariant.objects.all().delete()
            VariantAttribute.objects.all().delete()
            ProductImage.objects.all().delete()
            ProductReview.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.WARNING('Flushed catalog data'))

        # ---------- Variant Attributes ----------
        attr_color, _ = VariantAttribute.objects.get_or_create(
            slug='color', defaults={'name': 'Цвет'}
        )
        attr_size, _ = VariantAttribute.objects.get_or_create(
            slug='size', defaults={'name': 'Размер'}
        )
        self.stdout.write(self.style.SUCCESS(f'Attributes: {VariantAttribute.objects.count()}'))

        # ---------- Brands ----------
        brands_data = [
            ('Roncato', 'Италия. Чемоданы и дорожные аксессуары.'),
            ('Braun Büffel', 'Германия. Классические кожаные изделия.'),
            ('Lacoste', 'Франция. Стильные сумки и кошельки.'),
            ('Samsonite', 'США/Бельгия. Мировой лидер по чемоданам.'),
            ('Tous', 'Испания. Аксессуары и сумки для женщин.'),
            ('Piquadro', 'Италия. Бизнес-аксессуары и портфели.'),
        ]
        brands = {}
        for idx, (name, desc) in enumerate(brands_data):
            b, _ = Brand.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name, allow_unicode=True),
                          'description': desc}
            )
            brands[name] = b
            self.stdout.write(self.style.SUCCESS(f'Brand: {b.name}'))

        # ---------- Categories (2-level tree) ----------
        cat_top = [
            ('Сумки', 'Кроссбоди, шопперы, городские сумки', 'bags'),
            ('Чемоданы', 'Дорожные чемоданы разных размеров', 'luggage'),
            ('Кошельки', 'Кошельки, портмоне, картхолдеры', 'wallets'),
            ('Аксессуары', 'Ремни, ремешки, футляры', 'accessories'),
            ('Рюкзаки', 'Городские, туристические, бизнес-рюкзаки', 'backpacks'),
            ('Сумки для путешествий', 'Дуфл-сумки и дорожные сумки', 'travel'),
        ]
        sub_cats = {
            'Сумки': [
                ('Женские сумки', 'women-bags'),
                ('Мужские сумки', 'men-bags'),
                ('Кроссбоди', 'crossbody'),
                ('Шопперы', 'shoppers'),
            ],
            'Чемоданы': [
                ('Средние (24")', 'midi-24'),
                ('Крупные (28")', 'large-28'),
                ('Кабинные (20")', 'cabin-20'),
            ],
            'Кошельки': [
                ('Женские кошельки', 'w-wallets'),
                ('Мужские портмоне', 'm-wallets'),
                ('Картхолдеры', 'cardholders'),
            ],
            'Аксессуары': [
                ('Ремни', 'belts'),
                ('Пеналы и футляры', 'pens'),
                ('Обложки для паспорта', 'passport'),
            ],
            'Рюкзаки': [
                ('Городские', 'city-bp'),
                ('Бизнес', 'business-bp'),
            ],
            'Сумки для путешествий': [
                ('Дуфлы', 'duffles'),
                ('Спортивные', 'sport-bags'),
            ],
        }

        cat_objs = {}
        for i, (name, desc, slug) in enumerate(cat_top):
            parent, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'description': desc, 'order': i, 'image': None}
            )
            cat_objs[name] = parent
            self.stdout.write(self.style.SUCCESS(f'Cat: {parent}'))

            for j, (sc_name, sc_slug) in enumerate(sub_cats.get(name, [])):
                sub, _ = Category.objects.get_or_create(
                    slug=sc_slug,
                    defaults={
                        'name': sc_name,
                        'parent': parent,
                        'description': f'Подкатегория: {sc_name}',
                        'order': j,
                    }
                )
                cat_objs[sc_name] = sub

        # ---------- Product matrix ----------
        products_seed = [
            # Сумки
            ('women-bags', 'Lacoste', 'Сумка-шоппер Lacoste NF.2148',
             Decimal('12990'), Decimal('15990'), 'Бордовый', 'Хлопок', '38x30x14 см', Decimal('0.45'),
             {'is_popular': True, 'is_sale': True}),
            ('women-bags', 'Tous', 'Кожаная сумка Tous Mini Crossbody',
             Decimal('18500'), None, 'Кремовый', 'Натуральная кожа', '22x18x8 см', Decimal('0.38'),
             {'is_new': True, 'is_popular': True}),
            ('men-bags', 'Piquadro', 'Портфель Piquadro Briefcase',
             Decimal('42990'), Decimal('49990'), 'Чёрный', 'Натуральная кожа', '40x30x10 см', Decimal('1.1'),
             {'is_popular': True, 'is_sale': True}),
            ('crossbody', 'Braun Büffel', 'Кроссбоди Braun Büffel Siena',
             Decimal('23890'), None, 'Тёмно-коричневый', 'Натуральная кожа', '24x18x6 см', Decimal('0.4'),
             {'is_new': True}),
            ('shoppers', 'Lacoste', 'Шоппер Lacoste L.12.12',
             Decimal('8990'), Decimal('10990'), 'Зелёный', 'ПВХ', '35x34x12 см', Decimal('0.35'),
             {'is_sale': True, 'is_popular': True}),

            # Чемоданы
            ('cabin-20', 'Samsonite', 'Чемодан Samsonite Lite-Shock 20"',
             Decimal('32990'), Decimal('38990'), 'Синий', 'Полипропилен', '55x40x20 см', Decimal('2.1'),
             {'is_popular': True, 'is_sale': True}),
            ('midi-24', 'Samsonite', 'Чемодан Samsonite C-Lite 24"',
             Decimal('41990'), None, 'Чёрный', 'Curv', '67x45x28 см', Decimal('2.7'),
             {'is_popular': True}),
            ('large-28', 'Roncato', 'Чемодан Roncato Young 28"',
             Decimal('29890'), Decimal('34990'), 'Красный', 'Makrolon', '77x52x30 см', Decimal('3.4'),
             {'is_new': True, 'is_sale': True}),
            ('cabin-20', 'Roncato', 'Чемодан Roncato Box 2.0 Cabin 20"',
             Decimal('25990'), None, 'Тёмно-зелёный', 'Makrolon', '55x40x20 см', Decimal('2.3'),
             {'is_popular': True}),
            ('large-28', 'Samsonite', 'Чемодан Samsonite Base Boost 28"',
             Decimal('27490'), Decimal('32990'), 'Серый', 'Полиэстер', '78x52x31 см', Decimal('3.8'),
             {'is_sale': True}),

            # Кошельки
            ('w-wallets', 'Tous', 'Кошелёк Tous Logo Long',
             Decimal('7990'), None, 'Розовый', 'Натуральная кожа', '19x10x3 см', Decimal('0.15'),
             {'is_new': True}),
            ('m-wallets', 'Braun Büffel', 'Портмоне Braun Büffel Vasco',
             Decimal('11490'), Decimal('13490'), 'Коричневый', 'Натуральная кожа', '12x9.5x2 см', Decimal('0.12'),
             {'is_popular': True, 'is_sale': True}),
            ('cardholders', 'Piquadro', 'Картхолдер Piquadro Slider',
             Decimal('5990'), None, 'Чёрный', 'Натуральная кожа', '10.5x7.5x1 см', Decimal('0.06'),
             {'is_popular': True, 'is_new': True}),
            ('w-wallets', 'Lacoste', 'Кошелёк Lacoste Zip',
             Decimal('6490'), Decimal('7990'), 'Белый', 'ПВХ', '19x11x3 см', Decimal('0.14'),
             {'is_sale': True}),

            # Аксессуары
            ('belts', 'Braun Büffel', 'Ремень Braun Büffel Classic',
             Decimal('6990'), None, 'Коричневый', 'Натуральная кожа', 'на ремень', Decimal('0.18'),
             {'is_popular': True}),
            ('passport', 'Piquadro', 'Обложка на паспорт Piquadro',
             Decimal('4290'), Decimal('4990'), 'Чёрный', 'Натуральная кожа', '14x10x1 см', Decimal('0.05'),
             {'is_new': True, 'is_sale': True}),
            ('pens', 'Tous', 'Пенал Tous Mini',
             Decimal('3490'), None, 'Бежевый', 'ПВХ', '20x8x5 см', Decimal('0.09'),
             {}),

            # Рюкзаки
            ('city-bp', 'Lacoste', 'Рюкзак Lacoste Neocroc',
             Decimal('15990'), Decimal('18990'), 'Синий', 'ПВХ', '30x40x12 см', Decimal('0.5'),
             {'is_sale': True, 'is_popular': True}),
            ('business-bp', 'Piquadro', 'Рюкзак Piquadro Business 15.6"',
             Decimal('36990'), None, 'Чёрный', 'Натуральная кожа', '42x32x14 см', Decimal('1.05'),
             {'is_popular': True, 'is_new': True}),
            ('city-bp', 'Samsonite', 'Рюкзак Samsonite Guardit 2.0',
             Decimal('12490'), None, 'Чёрный', 'Полиэстер', '44x32x15 см', Decimal('0.7'),
             {'is_popular': True}),

            # Travel
            ('duffles', 'Samsonite', 'Дуфл Samsonite Midtown',
             Decimal('9990'), Decimal('12490'), 'Тёмно-синий', 'Полиэстер', '50x28x26 см', Decimal('0.9'),
             {'is_sale': True, 'is_new': True}),
            ('sport-bags', 'Lacoste', 'Спортивная сумка Lacoste Sport',
             Decimal('8490'), None, 'Бордовый', 'Полиэстер', '52x26x24 см', Decimal('0.6'),
             {}),

            # Ещё
            ('shoppers', 'Tous', 'Шоппер Tous Kaos Mini',
             Decimal('10490'), None, 'Кремовый', 'Натуральная кожа', '28x24x10 см', Decimal('0.35'),
             {'is_new': True}),
            ('midi-24', 'Roncato', 'Чемодан Roncato Ironik 24"',
             Decimal('31990'), Decimal('36990'), 'Чёрный', 'Makrolon', '65x42x27 см', Decimal('2.8'),
             {'is_popular': True, 'is_sale': True}),
        ]

        # Products with variants (color variants for certain products)
        variant_products = {
            0: {'colors': ['Бордовый', 'Чёрный', 'Синий']},           # Lacoste NF.2148
            1: {'colors': ['Кремовый', 'Чёрный', 'Розовый']},         # Tous Mini Crossbody
            4: {'colors': ['Зелёный', 'Чёрный', 'Белый']},            # Lacoste L.12.12
            18: {'colors': ['Чёрный', 'Серый', 'Синий']},             # Lacoste Neocroc
            21: {'colors': ['Тёмно-синий', 'Чёрный', 'Красный']},     # Samsonite Midtown
        }

        for idx, (cat_slug, brand_name, pname, price, old_price,
                  color, material, dims, weight, flags) in enumerate(products_seed):
            category = cat_objs.get(cat_slug) or Category.objects.filter(slug=cat_slug).first()
            if not category:
                self.stderr.write(f'skip product {pname}: no category {cat_slug}')
                continue
            brand = brands.get(brand_name)
            slug_base = slugify(pname, allow_unicode=True)
            slug = slug_base
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{slug_base}-{counter}'
                counter += 1

            p, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': pname,
                    'category': category,
                    'brand': brand,
                    'price': price,
                    'old_price': old_price,
                    'stock': 25 + idx % 50,
                    'sku': f'EDV-{1000 + idx:04d}',
                    'short_description': f'{pname} — качественное изделие от бренда {brand_name}. '
                                         f'Материал: {material}. Цвет: {color}.',
                    'description': (
                        f'{pname} — модель от бренда {brand_name}.\n\n'
                        f'Основные характеристики:\n'
                        f'• Материал: {material}\n'
                        f'• Цвет: {color}\n'
                        f'• Размеры: {dims}\n'
                        f'• Вес: {weight} кг\n\n'
                        f'Идеальный вариант для повседневного использования или путешествий. '
                        f'Качественная фурнитура, усиленные швы, гарантия производителя.'
                    ),
                    'color': color,
                    'material': material,
                    'dimensions': dims,
                    'weight': weight,
                    'status': 'in_stock',
                    **flags,
                }
            )
            if not created:
                continue

            # ---------- Product images (3 SVG placeholders) ----------
            colors_idx = [idx, idx + 1, idx + 2]
            for img_pos, ci in enumerate(colors_idx):
                svg_bytes = _svg(pname[:18] + f' [{img_pos+1}]', ci).encode('utf-8')
                ProductImage.objects.create(
                    product=p,
                    image=ContentFile(svg_bytes, name=f'{slug}-{img_pos+1}.svg'),
                    alt=f'{pname} — фото {img_pos + 1}',
                    is_main=(img_pos == 0),
                    order=img_pos,
                )

            # ---------- Variants for certain products ----------
            if idx in variant_products:
                vp = variant_products[idx]
                for ci, var_color in enumerate(vp.get('colors', [])):
                    variant, _ = ProductVariant.objects.get_or_create(
                        product=p,
                        name=var_color,
                        defaults={
                            'sku': f'{p.sku}-{ci+1:02d}' if p.sku else None,
                            'stock': 10 + ci * 5,
                            'is_active': True,
                        }
                    )
                    VariantAttributeValue.objects.get_or_create(
                        variant=variant,
                        attribute=attr_color,
                        defaults={'value': var_color}
                    )

            # ---------- Reviews ----------
            review_templates = [
                ('Отличное качество!',
                 'Очень понравилось. Доставка быстрая, упаковка хорошая. Рекомендую.',
                 'Всё супер!', 'Нет', 5),
                ('Хорошее соотношение цена/качество',
                 'Пользуюсь уже две недели, выглядит достойно. Покупкой доволен/льна.',
                 'Приятный материал, хороший цвет.', 'Нет', 4),
                ('Супер покупка',
                 'Лучшая покупка за последнее время. Все друзья уже спросили где купила.',
                 'Многофункциональность, дизайн.', 'Нет', 5),
                ('Сделано на совесть',
                 'Материал приятный, швы ровные, фурнитура крепкая. Беру второе изделие этого бренда.',
                 'Качество, бренд.', 'Нет', 5),
            ]
            for k, (rt_title, rt_text, rt_pros, rt_cons, rt_rating) in enumerate(review_templates):
                if (idx + k) % 3 == 0:
                    ProductReview.objects.create(
                        product=p,
                        name=['Анна С.', 'Иван П.', 'Мария К.', 'Дмитрий В.'][k],
                        email=f'user{idx}_{k}@example.com',
                        rating=rt_rating,
                        title=rt_title,
                        text=rt_text,
                        pros=rt_pros,
                        cons=rt_cons,
                        is_approved=True,
                    )

            self.stdout.write(self.style.SUCCESS(f'Product: {p.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'Seed complete: Brands={Brand.objects.count()}, '
            f'Categories={Category.objects.count()}, '
            f'Products={Product.objects.count()}, '
            f'Images={ProductImage.objects.count()}, '
            f'Variants={ProductVariant.objects.count()}, '
            f'Reviews={ProductReview.objects.count()}.'
        ))
