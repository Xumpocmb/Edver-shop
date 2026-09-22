from django.conf import settings
from django.db import models

from app_catalog.models import ProductVariant


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('awaiting_shipment', 'Ждёт отправки'),
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
        'app_cart.PromoCode', on_delete=models.SET_NULL, null=True, blank=True,
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
    paid = models.BooleanField(default=False, verbose_name='Оплачен')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')

    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата отправки')
    tracking_number = models.CharField(max_length=100, blank=True, verbose_name='Трек-номер')
    received_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата получения')

    # публичный номер заказа, показываем клиенту и шлём в ЕРИП-счёт
    number = models.CharField(
        max_length=30, unique=True, db_index=True,
        verbose_name='Номер заказа',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return f'Заказ {self.number} — {self.full_name} ({self.get_status_display()})'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items',
        verbose_name='Заказ',
    )
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True,
        verbose_name='Вариант (цвет)',
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


class Payment(models.Model):
    """Платёж заказа через ЕРИП-агрегатор (Express Pay).

    Один заказ может иметь несколько попыток оплаты: на каждый клик по кнопке
    «Оплатить» создаётся новый счёт (новая запись Payment). Подтверждение
    приходит либо по webhook от провайдера, либо при проверке статуса по
    кнопке «Проверить статус оплаты».
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('succeeded', 'Оплачен'),
        ('failed', 'Не оплачен'),
        ('refunded', 'Возврат'),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='payments',
        verbose_name='Заказ',
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Сумма',
    )
    currency = models.CharField(max_length=10, default='BYN', verbose_name='Валюта')
    method = models.CharField(max_length=20, default='erip', verbose_name='Метод оплаты')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Статус',
    )
    account_no = models.CharField(
        max_length=100, blank=True,
        verbose_name='Номер счёта (AccountNo)',
    )
    provider_payment_id = models.CharField(
        max_length=100, blank=True,
        verbose_name='Номер счёта у провайдера (InvoiceNo)',
    )
    payment_url = models.URLField(max_length=1000, blank=True, verbose_name='Ссылка на оплату')
    idempotency_key = models.CharField(
        max_length=120, unique=True,
        verbose_name='Ключ идемпотентности',
    )
    raw_response = models.JSONField(null=True, blank=True, verbose_name='Ответ провайдера')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Срок действия счёта')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата оплаты')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return f'Платёж {self.idempotency_key} — {self.get_status_display()}'

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']