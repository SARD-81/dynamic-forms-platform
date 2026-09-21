import os

# Bootstrap values let base settings import even when a caller has no development .env.
os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "test-only-secret-key-not-for-development-or-production",
)
os.environ.setdefault("CELERY_BROKER_URL", "memory://")

from .base import *  # noqa: E402,F403,I001

# Test settings are deterministic even when development/CI container variables are present.
SECRET_KEY = "test-only-secret-key-not-for-development-or-production"
CELERY_BROKER_URL = "memory://"

DEBUG = False

ALLOWED_HOSTS = ["testserver"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
