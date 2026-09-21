# Модели данных: Заказы и Оплаты

Документ для разработчиков. Описывает целевые модели модуля заказов и оплат и логику их статусов.
Текущие модели лежат в `app_cart/models.py`. Заказы работают уже сейчас; ниже — что добавить и как.
модели нужно перенести в `app_order`; **дублей моделей не создавать**.

---

## 1. Order — заказ

Модель уже существует. Достаём поля как есть, **добавляем 3 поля**: `number`, `payment_status`, `payment_method`, `paid_at`.

### Поля (существующие, не менять)
| Поле | Тип | Примечание |
|---|---|---|
| `id` | PK | публично не показывать |
| `user` | FK → `AUTH_USER_MODEL`, `SET_NULL`, null/blank | гостевой заказ = `NULL` |
| `session_key` | Char(64), `db_index` | для гостевых заказов и поиска «своего» заказа |
| `full_name` | Char(200) | ФИО |
| `phone` | Char(30) | телефон |
| `address` | Text(blank) | адрес для Белпочты |
| `delivery_type` | Char(20): `belpochta` / `evropochta` | |
| `evropochta_branch_id` / `_name` | Char(50)/Char(300), blank | отделение Европочты |
| `promo_code` | FK → `PromoCode`, `SET_NULL`, null/blank | |
| `promo_discount` | Decimal(10,2) | скидка, посчитана на сервере при оформлении |
| `total_price` | Decimal(10,2) | сумма товаров |
| `grand_total` | Decimal(10,2) | **итого к оплате** = `total_price − promo_discount` |
| `status` | Char(20): `new / processing / shipped / delivered / cancelled` | жизненный цикл доставки |
| `comment` | Text(blank) | |
| `created_at` / `updated_at` | auto | |

`Meta`: `ordering = ['-created_at']`, verbose_name «Заказ».

### Новые поля
```python
class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('failed', 'Не оплачен'),
        ('refunded', 'Возврат'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('erip', 'ЕРИП'),
        ('card', 'Банковская карта'),
        ('cash_on_delivery', 'Наличными при получении'),
    ]

    # публичный номер заказа, показываем клиенту и шлём в ЕРИП-счёт
    number = models.CharField(max_length=30, unique=True, db_index=True, verbose_name='Номер заказа')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES,
                                      default='pending', db_index=True, verbose_name='Статус оплаты')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES,
                                      default='erip', verbose_name='Способ оплаты')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='Оплачен')
```

**Генерация `number`**: вида `EDV-2026-000037` (префикс-год-6 цифр). Генерировать при создании заказа, при коллизии — повторить (unique). Сделать отдельной утилитой, чтобы использовать в `Payment.idempotency_key`.

**Примечание по доступу:** `order_success` и «проверить статус» (см. `app_cart/views.py:212`) сейчас открыты по `pk`. Для гостя ограничивать по `session_key`, для авторизованного — по `request.user`, либо добавить короткий `access_token` (в ссылку из ЕРИП-счёта). Иначе чужие заказы видны по номеру.

---

## 2. OrderItem — позиция заказа

Уже существует, не меняем:
| Поле | Тип | Примечание |
|---|---|---|
| `order` | FK → `Order`, `CASCADE`, related `items` | |
| `variant` | FK → `ProductVariant`, `SET_NULL`, null | снапшот остаётся по названию |
| `product_name` | Char(300) | зафиксировано при заказе |
| `product_color` | Char(100) | |
| `unit_price` | Decimal(10,2) | цена на момент заказа (снапшот) |
| `quantity` | PositiveInt | |

Свойство `line_total = unit_price * quantity`.

---

## 3. Payment — платёж (новое)

Один заказ может иметь несколько попыток оплаты → `Order` ↔ `Payment` — 1:N.

```python
class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('succeeded', 'Оплачен'),
        ('failed', 'Не оплачен'),
        ('refunded', 'Возврат'),
    ]
    METHOD_CHOICES = Order.PAYMENT_METHOD_CHOICES  # erip / card / cash_on_delivery

    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='payments', verbose_name='Заказ')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Сумма')
    currency = models.CharField(max_length=3, default='BYN', verbose_name='Валюта')

    method = models.CharField(max_length=30, choices=METHOD_CHOICES, verbose_name='Способ оплаты')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='pending', db_index=True, verbose_name='Статус')

    # данные провайдера
    provider = models.CharField(max_length=50, verbose_name='Провайдер')  # bePaid / WebPay / ...
    provider_payment_id = models.CharField(max_length=100, unique=True, verbose_name='ID счёта у провайдера')
    payment_url = models.URLField(null=True, blank=True, verbose_name='Ссылка на оплату')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Срок действия ссылки')

    # идемпотентность: повторный клик «Оплатить» не создаёт дубль счёта
    idempotency_key = models.CharField(max_length=100, unique=True, verbose_name='Ключ идемпотентности')

    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='Оплачен')
    refunded_at = models.DateTimeField(null=True, blank=True, verbose_name='Возврат')

    raw_response = models.JSONField(null=True, blank=True, editable=False, verbose_name='Ответ провайдера')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['status']),
        ]

    @property
    def is_succeeded(self):
        return self.status == 'succeeded'
```

Правила по данным:
- `amount` берём **только из БД** (`order.grand_total`), от клиента и из webhook сумму не принимать.
- `idempotency_key` = например `f'{order.number}-{attempt}'`; при `IntegrityError` — заказать новый счёт у провайдера с новым ключом.
- `provider_payment_id` уникален (поставщик шлёт свой ID) — защита от повторной передачи одного счёта.
- `raw_response` — сырой ответ API/webhook для отладки.

