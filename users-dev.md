# users-dev.md — Авторизация и регистрация по номеру телефона

Документ для разработчика. Описывает, как включить вход/регистрацию в магазине
EDVER Shop через **номер телефона + пароль**.

Требования владельца:
- почта (email) НЕ используется и не запрашивается;
- никаких «проверок входа» (без SMS-кода, без OTP, без подтверждения email) —
  регистрация = сразу создание аккаунта и вход;
- вход только по паре «номер телефона» + «пароль».

Далее: сначала поправка к популярному заблуждению, затем два способа
реализации (А — минимальный, Б — чистый), затем общие для обоих моменты.

## Важная поправка: Django НЕ требует email

Стандартная модель `django.contrib.auth.models.AbstractUser` устроена так:
- `username` — **обязательное** уникальное поле (это и есть «логин»);
- `email` — необязательное, НЕ уникальное, и в формах регистрации/входа не
  участвует.

То есть «разрешать ситуацию» нужно не с email, а с `username`: им станет **номер
телефона**. Формы входа `AuthenticationForm` и регистрации `UserCreationForm`
содержат ровно поля `username` + `password` — поэтому из коробки они почти
подходят, надо лишь:

1. переименовать подпись «Имя пользователя» → «Телефон»;
2. нормализовать номер (единый формат `+375XXXXXXXXX`);
3. убрать из форм всё, что про email (в современных Django оно уже не входит).

## Вариант А (рекомендуется сейчас): дефолтный User, телефон в username

Никакой замены модели, никакого сброса БД, переносимый минимум изменений.
Телефон хранится в поле `username`.

Плюсы: не трогаем существующее админ-окружение (`auth_user`), не меняем
`AUTH_USER_MODEL`, все FK на `settings.AUTH_USER_MODEL` (корзина/заказы в
`app_cart/models.py`) продолжают работать как есть.
Минус: поле в админке называется `username` (переименуем подписи), а не чистый
«телефон».

### Шаг 1. Нормализация телефона — `app_user/utils.py` (новый файл)

```python
import re

PHONE_SYMBOLS = re.compile(r'[\s\-()]')
PHONE_RE = re.compile(r'^\+375(25|29|33|44)\d{7}$')


def normalize_phone(value):
    """Приводит номер к виду +375XXXXXXXXX. Пустое значение -> пустая строка."""
    if not value:
        return ''
    raw = PHONE_SYMBOLS.sub('', str(value).strip())
    return raw if PHONE_RE.match(raw) else ''
```

### Шаг 2. Формы — `app_user/forms.py` (новый файл)

```python
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.contrib.auth import get_user_model

from .utils import normalize_phone

User = get_user_model()


class PhoneAuthenticationForm(AuthenticationForm):
    """Вход по номеру телефона и паролю."""

    username = UsernameField(label='Телефон', widget=forms.TextInput(attrs={
        'autofocus': True,
        'inputmode': 'tel',
        'placeholder': '+375 (29) XXX-XX-XX',
    }))

    def clean_username(self):
        username = normalize_phone(self.cleaned_data['username'])
        if not username:
            raise forms.ValidationError('Укажите номер в формате +375 (29) XXX-XX-XX.')
        return username


class PhoneUserCreationForm(UserCreationForm):
    """Регистрация: телефон + пароль. Email не запрашивается."""

    username = forms.CharField(label='Телефон', widget=forms.TextInput(attrs={
        'autofocus': True,
        'inputmode': 'tel',
        'placeholder': '+375 (29) XXX-XX-XX',
    }))

    class Meta:
        model = User
        fields = ('username',)

    def clean_username(self):
        username = normalize_phone(self.cleaned_data['username'])
        if not username:
            raise forms.ValidationError('Укажите номер в формате +375 (29) XXX-XX-XX.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким номером уже зарегистрирован.')
        return username
```

### Шаг 3. Вью — заменить заглушки в `app_user/views.py`

```python
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from app_cart.models import Cart, Order

from .forms import PhoneAuthenticationForm, PhoneUserCreationForm


def claim_guest_data(request, user):
    """Привязывает корзину и заказы гостя (session_key) к аккаунту."""
    cart = Cart.get_or_create(request)
    if cart.user is None or cart.user != user:
        cart.user = user
        cart.save(update_fields=['user'])
    Order.objects.filter(
        session_key=request.session.session_key,
        user__isnull=True,
    ).update(user=user)


class UserLoginView(LoginView):
    template_name = 'app_user/login.html'
    form_class = PhoneAuthenticationForm
    redirect_authenticated_user = True
    next_page = reverse_lazy('app_user:profile')


class UserRegisterView(CreateView):
    template_name = 'app_user/register.html'
    form_class = PhoneUserCreationForm
    success_url = reverse_lazy('app_user:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        claim_guest_data(self.request, self.object)
        return response


class UserLogoutView(LogoutView):
    next_page = '/'   # выход только через POST — так и задумано
```

`profile_dashboard` добавить декоратор:

```python
from django.contrib.auth.decorators import login_required

@login_required
def profile_dashboard(request):
    return render(request, 'app_user/profile.html')
```

### Шаг 4. URL — `app_user/urls.py`

