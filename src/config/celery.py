import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

app = Celery("dynamic_forms_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
if app.conf.broker_url.startswith("vercel"):
    from vercel.integrations.celery import install_vercel_celery_integration

    install_vercel_celery_integration(
        set_default_broker=False,
        set_default_result_backend=False,
    )
app.autodiscover_tasks()
