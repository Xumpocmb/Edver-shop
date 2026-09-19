from django.contrib import admin
from .models import Cart, CartItem, PromoCode, Order, OrderItem, EvropochtaBranch


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('variant', 'quantity', 'added_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_key', 'user', 'total_items', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('session_key',)
    inlines = [CartItemInline]


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'code', 'discount_type', 'discount_value',
        'used_count', 'max_uses', 'is_active', 'valid_to',
    )
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)
    list_editable = ('is_active',)
    readonly_fields = ('used_count', 'created_at')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'product_name', 'product_color', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'full_name', 'phone', 'delivery_type',
        'grand_total', 'status', 'created_at',
    )
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('full_name', 'phone')
    list_editable = ('status',)
    readonly_fields = (
        'user', 'session_key', 'full_name', 'phone', 'address',
        'delivery_type', 'evropochta_branch_id', 'evropochta_branch_name',
        'promo_code', 'promo_discount', 'total_price', 'grand_total',
        'comment', 'created_at', 'updated_at',
    )
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('status',),
        }),
        ('Данные клиента', {
            'fields': ('full_name', 'phone', 'comment'),
        }),
        ('Доставка', {
            'fields': (
                'delivery_type', 'address',
                'evropochta_branch_id', 'evropochta_branch_name',
            ),
        }),
        ('Оплата', {
            'fields': ('total_price', 'promo_discount', 'grand_total', 'promo_code'),
        }),
        ('Система', {
            'fields': ('user', 'session_key', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(EvropochtaBranch)
class EvropochtaBranchAdmin(admin.ModelAdmin):
    list_display = ('address_id', 'name', 'city', 'is_cash', 'is_card')
    list_filter = ('city', 'is_cash', 'is_card')
    search_fields = ('name', 'address', 'city')
    readonly_fields = ('updated_at',)
