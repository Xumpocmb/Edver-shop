from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from app_media.processing import preview_url

from . import yml_feed
from .models import Category, Product, ProductVariant, ProductImage


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


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        'color', 'color_hex', 'price',
        'discount_percent', 'stock', 'status', 'order', 'is_active',
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
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'color', 'color_hex', 'price',
        'sale_price', 'discount_percent', 'stock', 'status', 'order', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'product__category']
    search_fields = ['product__name', 'color']
    list_editable = ['price', 'discount_percent', 'stock', 'status', 'order', 'is_active']
    autocomplete_fields = ['product']
    inlines = [ProductImageInline]
    fieldsets = (
        (None, {
            'fields': (('product', 'color'), 'color_hex', 'status')
        }),
        ('Цены', {
            'fields': ('price', 'discount_percent')
        }),
        ('Остаток', {
            'fields': (('stock', 'order'), 'is_active'),
        }),
    )