from config.env import env_bool, env_list, required_env, required_positive_int_env

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

STATIC_ROOT = BASE_DIR.parent / "staticfiles"  # noqa: F405
# Opt in only behind Nginx, which overwrites this header and is the sole ingress.
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if env_bool("DJANGO_TRUST_NGINX_PROXY", default=False)
    else None
)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = required_env("DJANGO_EMAIL_HOST")
EMAIL_PORT = required_positive_int_env("DJANGO_EMAIL_PORT")
EMAIL_HOST_USER = required_env("DJANGO_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = required_env("DJANGO_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = required_positive_int_env("DJANGO_EMAIL_TIMEOUT")
DEFAULT_FROM_EMAIL = required_env("DJANGO_DEFAULT_FROM_EMAIL")
