"""Telegram-уведомления о заказах.

Токен бота и получатели хранятся в админке (модели TelegramBotSettings и
TelegramRecipient). Отправка — простой POST на API Telegram через `requests`.
Все ошибки сети/API перехватываются, чтобы уведомления никогда не ломали
оформление заказа или финализацию оплаты.
"""

import html
import logging

import requests

from .models import TelegramBotSettings, TelegramRecipient

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = 'https://api.telegram.org/bot{token}/sendMessage'


def _esc(value):
    """Экранировать значение для HTML parse_mode."""
    return html.escape(str(value))


def get_bot_settings():
    return TelegramBotSettings.objects.first()


def send_message(text):
    """Отправить текст всем активным получателям.

    Возвращает int — количество успешно отправленных сообщений.
    """
    settings = get_bot_settings()
    if settings is None or not settings.is_active or not settings.bot_token:
        return 0

    recipients = TelegramRecipient.objects.filter(is_active=True)
    if not recipients.exists():
        return 0

    sent = 0
    for recipient in recipients:
        try:
            response = requests.post(
                TELEGRAM_API_URL.format(token=settings.bot_token),
                data={'chat_id': recipient.chat_id, 'text': text, 'parse_mode': 'HTML'},
                timeout=10,
            )
            response.raise_for_status()
            sent += 1
        except Exception:  # noqa: BLE001
            logger.exception('Telegram: ошибка отправки получателю %s', recipient.chat_id)
    return sent


def _order_items_summary(order, limit=8):
    items = list(order.items.values_list('product_name', 'quantity')[:limit])
    lines = [f'• {name} — {qty} шт.' for name, qty in items]
    leftover = order.items.count() - len(lines)
    if leftover > 0:
        lines.append(f'... и ещё {leftover} поз.')
    return '\n'.join(lines) or '• позиции не указаны'


def notify_new_order(order):
    """Уведомление о новом заказе (приходит сразу, даже без оплаты)."""
    text = (
        '🛒 <b>Новый заказ {number}</b>\n'
        '\n'
        '👤 {full_name} ({phone})\n'
        '🚚 {delivery}\n'
        '{destination}\n'
        '💰 Сумма: <b>{total} BYN</b>\n'
        '{paid_line}'
        '\n'
        '<b>Состав заказа:</b>\n'
        '{items}'
    ).format(
        number=_esc(order.number),
        full_name=_esc(order.full_name),
        phone=_esc(order.phone),
        delivery=_esc(order.get_delivery_type_display()),
        destination=_delivery_destination(order),
        total=_esc(order.grand_total),
        paid_line='💳 Оплачен\n' if order.paid else '',
        items=_order_items_summary(order),
    )
    return send_message(text)


def notify_paid_order(order):
    """Уведомление о том, что заказ оплачен."""
    text = (
        '💳 <b>Заказ {number} оплачен</b>\n'
        '\n'
        '👤 {full_name} ({phone})\n'
        '💰 Сумма: <b>{total} BYN</b>\n'
        '🔗 Заказ: <code>{order_link}</code>'
    ).format(
        number=_esc(order.number),
        full_name=_esc(order.full_name),
        phone=_esc(order.phone),
        total=_esc(order.grand_total),
        order_link=_esc(f'/orders/{order.pk}/'),
    )
    return send_message(text)


def _delivery_destination(order):
    if order.delivery_type == 'evropochta':
        return f'📍 Отделение: {_esc(order.evropochta_branch_name or "—")}'
    return f'📍 Адрес: {_esc(order.address or "—")}'