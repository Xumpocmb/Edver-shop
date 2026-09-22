from django import forms
from django.contrib import admin

from app_cart.models import EvropochtaBranch
from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('variant', 'product_name', 'product_color', 'unit_price', 'quantity')


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = (
        'amount', 'currency', 'method', 'status', 'account_no',
        'provider_payment_id', 'payment_url', 'idempotency_key',
        'expires_at', 'paid_at', 'created_at',
    )


class OrderAdminForm(forms.ModelForm):
    branch_select = forms.ChoiceField(
        label='Отделение Европочты',
        required=False,
        choices=[('', '— Не выбрано —')],
    )

    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        branches = EvropochtaBranch.objects.order_by('city', 'name')
        choices = [('', '— Не выбрано —')]
        for b in branches:
            choices.append((b.address_id, f'{b.name} — {b.address}'))
        self.fields['branch_select'].choices = choices

        if self.instance and self.instance.pk and self.instance.evropochta_branch_id:
            self.fields['branch_select'].initial = self.instance.evropochta_branch_id

    def clean(self):
        cleaned_data = super().clean()
        branch_id = cleaned_data.get('branch_select')
        if branch_id:
            try:
                branch = EvropochtaBranch.objects.get(address_id=branch_id)
                cleaned_data['evropochta_branch_id'] = branch.address_id
                cleaned_data['evropochta_branch_name'] = f'{branch.name} — {branch.address}'
            except EvropochtaBranch.DoesNotExist:
                pass
        return cleaned_data


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = (
        'number', 'full_name', 'phone', 'delivery_type',
        'grand_total', 'status', 'paid', 'created_at',
    )
    list_filter = ('status', 'delivery_type', 'created_at')
    search_fields = ('number', 'full_name', 'phone')
    list_editable = ('status',)
    readonly_fields = (
        'number', 'user', 'session_key', 'phone',
        'evropochta_branch_id', 'evropochta_branch_name',
        'promo_code', 'promo_discount', 'total_price', 'grand_total',
        'created_at', 'updated_at',
    )
    inlines = [OrderItemInline, PaymentInline]
    fieldsets = (
        (None, {
            'fields': ('status', 'paid', 'number'),
        }),
        ('Данные клиента', {
            'fields': ('full_name', 'phone', 'comment'),
        }),
        ('Доставка', {
            'fields': (
                'delivery_type', 'address',
                'branch_select',
                'evropochta_branch_id', 'evropochta_branch_name',
            ),
        }),
        ('Отправка и получение', {
            'fields': ('shipped_at', 'tracking_number', 'received_at'),
        }),
        ('Оплата', {
            'fields': ('total_price', 'promo_discount', 'grand_total', 'promo_code'),
        }),
        ('Система', {
            'fields': ('user', 'session_key', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    class Media:
        js = ('admin/js/order_admin.js',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'idempotency_key', 'order', 'amount', 'currency',
        'status', 'paid_at', 'created_at',
    )
    list_filter = ('status', 'method', 'created_at')
    search_fields = ('idempotency_key', 'account_no', 'provider_payment_id', 'order__number')
    readonly_fields = (
        'order', 'amount', 'currency', 'method', 'idempotency_key',
        'account_no', 'provider_payment_id', 'payment_url',
        'raw_response', 'expires_at', 'paid_at', 'created_at', 'updated_at',
    )
