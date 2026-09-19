from django.db import models
from django.urls import reverse
from django.utils.text import slugify
import uuid


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
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
    has_gender = models.BooleanField(
        default=True,
        verbose_name="Разделять по полу",
        help_text=(
            "Выключите для категорий без деления на мужские/женские "
            "(например, зонты): у товаров категории поле «Пол» будет очищаться."
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('app_catalog:category_detail', kwargs={'slug': self.slug})


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

    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
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

    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        default=None,
        db_index=True,
        verbose_name="Пол (пусто — унисекс)",
    )

    group_id = models.UUIDField(
        default=uuid.uuid4,
        db_index=True,
        verbose_name="Группа товаров (одна модель — разные цвета)"
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
        verbose_name="Цена продажи"
    )
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Себестоимость"
    )
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Старая цена"
    )
    discount_percent = models.SmallIntegerField(
        default=0,
        verbose_name="Процент скидки"
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
            models.Index(fields=['group_id']),
        ]

    def save(self, *args, **kwargs):
        """Если категория не разделяется по полу — поле «Пол» очищается."""
        if self.gender and self.category_id:
            has_gender = Category.objects.filter(
                pk=self.category_id, has_gender=True
            ).exists()
            if not has_gender:
                self.gender = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — {self.color} ({self.price})"

    def get_absolute_url(self):
        return reverse('app_catalog:product_detail', kwargs={'slug': self.slug})

    @property
    def discount_percent_display(self):
        """Процент скидки для отображения (из поля или вычисляемый)."""
        if self.discount_percent > 0:
            return self.discount_percent
        if self.old_price and self.old_price > self.price:
            return int(100 - (self.price / self.old_price * 100))
        return 0

    @property
    def effective_old_price(self):
        """Старая цена: явная old_price или вычисленная из скидки."""
        if self.old_price and self.old_price > self.price:
            return self.old_price
        if self.discount_percent > 0:
            return (self.price / (1 - self.discount_percent / 100)).quantize(
                self.price, rounding=None
            )
        return None

    @property
    def main_image(self):
        first = self.images.filter(is_main=True).first()
        if not first:
            first = self.images.first()
        return first

    def get_siblings(self):
        """Все цвета той же модели (без текущего товара)."""
        return Product.objects.filter(
            group_id=self.group_id,
            is_active=True,
        ).exclude(id=self.id).select_related('brand').prefetch_related('images')

    def get_all_colors(self):
        """Все цвета той же модели (включая текущий)."""
        return Product.objects.filter(
            group_id=self.group_id,
            is_active=True,
        ).select_related('brand').prefetch_related('images')


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
