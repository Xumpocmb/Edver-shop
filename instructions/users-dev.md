# users-dev.md — Авторизация и регистрация по номеру телефона

Документ для разработчика. Описывает, как включить вход/регистрацию в магазине
EDVER Shop через **номер телефона + пароль**.

Требования владельца:
- почта (email) НЕ используется и не запрашивается;
- никаких «проверок входа» (без SMS-кода, без OTP, без подтверждения email) —
  регистрация = сразу создание аккаунта и вход;
- вход только по паре «номер телефона» + «пароль».

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

