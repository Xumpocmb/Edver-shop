from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from mptt.models import MPTTModel, TreeForeignKey, TreeManager

User = get_user_model()


class Category(MPTTModel):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )
    image = models.ImageField(
        upload_to='categories/',
        null=True,
        blank=True,
        verbose_name="Изображение"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TreeManager()

    class MPTTMeta:
        order_insertion_by = ['order', 'name']

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['tree_id', 'lft']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse('app_catalog:category_detail', kwargs={'slug': self.slug})

    def get_descendants_ids(self):
        return list(
            self.get_descendants(include_self=True).filter(is_active=True).values_list('id', flat=True)
        )


class Brand(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название бренда")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    logo = models.ImageField(
        upload_to='brands/',
        null=True,
        blank=True,
        verbose_name="Логотип"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_CHOICES = [
        ('in_stock', 'В наличии'),
        ('out_of_stock', 'Нет в наличии'),
        ('preorder', 'Предзаказ'),
    ]

    name = models.CharField(max_length=500, verbose_name="Название товара")
    slug = models.SlugField(max_length=500, unique=True, db_index=True)
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Артикул"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name="Категория"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Бренд"
    )
    short_description = models.TextField(
        blank=True,
        verbose_name="Краткое описание"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Подробное описание"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена"
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Старая цена"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Остаток")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_stock',
        verbose_name="Статус"
    )
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name="Вес, кг"
    )
    dimensions = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Размеры"
    )
    material = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Материал"
    )
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Цвет"
    )

    views_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    sales_count = models.PositiveIntegerField(default=0, verbose_name="Продано")

    is_popular = models.BooleanField(default=False, verbose_name="Популярный")
    is_new = models.BooleanField(default=False, verbose_name="Новинка")
    is_sale = models.BooleanField(default=False, verbose_name="Распродажа")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.price})"

    def get_absolute_url(self):
        return reverse('app_catalog:product_detail', kwargs={'slug': self.slug})

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(100 - (self.price / self.old_price * 100))
        return 0

    @property
    def main_image(self):
        first = self.images.filter(is_main=True).first()
        if not first:
            first = self.images.first()
        return first

    @property
    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if not reviews.exists():
            return 0
        avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    @property
    def reviews_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def has_variants(self):
        return self.variants.filter(is_active=True).exists()

    @property
    def available_stock(self):
        if self.has_variants:
            return sum(v.stock for v in self.variants.filter(is_active=True))
        return self.stock

    def get_variant_display(self):
        variants = self.variants.filter(is_active=True)
        if not variants.exists():
            return None
        attrs = {}
        for v in variants:
            for av in v.attribute_values.select_related('attribute'):
                attr_name = av.attribute.name
                if attr_name not in attrs:
                    attrs[attr_name] = set()
                attrs[attr_name].add(av.value)
        return {k: sorted(v) for k, v in attrs.items()}


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name="Товар"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название модификации"
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Артикул модификации"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена модификации"
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Старая цена модификации"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Остаток")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    image = models.ImageField(
        upload_to='products/variants/%Y/%m/',
        null=True,
        blank=True,
        verbose_name="Изображение модификации"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Модификация товара"
        verbose_name_plural = "Модификации товаров"
        ordering = ['name']

    def __str__(self):
        return f"{self.product.name} — {self.name}"

    @property
    def effective_price(self):
        return self.price if self.price is not None else self.product.price

    @property
    def effective_old_price(self):
        if self.old_price is not None:
            return self.old_price
        return self.product.old_price

    @property
    def discount_percent(self):
        old = self.effective_old_price
        if old and old > self.effective_price:
            return int(100 - (self.effective_price / old * 100))
        return 0


class VariantAttribute(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название атрибута")
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    class Meta:
        verbose_name = "Атрибут модификации"
        verbose_name_plural = "Атрибуты модификаций"
        ordering = ['name']

    def __str__(self):
        return self.name


class VariantAttributeValue(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='attribute_values',
        verbose_name="Модификация"
    )
    attribute = models.ForeignKey(
        VariantAttribute,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name="Атрибут"
    )
    value = models.CharField(max_length=255, verbose_name="Значение")

    class Meta:
        verbose_name = "Значение атрибута модификации"
        verbose_name_plural = "Значения атрибутов модификаций"
        unique_together = ['variant', 'attribute']

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Товар"
    )
    image = models.ImageField(
        upload_to='products/%Y/%m/',
        verbose_name="Изображение"
    )
    alt = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Alt-текст"
    )
    is_main = models.BooleanField(default=False, verbose_name="Главное")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        ordering = ['-is_main', 'order']

    def __str__(self):
        return f"Изображение для {self.product.name}"


class ProductReview(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Товар"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name="Пользователь"
    )
    name = models.CharField(max_length=150, verbose_name="Имя")
    email = models.EmailField(verbose_name="Email")
    rating = models.PositiveSmallIntegerField(
        default=5,
        choices=[(i, str(i)) for i in range(1, 6)],
        verbose_name="Оценка"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Заголовок отзыва"
    )
    text = models.TextField(verbose_name="Текст отзыва")
    pros = models.TextField(blank=True, verbose_name="Достоинства")
    cons = models.TextField(blank=True, verbose_name="Недостатки")
    is_approved = models.BooleanField(default=False, verbose_name="Одобрен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Отзыв на товар"
        verbose_name_plural = "Отзывы на товары"
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв {self.rating}★ на {self.product.name} от {self.name}"
