from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'product_name', 'product_color', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'full_name', 'phone', 'delivery_type',
        'grand_total', 'status', 'created_at',
    )
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('number', 'full_name', 'phone')
    list_editable = ('status',)
    readonly_fields = (
        'number', 'user', 'session_key', 'full_name', 'phone', 'address',
        'delivery_type', 'evropochta_branch_id', 'evropochta_branch_name',
        'promo_code', 'promo_discount', 'total_price', 'grand_total',
        'comment', 'created_at', 'updated_at',
    )
    inlines = [OrderItemInline]
    fieldsets = (
        (None, {
            'fields': ('status', 'number'),
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