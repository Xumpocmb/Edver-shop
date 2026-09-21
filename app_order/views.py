from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from app_cart.models import Order

from . import services


def orders_list(request):
    """Список заказов пользователя (Этап 1 + 3).

    Для авторизованного — заказы, привязанные к аккаунту (user.orders);
    для гостя — заказы его сессии (session_key). После входа историю гостя
    переносить на аккаунт (TODO, см. регистрацию).

    Показывать: номер, дату, сумму, статус доставки (status) и оплаты
    (payment_status — появится после Этапа 2, сейчас поле отсутствует).
    """
    if request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user)
    else:
        orders = Order.objects.filter(session_key=request.session.session_key or '')
    orders = orders.prefetch_related('items').order_by('-created_at')
    return render(request, 'app_order/orders_list.html', {'orders': orders})


def order_detail(request, order_id):
    """Детали заказа пользователя (Этап 1 + 3).

    Проверка прав: авторизованным — order.user == request.user, гость — по
    session_key (иначе 404). Показывать позиции, суммы, доставку, статусы.
    Блок платежей (кнопки «Оплатить» / «Проверить статус оплаты») появится
    вместе с моделью Payment (Этап 2).
    """
    qs = Order.objects.prefetch_related('items')
    if request.user.is_authenticated:
        order = get_object_or_404(qs, pk=order_id, user=request.user)
    else:
        order = get_object_or_404(
            qs, pk=order_id, session_key=request.session.session_key or ''
        )
    items = order.items.select_related('product')
    return render(request, 'app_order/order_detail.html', {'order': order, 'items': items})


@require_POST
def payment_create(request, order_id):
    """Заглушка «Оплатить» — создание ЕРИП-ссылки (Этап 2).

    Что нужно сделать разработчику:
    - проверить права: гость — по session_key, авторизованный — по request.user
      (закрыть доступ к чужим платежам);
    - проверить оплату статус заказа (payment_status == 'pending');
    - вызвать services.create_payment_invoice(order);
    - при наличии payment_url — вернуть клиенту редирект/JSON со ссылкой;
    - метод «наличными при получении» — без ссылки, статус ставится вручную.

    Сейчас — всегда заглушка: JSON с признаком not_implemented.
    """
    order = get_object_or_404(Order, pk=order_id)
    result = services.create_payment_invoice(order)
    return JsonResponse({
        'ok': False,
        'order_id': order_id,
        'result': result,
        'message': 'Заглушка: создание ссылки на оплату не реализовано',
    })


@require_POST
def payment_check_status(request, order_id):
    """Заглушка «Проверить статус оплаты» (Этап 2 + 3).

    Что нужно сделать разработчику:
    - права доступа, как в payment_create;
    - взять последний Payment заказа и вызвать services.get_payment_status(...);
    - если провайдер подтвердил оплату — services.finalize_payment(...) и вернуть
      {'status': 'paid'};
    - иначе вернуть текущий статус и, опционально, кнопку «оплатить».
    """
    order = get_object_or_404(Order, pk=order_id)
    result = services.get_payment_status(order_id)
    return JsonResponse({
        'ok': False,
        'order_id': order_id,
        'result': result,
        'message': 'Заглушка: проверка статуса оплаты не реализована',
    })


def payment_callback(request):
    """Заглушка webhook провайдера (Этап 2).

    Что нужно сделать разработчику:
    - @csrf_exempt (внешний сервис) + проверка подписи payload;
    - разобрать уведомление, найти Payment по provider_payment_id;
    - при подтверждении оплаты — finalize_payment;
    - ответ провайдеру 200, повторные уведомления безопасны (идемпотентность).
    """
    return JsonResponse({'ok': False, 'status': 'not_implemented'})


def payment_status_page(request, order_id):
    """Заглушка страницы статуса оплаты (после возврата с провайдера).

    Что нужно сделать разработчику:
    - рендерить templates/app_order/payment_status.html со статусом последнего
      Payment и кнопкой «Проверить статус оплаты»;
    - при первом показе можно автоматически дернуть get_payment_status
      (опционально), чтобы не заставлять клиента кликать дважды.
    """
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'app_order/payment_status.html', {'order': order})
