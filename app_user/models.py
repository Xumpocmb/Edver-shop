from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfile(models.Model):
    """Профиль пользователя: ФИО, телефон, адрес."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь',
    )
    full_name = models.CharField(max_length=200, blank=True, verbose_name='ФИО')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес доставки')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'Профиль {self.user.username}'