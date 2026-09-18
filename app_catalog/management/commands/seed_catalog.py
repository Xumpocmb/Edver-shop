import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify

from app_catalog.models import Brand, Category, Product, ProductImage


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


def _slug(text):
    return slugify(text, allow_unicode=True)


class Command(BaseCommand):
    help = "Seed demo data: 8 categories, 50 product models with gender & color groups"

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Clear catalog data first')

    def handle(self, *args, **options):
        if options.get('flush'):
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            self.stdout.write(self.style.WARNING('Flushed catalog data'))

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
        for name, desc in brands_data:
            b, _ = Brand.objects.get_or_create(
                name=name,
                defaults={'slug': _slug(name), 'description': desc}
            )
            brands[name] = b

        # ---------- Categories (корень + подкатегории) ----------
        cats_data = [
            ('Сумки', 'sumki', 0),
            ('Кошельки', 'koshelki', 1),
            ('Рюкзаки', 'ryukzaki', 2),
            ('Ремни', 'remni', 3),
            ('Зонты', 'zonty', 4),
            ('Дорожные сумки', 'dorozhnye-sumki', 5),
            ('Чемоданы', 'chemodany', 6),
            ('Аксессуары', 'aksessuary', 7),
        ]
        cat_objs = {}
        for name, slug, order in cats_data:
            c, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'order': order, 'description': name}
            )
            cat_objs[slug] = c

        # Подкатегории мужские/женские для всех категорий
        sub_data = {
            'sumki': [('Сумки мужские', 'sumki-muzhskie'), ('Сумки женские', 'sumki-zhenskie')],
            'koshelki': [('Кошельки мужские', 'koshelki-muzhskie'), ('Кошельки женские', 'koshelki-zhenskie')],
            'ryukzaki': [('Рюкзаки мужские', 'ryukzaki-muzhskie'), ('Рюкзаки женские', 'ryukzaki-zhenskie')],
            'remni': [('Ремни мужские', 'remni-muzhskie'), ('Ремни женские', 'remni-zhenskie')],
            'zonty': [('Зонты мужские', 'zonty-muzhskie'), ('Зонты женские', 'zonty-zhenskie')],
            'dorozhnye-sumki': [('Дорожные сумки мужские', 'dorozhnye-sumki-muzhskie'), ('Дорожные сумки женские', 'dorozhnye-sumki-zhenskie')],
            'chemodany': [('Чемоданы мужские', 'chemodany-muzhskie'), ('Чемоданы женские', 'chemodany-zhenskie')],
            'aksessuary': [('Аксессуары мужские', 'aksessuary-muzhskie'), ('Аксессуары женские', 'aksessuary-zhenskie')],
        }
        for parent_slug, children in sub_data.items():
            parent = cat_objs[parent_slug]
            for child_name, child_slug in children:
                child, _ = Category.objects.get_or_create(
                    slug=child_slug,
                    defaults={'name': child_name, 'parent': parent, 'description': child_name}
                )
                if child.parent_id != parent.id:
                    child.parent = parent
                    child.save()
                cat_objs[child_slug] = child

        # =====================================================
        # ТОВАРЫ — 50 моделей (групп цветов). Каждая группа = одна
        # модель товара в разных цветах (group_id одинаковый).
        # Формат: (category_slug, brand, name, gender, color, material,
        #          price, old_price, dims, weight, flags)
        # =====================================================

        products_seed = [
            # ===== СУМКИ (8 моделей) =====
            {
                'group': 'sumki-lacoste-nf2148',
                'items': [
                    ('sumki', 'Lacoste', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Бордовый', 'Хлопок',
                     Decimal('12990'), Decimal('15990'), '38x30x14', Decimal('0.45'), {'is_popular': True, 'is_sale': True}),
                    ('sumki', 'Lacoste', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Чёрный', 'Хлопок',
                     Decimal('12990'), None, '38x30x14', Decimal('0.45'), {'is_popular': True}),
                    ('sumki', 'Lacoste', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Синий', 'Хлопок',
                     Decimal('12990'), None, '38x30x14', Decimal('0.45'), {}),
                ],
            },
            {
                'group': 'sumki-tous-crossbody',
                'items': [
                    ('sumki', 'Tous', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {'is_new': True, 'is_popular': True}),
                    ('sumki', 'Tous', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {'is_new': True}),
                    ('sumki', 'Tous', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {}),
                ],
            },
            {
                'group': 'sumki-piquadro-briefcase',
                'items': [
                    ('sumki', 'Piquadro', 'Портфель Piquadro Briefcase', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('42990'), Decimal('49990'), '40x30x10', Decimal('1.1'), {'is_popular': True, 'is_sale': True}),
                    ('sumki', 'Piquadro', 'Портфель Piquadro Briefcase', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('42990'), None, '40x30x10', Decimal('1.1'), {'is_popular': True}),
                ],
            },
            {
                'group': 'sumki-braun-siena',
                'items': [
                    ('sumki', 'Braun Büffel', 'Кроссбоди Braun Büffel Siena', 'F', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('23890'), None, '24x18x6', Decimal('0.4'), {'is_new': True}),
                    ('sumki', 'Braun Büffel', 'Кроссбоди Braun Büffel Siena', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('23890'), None, '24x18x6', Decimal('0.4'), {}),
                ],
            },
            {
                'group': 'sumki-lacoste-shopper',
                'items': [
                    ('sumki', 'Lacoste', 'Шоппер Lacoste L.12.12', 'F', 'Зелёный', 'ПВХ',
                     Decimal('8990'), Decimal('10990'), '35x34x12', Decimal('0.35'), {'is_sale': True, 'is_popular': True}),
                    ('sumki', 'Lacoste', 'Шоппер Lacoste L.12.12', 'F', 'Чёрный', 'ПВХ',
                     Decimal('8990'), None, '35x34x12', Decimal('0.35'), {}),
                    ('sumki', 'Lacoste', 'Шоппер Lacoste L.12.12', 'F', 'Белый', 'ПВХ',
                     Decimal('8990'), None, '35x34x12', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'sumki-tous-kaos',
                'items': [
                    ('sumki', 'Tous', 'Шоппер Tous Kaos Mini', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('10490'), None, '28x24x10', Decimal('0.35'), {'is_new': True}),
                    ('sumki', 'Tous', 'Шоппер Tous Kaos Mini', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('10490'), None, '28x24x10', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'sumki-samsonite-venice',
                'items': [
                    ('sumki', 'Samsonite', 'Сумка-тоут Samsonite Venice', 'F', 'Чёрный', 'Полиэстер',
                     Decimal('7990'), None, '38x32x14', Decimal('0.5'), {'is_popular': True}),
                    ('sumki', 'Samsonite', 'Сумка-тоут Samsonite Venice', 'F', 'Серый', 'Полиэстер',
                     Decimal('7990'), None, '38x32x14', Decimal('0.5'), {}),
                ],
            },
            {
                'group': 'sumki-braun-brooklyn',
                'items': [
                    ('sumki', 'Braun Büffel', 'Тоут Braun Büffel Brooklyn', 'F', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('26990'), Decimal('29990'), '40x30x14', Decimal('0.85'), {'is_sale': True, 'is_new': True}),
                    ('sumki', 'Braun Büffel', 'Тоут Braun Büffel Brooklyn', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('26990'), None, '40x30x14', Decimal('0.85'), {}),
                ],
            },

            # ===== КОШЕЛЬКИ (8 моделей) =====
            {
                'group': 'kosh-tous-long',
                'items': [
                    ('koshelki', 'Tous', 'Кошелёк Tous Logo Long', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('7990'), None, '19x10x3', Decimal('0.15'), {'is_new': True}),
                    ('koshelki', 'Tous', 'Кошелёк Tous Logo Long', 'F', 'Бежевый', 'Натуральная кожа',
                     Decimal('7990'), None, '19x10x3', Decimal('0.15'), {}),
                ],
            },
            {
                'group': 'kosh-braun-vasco',
                'items': [
                    ('koshelki', 'Braun Büffel', 'Портмоне Braun Büffel Vasco', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('11490'), Decimal('13490'), '12x9.5x2', Decimal('0.12'), {'is_popular': True, 'is_sale': True}),
                    ('koshelki', 'Braun Büffel', 'Портмоне Braun Büffel Vasco', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('11490'), None, '12x9.5x2', Decimal('0.12'), {'is_popular': True}),
                ],
            },
            {
                'group': 'kosh-piquadro-slider',
                'items': [
                    ('koshelki', 'Piquadro', 'Картхолдер Piquadro Slider', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('5990'), None, '10.5x7.5x1', Decimal('0.06'), {'is_popular': True, 'is_new': True}),
                    ('koshelki', 'Piquadro', 'Картхолдер Piquadro Slider', 'M', 'Синий', 'Натуральная кожа',
                     Decimal('5990'), None, '10.5x7.5x1', Decimal('0.06'), {}),
                ],
            },
            {
                'group': 'kosh-lacoste-zip',
                'items': [
                    ('koshelki', 'Lacoste', 'Кошелёк Lacoste Zip', 'F', 'Белый', 'ПВХ',
                     Decimal('6490'), Decimal('7990'), '19x11x3', Decimal('0.14'), {'is_sale': True}),
                    ('koshelki', 'Lacoste', 'Кошелёк Lacoste Zip', 'F', 'Чёрный', 'ПВХ',
                     Decimal('6490'), None, '19x11x3', Decimal('0.14'), {}),
                ],
            },
            {
                'group': 'kosh-samsonite-slim',
                'items': [
                    ('koshelki', 'Samsonite', 'Кошелёк-слим Samsonite Slim', 'M', 'Чёрный', 'Полиуретан',
                     Decimal('3990'), None, '10x8x1.5', Decimal('0.07'), {'is_popular': True}),
                    ('koshelki', 'Samsonite', 'Кошелёк-слим Samsonite Slim', 'M', 'Тёмно-синий', 'Полиуретан',
                     Decimal('3990'), None, '10x8x1.5', Decimal('0.07'), {}),
                ],
            },
            {
                'group': 'kosh-piquadro-atlantic',
                'items': [
                    ('koshelki', 'Piquadro', 'Портмоне-трансформер Piquadro Atlantic', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('12990'), Decimal('14990'), '12x10x2.5', Decimal('0.14'), {'is_popular': True, 'is_sale': True}),
                    ('koshelki', 'Piquadro', 'Портмоне-трансформер Piquadro Atlantic', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('12990'), None, '12x10x2.5', Decimal('0.14'), {'is_new': True}),
                ],
            },
            {
                'group': 'kosh-braun-trento',
                'items': [
                    ('koshelki', 'Braun Büffel', 'Кошелёк Braun Büffel Trento', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('13990'), None, '18x9x3', Decimal('0.13'), {'is_new': True}),
                    ('koshelki', 'Braun Büffel', 'Кошелёк Braun Büffel Trento', 'F', 'Бордовый', 'Натуральная кожа',
                     Decimal('13990'), None, '18x9x3', Decimal('0.13'), {'is_popular': True}),
                ],
            },
            {
                'group': 'kosh-tous-mop',
                'items': [
                    ('koshelki', 'Tous', 'Монетница Tous Mother of Pearl', 'F', 'Бежевый', 'Натуральная кожа',
                     Decimal('4490'), None, '11x8x1.5', Decimal('0.05'), {'is_sale': True}),
                    ('koshelki', 'Tous', 'Монетница Tous Mother of Pearl', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('4490'), None, '11x8x1.5', Decimal('0.05'), {}),
                ],
            },

            # ===== РЮКЗАКИ (6 моделей) =====
            {
                'group': 'bp-lacoste-neocroc',
                'items': [
                    ('ryukzaki', 'Lacoste', 'Рюкзак Lacoste Neocroc', 'M', 'Синий', 'ПВХ',
                     Decimal('15990'), Decimal('18990'), '30x40x12', Decimal('0.5'), {'is_sale': True, 'is_popular': True}),
                    ('ryukzaki', 'Lacoste', 'Рюкзак Lacoste Neocroc', 'M', 'Чёрный', 'ПВХ',
                     Decimal('15990'), None, '30x40x12', Decimal('0.5'), {}),
                ],
            },
            {
                'group': 'bp-piquadro-business',
                'items': [
                    ('ryukzaki', 'Piquadro', 'Рюкзак Piquadro Business 15.6"', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('36990'), None, '42x32x14', Decimal('1.05'), {'is_popular': True, 'is_new': True}),
                    ('ryukzaki', 'Piquadro', 'Рюкзак Piquadro Business 15.6"', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('36990'), None, '42x32x14', Decimal('1.05'), {}),
                ],
            },
            {
                'group': 'bp-samsonite-guardit',
                'items': [
                    ('ryukzaki', 'Samsonite', 'Рюкзак Samsonite Guardit 2.0', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('12490'), None, '44x32x15', Decimal('0.7'), {'is_popular': True}),
                    ('ryukzaki', 'Samsonite', 'Рюкзак Samsonite Guardit 2.0', 'M', 'Серый', 'Полиэстер',
                     Decimal('12490'), None, '44x32x15', Decimal('0.7'), {}),
                ],
            },
            {
                'group': 'bp-samsonite-flapover',
                'items': [
                    ('ryukzaki', 'Samsonite', 'Рюкзак Samsonite Flapover 2.0', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('15990'), Decimal('18490'), '46x32x15', Decimal('0.75'), {'is_sale': True, 'is_popular': True}),
                    ('ryukzaki', 'Samsonite', 'Рюкзак Samsonite Flapover 2.0', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('15990'), None, '46x32x15', Decimal('0.75'), {}),
                ],
            },
            {
                'group': 'bp-roncato-urban',
                'items': [
                    ('ryukzaki', 'Roncato', 'Городской рюкзак Roncato Urban', 'M', 'Серый', 'Полиэстер',
                     Decimal('8990'), None, '40x30x13', Decimal('0.5'), {'is_popular': True}),
                    ('ryukzaki', 'Roncato', 'Городской рюкзак Roncato Urban', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('8990'), None, '40x30x13', Decimal('0.5'), {'is_new': True}),
                ],
            },
            {
                'group': 'bp-tous-mini',
                'items': [
                    ('ryukzaki', 'Tous', 'Рюкзак-мини Tous Bear', 'F', 'Кремовый', 'ПВХ',
                     Decimal('11490'), None, '28x34x12', Decimal('0.4'), {'is_new': True, 'is_popular': True}),
                    ('ryukzaki', 'Tous', 'Рюкзак-мини Tous Bear', 'F', 'Розовый', 'ПВХ',
                     Decimal('11490'), None, '28x34x12', Decimal('0.4'), {}),
                ],
            },

            # ===== РЕМНИ (5 моделей) =====
            {
                'group': 'rem-braun-classic',
                'items': [
                    ('remni', 'Braun Büffel', 'Ремень Braun Büffel Classic', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {'is_popular': True}),
                    ('remni', 'Braun Büffel', 'Ремень Braun Büffel Classic', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {}),
                    ('remni', 'Braun Büffel', 'Ремень Braun Büffel Classic', 'M', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {}),
                ],
            },
            {
                'group': 'rem-piquadro-buckle',
                'items': [
                    ('remni', 'Piquadro', 'Ремень Piquadro SB3 X-Fatto', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('11990'), Decimal('13990'), 'на ремень', Decimal('0.2'), {'is_sale': True, 'is_popular': True}),
                    ('remni', 'Piquadro', 'Ремень Piquadro SB3 X-Fatto', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('11990'), None, 'на ремень', Decimal('0.2'), {}),
                ],
            },
            {
                'group': 'rem-samsonite-tech',
                'items': [
                    ('remni', 'Samsonite', 'Ремень Samsonite Tech', 'M', 'Чёрный', 'Полиуретан',
                     Decimal('2990'), None, 'на ремень', Decimal('0.12'), {'is_popular': True}),
                    ('remni', 'Samsonite', 'Ремень Samsonite Tech', 'M', 'Серый', 'Полиуретан',
                     Decimal('2990'), None, 'на ремень', Decimal('0.12'), {}),
                ],
            },
            {
                'group': 'rem-lacoste-woven',
                'items': [
                    ('remni', 'Lacoste', 'Ремень плетёный Lacoste Classic', 'M', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('5490'), None, 'на ремень', Decimal('0.15'), {'is_new': True}),
                    ('remni', 'Lacoste', 'Ремень плетёный Lacoste Classic', 'M', 'Бордовый', 'Натуральная кожа',
                     Decimal('5490'), None, 'на ремень', Decimal('0.15'), {}),
                ],
            },
            {
                'group': 'rem-roncato-travel',
                'items': [
                    ('remni', 'Roncato', 'Дорожный ремень Roncato Travel', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('4990'), Decimal('5990'), 'на ремень', Decimal('0.17'), {'is_sale': True}),
                    ('remni', 'Roncato', 'Дорожный ремень Roncato Travel', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('4990'), None, 'на ремень', Decimal('0.17'), {}),
                ],
            },

            # ===== ЗОНТЫ (5 моделей) =====
            {
                'group': 'zont-samsonite-auto',
                'items': [
                    ('zonty', 'Samsonite', 'Зонт Samsonite Auto Open', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('4990'), None, 'D=100', Decimal('0.4'), {'is_popular': True}),
                    ('zonty', 'Samsonite', 'Зонт Samsonite Auto Open', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('4990'), None, 'D=100', Decimal('0.4'), {}),
                ],
            },
            {
                'group': 'zont-lacoste-compact',
                'items': [
                    ('zonty', 'Lacoste', 'Зонт Lacoste Compact', 'F', 'Бордовый', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {'is_new': True}),
                    ('zonty', 'Lacoste', 'Зонт Lacoste Compact', 'F', 'Чёрный', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {}),
                    ('zonty', 'Lacoste', 'Зонт Lacoste Compact', 'F', 'Кремовый', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'zont-samsonite-inverness',
                'items': [
                    ('zonty', 'Samsonite', 'Зонт Samsonite Inverness', 'M', 'Чёрный', 'Нейлон',
                     Decimal('6490'), Decimal('7490'), 'D=105', Decimal('0.45'), {'is_popular': True, 'is_sale': True}),
                    ('zonty', 'Samsonite', 'Зонт Samsonite Inverness', 'M', 'Тёмно-зелёный', 'Нейлон',
                     Decimal('6490'), None, 'D=105', Decimal('0.45'), {}),
                ],
            },
            {
                'group': 'zont-roncato-wind',
                'items': [
                    ('zonty', 'Roncato', 'Зонт ветрозащитный Roncato Compact', 'M', 'Серый', 'Полиэстер',
                     Decimal('3990'), None, 'D=98', Decimal('0.38'), {'is_new': True}),
                    ('zonty', 'Roncato', 'Зонт ветрозащитный Roncato Compact', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('3990'), None, 'D=98', Decimal('0.38'), {}),
                ],
            },
            {
                'group': 'zont-braun-auto',
                'items': [
                    ('zonty', 'Braun Büffel', 'Автоматический зонт Braun Büffel', 'F', 'Красный', 'Полиэстер',
                     Decimal('6990'), None, 'D=100', Decimal('0.42'), {'is_popular': True, 'is_new': True}),
                    ('zonty', 'Braun Büffel', 'Автоматический зонт Braun Büffel', 'F', 'Бежевый', 'Полиэстер',
                     Decimal('6990'), None, 'D=100', Decimal('0.42'), {}),
                ],
            },

            # ===== ДОРОЖНЫЕ СУМКИ (5 моделей) =====
            {
                'group': 'duff-samsonite-midtown',
                'items': [
                    ('dorozhnye-sumki', 'Samsonite', 'Дуфл Samsonite Midtown', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('9990'), Decimal('12490'), '50x28x26', Decimal('0.9'), {'is_sale': True, 'is_new': True}),
                    ('dorozhnye-sumki', 'Samsonite', 'Дуфл Samsonite Midtown', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('9990'), None, '50x28x26', Decimal('0.9'), {}),
                ],
            },
            {
                'group': 'duff-lacoste-sport',
                'items': [
                    ('dorozhnye-sumki', 'Lacoste', 'Спортивная сумка Lacoste Sport', 'M', 'Бордовый', 'Полиэстер',
                     Decimal('8490'), None, '52x26x24', Decimal('0.6'), {}),
                    ('dorozhnye-sumki', 'Lacoste', 'Спортивная сумка Lacoste Sport', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('8490'), None, '52x26x24', Decimal('0.6'), {}),
                ],
            },
            {
                'group': 'duff-roncato-weekender',
                'items': [
                    ('dorozhnye-sumki', 'Roncato', 'Выходная дорожная сумка Roncato Weekender', 'F', 'Тёмно-зелёный', 'Полиэстер',
                     Decimal('7490'), Decimal('8990'), '48x28x24', Decimal('0.8'), {'is_sale': True, 'is_popular': True}),
                    ('dorozhnye-sumki', 'Roncato', 'Выходная дорожная сумка Roncato Weekender', 'F', 'Серый', 'Полиэстер',
                     Decimal('7490'), None, '48x28x24', Decimal('0.8'), {}),
                ],
            },
            {
                'group': 'duff-samsonite-trolley',
                'items': [
                    ('dorozhnye-sumki', 'Samsonite', 'Сумка на колёсиках Samsonite Trolley', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('13490'), None, '46x38x25', Decimal('1.6'), {'is_popular': True}),
                    ('dorozhnye-sumki', 'Samsonite', 'Сумка на колёсиках Samsonite Trolley', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('13490'), None, '46x38x25', Decimal('1.6'), {}),
                ],
            },
            {
                'group': 'duff-piquadro-business',
                'items': [
                    ('dorozhnye-sumki', 'Piquadro', 'Бизнес-сумка Piquadro Travel', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('27990'), Decimal('31990'), '50x30x24', Decimal('1.4'), {'is_popular': True, 'is_sale': True}),
                    ('dorozhnye-sumki', 'Piquadro', 'Бизнес-сумка Piquadro Travel', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('27990'), None, '50x30x24', Decimal('1.4'), {}),
                ],
            },

            # ===== ЧЕМОДАНЫ (8 моделей) =====
            {
                'group': 'chem-samsonite-lite20',
                'items': [
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite Lite-Shock 20"', 'M', 'Синий', 'Полипропилен',
                     Decimal('32990'), Decimal('38990'), '55x40x20', Decimal('2.1'), {'is_popular': True, 'is_sale': True}),
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite Lite-Shock 20"', 'M', 'Чёрный', 'Полипропилен',
                     Decimal('32990'), None, '55x40x20', Decimal('2.1'), {'is_popular': True}),
                ],
            },
            {
                'group': 'chem-samsonite-clite24',
                'items': [
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite C-Lite 24"', 'M', 'Чёрный', 'Curv',
                     Decimal('41990'), None, '67x45x28', Decimal('2.7'), {'is_popular': True}),
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite C-Lite 24"', 'M', 'Серый', 'Curv',
                     Decimal('41990'), None, '67x45x28', Decimal('2.7'), {}),
                ],
            },
            {
                'group': 'chem-roncato-young28',
                'items': [
                    ('chemodany', 'Roncato', 'Чемодан Roncato Young 28"', 'M', 'Красный', 'Makrolon',
                     Decimal('29890'), Decimal('34990'), '77x52x30', Decimal('3.4'), {'is_new': True, 'is_sale': True}),
                    ('chemodany', 'Roncato', 'Чемодан Roncato Young 28"', 'M', 'Чёрный', 'Makrolon',
                     Decimal('29890'), None, '77x52x30', Decimal('3.4'), {}),
                ],
            },
            {
                'group': 'chem-roncato-box20',
                'items': [
                    ('chemodany', 'Roncato', 'Чемодан Roncato Box 2.0 Cabin 20"', 'M', 'Тёмно-зелёный', 'Makrolon',
                     Decimal('25990'), None, '55x40x20', Decimal('2.3'), {'is_popular': True}),
                    ('chemodany', 'Roncato', 'Чемодан Roncato Box 2.0 Cabin 20"', 'M', 'Серый', 'Makrolon',
                     Decimal('25990'), None, '55x40x20', Decimal('2.3'), {}),
                ],
            },
            {
                'group': 'chem-samsonite-base28',
                'items': [
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite Base Boost 28"', 'M', 'Серый', 'Полиэстер',
                     Decimal('27490'), Decimal('32990'), '78x52x31', Decimal('3.8'), {'is_sale': True}),
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite Base Boost 28"', 'M', 'Синий', 'Полиэстер',
                     Decimal('27490'), None, '78x52x31', Decimal('3.8'), {}),
                ],
            },
            {
                'group': 'chem-roncato-ironik24',
                'items': [
                    ('chemodany', 'Roncato', 'Чемодан Roncato Ironik 24"', 'M', 'Чёрный', 'Makrolon',
                     Decimal('31990'), Decimal('36990'), '65x42x27', Decimal('2.8'), {'is_popular': True, 'is_sale': True}),
                    ('chemodany', 'Roncato', 'Чемодан Roncato Ironik 24"', 'M', 'Красный', 'Makrolon',
                     Decimal('31990'), None, '65x42x27', Decimal('2.8'), {}),
                ],
            },
            {
                'group': 'chem-samsonite-scure24',
                'items': [
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite S\'Cure Spinner 24"', 'F', 'Серебристый', 'Поликарбонат',
                     Decimal('35990'), None, '66x45x30', Decimal('3.9'), {'is_popular': True, 'is_new': True}),
                    ('chemodany', 'Samsonite', 'Чемодан Samsonite S\'Cure Spinner 24"', 'F', 'Фиолетовый', 'Поликарбонат',
                     Decimal('35990'), None, '66x45x30', Decimal('3.9'), {}),
                ],
            },
            {
                'group': 'chem-roncato-okmini28',
                'items': [
                    ('chemodany', 'Roncato', 'Чемодан Roncato Ok Mini 28"', 'F', 'Розовый', 'Makrolon',
                     Decimal('24990'), Decimal('28990'), '76x54x31', Decimal('3.5'), {'is_sale': True}),
                    ('chemodany', 'Roncato', 'Чемодан Roncato Ok Mini 28"', 'F', 'Серебристый', 'Makrolon',
                     Decimal('24990'), None, '76x54x31', Decimal('3.5'), {'is_new': True}),
                ],
            },

            # ===== АКСЕССУАРЫ (5 моделей) =====
            {
                'group': 'acc-piquadro-passport',
                'items': [
                    ('aksessuary', 'Piquadro', 'Обложка на паспорт Piquadro', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('4290'), Decimal('4990'), '14x10x1', Decimal('0.05'), {'is_new': True, 'is_sale': True}),
                    ('aksessuary', 'Piquadro', 'Обложка на паспорт Piquadro', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('4290'), None, '14x10x1', Decimal('0.05'), {}),
                ],
            },
            {
                'group': 'acc-tous-pen',
                'items': [
                    ('aksessuary', 'Tous', 'Пенал Tous Mini', 'F', 'Бежевый', 'ПВХ',
                     Decimal('3490'), None, '20x8x5', Decimal('0.09'), {}),
                    ('aksessuary', 'Tous', 'Пенал Tous Mini', 'F', 'Розовый', 'ПВХ',
                     Decimal('3490'), None, '20x8x5', Decimal('0.09'), {}),
                ],
            },
            {
                'group': 'acc-piquadro-keycase',
                'items': [
                    ('aksessuary', 'Piquadro', 'Ключница Piquadro Key Case', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('2990'), None, '9x6x2', Decimal('0.04'), {'is_popular': True}),
                    ('aksessuary', 'Piquadro', 'Ключница Piquadro Key Case', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('2990'), None, '9x6x2', Decimal('0.04'), {}),
                ],
            },
            {
                'group': 'acc-samsonite-tags',
                'items': [
                    ('aksessuary', 'Samsonite', 'Набор багажных бирок Samsonite', 'M', 'Чёрный', 'Кожа',
                     Decimal('2490'), Decimal('2990'), '12x8x2', Decimal('0.05'), {'is_sale': True, 'is_popular': True}),
                    ('aksessuary', 'Samsonite', 'Набор багажных бирок Samsonite', 'M', 'Красный', 'Кожа',
                     Decimal('2490'), None, '12x8x2', Decimal('0.05'), {}),
                ],
            },
            {
                'group': 'acc-braun-glasses',
                'items': [
                    ('aksessuary', 'Braun Büffel', 'Футляр для очков Braun Büffel', 'F', 'Коричневый', 'Натуральная кожа',
                     Decimal('3990'), None, '16x6x4', Decimal('0.06'), {'is_new': True}),
                    ('aksessuary', 'Braun Büffel', 'Футляр для очков Braun Büffel', 'F', 'Бордовый', 'Натуральная кожа',
                     Decimal('3990'), None, '16x6x4', Decimal('0.06'), {}),
                ],
            },
        ]

        product_idx = 0
        for group_data in products_seed:
            group_uuid = uuid.uuid4()
            for (cat_slug, brand_name, pname, gender, color, material,
                 price, old_price, dims, weight, flags) in group_data['items']:

                # Переносим товары из корня в подкатегорию по полу
                effective_slug = cat_slug
                if cat_slug in sub_data:
                    effective_slug = f'{cat_slug}-{"muzhskie" if gender == "M" else "zhenskie"}'
                category = cat_objs.get(effective_slug)
                if not category:
                    self.stderr.write(f'Skip {pname}: no category {effective_slug}')
                    continue
                brand = brands.get(brand_name)

                slug_base = _slug(f'{pname} {color}')
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
                        'gender': gender,
                        'group_id': group_uuid,
                        'price': price,
                        'old_price': old_price,
                        'cost_price': (price * Decimal('0.6')).quantize(price),
                        'discount_percent': (int((old_price - price) / old_price * 100) if old_price and old_price > price else 0),
                        'stock': 15 + product_idx % 30,
                        'sku': f'EDV-{1000 + product_idx:04d}',
                        'short_description': f'{pname} — качественное изделие от бренда {brand_name}. '
                                             f'Материал: {material}. Цвет: {color}.',
                        'description': (
                            f'{pname} — модель от бренда {brand_name}.\n\n'
                            f'Основные характеристики:\n'
                            f'• Материал: {material}\n'
                            f'• Цвет: {color}\n'
                            f'• Размеры: {dims}\n'
                            f'• Вес: {weight} кг\n'
                            f'• Пол: {"Мужской" if gender == "M" else "Женский"}\n\n'
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

                for img_pos in range(3):
                    svg_bytes = _svg(pname[:18] + f' [{img_pos+1}]', product_idx + img_pos).encode('utf-8')
                    ProductImage.objects.create(
                        product=p,
                        image=ContentFile(svg_bytes, name=f'{slug}-{img_pos+1}.svg'),
                        alt=f'{pname} {color} — фото {img_pos + 1}',
                        is_main=(img_pos == 0),
                        order=img_pos,
                    )

                self.stdout.write(self.style.SUCCESS(f'  {p.name} — {p.color}'))
                product_idx += 1

        groups = Product.objects.values('group_id').distinct().count()
        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete: Brands={Brand.objects.count()}, '
            f'Categories={Category.objects.count()}, '
            f'Products={Product.objects.count()} (моделей/групп цветов: {groups}), '
            f'Images={ProductImage.objects.count()}.'
        ))