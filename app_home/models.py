from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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


class SiteReview(models.Model):
    name = models.CharField(max_length=100, verbose_name='Имя')
    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка',
    )
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f'{self.name} — {self.rating}/5'

    class Meta:
        verbose_name = 'Отзыв о сайте'
        verbose_name_plural = 'Отзывы о сайте'
        ordering = ['-created_at']
