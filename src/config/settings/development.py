from config.env import env_list

from .base import *  # noqa: F403


DEBUG = True

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", required=True)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
