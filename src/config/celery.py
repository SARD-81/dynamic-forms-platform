import os

from celery import Celery

from config.vercel_worker import DjangoThreadWorker

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

app = Celery("dynamic_forms_platform")
if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.vercel":
    app.WorkController = app.subclass_with_self(DjangoThreadWorker)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
