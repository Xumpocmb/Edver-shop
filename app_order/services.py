"""Сервисный слой оплат: связывает заказы (Order) с ЕРИП-агрегатором (erip_api).

Правила:
- сумма и статусы только с сервера/провайдера, клиенту не доверяем;
- валюта BYN, работаем с Decimal, не float;
- переходы статусов идемпотентны и обёрнуты в транзакции с select_for_update;
- ошибки провайдера не роняют заказ — возвращаем error, даём повторить.
"""

import hmac
import logging
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import erip_api
from .models import Order, Payment
from .telegram import notify_paid_order
from .utils import payment_idempotency_key

logger = logging.getLogger(__name__)


def get_latest_payment(order):
    """Последняя попытка оплаты заказа (или None)."""
    return order.payments.order_by('-created_at', '-pk').first()


def create_payment_invoice(order):
    """Создать ЕРИП-счёт для заказа и вернуть ссылку на оплату.

    Каждый вызов создаёт новый счёт у провайдера (предыдущие неоплаченные
    счета того же заказа агрегатор сам отменяет). Возвращает dict:
    {'payment_url': str|None, 'payment_id': int|None, 'status': str,
     'message': str, 'error': str|None}.
    """
    if order.paid:
        return {
            'payment_url': None,
            'payment_id': None,
            'status': 'paid',
            'message': 'Заказ уже оплачен',
            'error': None,
        }

    attempt = order.payments.count() + 1
    idempotency_key = payment_idempotency_key(order.number, attempt)
    logger.info(
        'ERIP: создание счёта, order=%s attempt=%s сумма=%s',
        order.number, attempt, order.grand_total,
    )

    # Дубликат (повторный вызов с тем же ключом) — отдаём уже созданный счёт.
    existing = Payment.objects.filter(
        idempotency_key=idempotency_key,
    ).first()
    if existing is not None:
        logger.info('ERIP: счёт уже создан (дубликат), payment=%s', existing.pk)
        return _payment_result(existing, created=False)

    payment = Payment.objects.create(
        order=order,
        amount=order.grand_total,
        currency='BYN',
        method='erip',
        idempotency_key=idempotency_key,
    )

    try:
        result = erip_api.erip_create_payment_invoice(order.grand_total, order.number)
        # erip_api возвращает payment_id = AccountNo ("2026-000007") и InvoiceUrl.
        payment.account_no = result.get('payment_id') or ''
        payment.payment_url = result.get('payment_url') or ''
        payment.expires_at = timezone.now() + timedelta(hours=1)
        payment.raw_response = result
        payment.save(update_fields=[
            'account_no', 'payment_url', 'expires_at', 'raw_response', 'updated_at',
        ])
        if not payment.payment_url:
            logger.warning('ERIP: счёт создан без ссылки на оплату, order=%s', order.number)
            payment.status = 'failed'
            payment.save(update_fields=['status', 'updated_at'])
        else:
            logger.info('ERIP: счёт создан, payment=%s account_no=%s', payment.pk, payment.account_no)
        return _payment_result(payment)
    except Exception as exc:  # noqa: BLE001
        logger.exception('ERIP: ошибка создания счёта, order=%s', order.number)
        payment.raw_response = {'error': str(exc)}
        payment.status = 'failed'
        payment.save(update_fields=['status', 'raw_response', 'updated_at'])
        return _payment_result(payment, error='Не удалось выставить счёт на оплату. Попробуйте ещё раз.')


def _payment_result(payment, created=True, error=None):
    """Собрать результат создания счёта."""
    return {
        'payment_url': payment.payment_url or None,
        'payment_id': payment.pk,
        'status': payment.status,
        'message': 'Ссылка на оплату создана' if payment.payment_url else ('Счёт уже создан' if not created else 'Счёт не создан'),
        'error': error,
    }


def finalize_payment(payment_id):
    """Подтвердить оплату заказа РОВНО ОДИН РАЗ.

    Идемпотентно: повторные вызовы (webhook + кнопка «Проверить статус»)
    безопасны. После подтверждения отмечает заказ оплаченным (order.paid=True).
    Возвращает Order или None, если платёж не найден.
    """
    with transaction.atomic():
        payment = Payment.objects.select_for_update().filter(pk=payment_id).first()
        if payment is None:
            logger.warning('ERIP: финализация — платёж не найден, payment=%s', payment_id)
            return None

        if payment.status == 'succeeded':
            logger.info('ERIP: финализация — платёж уже подтверждён, payment=%s', payment.pk)
            return payment.order

        order = Order.objects.select_for_update().get(pk=payment.order_id)
        payment.status = 'succeeded'
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at', 'updated_at'])
        order.paid = True
        order.save(update_fields=['paid', 'updated_at'])
        logger.info('ERIP: заказ %s оплачен (payment %s)', order.number, payment.pk)

    # Уведомление вне транзакции — ошибки отправки не откатывают подтверждение.
    try:
        notify_paid_order(order)
    except Exception:  # noqa: BLE001
        logger.exception('Telegram: не удалось уведомить об оплате заказа %s', order.number)
    return order


