import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

from app_catalog.models import Product, ProductVariant


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
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Модификация"
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        unique_together = ['cart', 'product', 'variant']

    def __str__(self):
        variant_str = f" ({self.variant})" if self.variant else ""
        return f"{self.product.name}{variant_str} x{self.quantity}"

    @property
    def unit_price(self):
        if self.variant:
            return self.variant.effective_price
        return self.product.price

    @property
    def old_unit_price(self):
        if self.variant:
            return self.variant.effective_old_price
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
        if self.variant:
            return self.variant.stock
        return self.product.stock
