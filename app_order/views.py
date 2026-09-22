import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order

from . import services

logger = logging.getLogger(__name__)


def _get_order_for_request(request, order_id):
    """Заказ, к которому у текущего пользователя/сессии есть доступ."""
    qs = Order.objects.prefetch_related('items', 'payments')
    if request.user.is_authenticated:
        return get_object_or_404(qs, pk=order_id, user=request.user)
    return get_object_or_404(
        qs, pk=order_id, session_key=request.session.session_key or ''
    )


def orders_list(request):
    """Список заказов пользователя.

    Для авторизованного — заказы, привязанные к аккаунту (user.orders);
    для гостя — заказы его сессии (session_key). После входа историю гостя
    переносить на аккаунт (см. регистрацию).
    """
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        orders = Order.objects.filter(session_key=request.session.session_key or '')
    orders = orders.prefetch_related('items').order_by('-created_at')
    return render(request, 'app_order/orders_list.html', {'orders': orders})


def order_detail(request, order_id):
    """Детали заказа пользователя."""
    order = _get_order_for_request(request, order_id)
    items = order.items.select_related('variant__product')
    payment = order.payments.order_by('-created_at', '-pk').first()
    return render(
        request, 'app_order/order_detail.html',
        {'order': order, 'items': items, 'payment': payment},
    )


@require_POST
def payment_create(request, order_id):
    """Создать счёт ЕРИП и вернуть ссылку на оплату (кнопка «Оплатить»).

    Клиент получает JSON: ok, result.payment_url, result.message, result.error.
    """
    order = _get_order_for_request(request, order_id)
    logger.info('ERIP: запрос на создание счёта, order=%s', order.number)
    result = services.create_payment_invoice(order)
    if order.paid:
        logger.info('ERIP: заказ уже оплачен, order=%s', order.number)
        return JsonResponse({
            'ok': False,
            'order_id': order_id,
            'status': 'paid',
            'result': result,
            'message': 'Заказ уже оплачен',
        })
    if not result.get('payment_url'):
        logger.warning(
            'ERIP: ссылка на оплату не создана, order=%s, status=%s, error=%s',
            order.number, result.get('status'), result.get('error'),
        )
    return JsonResponse({
        'ok': bool(result.get('payment_url')),
        'order_id': order_id,
        'status': result.get('status'),
        'result': result,
        'message': result.get('error') or result.get('message', ''),
    })


@require_POST
def payment_check_status(request, order_id):
    """Проверить статус оплаты последнего счёта (кнопка «Проверить статус»)."""
    order = _get_order_for_request(request, order_id)
    if order.paid:
        logger.info('ERIP: проверка статуса — заказ уже оплачен, order=%s', order.number)
        return JsonResponse({
            'ok': True,
            'order_id': order_id,
            'status': 'paid',
            'message': 'Заказ оплачен ✓',
        })

    payment = order.payments.order_by('-created_at', '-pk').first()
    if payment is None:
        logger.warning('ERIP: проверка статуса — счёт не найден, order=%s', order.number)
        return JsonResponse({
            'ok': False,
            'order_id': order_id,
            'status': 'none',
            'message': 'Счёт ещё не выставлен — нажмите «Оплатить»',
        })

    logger.info('ERIP: проверка статуса счёта payment=%s order=%s', payment.pk, order.number)
    result = services.get_payment_status(payment.pk)
    logger.info('ERIP: результат проверки status=%s payment=%s', result['status'], payment.pk)
    return JsonResponse({
        'ok': result['status'] == 'paid',
        'order_id': order_id,
        'status': result['status'],
        'message': result['message'],
        'payment_url': result.get('payment_url'),
    })


def payment_status_page(request, order_id):
    """Страница статуса оплаты (после возврата с провайдера)."""
    order = _get_order_for_request(request, order_id)
    payment = order.payments.order_by('-created_at', '-pk').first()
    logger.info('ERIP: открыта страница статуса, order=%s payment=%s', order.number, payment.pk if payment else None)
    return render(
        request, 'app_order/payment_status.html',
        {'order': order, 'payment': payment},
    )


@csrf_exempt
def payment_callback(request):
    """Webhook провайдера (внешний сервис — без CSRF)."""
    payload = request.POST or request.GET
    logger.info('ERIP: получен webhook, order-полей=%d', len(payload))
    result = services.process_payment_callback(payload)
    logger.info('ERIP: webhook обработан: %s', result)
    return JsonResponse(result)