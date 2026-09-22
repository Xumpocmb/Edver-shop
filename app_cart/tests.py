from unittest import mock

from django.test import TestCase
from django.urls import reverse

from app_catalog.models import Category, Product, ProductVariant
from app_cart.models import Cart, CartItem
from app_order.models import Order


class CheckoutTests(TestCase):
    def test_checkout_sends_new_order_notification_even_unpaid(self):
        category = Category.objects.create(name='Куртки', slug='kurtki', has_gender=False)
        product = Product.objects.create(name='Куртка', slug='kurtka', category=category, is_active=True)
        variant = ProductVariant.objects.create(
            product=product, color='Чёрный', price='100.00', stock=5, is_active=True,
        )

        session = self.client.session
        session['cart_session'] = True
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, variant=variant, quantity=2)

        with mock.patch('app_cart.views.notify_new_order') as notify:
            resp = self.client.post(
                reverse('app_cart:checkout'),
                {
                    'full_name': 'Иван Иванов',
                    'phone': '+375296111111',
                    'delivery_type': 'belpochta',
                    'address': 'ул. Ленина, 1',
                },
            )

        self.assertEqual(resp.status_code, 302)
        notify.assert_called_once()
        order = notify.call_args.args[0]
        self.assertEqual(order.full_name, 'Иван Иванов')
        self.assertFalse(order.paid)
        self.assertTrue(order.items.exists())

    def test_checkout_notification_error_does_not_break_order(self):
        category = Category.objects.create(name='Куртки', slug='kurtki', has_gender=False)
        product = Product.objects.create(name='Куртка', slug='kurtka', category=category, is_active=True)
        variant = ProductVariant.objects.create(
            product=product, color='Чёрный', price='100.00', stock=5, is_active=True,
        )

        session = self.client.session
        session['cart_session'] = True
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, variant=variant, quantity=1)

        with mock.patch('app_cart.views.notify_new_order', side_effect=RuntimeError('telegram down')):
            resp = self.client.post(
                reverse('app_cart:checkout'),
                {
                    'full_name': 'Иван Иванов',
                    'phone': '+375296111111',
                    'delivery_type': 'belpochta',
                    'address': 'ул. Ленина, 1',
                },
            )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CartItem.objects.count(), 0)
        order = Order.objects.get(session_key=cart.session_key)
        self.assertEqual(order.full_name, 'Иван Иванов')