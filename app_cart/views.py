from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages

from app_catalog.models import Product
from .models import Cart, CartItem, PromoCode, Order, OrderItem, EvropochtaBranch


def _cart_response(request, cart, message=None, success=True):
    """Return JSON or redirect depending on request type."""
    if request.headers.get('Accept') == 'application/json':
        data = {
            'success': success,
            'message': message,
            'total_items': cart.total_items,
            'total_price': str(cart.total_price),
            'items': [
                {
                    'id': item.id,
                    'product_id': item.product_id,
                    'product_name': item.product.name,
                    'product_slug': item.product.slug,
                    'product_color': item.product.color,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'line_total': str(item.line_total),
                    'image_url': item.product.main_image.image.url if item.product.main_image else None,
                }
                for item in cart.items.select_related('product').prefetch_related('product__images')
            ],
        }
        return JsonResponse(data)
    return redirect('app_cart:cart_detail')


@require_POST
def add_to_cart(request):
    product_id = request.POST.get('product_id') or request.headers.get('X-Product-Id')
    quantity = int(request.POST.get('quantity', 1) or request.headers.get('X-Quantity', 1))

    product = get_object_or_404(Product, id=product_id, is_active=True)

    cart = Cart.get_or_create(request)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=['quantity'])

    return _cart_response(request, cart, f'{product.name} ({product.color}) добавлен в корзину')


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
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = f'{item.product.name} ({item.product.color})'
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
            f'Минимальная сумма заказа для этого промокода: {promo.min_order_sum} ₽',
            success=False,
        )

    cart.promo_code = promo
    cart.save(update_fields=['promo_code'])

    discount = promo.calc_discount(cart.total_price)
    return _cart_response(request, cart, f'Промокод применён! Скидка: {discount} ₽')


@require_POST
def remove_promo(request):
    cart = Cart.get_or_create(request)
    cart.promo_code = None
    cart.save(update_fields=['promo_code'])
    return _cart_response(request, cart, 'Промокод удалён')


def cart_detail(request):
    cart = Cart.get_or_create(request)
    items = cart.items.select_related('product').prefetch_related('product__images')
    context = {
        'cart': cart,
        'items': items,
        'page_title': 'Корзина',
    }
    return render(request, 'app_cart/cart_detail.html', context)


@require_POST
def checkout(request):
    cart = Cart.get_or_create(request)
    items = cart.items.select_related('product')
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

    order = Order.objects.create(
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
            product=item.product,
            product_name=item.product.name,
            product_color=item.product.color,
            unit_price=item.unit_price,
            quantity=item.quantity,
        )
        item.product.stock = max(item.product.stock - item.quantity, 0)
        item.product.save(update_fields=['stock'])

    if cart.promo_code:
        cart.promo_code.used_count += 1
        cart.promo_code.save(update_fields=['used_count'])

    cart.clear()
    messages.success(request, f'Заказ #{order.pk} оформлен! Мы свяжемся с вами для подтверждения.')
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
