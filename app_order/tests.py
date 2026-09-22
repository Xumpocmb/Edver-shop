import re
from decimal import Decimal
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.test import TestCase

from app_order import erip_api, services, telegram
from app_order.models import Order, Payment, TelegramBotSettings, TelegramRecipient
from app_order.utils import create_order_with_number

NUMBER_RE = re.compile(r'^EDV-\d{4}-\d{6}$')


class OrderNumberUtilsTests(TestCase):
    def test_next_order_number_format(self):
        self.assertRegex(erip_api.get_payment_id_by_order_number('EDV-2026-000037'), '2026-000037')

    def test_payment_idempotency_key(self):
        from app_order.utils import payment_idempotency_key
        self.assertEqual(payment_idempotency_key('EDV-2026-000037', 2), 'EDV-2026-000037-2')


class PaymentServicesTestCase(TestCase):
    def setUp(self):
        self.order = create_order_with_number(
            full_name='Иван', phone='+375', delivery_type='belpochta',
            grand_total=Decimal('100.00'), session_key='sess',
        )

    @mock.patch.object(erip_api, 'erip_create_payment_invoice')
    def test_create_invoice_saves_payment_and_returns_url(self, mock_create):
        mock_create.return_value = {
            'payment_id': '2026-000001',
            'payment_url': 'https://pay.example/inv/1',
        }
        result = services.create_payment_invoice(self.order)

        mock_create.assert_called_once()
        self.assertEqual(result['payment_url'], 'https://pay.example/inv/1')
        self.assertIsNotNone(result['payment_id'])
        payment = Payment.objects.get(pk=result['payment_id'])
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.account_no, '2026-000001')
        self.assertEqual(payment.payment_url, 'https://pay.example/inv/1')
        self.assertEqual(payment.status, 'pending')

    def test_create_invoice_returns_paid_for_paid_order(self):
        self.order.paid = True
        self.order.save(update_fields=['paid'])
        with mock.patch.object(erip_api, 'erip_create_payment_invoice') as mock_create:
            result = services.create_payment_invoice(self.order)
            mock_create.assert_not_called()
        self.assertEqual(result['status'], 'paid')
        self.assertEqual(Payment.objects.count(), 0)

    @mock.patch.object(erip_api, 'erip_create_payment_invoice')
    def test_create_invoice_handles_provider_error(self, mock_create):
        mock_create.side_effect = Exception('boom')
        result = services.create_payment_invoice(self.order)
        self.assertIsNone(result['payment_url'])
        self.assertIn('error', result)
        payment = Payment.objects.get(pk=result['payment_id'])
        self.assertEqual(payment.status, 'failed')

    @mock.patch.object(erip_api, 'erip_create_payment_invoice')
    @mock.patch.object(erip_api, 'erip_check_invoice_status')
    def test_finalize_payment_is_idempotent(self, mock_check, mock_create):
        mock_create.return_value = {
            'payment_id': '2026-000001',
            'payment_url': 'https://pay.example/inv/1',
        }
        mock_check.return_value = {'payment_id': '2026-000001', 'status': 'paid'}

        result = services.create_payment_invoice(self.order)
        payment_id = result['payment_id']

        order1 = services.finalize_payment(payment_id)
        order2 = services.finalize_payment(payment_id)

        self.assertEqual(order1.pk, self.order.pk)
        self.assertEqual(order2.pk, self.order.pk)
        payment = Payment.objects.get(pk=payment_id)
        self.assertEqual(payment.status, 'succeeded')
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    @mock.patch.object(erip_api, 'erip_create_payment_invoice')
    @mock.patch.object(erip_api, 'erip_check_invoice_status')
    def test_get_payment_status_confirms_paid(self, mock_check, mock_create):
        mock_create.return_value = {
            'payment_id': '2026-000001',
            'payment_url': 'https://pay.example/inv/1',
        }
        mock_check.return_value = {'payment_id': '2026-000001', 'status': 'paid'}

        result = services.create_payment_invoice(self.order)
        status = services.get_payment_status(result['payment_id'])

        self.assertEqual(status['status'], 'paid')
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)


class PaymentCallbackTests(TestCase):
    def setUp(self):
        self.order = create_order_with_number(
            full_name='Иван', phone='+375', delivery_type='belpochta',
            grand_total=Decimal('100.00'), session_key='sess',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('100.00'),
            idempotency_key='EDV-2026-000001-1',
            account_no='2026-000001',
        )

    def _signed_payload(self, **overrides):
        data = {'AccountNo': '2026-000001', 'Status': '3', 'Amount': '100.00'}
        data.update(overrides)
        raw = '&'.join(f'{k}={v}' for k, v in sorted(data.items()))
        data['signature'] = erip_api.get_signature(raw)
        return data

    def test_callback_with_valid_signature_finalizes(self):
        result = services.process_payment_callback(self._signed_payload())
        self.assertEqual(result, {'ok': True, 'status': 'paid'})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'succeeded')
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    def test_callback_rejects_bad_signature(self):
        payload = self._signed_payload()
        payload['signature'] = payload['signature'][:-2] + 'XX'
        result = services.process_payment_callback(payload)
        self.assertEqual(result, {'ok': False, 'status': 'bad_signature'})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_callback_is_idempotent_on_repeat(self):
        first = services.process_payment_callback(self._signed_payload())
        second = services.process_payment_callback(self._signed_payload())
        self.assertEqual(first, {'ok': True, 'status': 'paid'})
        self.assertEqual(second, {'ok': True, 'status': 'paid'})

    def test_callback_ignores_unpaid_statuses(self):
        result = services.process_payment_callback(self._signed_payload(Status='1'))
        self.assertEqual(result['ok'], True)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')


class PaymentViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ivan', password='pass')
        self.order = create_order_with_number(
            user=self.user,
            full_name='Иван', phone='+375', delivery_type='belpochta',
            grand_total=Decimal('100.00'), session_key='sess',
        )
        self.client.force_login(self.user)

    @mock.patch.object(erip_api, 'erip_create_payment_invoice')
    def test_payment_create_returns_url(self, mock_create):
        mock_create.return_value = {
            'payment_id': '2026-000001',
            'payment_url': 'https://pay.example/inv/1',
        }
        resp = self.client.post(
            f'/orders/{self.order.pk}/pay/',
            headers={'Accept': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['result']['payment_url'], 'https://pay.example/inv/1')

    def test_payment_create_requires_post(self):
        resp = self.client.get(f'/orders/{self.order.pk}/pay/')
        self.assertEqual(resp.status_code, 405)

    def test_order_detail_renders(self):
        resp = self.client.get(f'/orders/{self.order.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.order.number)

    def test_payment_status_page_renders(self):
        resp = self.client.get(f'/orders/{self.order.pk}/check/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Оплатить')

    def test_payment_check_status_no_payment(self):
        resp = self.client.post(
            f'/orders/{self.order.pk}/status/',
            headers={'Accept': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'none')

    def test_foreign_order_hidden(self):
        other = User.objects.create_user(username='other', password='pass')
        order2 = create_order_with_number(
            user=other,
            full_name='Пётр', phone='+375', delivery_type='belpochta',
            session_key='sess2',
        )
        resp = self.client.post(
            f'/orders/{order2.pk}/pay/',
            headers={'Accept': 'application/json'},
        )
        self.assertEqual(resp.status_code, 404)


class TelegramSendMessageTests(TestCase):
    def setUp(self):
        self.settings = TelegramBotSettings.objects.create(bot_token='123:token')
        self.r1 = TelegramRecipient.objects.create(chat_id='111', name='Админ')
        self.r2 = TelegramRecipient.objects.create(chat_id='222', name='Склад')

    @mock.patch('app_order.telegram.requests.post')
    def test_send_message_to_all_active(self, post):
        post.return_value = mock.Mock(**{'raise_for_status': lambda: None})
        sent = telegram.send_message('Привет')
        self.assertEqual(sent, 2)
        self.assertEqual(post.call_count, 2)
        kwargs = post.call_args_list[0].kwargs
        self.assertEqual(kwargs['data']['chat_id'], '111')
        self.assertIn('Привет', kwargs['data']['text'])

    @mock.patch('app_order.telegram.requests.post')
    def test_inactive_recipient_skipped(self, post):
        self.r2.is_active = False
        self.r2.save()
        post.return_value = mock.Mock(**{'raise_for_status': lambda: None})
        sent = telegram.send_message('Привет')
        self.assertEqual(sent, 1)
        self.assertEqual(post.call_args.kwargs['data']['chat_id'], '111')

    @mock.patch('app_order.telegram.requests.post')
    def test_disabled_settings_send_nothing(self, post):
        self.settings.bot_token = ''
        self.settings.save()
        self.assertEqual(telegram.send_message('Привет'), 0)
        post.assert_not_called()

    @mock.patch('app_order.telegram.requests.post')
    def test_no_recipients_send_nothing(self, post):
        TelegramRecipient.objects.all().delete()
        self.assertEqual(telegram.send_message('Привет'), 0)
        post.assert_not_called()

    @mock.patch('app_order.telegram.requests.post')
    def test_api_error_swallowed(self, post):
        post.side_effect = requests.ConnectionError('boom')
        self.assertEqual(telegram.send_message('Привет'), 0)


class TelegramNotificationTests(TestCase):
    def test_notify_new_order_builds_message(self):
        order = create_order_with_number(
            full_name='Иван Иванов', phone='+375296111111',
            delivery_type='belpochta', address='ул. Ленина, 1',
            grand_total=Decimal('150.00'), session_key='sess1',
        )
        with mock.patch.object(telegram, 'send_message') as send:
            telegram.notify_new_order(order)
            send.assert_called_once()
            text = send.call_args.args[0]
            self.assertIn(order.number, text)
            self.assertIn('Иван Иванов', text)
            self.assertIn('150.00', text)
            self.assertIn('Новый заказ', text)

    def test_notify_paid_order_builds_message(self):
        order = create_order_with_number(
            full_name='Иван Иванов', phone='+375296111111',
            delivery_type='evropochta', evropochta_branch_name='Брест-4',
            grand_total=Decimal('150.00'), session_key='sess2',
        )
        with mock.patch.object(telegram, 'send_message') as send:
            telegram.notify_paid_order(order)
            send.assert_called_once()
            text = send.call_args.args[0]
            self.assertIn('оплачен', text)
            self.assertIn(order.number, text)

    @mock.patch('app_order.services.notify_paid_order')
    def test_finalize_payment_sends_notification(self, notify):
        order = create_order_with_number(
            full_name='Иван', phone='+375', delivery_type='belpochta',
            grand_total=Decimal('100.00'), session_key='sess3',
        )
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('100.00'),
            idempotency_key='EDV-2026-000002-1',
        )
        services.finalize_payment(payment.pk)
        notify.assert_called_once_with(order)

    @mock.patch('app_order.services.notify_paid_order')
    def test_finalize_payment_not_repeated_for_paid(self, notify):
        order = create_order_with_number(
            full_name='Иван', phone='+375', delivery_type='belpochta',
            grand_total=Decimal('100.00'), session_key='sess4',
        )
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('100.00'),
            idempotency_key='EDV-2026-000003-1',
        )
        services.finalize_payment(payment.pk)
        services.finalize_payment(payment.pk)
        self.assertEqual(notify.call_count, 1)