from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from ckeditor.fields import RichTextField


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


class SiteFavicon(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    image = models.ImageField(upload_to='favicon/', verbose_name='Фавиконка')

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Фавиконка сайта'

    class Meta:
        verbose_name = 'Фавиконка сайта'
        verbose_name_plural = 'Фавиконка сайта'


class PhoneNumber(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    number = models.CharField(
        max_length=20,
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
    icon = models.CharField(
        max_length=10,
        default='📷',
        blank=True,
        verbose_name='Иконка (эмодзи)',
    )
    icon_image = models.ImageField(
        upload_to='icons/',
        blank=True,
        null=True,
        verbose_name='Иконка (картинка)',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = 'Instagram'
        verbose_name_plural = 'Instagram'


class ProfileIcon(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    icon = models.CharField(
        max_length=10,
        default='👤',
        blank=True,
        verbose_name='Иконка (эмодзи)',
    )
    icon_image = models.ImageField(
        upload_to='icons/',
        blank=True,
        null=True,
        verbose_name='Иконка (картинка)',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Иконка профиля'

    class Meta:
        verbose_name = 'Иконка профиля'
        verbose_name_plural = 'Иконка профиля'


class CartIcon(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    icon = models.CharField(
        max_length=10,
        default='🛒',
        blank=True,
        verbose_name='Иконка (эмодзи)',
    )
    icon_image = models.ImageField(
        upload_to='icons/',
        blank=True,
        null=True,
        verbose_name='Иконка (картинка)',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Иконка корзины'

    class Meta:
        verbose_name = 'Иконка корзины'
        verbose_name_plural = 'Иконка корзины'


class TikTok(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    url = models.URLField(
        default='https://www.tiktok.com/',
        verbose_name='Ссылка на TikTok',
    )
    icon = models.CharField(
        max_length=10,
        default='🎵',
        blank=True,
        verbose_name='Иконка (эмодзи)',
    )
    icon_image = models.ImageField(
        upload_to='icons/',
        blank=True,
        null=True,
        verbose_name='Иконка (картинка)',
    )

    def save(self, *args, **kwargs):
        self.is_singleton = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = 'TikTok'
        verbose_name_plural = 'TikTok'


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


class Advantage(models.Model):
    icon = models.CharField(max_length=10, verbose_name='Иконка (эмодзи)')
    title = models.CharField(max_length=100, verbose_name='Заголовок')
    text = models.TextField(verbose_name='Описание')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Преимущество'
        verbose_name_plural = 'Преимущества'
        ordering = ['order', 'id']


class StaticPage(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=120, unique=True, verbose_name='Адрес (slug)')
    content = RichTextField(blank=True, verbose_name='Содержимое', config_name='default')
    is_published = models.BooleanField(default=True, verbose_name='Опубликована')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
        ordering = ['title']

    def __str__(self):
        return self.title


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
