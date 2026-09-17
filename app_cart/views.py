from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from app_catalog.models import Product
from .models import Cart, CartItem


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


def cart_detail(request):
    cart = Cart.get_or_create(request)
    items = cart.items.select_related('product').prefetch_related('product__images')
    context = {
        'cart': cart,
        'items': items,
        'page_title': 'Корзина',
    }
    return render(request, 'app_cart/cart_detail.html', context)


def cart_count(request):
    """AJAX endpoint to get cart count."""
    cart = Cart.get_or_create(request)
    return JsonResponse({
        'total_items': cart.total_items,
        'total_price': str(cart.total_price),
    })
