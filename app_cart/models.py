from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

from app_catalog.models import Product


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Процент'),
        ('fixed', 'Фиксированная сумма'),
    ]

    code = models.CharField(max_length=50, unique=True, verbose_name='Промокод')
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percent',
        verbose_name='Тип скидки',
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Значение скидки',
    )
    min_order_sum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Минимальная сумма заказа',
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        verbose_name='Макс. кол-во использований (0 = без ограничений)',
    )
    used_count = models.PositiveIntegerField(default=0, verbose_name='Использовано раз')
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name='Действует с')
    valid_to = models.DateTimeField(null=True, blank=True, verbose_name='Действует до')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.code} ({self.get_discount_type_display()} {self.discount_value})'

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def calc_discount(self, total):
        if not self.is_valid:
            return Decimal(0)
        if total < self.min_order_sum:
            return Decimal(0)
        if self.discount_type == 'percent':
            return (total * self.discount_value / 100).quantize(Decimal('0.01'))
        return min(self.discount_value, total)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']


class Cart(models.Model):
    """Server-side cart tied to session or user."""
    session_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Ключ сессии"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name="Пользователь"
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name="Промокод"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Cart {self.session_key} ({self.items.count()} items)"

    @classmethod
    def get_or_create(cls, request):
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, _ = cls.objects.get_or_create(
            session_key=session_key,
            defaults={'user': request.user if request.user.is_authenticated else None}
        )
        if request.user.is_authenticated and cart.user is None:
            cart.user = request.user
            cart.save(update_fields=['user'])
        return cart

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_discount(self):
        total = Decimal(0)
        for item in self.items.all():
            if item.old_line_total:
                total += item.old_line_total - item.line_total
        return total

    @property
    def promo_discount(self):
        if self.promo_code and self.promo_code.is_valid:
            return self.promo_code.calc_discount(self.total_price)
        return Decimal(0)

    @property
    def grand_total(self):
        return max(self.total_price - self.promo_discount, Decimal(0))

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Корзина"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Товар"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} ({self.product.color}) x{self.quantity}"

    @property
    def unit_price(self):
        return self.product.price

    @property
    def old_unit_price(self):
        return self.product.old_price

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def old_line_total(self):
        old = self.old_unit_price
        if old and old > self.unit_price:
            return old * self.quantity
        return None

    @property
    def available_stock(self):
        return self.product.stock


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]
    DELIVERY_CHOICES = [
        ('belpochta', 'Белпочта'),
        ('evropochta', 'Европочта'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
        verbose_name='Пользователь',
    )
    session_key = models.CharField(max_length=64, db_index=True, verbose_name='Сессия')

    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    phone = models.CharField(max_length=30, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес (Белпочта)')

    delivery_type = models.CharField(
        max_length=20, choices=DELIVERY_CHOICES, default='belpochta',
        verbose_name='Тип доставки',
    )
    evropochta_branch_id = models.CharField(
        max_length=50, blank=True,
        verbose_name='ID отделения Европочты',
    )
    evropochta_branch_name = models.CharField(
        max_length=300, blank=True,
        verbose_name='Название отделения Европочты',
    )

    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Промокод',
    )
    promo_discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Скидка по промокоду',
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Сумма товаров',
    )
    grand_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Итого к оплате',
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='new',
        verbose_name='Статус',
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return f'Заказ #{self.pk} — {self.full_name} ({self.get_status_display()})'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items',
        verbose_name='Заказ',
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True,
        verbose_name='Товар',
    )
    product_name = models.CharField(max_length=300, verbose_name='Название товара')
    product_color = models.CharField(max_length=100, verbose_name='Цвет')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за шт.')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    def __str__(self):
        return f'{self.product_name} ({self.product_color}) x{self.quantity}'

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'


class EvropochtaBranch(models.Model):
    address_id = models.CharField(max_length=50, unique=True, verbose_name='AddressId')
    name = models.CharField(max_length=300, verbose_name='Название')
    address = models.TextField(verbose_name='Адрес')
    city = models.CharField(max_length=200, blank=True, verbose_name='Город')
    latitude = models.CharField(max_length=30, blank=True, verbose_name='Широта')
    longitude = models.CharField(max_length=30, blank=True, verbose_name='Долгота')
    is_cash = models.BooleanField(default=False, verbose_name='Наличные')
    is_card = models.BooleanField(default=False, verbose_name='Карты')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} — {self.address}'

    class Meta:
        verbose_name = 'Отделение Европочты'
        verbose_name_plural = 'Отделения Европочты'
        ordering = ['city', 'name']
