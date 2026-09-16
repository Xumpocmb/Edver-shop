from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import (
    Category, Brand, Product, ProductImage, ProductReview,
    ProductVariant, VariantAttribute, VariantAttributeValue
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ['image', 'alt', 'is_main', 'order']


class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ['name', 'email', 'rating', 'title', 'text', 'is_approved', 'created_at']
    readonly_fields = ['created_at']


class VariantAttributeValueInline(admin.TabularInline):
    model = VariantAttributeValue
    extra = 1
    fields = ['attribute', 'value']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['name', 'sku', 'price', 'old_price', 'stock', 'is_active']
    inlines = [VariantAttributeValueInline]


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'sku', 'category', 'brand', 'price', 'old_price',
        'stock', 'status', 'is_popular', 'is_new', 'is_sale', 'is_active',
        'views_count', 'created_at'
    ]
    list_filter = [
        'is_active', 'status', 'is_popular', 'is_new', 'is_sale',
        'category', 'brand', 'color', 'created_at'
    ]
    search_fields = ['name', 'slug', 'sku', 'description', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'old_price', 'stock', 'status', 'is_popular', 'is_new', 'is_sale', 'is_active']
    inlines = [ProductImageInline, ProductVariantInline, ProductReviewInline]
    save_on_top = True
    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), ('sku', 'category', 'brand'), 'status')
        }),
        ('Цены и остатки', {
            'fields': (('price', 'old_price'), 'stock')
        }),
        ('Характеристики', {
            'fields': ('material', 'color', 'weight', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('Описание', {
            'fields': ('short_description', 'description'),
        }),
        ('Метки', {
            'fields': (('is_popular', 'is_new', 'is_sale'), 'is_active'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': (('views_count', 'sales_count'),),
            'classes': ('collapse',),
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'sku', 'price', 'old_price', 'stock', 'is_active']
    list_filter = ['is_active', 'product__category']
    search_fields = ['name', 'sku', 'product__name']
    list_editable = ['price', 'old_price', 'stock', 'is_active']
    inlines = [VariantAttributeValueInline]


@admin.register(VariantAttribute)
class VariantAttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'email', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating', 'created_at']
    search_fields = ['name', 'email', 'title', 'text', 'product__name']
    list_editable = ['is_approved']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
