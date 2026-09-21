from config.env import env_bool, env_list

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", required=True)
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    required=True,
)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=True,
)
