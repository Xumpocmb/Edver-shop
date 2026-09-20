from django.shortcuts import render, redirect
from django.contrib import messages


def profile_dashboard(request):
    """Заглушка «Личный кабинет» (Этап 3 плана).

    Что нужно сделать разработчику:
    - поставить @login_required (или LoginRequiredMixin) с редиректом на login?next=...;
    - вывести данные пользователя: ФИО, email, телефон, адрес по умолчанию;
    - показать N последних заказов со ссылками на order_detail;
    - после входа переносить корзину и историю заказов гостя (по session_key)
      на аккаунт, чтобы данные не потерялись;
    - из шапки иконка 👤 уже ведёт на /profile/.
    """
    return render(request, 'app_user/profile.html')


def login_view(request):
    """Заглушка входа (Этап 3 плана).

    Что нужно сделать разработчику:
    - форма «логин + пароль» (или django.contrib.auth.views.LoginView +
      собственный шаблон), CSRF;
    - успешный вход -> редирект на ?next=... или на /profile/;
    - ошибки — сообщения на форме (не только console);
    - запрет повторного входа залогиненным пользователям (редирект на profile).
    """
    return render(request, 'app_user/login.html')


def register_view(request):
    """Заглушка регистрации (Этап 3 плана).

    Что нужно сделать разработчику:
    - форма: имя/Ник, email, пароль x2; валидация уникальности email;
    - создать пользователя (django.contrib.auth), можно без активации по email;
    - после регистрации — авто-вход и редирект на /profile/;
    - привязать корзину/заказы гостя (session_key) к новому аккаунту.
    """
    return render(request, 'app_user/register.html')


def logout_view(request):
    """Заглушка выхода (Этап 3 плана).

    Что нужно сделать разработчику:
    - только POST (по современным требованиям безопасности) или действие по кнопке,
      вызывающее django.contrib.auth.logout;
    - после выхода — редирект на главную.
    """
    messages.info(request, 'Заглушка: выход ещё не реализован.')
    return redirect('/')