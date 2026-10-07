import os
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


load_dotenv(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it to the .env file.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG") == "True"

if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', "edvershop.by", "0.0.0.0", "130.49.141.230"]

    # HTTPS: nginx должен передавать X-Forwarded-Proto,
    # иначе SECURE_SSL_REDIRECT уйдёт в редирект-петлю.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_summernote',

    "app_home.apps.AppHomeConfig",
    "app_catalog.apps.AppCatalogConfig",
    "app_user.apps.AppUserConfig",
    "app_cart.apps.AppCartConfig",
    "app_order.apps.AppOrderConfig",
    "app_media.apps.AppMediaConfig",

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '_settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.csrf',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app_home.context_processors.site_logo',
                'app_home.context_processors.site_favicon',
                'app_home.context_processors.phone',
                'app_home.context_processors.site_email',
                'app_home.context_processors.instagram',
                'app_home.context_processors.profile_icon',
                'app_home.context_processors.cart_icon',
                'app_home.context_processors.tiktok',
                'app_home.context_processors.footer_info',
                'app_home.context_processors.footer_pages',
                'app_home.context_processors.payment_page',
                'app_home.context_processors.cart_count',
                'app_home.context_processors.gender_categories',
                'app_home.context_processors.order_availability',
            ],
        },
    },
]

WSGI_APPLICATION = '_settings.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = '/profile/login/'
LOGIN_REDIRECT_URL = '/profile/'
LOGOUT_REDIRECT_URL = '/'


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
if DEBUG:
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]
else:
    STATIC_ROOT = BASE_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}

# Summernote (редактор в StaticPage).
# Тема lite: редактор живёт в iframe, поэтому Bootstrap из тем bs3/bs4/bs5 не нужен.
SUMMERNOTE_THEME = 'lite'

SUMMERNOTE_CONFIG = {
    'summernote': {
        # LANGUAGE_CODE = 'ru-ru' не совпадает с ключом в таблице локалей пакета,
        # без явного lang интерфейс редактора был бы на английском.
        'lang': 'ru-RU',
        'width': '100%',
        'height': 600,
        'placeholder': 'Текст страницы...',
        'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'italic', 'underline', 'strikethrough']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['insert', ['link', 'picture']],
            ['view', ['fullscreen']],
        ],
    },
    'attachment_filesize_limit': 10 * 1024 * 1024,
    # По умолчанию загружать файлы может любой посетитель сайта.
    'attachment_require_authentication': True,
}

# Django MPTT
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FIXTURE_DIRS = [BASE_DIR / 'fixtures']

# YML-фид товаров для Яндекс Маркета.
# SITE_URL нужен management-командам и фоновым задачам, где нет request.
FEED = {
    'site_url': os.getenv('SITE_URL', 'https://edvershop.by'),
    'shop_name': 'EDVER Shop',
    'company_name': 'EDVER Shop',
    'vendor_name': 'EDVER Shop',
    'currency': 'BYN',
    # Яндекс не принимает SVG, поэтому в фид попадают только эти форматы.
    'picture_extensions': {'.jpg', '.jpeg', '.png'},
}


# Celery
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

CELERY_BEAT_SCHEDULE = {
    'update-evropochta-branches-daily': {
        'task': 'app_cart.tasks.update_evropochta_branches',
        'schedule': crontab(hour=7, minute=0),
    },
}



# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")


# Logging
# Логи всего app_order пишутся в logs/app_order.log с ротацией по размеру:
# максимум 1 МБ на файл, хранится 5 файлов (app_order.log, app_order.log.1, ...).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'app_order_file': {
            'class': '_settings.logging.EnsureRotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'app_order.log',
            'maxBytes': 1_000_000,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'app_order': {
            'handlers': ['app_order_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

