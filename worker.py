"""Private Vercel Queue subscriber with registered Django report tasks."""

import vercel_app  # noqa: F401
from config.celery import app

app.autodiscover_tasks(force=True)

__all__ = ["app"]
