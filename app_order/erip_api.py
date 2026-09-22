from datetime import datetime, timedelta
import hashlib
import hmac
from decimal import Decimal
import requests

"""При создании платежа необходим order_number формата "EDV-2026-000007"
Затем этот номер заказа парсится в payment_id формата "2026-000007", отбрасывая EDV
Покупателю при оплате показывается номер счета формата "34789-1-[payment_id]", а также продавец "ИП Рогальская В.И."
34789-1 - это данные услуги "Оплата товара" в ЛК express pay
"""

EXPRESS_PAY_TOKEN = "c97db2a0fc171b79667eb53de5a5bbba"  # токен для отправки запросов (данные из ЛК)
EXPRESS_PAY_URL = "https://api.express-pay.by/v1/"  # url
KEY = "Edver"  # кодовое слово для цифровой подписи (данные из ЛК)

# словарь {статус express pay - перевод}
PAYMENT_STATUS = {
    "1": "pending",
    "2": "failed",
    "3": "paid",
    "5": "failed",
}


def get_signature(data):
    """Получение цифровой подписи"""
    key = KEY.encode("utf-8")
    raw = data.encode("utf-8")

    digester = hmac.new(key, raw, hashlib.sha1)
    signature = digester.hexdigest()

    return signature.upper()


def get_payment_id_by_order_number(order_number: str):
    """Отбрасывание EDV из номера заказа для получения номера счета
    Возвращает строку формата 2026-000006"""
    number = order_number.split('-')
    payment_id = f"{number[1]}-{number[2]}"
    return payment_id


def erip_get_invoices(payment_id: str, status: int | None = None):
    """Получаем все выставленные счета клиента по payment_id.
    Используется для получения статуса, а также очищения неоплаченных счетов при выставлении нового
    Если status не передан - возвращаются все счета
    Если status = 1 - возвращаются только не оплаченные (для их отмены при выставлении нового)"""
    url = EXPRESS_PAY_URL + "invoices"

    params = {
        "Token": EXPRESS_PAY_TOKEN,
        "AccountNo": payment_id,
    }

    if status is not None:
        params["Status"] = status

    data = ""
    for p in params.values():
        data += str(p)

    signature = get_signature(data)
    params["signature"] = signature
    if status is not None:
        url += f"?token={EXPRESS_PAY_TOKEN}&AccountNo={payment_id}&Status={status}&signature={signature}"
    else:
        url += f"?token={EXPRESS_PAY_TOKEN}&AccountNo={payment_id}&signature={signature}"
    res_invoices = requests.get(url, data=params).json()
    return res_invoices.get("Items", [])


def erip_clear_not_paid_invoices(payment_id: str):
    """Очищает выставленные и неоплаченные счета клиента, чтобы не суммировались прайсы платежей
    Ничего не возвращает"""
    url = EXPRESS_PAY_URL + "invoices"

    invoices = erip_get_invoices(payment_id, status=1)  # получаем все неоплаченные счета

    for inv in invoices:  # отменяем каждый
        params = {
            "Token": EXPRESS_PAY_TOKEN,
            "InvoiceNo": inv.get("InvoiceNo")
        }
        data = ""
        for p in params.values():
            data += str(p)
        signature = get_signature(data)
        params["signature"] = signature
        url += f"/{str(inv.get('InvoiceNo'))}?token={EXPRESS_PAY_TOKEN}&InvoiceNo={str(inv.get('InvoiceNo'))}" \
               f"&signature={signature}"
        requests.delete(url, data=params)


def erip_create_payment_invoice(amount: Decimal, order_number: str):
    """Получение payment_id и ссылки на оплату.
    Сначала из order_number получается номер счета, затем отправляется запрос провайдеру.
    Возвращает payment_id и payment_url
    Срок жизни счета - 1 час. По истечению этого времени счет перейдет в статус просрочен"""
    payment_id = get_payment_id_by_order_number(order_number)  # получаем номер счета из номера заказа
    erip_clear_not_paid_invoices(payment_id)  # очищаем все неоплаченные счета к этому же заказу
    url = f"{EXPRESS_PAY_URL}invoices?token={EXPRESS_PAY_TOKEN}"
    expiration = (datetime.now() + timedelta(hours=1)).strftime("%Y%m%d%H%M")  # срок истечет в [сейчас + час]
    params = {
        "Token": EXPRESS_PAY_TOKEN,
        "AccountNo": payment_id,
        "Amount": str(amount),
        "Currency": "933",
        "Expiration": expiration,
        "IsAmountEditable": "0",
        "ReturnInvoiceUrl": "1"
    }

    data = ""
    for p in params.values():
        data += str(p)

    params["signature"] = get_signature(data)
    res = requests.post(url, data=params).json()

    payment_url = res.get("InvoiceUrl", None)

    return {
        "payment_id": payment_id,
        "payment_url": payment_url
    }


def erip_check_invoice_status(payment_id: str):
    """Проверка статуса выставленных счетов"""
    invoices = erip_get_invoices(payment_id)  # получаем все счета, выставленные на этот заказ
    if len(invoices) == 0:  # если ни одного нужного счета не найдено
        return {
            "payment_id": None,
            "status": None
        }
    for inv in invoices:  # проверка всех подходящих счетов на статус "ожидает оплаты"
        if inv["Status"] == 1:
            return {
                "payment_id": inv.get("AccountNo", None),
                "status": PAYMENT_STATUS.get(str(inv["Status"]), None)
            }
    for inv in invoices:  # проверка всех подходящих счетов на статус "оплачено"
        if inv["Status"] == 3:
            return {
                "payment_id": inv.get("AccountNo", None),
                "status": PAYMENT_STATUS.get(str(inv["Status"]), None)
            }
    return {  # если нет ни одного оплаченного или ожидает оплаты счета (то есть все отменены или просрочены)
        "payment_id": payment_id,
        "status": PAYMENT_STATUS.get("5", None)
    }