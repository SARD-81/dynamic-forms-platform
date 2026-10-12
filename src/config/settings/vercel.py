"""Vercel profile; Docker production keeps its existing Redis/Daphne topology."""

from config.env import env_value, required_env

from .production import *  # noqa: F403

# Vercel is the TLS-terminating ingress and owns this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

for platform_variable in ("VERCEL_URL", "VERCEL_BRANCH_URL"):
    platform_host = env_value(platform_variable)
    if platform_host and platform_host.endswith(".vercel.app") and "/" not in platform_host:
        ALLOWED_HOSTS.append(platform_host)  # noqa: F405
        CSRF_TRUSTED_ORIGINS.append(f"https://{platform_host}")  # noqa: F405

DATABASES["default"]["OPTIONS"]["sslmode"] = "require"  # noqa: F405
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True  # noqa: F405
# PgBouncer rejects statement_timeout as a startup parameter. The disposable
# readiness connection uses the direct endpoint while business traffic is pooled.
READINESS_DATABASE_HOST = required_env("POSTGRES_DIRECT_HOST")

STATIC_URL = "/static/"
# Native Django discovery resolves entrypoint paths from the repository root.
ASGI_APPLICATION = "vercel_app.application"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}

VERCEL_CRON_ENABLED = True
CRON_SECRET = required_env("CRON_SECRET")
CELERY_TASK_DEFAULT_QUEUE = "reports"
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"use_task_id_as_idempotency_key": True}
# Vercel Cron enqueues the existing due-report task instead of Celery Beat.
CELERY_BEAT_SCHEDULE = {}
