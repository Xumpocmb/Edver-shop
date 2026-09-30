"""Имена файлов и slug'и латиницей: транслитерация, чтобы кириллица не ломала пути."""

from django.utils.text import slugify

TRANSLIT_DICT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}

_TRANSLIT_TABLE = str.maketrans(TRANSLIT_DICT)


def translit_slug(text):
    """``Сумка красная`` -> ``sumka-krasnaya``."""
    return slugify(text.lower().translate(_TRANSLIT_TABLE))