```python
from django.urls import path

from app_order import views as order_views
from . import views

app_name = 'app_user'

urlpatterns = [
    path('', views.profile_dashboard, name='profile'),
    path('orders/', order_views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', order_views.order_detail, name='order_detail'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
]
```

Заглушки `login_view`, `register_view`, `logout_view` удалить.

### Шаг 5. Настройки `_settings/settings.py`

```python
LOGIN_URL = '/profile/login/'
LOGIN_REDIRECT_URL = '/profile/'
LOGOUT_REDIRECT_URL = '/'
```

### Шаг 6. Шаблоны

- `app_user/login.html`, `app_user/register.html` — формы рендерятся как обычно
  (`form.as_p` или вручную). Поля уже подписаны «Телефон». После успешного входа
  `LoginView` сам ведёт на `?next=...` или на `/profile/`.
- В шапке переключатель: если `request.user.is_authenticated` — «Выйти» (POST),
  иначе «Войти» / «Регистрация». Иконка 👤 уже ведёт на `/profile/`.

### Шаг 7. Админка: переименовать подписи и скрыть email

```python
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

class UserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser',
                              'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    filter_horizontal = ('groups', 'user_permissions')
    list_display = ('username', 'first_name', 'last_name', 'is_staff')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
```

Email при желании можно совсем убрать из fieldsets (поле останется пустым).

## Вариант Б (более чистый, когда можно сбросить БД): кастомная модель User

Предпочтителен по архитектуре, но требует `AUTH_USER_MODEL` ДО первой миграции.
В этом проекте миграции не в git и есть скрипт сидирования каталога — поэтому
переход возможен ценой пересоздания dev-базы.

Вариант Б не для «на живую» БД: во время продакшена менять
`AUTH_USER_MODEL` нельзя (потребует ручного переноса `auth_user` → новая таблица).
Делать до релиза или на чистой dev-базе.

### Модель — `app_user/models.py`

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .utils import PHONE_RE


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError('Телефон обязателен.')
        phone = str(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(phone, password, **extra_fields)


class User(AbstractUser):
    username = None          # отключаем стандартный логин
    email = None             # не используем
    phone = models.CharField(
        'Телефон',
        max_length=16,
        unique=True,
        validators=[PHONE_RE.fullmatch],
    )

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.phone
```

(Поле `phone` должно описываться регуляркой вида
`re.compile(r'^\+375(25|29|33|44)\d{7}$')` — см. `app_user/utils.py`.)

### Настройки

```python
AUTH_USER_MODEL = 'app_user.User'
```

Обязательно до пересоздания БД и до `makemigrations`. Приложение `app_user` уже
в `INSTALLED_APPS`. Все FK (`app_cart.models.Order.user`, `Cart.user`,
`CartItem`/`OrderItem`) ссылаются на `settings.AUTH_USER_MODEL` — автоматически
последуют за новой моделью.

### Пересоздание dev-базы

```bash
rm -f db.sqlite3 media/uploads/*
venv/bin/python manage.py makemigrations app_user app_cart app_catalog app_home app_order
venv/bin/python manage.py migrate
venv/bin/python manage.py createsuperuser --phone '+375291111111'   # админ
venv/bin/python manage.py seed_catalog
```

### Формы — берутся из Варианта А

`PhoneAuthenticationForm` и `PhoneUserCreationForm` подходят без изменений:
`UserCreationForm` собирает поля из `Meta.fields` — оставляем только `phone`:

```python
class PhoneUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('phone',)
        field_classes = {'phone': forms.CharField}
```

label переопределяется так же (см. Шаг 3 Варианта А). Вход —
`AuthenticationForm` — работает по `USERNAME_FIELD` = `phone`, надо только
переименовать метку и нормализовать номер.

### Админка — свой ModelAdmin

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class UserAdmin(UserAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'last_name')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser',
                              'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('phone', 'password1', 'password2')}),
    )
    list_display = ('phone', 'first_name', 'last_name', 'is_staff')
    search_fields = ('phone', 'first_name', 'last_name')
    ordering = ('phone',)
```

## Что намеренно НЕ делаем

- email не собираем и не валидируем;
- никаких SMS/OTP/кодов — вход без «проверок»;
- никакой активации по почте и «подтверждений».

Внимание к безопасности (на память): без OTP атака «по номеру телефона»
защищается только паролем. Рекомендуется https на проде, `SECURE_SSL_REDIRECT`
и стандартные `AUTH_PASSWORD_VALIDATORS` (в `settings.py` они уже подключены,
линия ~91).

## Чек-лист проверки (dev)

1. `venv/bin/python manage.py check` — 0 issues.
2. Регистрация: создаёт пользователя, сразу входит, корзина гостя переезжает.
3. Вход по номеру в формате `+375 (29) 111-11-11` и `+375291111111` — оба
   распознаются как один номер (нормализация).
4. Дубль номера при регистрации → ошибка формы, а не 500.
5. Неверный пароль → ошибка «Введите правильный номер телефона и пароль».
6. `/profile/` без входа → редирект на `/profile/login/?next=/profile/`.
7. Выход — только POST.
8. Заказы гостя (`/profile/orders/`) после входа привязались к аккаунту.
9. Админка: создание/редактирование пользователя по телефону без email.