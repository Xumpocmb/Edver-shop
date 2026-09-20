"""Заглушки сервиса оплат (Этапы 1–2 плана).

Реальные интеграции здесь НЕ реализованы — функции описывают контракт,
который предстоит написать разработчику (провайдер: ЕРИП-агрегатор, механизм
«счёт + ссылка на оплату»). Целевые модели — см. models-dev.md (Order, Payment).

Общие правила для всех функций:
- сумма и статусы — только с сервера/провайдера, клиенту не доверять;
- валюта BYN, работать с Decimal, не float;
- переходы статусов идемпотентны и обёрнуты в транзакции с select_for_update.
"""

from decimal import Decimal


def create_payment_invoice(order):
    """Создать счёт у провайдера и вернуть ссылку на оплату.

    Что нужно сделать разработчику:
    1. Убедиться, что заказ существует и ещё не оплачен
       (order.payment_status == 'pending').
    2. Создать запись Payment (модель в models-dev.md): amount=order.grand_total,
       currency='BYN', method='erip', status='pending',
       idempotency_key = f'{order.number}-<номер попытки>'.
    3. Вызвать API провайдера (создать счёт): передать сумму и уникальный номер
       заказа (order.number), получить provider_payment_id, payment_url, expires_at.
    4. Сохранить сырой ответ провайдера в Payment.raw_response и вернуть payment_url.
    5. На случай ДУБЛЯ: повторный вызов по одному order.number не должен создавать
       второй счёт — использовать idempotency_key, при IntegrityError возвращать
       существующий Payment.
    6. При ошибке провайдера — НЕ ронять заказ: вернуть ссылку-заглушку None,
       чтобы кнопка «Оплатить» показывала ошибку и давала повторить.

    Ожидается возврат: dict {'payment_url': str|None, 'payment_id': int|None}.
    """
    # TODO (Этап 2): интеграция с конкретным ЕРИП-агрегатором.
    return {
        'payment_url': None,
        'payment_id': None,
        'error': 'not_implemented',
    }


def get_payment_status(payment_id):
    """Запросить у провайдера актуальный статус счёта.

    Что нужно сделать разработчику:
    1. Взять Payment по payment_id (заглушка — по номеру заказа можно найти
       последний Payment с order.pk).
    2. Вызвать API провайдера (запрос статуса по provider_payment_id).
    3. Проверить подпись/ключ ответа провайдера.
    4. Если провайдер подтвердил оплату — вызвать finalize_payment(payment_id),
       чтобы перевести Order в 'paid' РОВНО ОДИН РАЗ.
    5. Если счёт протух / не оплачен — вернуть текущий статус без изменений.

    Ожидается возврат: dict {'status': 'succeeded'|'pending'|'failed',
    'payment_url': str|None, 'message': str}.
    """
    # TODO (Этап 2): проверка статуса через API провайдера.
    return {
        'status': 'pending',
        'payment_url': None,
        'message': 'Заглушка: статус не запрашивался',
    }


def finalize_payment(payment_id):
    """Подтвердить оплату заказа РОВНО ОДИН РАЗ (единая точка финализации).

    Что нужно сделать разработчику (см. models-dev.md, раздел 5):
    - вся логика в @transaction.atomic + select_for_update на Payment/Order;
    - guard: переход payment.status 'pending' -> 'succeeded' только один раз;
      повторные вызовы (webhook + кнопка «проверить») безопасны (no-op);
    - после подтверждения: order.payment_status='paid', order.paid_at ...
    - списание остатка: если политика «списываем при создании заказа» — здесь
      только фиксируем; если «при оплате» — списываем (F('stock') - quantity, мин 0);
    - инкремент PromoCode.used_count только здесь (он сейчас в app_cart/views.py:203);
    - отправка писем: подтверждение клиенту + уведомление админу.

    Ожидается возврат: Order (или None, если платёж не найден).
    """
    # TODO (Этап 2): финализация по итогам webhook/кнопки «проверить статус».
    return None


def process_payment_callback(request_body):
    """Обработать уведомление (webhook) от провайдера об оплате.

    Что нужно сделать разработчику:
    1. Endpoint — @csrf_exempt (внешний сервис, CSRF не применим);
       НО подпись payload обязательна (проверять по секретному ключу из env).
    2. Разобрать request_body: найти provider_payment_id.
    3. Найти Payment по provider_payment_id.
    4. Если провайдер подтвердил оплату и сумма совпадает — finalize_payment(payment_id).
    5. Ответить провайдеру 200 даже на повторную доставку (идемпотентность в finalize).

    Ожидается возврат: dict {'ok': bool, 'status': str}.
    """
    # TODO (Этап 2): проверка подписи + разбор уведомления провайдера.
    return {
        'ok': False,
        'status': 'not_implemented',
    }


def refund_payment(payment_id):
    """Оформить возврат платежа (действие из админки / кабинета).

    Что нужно сделать разработчику:
    1. Найти Payment (payment_id), сменить статус на 'refunded' (и Order
       payment_status='refunded') только после подтверждения провайдером.
    2. Вернуть остаток товара (если списывали при создании заказа).
    3. Откатить использованный промокод (ограничено: не ниже минимума).
    4. При «оплате при получении» возврат не применяется — статус ставится вручную.

    Ожидается возврат: dict {'ok': bool, 'message': str}.
    """
    # TODO (Этап 2): возврат через API провайдера.
    return {
        'ok': False,
        'message': 'Заглушка: возврат не реализован',
    }


def cancel_unpaid_orders(hours=24):
    """Авто-отмена заказов, не оплаченных в течение N часов (management-команда).

    Что нужно сделать разработчику:
    1. Найти Order с payment_status='pending' и created_at старше hours.
    2. Перевести в order.payment_status='failed', order.status='cancelled'.
    3. Вернуть остатки (если списывались) и откатить PromoCode.used_count.
    4. Учесть задержку уведомлений ЕРИП — порог не менее 24–48 ч.

    Возвращает число обработанных заказов.
    """
    # TODO (Этап 2): management command + celery/cron.
    return 0