from django.contrib import admin
from .models import Category, Brand, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt', 'is_main', 'order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    raw_id_fields = ['parent']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'color', 'sku', 'category', 'brand', 'gender', 'price',
        'cost_price', 'old_price', 'discount_percent', 'stock', 'status', 'is_popular', 'is_new', 'is_sale',
        'is_active', 'views_count', 'created_at'
    ]
    list_filter = [
        'is_active', 'status', 'gender', 'is_popular', 'is_new', 'is_sale',
        'category', 'brand', 'color', 'material', 'created_at'
    ]
    search_fields = ['name', 'slug', 'sku', 'description', 'short_description', 'color']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'cost_price', 'old_price', 'discount_percent', 'stock', 'status', 'gender', 'is_popular', 'is_new', 'is_sale', 'is_active']
    inlines = [ProductImageInline]
    save_on_top = True
    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), ('sku', 'category', 'brand'), ('gender', 'group_id'), 'status')
        }),
        ('Цены и остатки', {
            'fields': (('price', 'cost_price'), ('old_price', 'discount_percent'), 'stock')
        }),
        ('Характеристики', {
            'fields': ('material', 'color', 'weight', 'dimensions'),
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
