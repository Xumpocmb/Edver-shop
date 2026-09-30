import sys
import traceback

from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError
from django.template.loader import render_to_string
from django.views.decorators.csrf import requires_csrf_token

ERROR_403_TEMPLATE = 'app_home/error_403.html'
ERROR_404_TEMPLATE = 'app_home/error_404.html'
ERROR_500_TEMPLATE = 'app_home/error_500.html'

FALLBACK_500_BODY = (
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    '<title>500 — EDVER Shop</title></head><body>'
    '<h1>500 — серверная ошибка</h1>'
    '<p>Мы уже знаем о проблеме. Попробуйте обновить страницу или вернуться позже.</p>'
    '</body></html>'
)


def _current_user(request):
    return getattr(request, 'user', None)


def _error_report(request, exception):
    actor = _current_user(request)
    return {
        'type': f'{type(exception).__module__}.{type(exception).__name__}',
        'message': str(exception) or '(сообщение отсутствует)',
        'traceback': ''.join(traceback.format_exception(exception)),
        'method': request.method,
        'path': request.get_full_path(),
        'referer': request.META.get('HTTP_REFERER') or '—',
        'remote_addr': request.META.get('REMOTE_ADDR') or '—',
        'actor': str(actor) if actor else '—',
    }


@requires_csrf_token
def permission_denied(request, exception, template_name=ERROR_403_TEMPLATE):
    context = {
        'code': 403,
        'icon': '\U0001f512',
        'title': 'Доступ закрыт',
        'text': 'У вас нет прав, чтобы открыть эту страницу. '
                'Войдите в аккаунт с нужными правами или вернитесь на главную.',
        'show_login': not getattr(_current_user(request), 'is_authenticated', False),
    }
    return HttpResponseForbidden(render_to_string(template_name, context, request=request))


@requires_csrf_token
def page_not_found(request, exception, template_name=ERROR_404_TEMPLATE):
    context = {
        'code': 404,
        'icon': '\U0001f9ed',
        'title': 'Страница не найдена',
        'text': 'Такой страницы нет. Возможно, адрес введён с ошибкой, '
                'товар снят с продажи или раздел переехал.',
    }
    return HttpResponseNotFound(render_to_string(template_name, context, request=request))


@requires_csrf_token
def server_error(request, exception=None, template_name=ERROR_500_TEMPLATE):
    # Django вызывает 500-хендлер как callback(request), без exception,
    # но прямо во время обработки исключения — поэтому добираем его из sys.
    if exception is None:
        exception = sys.exc_info()[1]

    actor = _current_user(request)
    context = {
        'code': 500,
        'icon': '⚠️',
        'title': 'Что-то пошло не так',
        'text': 'Сервер не смог обработать запрос. Мы уже знаем о проблеме — '
                'попробуйте обновить страницу или вернуться позже.',
        'error': _error_report(request, exception) if getattr(actor, 'is_superuser', False) else None,
    }

    try:
        html = render_to_string(template_name, context, request=request)
    except Exception:
        # Страница ошибки не должна приводить к новой ошибке:
        # если сломался рендер (например, недоступна БД) — отдаём запасной вариант.
        html = FALLBACK_500_BODY
    return HttpResponseServerError(html)
