from pathlib import Path

from celery.schedules import crontab

from config.env import bounded_int_env, required_env

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

POSTGRES_CONNECT_TIMEOUT_SECONDS = bounded_int_env(
    "POSTGRES_CONNECT_TIMEOUT_SECONDS", default=2, minimum=2, maximum=10
)
READINESS_DB_QUERY_TIMEOUT_MS = bounded_int_env(
    "READINESS_DB_QUERY_TIMEOUT_MS", default=1000, minimum=100, maximum=5000
)
# A probe-only connection bounds queries and dead TCP peers without imposing a
# statement timeout on business transactions. libpq's connect_timeout is per host.
READINESS_DATABASE_OPTIONS = {
    "options": f"-c statement_timeout={READINESS_DB_QUERY_TIMEOUT_MS}",
    "keepalives": 1,
    "keepalives_idle": 1,
    "keepalives_interval": 1,
    "keepalives_count": 2,
    "tcp_user_timeout": 2000,
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_env("POSTGRES_DB"),
        "USER": required_env("POSTGRES_USER"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": required_env("POSTGRES_HOST"),
        "PORT": required_env("POSTGRES_PORT"),
        "OPTIONS": {"connect_timeout": POSTGRES_CONNECT_TIMEOUT_SECONDS},
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

PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT = 5
PARTICIPANT_UNLOCK_RATE_LIMIT_WINDOW_SECONDS = 15 * 60

REDIS_CACHE_URL = required_env("REDIS_CACHE_URL")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "OPTIONS": {
            "socket_connect_timeout": bounded_int_env(
                "REDIS_CONNECT_TIMEOUT_SECONDS", default=1, minimum=1, maximum=5
            ),
            "socket_timeout": bounded_int_env(
                "REDIS_SOCKET_TIMEOUT_SECONDS", default=1, minimum=1, maximum=5
            ),
            "retry_on_timeout": False,
            "retry_on_error": [],
        },
    }
}

CELERY_BROKER_URL = required_env("CELERY_BROKER_URL")
CELERY_TASK_IGNORE_RESULT = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_REDIRECT_STDOUTS = False
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-periodic-reports-hourly": {
        "task": "apps.reports.tasks.dispatch_due_report_subscriptions",
        "schedule": crontab(minute=0),
    },
}

REPORT_API_DELIVERY_TIMEOUT_SECONDS = 10
REPORT_DELIVERY_MAX_RETRIES = 2
REPORT_DELIVERY_RETRY_DELAY_SECONDS = 30
REPORT_DELIVERY_RETRY_MAX_DELAY_SECONDS = 5 * 60

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Dynamic Forms Platform API",
    "DESCRIPTION": "API Foundation and documentation for Gate 3",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sensitive_data_filter": {
            "()": "apps.core.logging.SensitiveDataFilter",
        },
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["sensitive_data_filter"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "daphne": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "multiprocessing": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