def get_payment_status(payment_id):
    """Запросить у провайдера статус счёта и, если оплачен, подтвердить.

    Ожидается возврат: dict {'status': 'paid'|'pending'|'failed'|'none',
    'payment_url': str|None, 'message': str}.
    """
    payment = Payment.objects.select_related('order').filter(pk=payment_id).first()
    if payment is None:
        return _status_result('none', 'Счёт не найден')

    if payment.order.paid or payment.status == 'succeeded':
        return _status_result('paid', 'Заказ оплачен', payment.payment_url)

    if not payment.account_no:
        return _status_result('pending', 'Счёт ещё не выставлен — нажмите «Оплатить»', payment.payment_url)

    try:
        result = erip_api.erip_check_invoice_status(payment.account_no)
        provider_status = result.get('status')
    except Exception:  # noqa: BLE001
        logger.exception('ERIP: ошибка проверки статуса, payment=%s', payment.pk)
        provider_status = None

    if provider_status == 'paid':
        logger.info('ERIP: провайдер подтвердил оплату payment=%s, финализирую', payment.pk)
        finalize_payment(payment.pk)
        return _status_result('paid', 'Заказ оплачен', payment.payment_url)

    mapping = {
        'pending': ('pending', 'Оплата пока не получена'),
        'failed': ('failed', 'Счёт просрочен или отменён — попробуйте оплатить снова'),
    }
    status, message = mapping.get(
        provider_status,
        ('pending', 'Не удалось получить статус. Попробуйте ещё раз.'),
    )
    if provider_status is None:
        logger.warning('ERIP: не удалось получить статус от провайдера, payment=%s', payment.pk)
    else:
        logger.info('ERIP: статус от провайдера=%s payment=%s', provider_status, payment.pk)
    return _status_result(status, message, payment.payment_url)


def _status_result(status, message, payment_url=None):
    return {
        'status': status,
        'payment_url': payment_url,
        'message': message,
    }


def _notification_signature_matches(data, signature):
    """Проверить подпись webhook-уведомления Express Pay.

    Перебираем несколько распространённых способов сборки подписываемой
    строки, чтобы совместиться и со стандартным форматом провайдера
    (``key=value&...``), и со стилем нашего ``erip_api.get_signature``
    (значения подряд, без имён полей и разделителей).
    """
    if not signature:
        return False
    base = data.copy()
    base.pop('signature', None)
    if not base:
        return False

    variants = []

    # Разные способы сборки строки подписи.
    for ordered in (sorted(base.keys()), list(base.keys())):
        for exclude_token in (False, True):
            part = {
                k: v for k, v in ((k, base[k]) for k in ordered)
                if not (exclude_token and k == 'Token')
            }
            variants.append('&'.join(f'{k}={v}' for k, v in part.items()))
    # Стиль erip_api.get_signature: только значения, подряд, без имён полей.
    variants.append(''.join(base.values()))

    expected = signature.upper()
    for raw in set(variants):
        if hmac.compare_digest(erip_api.get_signature(raw).upper(), expected):
            return True
    return False


def _parse_amount(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def process_payment_callback(request_data):
    """Обработать webhook-уведомление провайдера об оплате.

    Возвращает dict {'ok': bool, 'status': str} — без исключений, чтобы
    провайдер получал 200 даже на повторные уведомления (идемпотентность).
    """
    data = dict(request_data) if hasattr(request_data, 'items') else dict(request_data or {})
    signature = data.pop('signature', '') or ''

    account_no = str(data.get('AccountNo', '') or '')
    status_raw = str(data.get('Status', '') or '')
    logger.info('ERIP: webhook AccountNo=%s Status=%s', account_no, status_raw)

    if not _notification_signature_matches(data, signature):
        logger.warning('ERIP: webhook — подпись не совпала, AccountNo=%s', account_no)
        return {'ok': False, 'status': 'bad_signature'}

    payment_status = erip_api.PAYMENT_STATUS.get(status_raw)

    if status_raw != '3':  # 3 = оплачен; остальные финализации не требуют
        return {'ok': str(payment_status) in ('pending', 'failed'), 'status': payment_status or status_raw}

    payment = Payment.objects.filter(
        status='pending', account_no=account_no,
    ).order_by('-created_at', '-pk').first()
    if payment is None:
        # Повторное уведомление уже подтверждённого платежа — отвечаем 200.
        already = Payment.objects.filter(
            status='succeeded', account_no=account_no,
        ).order_by('-created_at', '-pk').first()
        if already is not None:
            logger.info('ERIP: webhook уже обработан ранее, payment=%s', already.pk)
            return {'ok': True, 'status': 'paid'}
        logger.warning('ERIP: webhook — платёж не найден, AccountNo=%s', account_no)
        return {'ok': False, 'status': 'payment_not_found'}

    amount = _parse_amount(data.get('Amount'))
    if amount is not None and amount != payment.amount:
        logger.warning(
            'ERIP: webhook — сумма не совпала, payment=%s ожидалось=%s пришло=%s',
            payment.pk, payment.amount, amount,
        )
        return {'ok': False, 'status': 'amount_mismatch'}

    order = finalize_payment(payment.pk)
    if order is None:
        return {'ok': False, 'status': 'payment_not_found'}
    logger.info('ERIP: webhook — оплата подтверждена, order=%s', order.number)
    return {'ok': True, 'status': 'paid'}