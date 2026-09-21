import re

from django.test import TestCase

from app_order.models import Order
from app_order.utils import (
    create_order_with_number, next_order_number,
    payment_idempotency_key,
)

NUMBER_RE = re.compile(r'^EDV-\d{4}-\d{6}$')


class OrderNumberUtilsTests(TestCase):
    def test_next_order_number_format(self):
        self.assertRegex(next_order_number(), NUMBER_RE)

    def test_next_order_number_uses_current_year(self):
        number = next_order_number(year=2026)
        self.assertTrue(number.startswith('EDV-2026-'))

    def test_sequential_numbers(self):
        create_order_with_number(full_name='Иван', phone='+375', delivery_type='belpochta')
        self.assertEqual(next_order_number(), 'EDV-2026-000002')

    def test_create_order_with_unique_number(self):
        order = create_order_with_number(full_name='Иван', phone='+375', delivery_type='belpochta')
        self.assertRegex(order.number, NUMBER_RE)
        self.assertEqual(Order.objects.filter(number=order.number).count(), 1)

    def test_create_many_orders_all_unique(self):
        numbers = {
            create_order_with_number(full_name='N', phone='1', delivery_type='belpochta').number
            for _ in range(20)
        }
        self.assertEqual(len(numbers), 20)

    def test_payment_idempotency_key(self):
        self.assertEqual(payment_idempotency_key('EDV-2026-000037', 2), 'EDV-2026-000037-2')