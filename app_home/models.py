from django.db import models


class SiteLogo(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    text = models.CharField(max_length=100, default='EDVER Shop', verbose_name='Текст (если нет картинки)')
    image = models.ImageField(upload_to='logo/', blank=True, null=True, verbose_name='Картинка')

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Логотип сайта'

    class Meta:
        verbose_name = 'Логотип сайта'
        verbose_name_plural = 'Логотип сайта'