---

## 4. Переходы статусов

### Payment.status
```
pending ──► succeeded      (подтверждено провайдером: webhook ИЛИ кнопка «проверить»)
pending ──► failed         (провайдер вернул отказ)
succeeded ─► refunded      (операция возврата)
```
Любой переход `pending → succeeded` выполняется **только один раз** через единую функцию финализации.

### Order.payment_status
```
pending ──► paid      (есть Payment.succeeded)
paid ────► refunded   (возврат оформлен)
pending ──► failed    (заказ протух и не оплачен → авто-отмена)
```

### Order.status (независимо, жизненный цикл доставки)
```
new ──► processing ──► shipped ──► delivered
любой ──► cancelled            (при отмене — вернуть остаток и used_count промокода)
```

---

## 5. Единая функция финализации

кнопка «Проверить статус оплаты» 

```python
from django.db import transaction


@transaction.atomic
def finalize_payment(payment_id: int) -> Payment:
    """Пометить платёж успешным РОВНО ОДИН РАЗ и завершить заказ."""
    payment = Payment.objects.select_for_update().select_related('order').get(pk=payment_id)

    if payment.status == 'succeeded':
        return payment  # уже обработан — повторный webhook/клик безопасен

    if payment.status != 'pending':
        return payment  # failed/refunded не трогаем

    # ставим статус сразу, чтобы второй поток/повторный вызов не прошёл
    payment.status = 'succeeded'
    payment.paid_at = timezone.now()
    payment.save(update_fields=['status', 'paid_at', 'updated_at'])

    order = payment.order
    order.payment_status = 'paid'
    order.paid_at = payment.paid_at
    order.save(update_fields=['payment_status', 'paid_at', 'updated_at'])

    # если политика «списываем при оплате» (а не при создании заказа):
    #   for item in order.items.all():
    #       ProductVariant.objects.filter(pk=item.variant_id).select_for_update()
    #           .update(stock=F('stock') - item.quantity))  # не ниже 0

    # счётчик промокода — только здесь, один раз (сейчас он в app_cart/views.py:203–205, убрать)
    if order.promo_code:
        PromoCode.objects.filter(pk=order.promo_code_id). \
            update(used_count=F('used_count') + 1)

    # письма: подтверждение оплаты клиенту + уведомление админу
    return payment
```

Точки входа:
1. **Webhook провайдера** — `@csrf_exempt`, проверка подписи → найти `Payment` по `provider_payment_id` → `finalize_payment(id)`.
2. **Кнопка «Проверить статус оплаты»** — сервер сам запрашивает у провайдера статус по `provider_payment_id`; если провайдер подтверждает оплату → `finalize_payment(id)`, иначе возвращаем клиенту «ещё не оплачено».
3. Первый показ страницы заказа — той же функцией подтянуть свежий статус (опционально, без клика).

Правило: **никто и ничто (ни клиент, ни повторный webhook) не может «заявить» оплату** — только ответ провайдера, проверенный подписью/ключом.

---

## 6. Что учесть при реализации (нюансы)

- **Деньги**: везде `Decimal`, НЕ float; округление до `0.01`; `amount` в BYN (сайт сейчас показывает «₽» — согласовать отображение, технически менять нечего).
- **Гонки**: `select_for_update()` на `Payment` (и `Order`/`ProductVariant` при списании). На SQLite конкурентность слабая — до онлайн-оплат перейти на PostgreSQL.
- **Списание остатка**: если списываем при создании заказа (текущее поведение) — возвращать остаток при `cancelled` и авто-отмене «не оплачен по таймауту»; если при оплате — финализация списывает. Выбрать один вариант и держать в одном месте.
- **Таймаут неоплаченных**: ЕРИП-уведомления приходят с задержкой (минуты–часы) — авто-отмену ставить не раньше 24–48 ч (management-команда по расписанию: `pending` старше N часов → `failed`, вернуть остаток и `used_count`).
- **Промокод**: `used_count` инкрементировать только в `finalize_payment` (не при создании заказа).
- **Ретрай ссылки**: кнопка «Оплатить» повторно → новая попытка `Payment` с новым `idempotency_key`; протухший `payment_url`/`expires_at` — только новый счёт, без дублей.
- **Гость vs пользователь**: платежи и заказы гостя привязывать к `session_key` (доступ к «проверить статус» — только по своей сессии); после входа переносить на `user`. В кабинете показывать только `user.orders`.
- **Подпись webhook**: `@csrf_exempt` допустим только при проверке подписи провайдера; ключи — в env, не в git.
- **Существующие модели не ломать**: `PromoCode`, `EvropochtaBranch`, `OrderItem` остаются как есть.
- **Миграции**: файлы миграций не в git — после правки моделей прогнать `makemigrations` + `migrate` на каждой среде (dev/stage/prod отдельно).

---

## 7. Сводная схема связей

```
Order ──1:N──► OrderItem ──► ProductVariant (SET_NULL)
  │
  ├──FK user (AUTH_USER_MODEL, SET_NULL)      # авторизованный
  ├──session_key                               # гость
  ├──promo_code ──► PromoCode
  │
  └──1:N──► Payment ──► provider_payment_id / payment_url / idempotency_key
```

Декомпозиция задач: 1) поля `Order` + генерация `number`; 2) модель `Payment`; 3) функция `finalize_payment`; 4) endpoint «проверить статус» + кнопка; 5) webhook провайдера; 6) авто-отмена по таймауту; 7) возвраты; 8) сообщения/письма.
