from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify

from app_catalog.models import Category, Product, ProductVariant, ProductImage
from app_cart.models import PromoCode
from app_home.models import SiteReview


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


TRANSLIT_DICT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}

_TRANSLIT_TABLE = str.maketrans(TRANSLIT_DICT)


def _translit(text):
    return text.lower().translate(_TRANSLIT_TABLE)


def _slug(text):
    return slugify(_translit(text))


class Command(BaseCommand):
    help = "Seed demo data: 8 categories, 50 product models with color variants"

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Clear catalog data first')

    def handle(self, *args, **options):
        if options.get('flush'):
            ProductImage.objects.all().delete()
            ProductVariant.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            PromoCode.objects.all().delete()
            SiteReview.objects.all().delete()
            self.stdout.write(self.style.WARNING('Flushed catalog data'))

        # ---------- Categories (корень + подкатегории) ----------
        # has_gender=False — категория без деления на мужские/женские
        cats_data = [
            ('Сумки', 'sumki', 0, True),
            ('Кошельки', 'koshelki', 1, True),
            ('Рюкзаки', 'ryukzaki', 2, True),
            ('Ремни', 'remni', 3, True),
            ('Зонты', 'zonty', 4, False),
            ('Дорожные сумки', 'dorozhnye-sumki', 5, True),
            ('Чемоданы', 'chemodany', 6, True),
            ('Аксессуары', 'aksessuary', 7, True),
        ]
        cat_objs = {}
        for name, slug, order, has_gender in cats_data:
            c, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name, 'order': order, 'description': name,
                    'has_gender': has_gender,
                }
            )
            if c.has_gender != has_gender:
                c.has_gender = has_gender
                c.save(update_fields=['has_gender'])
            cat_objs[slug] = c

        # =====================================================
        # ТОВАРЫ — 50 моделей в разных цветах. Каждая группа = одна
        # модель Product + ProductVariant на каждый цвет.
        # Формат: (category_slug, name, gender, color, material,
        #          final_price, base_price, dims, weight, flags)
        #   final_price — продажная цена без скидки,
        #   base_price  — базовая цена «до скидки». Если она больше
        #                 final_price, варианту ставится price=base_price и
        #                 discount_percent, чтобы цена со скидкой была
        #                 близка к final_price.
        # =====================================================

        products_seed = [
            # ===== СУМКИ (8 моделей) =====
            {
                'group': 'sumki-lacoste-nf2148',
                'items': [
                    ('sumki', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Бордовый', 'Хлопок',
                     Decimal('12990'), Decimal('15990'), '38x30x14', Decimal('0.45'), {'is_popular': True, 'is_sale': True}),
                    ('sumki', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Чёрный', 'Хлопок',
                     Decimal('12990'), None, '38x30x14', Decimal('0.45'), {'is_popular': True}),
                    ('sumki', 'Сумка-шоппер Lacoste NF.2148', 'F', 'Синий', 'Хлопок',
                     Decimal('12990'), None, '38x30x14', Decimal('0.45'), {}),
                ],
            },
            {
                'group': 'sumki-tous-crossbody',
                'items': [
                    ('sumki', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {'is_new': True, 'is_popular': True}),
                    ('sumki', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {'is_new': True}),
                    ('sumki', 'Кожаная сумка Tous Mini Crossbody', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('18500'), None, '22x18x8', Decimal('0.38'), {}),
                ],
            },
            {
                'group': 'sumki-piquadro-briefcase',
                'items': [
                    ('sumki', 'Портфель Piquadro Briefcase', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('42990'), Decimal('49990'), '40x30x10', Decimal('1.1'), {'is_popular': True, 'is_sale': True}),
                    ('sumki', 'Портфель Piquadro Briefcase', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('42990'), None, '40x30x10', Decimal('1.1'), {'is_popular': True}),
                ],
            },
            {
                'group': 'sumki-braun-siena',
                'items': [
                    ('sumki', 'Кроссбоди Braun Büffel Siena', 'F', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('23890'), None, '24x18x6', Decimal('0.4'), {'is_new': True}),
                    ('sumki', 'Кроссбоди Braun Büffel Siena', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('23890'), None, '24x18x6', Decimal('0.4'), {}),
                ],
            },
            {
                'group': 'sumki-lacoste-shopper',
                'items': [
                    ('sumki', 'Шоппер Lacoste L.12.12', 'F', 'Зелёный', 'ПВХ',
                     Decimal('8990'), Decimal('10990'), '35x34x12', Decimal('0.35'), {'is_sale': True, 'is_popular': True}),
                    ('sumki', 'Шоппер Lacoste L.12.12', 'F', 'Чёрный', 'ПВХ',
                     Decimal('8990'), None, '35x34x12', Decimal('0.35'), {}),
                    ('sumki', 'Шоппер Lacoste L.12.12', 'F', 'Белый', 'ПВХ',
                     Decimal('8990'), None, '35x34x12', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'sumki-tous-kaos',
                'items': [
                    ('sumki', 'Шоппер Tous Kaos Mini', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('10490'), None, '28x24x10', Decimal('0.35'), {'is_new': True}),
                    ('sumki', 'Шоппер Tous Kaos Mini', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('10490'), None, '28x24x10', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'sumki-samsonite-venice',
                'items': [
                    ('sumki', 'Сумка-тоут Samsonite Venice', 'F', 'Чёрный', 'Полиэстер',
                     Decimal('7990'), None, '38x32x14', Decimal('0.5'), {'is_popular': True}),
                    ('sumki', 'Сумка-тоут Samsonite Venice', 'F', 'Серый', 'Полиэстер',
                     Decimal('7990'), None, '38x32x14', Decimal('0.5'), {}),
                ],
            },
            {
                'group': 'sumki-braun-brooklyn',
                'items': [
                    ('sumki', 'Тоут Braun Büffel Brooklyn', 'F', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('26990'), Decimal('29990'), '40x30x14', Decimal('0.85'), {'is_sale': True, 'is_new': True}),
                    ('sumki', 'Тоут Braun Büffel Brooklyn', 'F', 'Чёрный', 'Натуральная кожа',
                     Decimal('26990'), None, '40x30x14', Decimal('0.85'), {}),
                ],
            },

            # ===== КОШЕЛЬКИ (8 моделей) =====
            {
                'group': 'kosh-tous-long',
                'items': [
                    ('koshelki', 'Кошелёк Tous Logo Long', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('7990'), None, '19x10x3', Decimal('0.15'), {'is_new': True}),
                    ('koshelki', 'Кошелёк Tous Logo Long', 'F', 'Бежевый', 'Натуральная кожа',
                     Decimal('7990'), None, '19x10x3', Decimal('0.15'), {}),
                ],
            },
            {
                'group': 'kosh-braun-vasco',
                'items': [
                    ('koshelki', 'Портмоне Braun Büffel Vasco', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('11490'), Decimal('13490'), '12x9.5x2', Decimal('0.12'), {'is_popular': True, 'is_sale': True}),
                    ('koshelki', 'Портмоне Braun Büffel Vasco', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('11490'), None, '12x9.5x2', Decimal('0.12'), {'is_popular': True}),
                ],
            },
            {
                'group': 'kosh-piquadro-slider',
                'items': [
                    ('koshelki', 'Картхолдер Piquadro Slider', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('5990'), None, '10.5x7.5x1', Decimal('0.06'), {'is_popular': True, 'is_new': True}),
                    ('koshelki', 'Картхолдер Piquadro Slider', 'M', 'Синий', 'Натуральная кожа',
                     Decimal('5990'), None, '10.5x7.5x1', Decimal('0.06'), {}),
                ],
            },
            {
                'group': 'kosh-lacoste-zip',
                'items': [
                    ('koshelki', 'Кошелёк Lacoste Zip', 'F', 'Белый', 'ПВХ',
                     Decimal('6490'), Decimal('7990'), '19x11x3', Decimal('0.14'), {'is_sale': True}),
                    ('koshelki', 'Кошелёк Lacoste Zip', 'F', 'Чёрный', 'ПВХ',
                     Decimal('6490'), None, '19x11x3', Decimal('0.14'), {}),
                ],
            },
            {
                'group': 'kosh-samsonite-slim',
                'items': [
                    ('koshelki', 'Кошелёк-слим Samsonite Slim', 'M', 'Чёрный', 'Полиуретан',
                     Decimal('3990'), None, '10x8x1.5', Decimal('0.07'), {'is_popular': True}),
                    ('koshelki', 'Кошелёк-слим Samsonite Slim', 'M', 'Тёмно-синий', 'Полиуретан',
                     Decimal('3990'), None, '10x8x1.5', Decimal('0.07'), {}),
                ],
            },
            {
                'group': 'kosh-piquadro-atlantic',
                'items': [
                    ('koshelki', 'Портмоне-трансформер Piquadro Atlantic', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('12990'), Decimal('14990'), '12x10x2.5', Decimal('0.14'), {'is_popular': True, 'is_sale': True}),
                    ('koshelki', 'Портмоне-трансформер Piquadro Atlantic', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('12990'), None, '12x10x2.5', Decimal('0.14'), {'is_new': True}),
                ],
            },
            {
                'group': 'kosh-braun-trento',
                'items': [
                    ('koshelki', 'Кошелёк Braun Büffel Trento', 'F', 'Кремовый', 'Натуральная кожа',
                     Decimal('13990'), None, '18x9x3', Decimal('0.13'), {'is_new': True}),
                    ('koshelki', 'Кошелёк Braun Büffel Trento', 'F', 'Бордовый', 'Натуральная кожа',
                     Decimal('13990'), None, '18x9x3', Decimal('0.13'), {'is_popular': True}),
                ],
            },
            {
                'group': 'kosh-tous-mop',
                'items': [
                    ('koshelki', 'Монетница Tous Mother of Pearl', 'F', 'Бежевый', 'Натуральная кожа',
                     Decimal('4490'), None, '11x8x1.5', Decimal('0.05'), {'is_sale': True}),
                    ('koshelki', 'Монетница Tous Mother of Pearl', 'F', 'Розовый', 'Натуральная кожа',
                     Decimal('4490'), None, '11x8x1.5', Decimal('0.05'), {}),
                ],
            },

            # ===== РЮКЗАКИ (6 моделей) =====
            {
                'group': 'bp-lacoste-neocroc',
                'items': [
                    ('ryukzaki', 'Рюкзак Lacoste Neocroc', 'M', 'Синий', 'ПВХ',
                     Decimal('15990'), Decimal('18990'), '30x40x12', Decimal('0.5'), {'is_sale': True, 'is_popular': True}),
                    ('ryukzaki', 'Рюкзак Lacoste Neocroc', 'M', 'Чёрный', 'ПВХ',
                     Decimal('15990'), None, '30x40x12', Decimal('0.5'), {}),
                ],
            },
            {
                'group': 'bp-piquadro-business',
                'items': [
                    ('ryukzaki', 'Рюкзак Piquadro Business 15.6"', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('36990'), None, '42x32x14', Decimal('1.05'), {'is_popular': True, 'is_new': True}),
                    ('ryukzaki', 'Рюкзак Piquadro Business 15.6"', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('36990'), None, '42x32x14', Decimal('1.05'), {}),
                ],
            },
            {
                'group': 'bp-samsonite-guardit',
                'items': [
                    ('ryukzaki', 'Рюкзак Samsonite Guardit 2.0', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('12490'), None, '44x32x15', Decimal('0.7'), {'is_popular': True}),
                    ('ryukzaki', 'Рюкзак Samsonite Guardit 2.0', 'M', 'Серый', 'Полиэстер',
                     Decimal('12490'), None, '44x32x15', Decimal('0.7'), {}),
                ],
            },
            {
                'group': 'bp-samsonite-flapover',
                'items': [
                    ('ryukzaki', 'Рюкзак Samsonite Flapover 2.0', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('15990'), Decimal('18490'), '46x32x15', Decimal('0.75'), {'is_sale': True, 'is_popular': True}),
                    ('ryukzaki', 'Рюкзак Samsonite Flapover 2.0', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('15990'), None, '46x32x15', Decimal('0.75'), {}),
                ],
            },
            {
                'group': 'bp-roncato-urban',
                'items': [
                    ('ryukzaki', 'Городской рюкзак Roncato Urban', 'M', 'Серый', 'Полиэстер',
                     Decimal('8990'), None, '40x30x13', Decimal('0.5'), {'is_popular': True}),
                    ('ryukzaki', 'Городской рюкзак Roncato Urban', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('8990'), None, '40x30x13', Decimal('0.5'), {'is_new': True}),
                ],
            },
            {
                'group': 'bp-tous-mini',
                'items': [
                    ('ryukzaki', 'Рюкзак-мини Tous Bear', 'F', 'Кремовый', 'ПВХ',
                     Decimal('11490'), None, '28x34x12', Decimal('0.4'), {'is_new': True, 'is_popular': True}),
                    ('ryukzaki', 'Рюкзак-мини Tous Bear', 'F', 'Розовый', 'ПВХ',
                     Decimal('11490'), None, '28x34x12', Decimal('0.4'), {}),
                ],
            },

            # ===== РЕМНИ (5 моделей) =====
            {
                'group': 'rem-braun-classic',
                'items': [
                    ('remni', 'Ремень Braun Büffel Classic', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {'is_popular': True}),
                    ('remni', 'Ремень Braun Büffel Classic', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {}),
                    ('remni', 'Ремень Braun Büffel Classic', 'M', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('6990'), None, 'на ремень', Decimal('0.18'), {}),
                ],
            },
            {
                'group': 'rem-piquadro-buckle',
                'items': [
                    ('remni', 'Ремень Piquadro SB3 X-Fatto', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('11990'), Decimal('13990'), 'на ремень', Decimal('0.2'), {'is_sale': True, 'is_popular': True}),
                    ('remni', 'Ремень Piquadro SB3 X-Fatto', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('11990'), None, 'на ремень', Decimal('0.2'), {}),
                ],
            },
            {
                'group': 'rem-samsonite-tech',
                'items': [
                    ('remni', 'Ремень Samsonite Tech', 'M', 'Чёрный', 'Полиуретан',
                     Decimal('2990'), None, 'на ремень', Decimal('0.12'), {'is_popular': True}),
                    ('remni', 'Ремень Samsonite Tech', 'M', 'Серый', 'Полиуретан',
                     Decimal('2990'), None, 'на ремень', Decimal('0.12'), {}),
                ],
            },
            {
                'group': 'rem-lacoste-woven',
                'items': [
                    ('remni', 'Ремень плетёный Lacoste Classic', 'M', 'Тёмно-синий', 'Натуральная кожа',
                     Decimal('5490'), None, 'на ремень', Decimal('0.15'), {'is_new': True}),
                    ('remni', 'Ремень плетёный Lacoste Classic', 'M', 'Бордовый', 'Натуральная кожа',
                     Decimal('5490'), None, 'на ремень', Decimal('0.15'), {}),
                ],
            },
            {
                'group': 'rem-roncato-travel',
                'items': [
                    ('remni', 'Дорожный ремень Roncato Travel', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('4990'), Decimal('5990'), 'на ремень', Decimal('0.17'), {'is_sale': True}),
                    ('remni', 'Дорожный ремень Roncato Travel', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('4990'), None, 'на ремень', Decimal('0.17'), {}),
                ],
            },

            # ===== ЗОНТЫ (5 моделей, унисекс) =====
            {
                'group': 'zont-samsonite-auto',
                'items': [
                    ('zonty', 'Зонт Samsonite Auto Open', None, 'Чёрный', 'Полиэстер',
                     Decimal('4990'), None, 'D=100', Decimal('0.4'), {'is_popular': True}),
                    ('zonty', 'Зонт Samsonite Auto Open', None, 'Тёмно-синий', 'Полиэстер',
                     Decimal('4990'), None, 'D=100', Decimal('0.4'), {}),
                ],
            },
            {
                'group': 'zont-lacoste-compact',
                'items': [
                    ('zonty', 'Зонт Lacoste Compact', None, 'Бордовый', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {'is_new': True}),
                    ('zonty', 'Зонт Lacoste Compact', None, 'Чёрный', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {}),
                    ('zonty', 'Зонт Lacoste Compact', None, 'Кремовый', 'Полиэстер',
                     Decimal('5990'), None, 'D=95', Decimal('0.35'), {}),
                ],
            },
            {
                'group': 'zont-samsonite-inverness',
                'items': [
                    ('zonty', 'Зонт Samsonite Inverness', None, 'Чёрный', 'Нейлон',
                     Decimal('6490'), Decimal('7490'), 'D=105', Decimal('0.45'), {'is_popular': True, 'is_sale': True}),
                    ('zonty', 'Зонт Samsonite Inverness', None, 'Тёмно-зелёный', 'Нейлон',
                     Decimal('6490'), None, 'D=105', Decimal('0.45'), {}),
                ],
            },
            {
                'group': 'zont-roncato-wind',
                'items': [
                    ('zonty', 'Зонт ветрозащитный Roncato Compact', None, 'Серый', 'Полиэстер',
                     Decimal('3990'), None, 'D=98', Decimal('0.38'), {'is_new': True}),
                    ('zonty', 'Зонт ветрозащитный Roncato Compact', None, 'Чёрный', 'Полиэстер',
                     Decimal('3990'), None, 'D=98', Decimal('0.38'), {}),
                ],
            },
            {
                'group': 'zont-braun-auto',
                'items': [
                    ('zonty', 'Автоматический зонт Braun Büffel', None, 'Красный', 'Полиэстер',
                     Decimal('6990'), None, 'D=100', Decimal('0.42'), {'is_popular': True, 'is_new': True}),
                    ('zonty', 'Автоматический зонт Braun Büffel', None, 'Бежевый', 'Полиэстер',
                     Decimal('6990'), None, 'D=100', Decimal('0.42'), {}),
                ],
            },

            # ===== ДОРОЖНЫЕ СУМКИ (5 моделей) =====
            {
                'group': 'duff-samsonite-midtown',
                'items': [
                    ('dorozhnye-sumki', 'Дуфл Samsonite Midtown', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('9990'), Decimal('12490'), '50x28x26', Decimal('0.9'), {'is_sale': True, 'is_new': True}),
                    ('dorozhnye-sumki', 'Дуфл Samsonite Midtown', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('9990'), None, '50x28x26', Decimal('0.9'), {}),
                ],
            },
            {
                'group': 'duff-lacoste-sport',
                'items': [
                    ('dorozhnye-sumki', 'Спортивная сумка Lacoste Sport', 'M', 'Бордовый', 'Полиэстер',
                     Decimal('8490'), None, '52x26x24', Decimal('0.6'), {}),
                    ('dorozhnye-sumki', 'Спортивная сумка Lacoste Sport', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('8490'), None, '52x26x24', Decimal('0.6'), {}),
                ],
            },
            {
                'group': 'duff-roncato-weekender',
                'items': [
                    ('dorozhnye-sumki', 'Выходная дорожная сумка Roncato Weekender', 'F', 'Тёмно-зелёный', 'Полиэстер',
                     Decimal('7490'), Decimal('8990'), '48x28x24', Decimal('0.8'), {'is_sale': True, 'is_popular': True}),
                    ('dorozhnye-sumki', 'Выходная дорожная сумка Roncato Weekender', 'F', 'Серый', 'Полиэстер',
                     Decimal('7490'), None, '48x28x24', Decimal('0.8'), {}),
                ],
            },
            {
                'group': 'duff-samsonite-trolley',
                'items': [
                    ('dorozhnye-sumki', 'Сумка на колёсиках Samsonite Trolley', 'M', 'Чёрный', 'Полиэстер',
                     Decimal('13490'), None, '46x38x25', Decimal('1.6'), {'is_popular': True}),
                    ('dorozhnye-sumki', 'Сумка на колёсиках Samsonite Trolley', 'M', 'Тёмно-синий', 'Полиэстер',
                     Decimal('13490'), None, '46x38x25', Decimal('1.6'), {}),
                ],
            },
            {
                'group': 'duff-piquadro-business',
                'items': [
                    ('dorozhnye-sumki', 'Бизнес-сумка Piquadro Travel', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('27990'), Decimal('31990'), '50x30x24', Decimal('1.4'), {'is_popular': True, 'is_sale': True}),
                    ('dorozhnye-sumki', 'Бизнес-сумка Piquadro Travel', 'M', 'Тёмно-коричневый', 'Натуральная кожа',
                     Decimal('27990'), None, '50x30x24', Decimal('1.4'), {}),
                ],
            },

            # ===== ЧЕМОДАНЫ (8 моделей) =====
            {
                'group': 'chem-samsonite-lite20',
                'items': [
                    ('chemodany', 'Чемодан Samsonite Lite-Shock 20"', 'M', 'Синий', 'Полипропилен',
                     Decimal('32990'), Decimal('38990'), '55x40x20', Decimal('2.1'), {'is_popular': True, 'is_sale': True}),
                    ('chemodany', 'Чемодан Samsonite Lite-Shock 20"', 'M', 'Чёрный', 'Полипропилен',
                     Decimal('32990'), None, '55x40x20', Decimal('2.1'), {'is_popular': True}),
                ],
            },
            {
                'group': 'chem-samsonite-clite24',
                'items': [
                    ('chemodany', 'Чемодан Samsonite C-Lite 24"', 'M', 'Чёрный', 'Curv',
                     Decimal('41990'), None, '67x45x28', Decimal('2.7'), {'is_popular': True}),
                    ('chemodany', 'Чемодан Samsonite C-Lite 24"', 'M', 'Серый', 'Curv',
                     Decimal('41990'), None, '67x45x28', Decimal('2.7'), {}),
                ],
            },
            {
                'group': 'chem-roncato-young28',
                'items': [
                    ('chemodany', 'Чемодан Roncato Young 28"', 'M', 'Красный', 'Makrolon',
                     Decimal('29890'), Decimal('34990'), '77x52x30', Decimal('3.4'), {'is_new': True, 'is_sale': True}),
                    ('chemodany', 'Чемодан Roncato Young 28"', 'M', 'Чёрный', 'Makrolon',
                     Decimal('29890'), None, '77x52x30', Decimal('3.4'), {}),
                ],
            },
            {
                'group': 'chem-roncato-box20',
                'items': [
                    ('chemodany', 'Чемодан Roncato Box 2.0 Cabin 20"', 'M', 'Тёмно-зелёный', 'Makrolon',
                     Decimal('25990'), None, '55x40x20', Decimal('2.3'), {'is_popular': True}),
                    ('chemodany', 'Чемодан Roncato Box 2.0 Cabin 20"', 'M', 'Серый', 'Makrolon',
                     Decimal('25990'), None, '55x40x20', Decimal('2.3'), {}),
                ],
            },
            {
                'group': 'chem-samsonite-base28',
                'items': [
                    ('chemodany', 'Чемодан Samsonite Base Boost 28"', 'M', 'Серый', 'Полиэстер',
                     Decimal('27490'), Decimal('32990'), '78x52x31', Decimal('3.8'), {'is_sale': True}),
                    ('chemodany', 'Чемодан Samsonite Base Boost 28"', 'M', 'Синий', 'Полиэстер',
                     Decimal('27490'), None, '78x52x31', Decimal('3.8'), {}),
                ],
            },
            {
                'group': 'chem-roncato-ironik24',
                'items': [
                    ('chemodany', 'Чемодан Roncato Ironik 24"', 'M', 'Чёрный', 'Makrolon',
                     Decimal('31990'), Decimal('36990'), '65x42x27', Decimal('2.8'), {'is_popular': True, 'is_sale': True}),
                    ('chemodany', 'Чемодан Roncato Ironik 24"', 'M', 'Красный', 'Makrolon',
                     Decimal('31990'), None, '65x42x27', Decimal('2.8'), {}),
                ],
            },
            {
                'group': 'chem-samsonite-scure24',
                'items': [
                    ('chemodany', 'Чемодан Samsonite S\'Cure Spinner 24"', 'F', 'Серебристый', 'Поликарбонат',
                     Decimal('35990'), None, '66x45x30', Decimal('3.9'), {'is_popular': True, 'is_new': True}),
                    ('chemodany', 'Чемодан Samsonite S\'Cure Spinner 24"', 'F', 'Фиолетовый', 'Поликарбонат',
                     Decimal('35990'), None, '66x45x30', Decimal('3.9'), {}),
                ],
            },
            {
                'group': 'chem-roncato-okmini28',
                'items': [
                    ('chemodany', 'Чемодан Roncato Ok Mini 28"', 'F', 'Розовый', 'Makrolon',
                     Decimal('24990'), Decimal('28990'), '76x54x31', Decimal('3.5'), {'is_sale': True}),
                    ('chemodany', 'Чемодан Roncato Ok Mini 28"', 'F', 'Серебристый', 'Makrolon',
                     Decimal('24990'), None, '76x54x31', Decimal('3.5'), {'is_new': True}),
                ],
            },

            # ===== АКСЕССУАРЫ (5 моделей) =====
            {
                'group': 'acc-piquadro-passport',
                'items': [
                    ('aksessuary', 'Обложка на паспорт Piquadro', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('4290'), Decimal('4990'), '14x10x1', Decimal('0.05'), {'is_new': True, 'is_sale': True}),
                    ('aksessuary', 'Обложка на паспорт Piquadro', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('4290'), None, '14x10x1', Decimal('0.05'), {}),
                ],
            },
            {
                'group': 'acc-tous-pen',
                'items': [
                    ('aksessuary', 'Пенал Tous Mini', 'F', 'Бежевый', 'ПВХ',
                     Decimal('3490'), None, '20x8x5', Decimal('0.09'), {}),
                    ('aksessuary', 'Пенал Tous Mini', 'F', 'Розовый', 'ПВХ',
                     Decimal('3490'), None, '20x8x5', Decimal('0.09'), {}),
                ],
            },
            {
                'group': 'acc-piquadro-keycase',
                'items': [
                    ('aksessuary', 'Ключница Piquadro Key Case', 'M', 'Чёрный', 'Натуральная кожа',
                     Decimal('2990'), None, '9x6x2', Decimal('0.04'), {'is_popular': True}),
                    ('aksessuary', 'Ключница Piquadro Key Case', 'M', 'Коричневый', 'Натуральная кожа',
                     Decimal('2990'), None, '9x6x2', Decimal('0.04'), {}),
                ],
            },
            {
                'group': 'acc-samsonite-tags',
                'items': [
                    ('aksessuary', 'Набор багажных бирок Samsonite', 'M', 'Чёрный', 'Кожа',
                     Decimal('2490'), Decimal('2990'), '12x8x2', Decimal('0.05'), {'is_sale': True, 'is_popular': True}),
                    ('aksessuary', 'Набор багажных бирок Samsonite', 'M', 'Красный', 'Кожа',
                     Decimal('2490'), None, '12x8x2', Decimal('0.05'), {}),
                ],
            },
            {
                'group': 'acc-braun-glasses',
                'items': [
                    ('aksessuary', 'Футляр для очков Braun Büffel', 'F', 'Коричневый', 'Натуральная кожа',
                     Decimal('3990'), None, '16x6x4', Decimal('0.06'), {'is_new': True}),
                    ('aksessuary', 'Футляр для очков Braun Büffel', 'F', 'Бордовый', 'Натуральная кожа',
                     Decimal('3990'), None, '16x6x4', Decimal('0.06'), {}),
                ],
            },
        ]

        # Цвета для нити свотчей (color_hex на варианте)
        COLOR_HEX = {
            'Бордовый': '#8b0000',
            'Чёрный': '#1f1f1f',
            'Синий': '#1565c0',
            'Кремовый': '#f5e6c8',
            'Розовый': '#f06292',
            'Тёмно-коричневый': '#4e342e',
            'Зелёный': '#2e7d32',
            'Белый': '#fafafa',
            'Серый': '#9e9e9e',
            'Тёмно-синий': '#1a2c4e',
            'Коричневый': '#795548',
            'Бежевый': '#d7c4a1',
            'Тёмно-зелёный': '#1b5e20',
            'Красный': '#d32f2f',
            'Серебристый': '#b0b4ba',
            'Фиолетовый': '#6a1b9a',
        }

        product_idx = 0
        variant_idx = 0
        for group_data in products_seed:
            items = group_data['items']
            if not items:
                continue

            first = items[0]
            cat_slug, pname, gender, _color, material, _final, _base, dims, weight, flags = first

            category = cat_objs.get(cat_slug)
            if not category:
                self.stderr.write(f'Skip {pname}: no category {cat_slug}')
                continue

            gender_label = 'Унисекс' if gender is None else ('Мужской' if gender == 'M' else 'Женский')

            slug = _slug(pname)
            if Product.objects.filter(slug=slug).exists():
                slug = f'{slug}-{cat_slug}'

            p, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': pname,
                    'category': category,
                    'gender': gender,
                    'short_description': f'{pname} — качественное изделие. '
                                         f'Материал: {material}.',
                    'description': (
                        f'{pname}.\n\n'
                        f'Основные характеристики:\n'
                        f'• Материал: {material}\n'
                        f'• Размеры: {dims}\n'
                        f'• Вес: {weight} кг\n'
                        f'• Пол: {gender_label}\n\n'
                        f'Идеальный вариант для повседневного использования или путешествий. '
                        f'Качественная фурнитура, усиленные швы, гарантия производителя.'
                    ),
                    'material': material,
                    'dimensions': dims,
                    'weight': weight,
                    **flags,
                }
            )
            if not created:
                self.stderr.write(f'SKIP (exists): {pname}')
                continue

            for v_idx, (v_cat, v_pname, v_gender, color, v_material,
                        v_final, v_base, v_dims, v_weight, v_flags) in enumerate(items):
                if v_base and v_base > v_final:
                    base_price = v_base
                    discount = int((v_base - v_final) / v_base * 100)
                else:
                    base_price = v_final
                    discount = 0
                variant, v_created = ProductVariant.objects.get_or_create(
                    product=p,
                    color=color,
                    defaults={
                        'color_hex': COLOR_HEX.get(color, '#888888'),
                        'price': base_price,
                        'discount_percent': discount,
                        'stock': 15 + product_idx % 30,
                        'order': v_idx,
                        'status': 'in_stock',
                    }
                )
                if not v_created:
                    continue

                for img_pos in range(3):
                    svg_bytes = _svg(f'{pname} {color} [{img_pos + 1}]', product_idx + variant_idx + img_pos).encode('utf-8')
                    ProductImage.objects.create(
                        variant=variant,
                        image=ContentFile(svg_bytes, name=f'{variant.id}-{v_idx}-{img_pos + 1}.svg'),
                        alt=f'{pname} {color} — фото {img_pos + 1}',
                        is_main=(img_pos == 0),
                        order=img_pos,
                    )
                variant_idx += 1

            self.stdout.write(
                self.style.SUCCESS(f'  {p.name} — {p.variants.count()} цвет(ов)')
            )
            product_idx += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete: '
            f'Categories={Category.objects.count()}, '
            f'Products={Product.objects.count()} (моделей), '
            f'Variants={ProductVariant.objects.count()} (цветов), '
            f'Images={ProductImage.objects.count()}.'
        ))

        # ---------- Promo codes ----------
        promos_data = [
            ('SALE10', 'percent', Decimal('10'), Decimal('3000'), 0),
            ('SALE20', 'percent', Decimal('20'), Decimal('10000'), 0),
            ('WELCOME15', 'percent', Decimal('15'), Decimal('5000'), 0),
        ]
        for code, dtype, value, min_sum, max_uses in promos_data:
            PromoCode.objects.get_or_create(
                code=code,
                defaults={
                    'discount_type': dtype,
                    'discount_value': value,
                    'min_order_sum': min_sum,
                    'max_uses': max_uses,
                }
            )
        self.stdout.write(self.style.SUCCESS(
            f'Promo codes: {PromoCode.objects.count()}'
        ))

        # ---------- Site reviews ----------
        reviews_data = [
            ('Анна', 'Заказывала сумку — всё пришло быстро, упаковка отличная.', 5),
            ('Дмитрий', 'Хороший выбор чемоданов по адекватным ценам.', 4),
            ('Ольга', 'Кошелёк отличного качества, выглядит дороже своей цены.', 5),
        ]
        for name, text, rating in reviews_data:
            SiteReview.objects.get_or_create(
                name=name,
                text=text,
                defaults={'rating': rating, 'is_published': True},
            )
        self.stdout.write(self.style.SUCCESS(
            f'Site reviews: {SiteReview.objects.count()}'
        ))

        # ---------- Нормализация слагов: только латиница ----------
        # Чинит товары/категории, созданные старой версией сида с кириллицей.
        changed = 0
        for obj in Category.objects.all():
            new = _slug(obj.name)
            if obj.slug != new:
                obj.slug = new
                obj.save(update_fields=['slug'])
                changed += 1
        for obj in Product.objects.all().select_related('category'):
            new = _slug(obj.name)
            if Product.objects.filter(slug=new).exclude(pk=obj.pk).exists():
                new = f'{new}-{obj.category.slug}'
            if obj.slug != new:
                obj.slug = new
                obj.save(update_fields=['slug'])
                changed += 1
        if changed:
            self.stdout.write(self.style.SUCCESS(f'Slugs normalized to latin: {changed}'))