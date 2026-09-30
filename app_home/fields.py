"""Поля моделей с HTML-редактором Summernote.

Summernote из коробки чистит HTML через bleach с allowlist, в котором у `<img>`
нет `src`, — загруженная в редактор картинка исчезала бы при сохранении.
Поэтому фильтруем сами, оставляя всё, что редактор реально производит.
"""

import bleach
from django import forms
from django.db import models
from django_summernote.fields import SummernoteTextField, SummernoteTextFormField

ALLOWED_TAGS = [
    'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'figcaption', 'figure',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img', 'li', 'ol', 'p',
    'pre', 's', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td',
    'tfoot', 'th', 'thead', 'tr', 'u', 'ul',
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style', 'title', 'align'],
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan', 'scope'],
}

ALLOWED_STYLES = [
    'background-color', 'color', 'font-family', 'font-size', 'font-style',
    'font-weight', 'height', 'line-height', 'margin', 'padding', 'text-align',
    'text-decoration', 'width',
]


def clean_html(value):
    if not value:
        return value
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        styles=ALLOWED_STYLES,
    )


class SummernoteFormField(SummernoteTextFormField):
    def to_python(self, value):
        return clean_html(forms.CharField.to_python(self, value))


class SummernoteContentField(SummernoteTextField):
    def formfield(self, **kwargs):
        # Пропускаем SummernoteTextField.formfield: он подставляет свой
        # SummernoteTextFormField поверх переданного form_class.
        return super(SummernoteTextField, self).formfield(
            form_class=SummernoteFormField, **kwargs
        )

    def to_python(self, value):
        return clean_html(models.TextField.to_python(self, value))
