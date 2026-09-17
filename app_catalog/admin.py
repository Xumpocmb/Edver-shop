from django.contrib import admin
from .models import Category, Brand, Product, ProductImage, ProductReview


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt', 'is_main', 'order']


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ['name', 'email', 'rating', 'title', 'text', 'is_approved', 'created_at']
    readonly_fields = ['created_at']


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
    inlines = [ProductImageInline, ProductReviewInline]
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


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'email', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['name', 'email', 'title', 'text', 'product__name']
    list_editable = ['is_approved']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
