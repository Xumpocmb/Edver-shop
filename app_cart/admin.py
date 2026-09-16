from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['product', 'variant', 'quantity']
    readonly_fields = ['added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'user', 'total_items_display', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['session_key', 'user__username']
    inlines = [CartItemInline]
    readonly_fields = ['created_at', 'updated_at']

    def total_items_display(self, obj):
        return obj.total_items
    total_items_display.short_description = 'Товаров'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'variant', 'quantity', 'added_at']
    list_filter = ['added_at']
    search_fields = ['product__name', 'cart__session_key']
