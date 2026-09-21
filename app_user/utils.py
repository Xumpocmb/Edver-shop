import re

PHONE_SYMBOLS = re.compile(r'[\s\-()]')
PHONE_RE = re.compile(r'^\+375(25|29|33|44)\d{7}$')


def normalize_phone(value):
    """Приводит номер к виду +375XXXXXXXXX. Пустое значение -> пустая строка."""
    if not value:
        return ''
    raw = PHONE_SYMBOLS.sub('', str(value).strip())
    return raw if PHONE_RE.match(raw) else ''