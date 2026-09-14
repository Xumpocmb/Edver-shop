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


class PhoneNumber(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    number = models.CharField(
        max_length=20,
        default='+375299673138',
        verbose_name='Номер телефона',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'Номер телефона'
        verbose_name_plural = 'Номер телефона'


class Instagram(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    url = models.URLField(
        default='https://instagram.com/',
        verbose_name='Ссылка на Instagram',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = 'Instagram'
        verbose_name_plural = 'Instagram'


class FooterInfo(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    text = models.TextField(verbose_name='Текст', default='')

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Информация в футере'

    class Meta:
        verbose_name = 'Информация в футере'
        verbose_name_plural = 'Информация в футере'
