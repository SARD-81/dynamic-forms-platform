import os

# Bootstrap values let base settings import even when a caller has no development .env.
os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "test-only-secret-key-not-for-development-or-production",
)
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("REDIS_CACHE_URL", "redis://127.0.0.1:6379/0")

from .base import *  # noqa: E402,F403,I001

# Test settings are deterministic even when development/CI container variables are present.
SECRET_KEY = "test-only-secret-key-not-for-development-or-production"
CELERY_BROKER_URL = "memory://"

DEBUG = False

ALLOWED_HOSTS = ["testserver"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "dynamic-forms-tests",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
