from django.contrib import admin
from .models import Cart, CartItem, PromoCode, EvropochtaBranch


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


@admin.register(EvropochtaBranch)
class EvropochtaBranchAdmin(admin.ModelAdmin):
    list_display = ('address_id', 'name', 'city', 'is_cash', 'is_card')
    list_filter = ('city', 'is_cash', 'is_card')
    search_fields = ('name', 'address', 'city')
    readonly_fields = ('updated_at',)
