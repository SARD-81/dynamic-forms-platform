from pathlib import Path

from config.env import required_env

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = required_env("DJANGO_SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "apps.accounts.apps.AccountsConfig",
    "apps.core.apps.CoreConfig",
    "apps.forms.apps.FormsConfig",
    "apps.processes.apps.ProcessesConfig",
    "apps.reports.apps.ReportsConfig",
    "drf_spectacular",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": required_env("POSTGRES_HOST"),
        "PORT": required_env("POSTGRES_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"

DEFAULT_FROM_EMAIL = "no-reply@dynamic-forms.local"

ACCOUNT_OTP_LENGTH = 6
ACCOUNT_OTP_LIFETIME_SECONDS = 5 * 60
ACCOUNT_OTP_MAX_ATTEMPTS = 5
ACCOUNT_OTP_RESEND_COOLDOWN_SECONDS = 60
ACCOUNT_OTP_RATE_LIMIT_COUNT = 5
ACCOUNT_OTP_RATE_LIMIT_WINDOW_SECONDS = 15 * 60

CELERY_BROKER_URL = required_env("CELERY_BROKER_URL")
CELERY_TASK_IGNORE_RESULT = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Dynamic Forms Platform API",
    "DESCRIPTION": "API Foundation and documentation for Gate 3",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
