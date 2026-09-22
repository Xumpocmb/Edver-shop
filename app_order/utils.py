"""Генерация публичных номеров заказов и ключей идемпотентности платежей.

Номер заказа — строка вида ``EDV-2026-000037`` (префикс-год-6 цифр).
Генерируется при создании заказа (см. ``create_order_with_number``), при
коллизии unique — попытка повторяется. Тот же номер служит основой для
``Payment.idempotency_key`` (``f'{order.number}-{attempt}'``), поэтому логика
вынесена сюда и переиспользуется из app_cart и app_order.
"""

from datetime import date
import logging

from django.db import IntegrityError
from django.db.models import Max

from app_order.models import Order

logger = logging.getLogger(__name__)

NUMBER_PREFIX = 'EDV'
SEQUENCE_DIGITS = 6
MAX_ATTEMPTS = 100


def _build_number(sequence, prefix=NUMBER_PREFIX, year=None):
    year = year or date.today().year
    return f'{prefix}-{year}-{sequence:0{SEQUENCE_DIGITS}d}'


def _max_sequence(queryset, prefix=NUMBER_PREFIX, year=None):
    year = year or date.today().year
    last = queryset.filter(
        number__startswith=f'{prefix}-{year}-',
    ).aggregate(max_number=Max('number'))['max_number']
    if not last:
        return 0
    return int(last.rsplit('-', 1)[1])


def next_order_number(queryset=None, prefix=NUMBER_PREFIX, year=None):
    """Сгенерировать следующий номер заказа вида ``EDV-2026-000037``.

    Номер строится как следующий после максимального за текущий год. Это
    «кандидат»: окончательную уникальность гарантирует unique-поле и повтор
    попытки в ``create_order_with_number`` при коллизии.
    """
    queryset = queryset or Order.objects.all()
    year = year or date.today().year
    return _build_number(_max_sequence(queryset, prefix, year) + 1, prefix, year)


def create_order_with_number(queryset=None, prefix=NUMBER_PREFIX, year=None,
                             max_attempts=MAX_ATTEMPTS, **fields):
    """Создать заказ, проставив уникальный ``number`` (с повтором при коллизии).

    Пока не задан явно ``fields['number']`` — номер берётся из
    ``next_order_number``. При ``IntegrityError`` (гонка двух запросов по unique)
    номер пересоздаётся и попытка повторяется до ``max_attempts`` раз.
    """
    queryset = queryset or Order.objects.all()
    for _ in range(max_attempts):
        fields['number'] = fields.get('number') or next_order_number(queryset, prefix, year)
        try:
            order = queryset.create(**fields)
            logger.info('Заказ создан: %s (пользователь=%s)', order.number, fields.get('user'))
            return order
        except IntegrityError:
            logger.warning('Коллизия номера заказа %s, повторная попытка', fields['number'])
            continue
    logger.critical('Не удалось создать заказ после %d попыток', max_attempts)
    raise RuntimeError('Не удалось создать заказ: не получилось сгенерировать уникальный номер')


def payment_idempotency_key(order_number, attempt):
    """Ключ идемпотентности Payment: ``'{order.number}-{номер попытки}'``."""
    return f'{order_number}-{attempt}'