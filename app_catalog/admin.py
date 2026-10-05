import re

from django import forms
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from app_media.processing import preview_url

from . import yml_feed
from .models import Category, Product, ProductVariant, ProductImage


HEX_RE = re.compile(r'^#?([0-9a-f]{3}|[0-9a-f]{6})$', re.IGNORECASE)


def normalize_hex(value):
    """``'#abc'`` -> ``'#aabbcc'``, ``'ABCdef'`` -> ``'#abcdef'``; пусто и мусор -> ``None``."""
    match = HEX_RE.match((value or '').strip())
    if not match:
        return None
    digits = match.group(1).lower()
    if len(digits) == 3:
        digits = ''.join(c * 2 for c in digits)
    return f'#{digits}'


class ColorHexWidget(forms.TextInput):
    """Hex-поле с пипеткой: в БД остаётся обычный текст.

    Нативный <input type="color"> подставляет значение в текстовое поле и
    забирает его обратно, скрипт — static/admin/js/color_hex.js.
    """

    class Media:
        js = ('admin/js/color_hex.js',)

    def render(self, name, value, attrs=None, renderer=None):
        # Поле обязано лежать внутри .color-hex: скрипт ищет его именно там,
        # поэтому обрамляем инпут вместе с пипеткой, а не после него.
        return format_html(
            '<span class="color-hex">{}'
            '<input type="color" class="color-hex__picker" data-color-hex-picker'
            ' value="{}" aria-label="Выбрать цвет">'
            '<button type="button" class="color-hex__clear" data-color-hex-clear'
            ' title="Убрать цвет" aria-label="Убрать цвет">✕</button>'
            '</span>',
            mark_safe(super().render(name, value, attrs, renderer)),
            normalize_hex(value) or '#000000',
        )


class ColorHexFieldMixin:
    """Включает пипетку только для color_hex, не задевая другие CharField."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'color_hex':
            kwargs['widget'] = ColorHexWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt', 'is_main', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    class Media:
        js = ('admin/js/urlify_ru.js',)

    list_display = ['name', 'slug', 'has_gender', 'is_active', 'order']
    list_filter = ['is_active', 'has_gender']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active', 'has_gender']


class ProductVariantInline(ColorHexFieldMixin, admin.TabularInline):
    model = ProductVariant
    extra = 1
    # Ссылка «Изменить» у каждой сохранённой строки — на страницу варианта.
    show_change_link = True
    fields = [
        'color', 'color_hex', 'price',
        'discount_percent', 'stock', 'status', 'order', 'is_main', 'is_active',
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    class Media:
        js = ('admin/js/urlify_ru.js',)

    list_display = ['main_image', 'name', 'category']
    list_display_links = ['name']
    list_filter = ['is_active', 'gender', 'is_popular', 'is_new', 'is_sale', 'category']
    search_fields = ['name', 'slug', 'description', 'short_description', 'variants__color']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]
    save_on_top = True
    change_list_template = 'admin/app_catalog/product/change_list.html'
    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), ('category',), 'gender')
        }),
        ('Характеристики', {
            'fields': ('material', 'weight', 'dimensions'),
        }),
        ('Описание', {
            'fields': ('short_description', 'description'),
        }),
        ('Метки', {
            'fields': (('is_popular', 'is_new', 'is_sale'), 'is_active'),
        }),
        ('Статистика', {
            'fields': (('views_count', 'sales_count'),),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Фото')
    def main_image(self, obj):
        variant = obj.main_variant
        img = variant.main_image if variant else None
        if not img:
            return ''
        return format_html(
            '<img src="{}" style="width:48px;height:48px;object-fit:cover;'
            'border-radius:4px;display:block;">',
            preview_url(img.image),
        )

    def get_urls(self):
        return [
            path(
                'export-yml/',
                self.admin_site.admin_view(self.export_yml),
                name='app_catalog_product_export_yml',
            ),
        ] + super().get_urls()

    def export_yml(self, request):
        """Скачивание YML-фида для Яндекс Маркета прямо со списка товаров."""
        text, _ = yml_feed.build_feed()
        filename = f'edver-shop-yml-{timezone.now():%Y-%m-%d}.yml'
        response = HttpResponse(text, content_type='application/x-yaml; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


@admin.register(ProductVariant)
class ProductVariantAdmin(ColorHexFieldMixin, admin.ModelAdmin):
    list_display = [
        'product', 'color', 'is_main', 'color_swatch', 'price',
        'sale_price', 'discount_percent', 'stock', 'status', 'order', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'is_main', 'product__category']
    search_fields = ['product__name', 'color']
    list_editable = ['is_main', 'price', 'discount_percent', 'stock', 'status', 'order', 'is_active']
    autocomplete_fields = ['product']
    inlines = [ProductImageInline]
    readonly_fields = ['product_link']
    fieldsets = (
        (None, {
            'fields': (('product', 'color'), 'color_hex', 'status', 'is_main')
        }),
        ('Ссылки', {
            'fields': ('product_link',),
        }),
        ('Цены', {
            'fields': ('price', 'discount_percent')
        }),
        ('Остаток', {
            'fields': (('stock', 'order'), 'is_active'),
        }),
    )

    @admin.display(description='Оттенок', ordering='color_hex')
    def color_swatch(self, obj):
        """Свотч вместо кода: сам код остаётся в подсказке."""
        hex_color = normalize_hex(obj.color_hex)
        if not hex_color:
            return obj.color_hex or '—'
        return format_html(
            '<span class="color-swatch" style="background: {};" title="{}"></span>',
            hex_color, obj.color_hex,
        )

    @admin.display(description='Карточка товара')
    def product_link(self, obj):
        """Ссылка на родительский товар (автокомплит открывает поиск, а не карточку)."""
        if not obj.product_id:
            return '-'
        url = reverse('admin:app_catalog_product_change', args=[obj.product_id])
        return format_html('<a href="{}">{}</a>', url, obj.product)
