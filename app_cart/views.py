from decimal import Decimal
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from app_catalog.models import ProductVariant
from app_order.models import Order, OrderItem
from app_order.telegram import notify_new_order
from app_order.utils import create_order_with_number
from .models import Cart, CartItem, PromoCode, EvropochtaBranch

logger = logging.getLogger(__name__)


def _cart_response(request, cart, message=None, success=True):
    """Return JSON or redirect depending on request type."""
    if request.headers.get('Accept') == 'application/json':
        data = {
            'success': success,
            'message': message,
            'total_items': cart.total_items,
            'total_price': str(cart.total_price),
            'promo_discount': str(cart.promo_discount),
            'grand_total': str(cart.grand_total),
            'has_promo': cart.promo_code is not None,
            'promo_code': cart.promo_code.code if cart.promo_code else '',
            'items': [
                {
                    'id': item.id,
                    'variant_id': item.variant_id,
                    'product_name': item.variant.product.name,
                    'product_slug': item.variant.product.slug,
                    'product_color': item.variant.color,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'line_total': str(item.line_total),
                    'image_url': item.variant.main_image.image.url if item.variant.main_image else None,
                }
                for item in cart.items.select_related('variant__product').prefetch_related('variant__images')
            ],
        }
        return JsonResponse(data)
    return redirect('app_cart:cart_detail')


@require_POST
def add_to_cart(request):
    variant_id = request.POST.get('variant_id') or request.headers.get('X-Product-Id')
    quantity = int(request.POST.get('quantity', 1) or request.headers.get('X-Quantity', 1))

    variant = get_object_or_404(
        ProductVariant.objects.select_related('product'),
        id=variant_id,
        is_active=True,
        product__is_active=True,
    )

    cart = Cart.get_or_create(request)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        variant=variant,
        defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=['quantity'])

    return _cart_response(request, cart, f'{variant.product.name} ({variant.color}) добавлен в корзину')


@require_POST
def update_cart_item(request, item_id):
    cart = Cart.get_or_create(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        item.delete()
        return _cart_response(request, cart, 'Товар удалён из корзины')

    item.quantity = quantity
    item.save(update_fields=['quantity'])
    return _cart_response(request, cart, 'Корзина обновлена')


@require_POST
def remove_from_cart(request, item_id):
    cart = Cart.get_or_create(request)
    item = get_object_or_404(
        CartItem.objects.select_related('variant__product'),
        id=item_id, cart=cart,
    )
    product_name = f'{item.variant.product.name} ({item.variant.color})'
    item.delete()
    return _cart_response(request, cart, f'{product_name} удалён из корзины')


@require_POST
def clear_cart(request):
    cart = Cart.get_or_create(request)
    cart.clear()
    return _cart_response(request, cart, 'Корзина очищена')


@require_POST
def apply_promo(request):
    code = request.POST.get('promo_code', '').strip().upper()
    cart = Cart.get_or_create(request)

    if not code:
        return _cart_response(request, cart, 'Введите промокод', success=False)

    try:
        promo = PromoCode.objects.get(code__iexact=code)
    except PromoCode.DoesNotExist:
        return _cart_response(request, cart, 'Промокод не найден', success=False)

    if not promo.is_valid:
        return _cart_response(request, cart, 'Промокод недействителен', success=False)

    if cart.total_price < promo.min_order_sum:
        return _cart_response(
            request, cart,
            f'Минимальная сумма заказа для этого промокода: {promo.min_order_sum} бел. руб.',
            success=False,
        )

    cart.promo_code = promo
    cart.save(update_fields=['promo_code'])

    discount = promo.calc_discount(cart.total_price)
    return _cart_response(request, cart, f'Промокод применён! Скидка: {discount} бел. руб.')


@require_POST
def remove_promo(request):
    cart = Cart.get_or_create(request)
    cart.promo_code = None
    cart.save(update_fields=['promo_code'])
    return _cart_response(request, cart, 'Промокод удалён')


def cart_detail(request):
    cart = Cart.get_or_create(request)
    items = cart.items.select_related('variant__product').prefetch_related('variant__images')

    # Профиль для автозаполнения формы оформления
    profile_data = {}
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        profile_data = {
            'full_name': profile.full_name,
            'phone': profile.phone,
            'address': profile.address,
        }

    context = {
        'cart': cart,
        'items': items,
        'page_title': 'Корзина',
        'profile_data': profile_data,
    }
    return render(request, 'app_cart/cart_detail.html', context)


@require_POST
def checkout(request):
    cart = Cart.get_or_create(request)
    items = cart.items.select_related('variant__product')
    if not items.exists():
        messages.error(request, 'Корзина пуста.')
        return redirect('app_cart:cart_detail')

    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    delivery_type = request.POST.get('delivery_type', 'belpochta')
    address = request.POST.get('address', '').strip()
    branch_id = request.POST.get('evropochta_branch_id', '').strip()
    branch_name = request.POST.get('evropochta_branch_name', '').strip()
    comment = request.POST.get('comment', '').strip()

    if not full_name or not phone:
        messages.error(request, 'Заполните ФИО и телефон.')
        return redirect('app_cart:cart_detail')

    if delivery_type == 'evropochta' and not branch_id:
        messages.error(request, 'Выберите отделение Европочты.')
        return redirect('app_cart:cart_detail')

    if delivery_type == 'belpochta' and not address:
        messages.error(request, 'Укажите адрес доставки.')
        return redirect('app_cart:cart_detail')

    order = create_order_with_number(
        user=request.user if request.user.is_authenticated else None,
        session_key=cart.session_key,
        full_name=full_name,
        phone=phone,
        delivery_type=delivery_type,
        address=address,
        evropochta_branch_id=branch_id,
        evropochta_branch_name=branch_name,
        promo_code=cart.promo_code,
        promo_discount=cart.promo_discount,
        total_price=cart.total_price,
        grand_total=cart.grand_total,
        comment=comment,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            variant=item.variant,
            product_name=item.variant.product.name,
            product_color=item.variant.color,
            unit_price=item.unit_price,
            quantity=item.quantity,
        )
        item.variant.stock = max(item.variant.stock - item.quantity, 0)
        item.variant.save(update_fields=['stock'])

    if cart.promo_code:
        cart.promo_code.used_count += 1
        cart.promo_code.save(update_fields=['used_count'])

    cart.clear()
    try:
        notify_new_order(order)
    except Exception:  # noqa: BLE001
        logger.exception('Telegram: не удалось уведомить о заказе %s', order.number)
    return redirect('app_cart:order_success', order_id=order.pk)


def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    context = {'order': order}
    return render(request, 'app_cart/order_success.html', context)


def branches_json(request):
    branches = list(
        EvropochtaBranch.objects.values_list('address_id', 'name', 'address', 'city')
    )
    data = [
        {'id': b[0], 'name': b[1], 'address': b[2], 'city': b[3]}
        for b in branches
    ]
    return JsonResponse({'branches': data})


def cart_count(request):
    """AJAX endpoint to get cart count."""
    cart = Cart.get_or_create(request)
    return JsonResponse({
        'total_items': cart.total_items,
        'total_price': str(cart.total_price),
    })
