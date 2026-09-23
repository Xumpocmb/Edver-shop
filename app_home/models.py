from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_delete
from django.dispatch import receiver
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
    icon = models.CharField(
        max_length=10,
        default='📞',
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


class SiteEmail(models.Model):
    is_singleton = models.BooleanField(default=True, unique=True, editable=False)
    email = models.EmailField(
        verbose_name='Email',
    )
    icon = models.CharField(
        max_length=10,
        default='✉️',
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
        return self.email

    class Meta:
        verbose_name = 'Email'
        verbose_name_plural = 'Email'


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


class Slide(models.Model):
    LINK_TARGET_CHOICES = [
        ('catalog', 'Каталог (все товары)'),
        ('on_sale', 'Скидки и акции'),
        ('category', 'Категория каталога'),
        ('product', 'Товар'),
        ('page', 'Страница сайта'),
        ('custom', 'Своя ссылка'),
    ]

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='Подзаголовок')
    cta = models.CharField(max_length=100, default='Подробнее', verbose_name='Текст кнопки')
    link_target = models.CharField(
        max_length=20,
        choices=LINK_TARGET_CHOICES,
        default='catalog',
        verbose_name='Куда ведёт кнопка',
    )
    category = models.ForeignKey(
        'app_catalog.Category',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Категория',
        help_text='Для выбора «Категория каталога».',
    )
    product = models.ForeignKey(
        'app_catalog.Product',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Товар',
        help_text='Для выбора «Товар».',
    )
    page = models.ForeignKey(
        'StaticPage',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Страница',
        help_text='Для выбора «Страница сайта».',
    )
    href = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Своя ссылка',
        help_text='Например: /catalog/?gender=M. Заполняется для выбора «Своя ссылка».',
    )
    bg = models.CharField(
        max_length=50,
        default='var(--color-accent)',
        verbose_name='Цвет фона (CSS)',
    )
    image = models.ImageField(
        upload_to='slides/',
        blank=True,
        null=True,
        verbose_name='Фоновая картинка',
        help_text='Если загрузить, будет использоваться вместо цвета фона.',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    def get_url(self):
        if self.link_target == 'catalog':
            return '/catalog/'
        if self.link_target == 'on_sale':
            return '/catalog/?on_sale=1'
        if self.link_target == 'category':
            return self.category.get_absolute_url() if self.category else '/catalog/'
        if self.link_target == 'product':
            return self.product.get_absolute_url() if self.product else '/catalog/'
        if self.link_target == 'page':
            return f'/{self.page.slug}/' if self.page else '/catalog/'
        return self.href or '/catalog/'

    def save(self, *args, **kwargs):
        if self.pk:
            old = Slide.objects.filter(pk=self.pk).first()
            if old and old.image and old.image != self.image:
                old.image.delete(save=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Слайд'
        verbose_name_plural = 'Слайды'
        ordering = ['order', 'id']


@receiver(post_delete, sender=Slide)
def delete_slide_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


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
