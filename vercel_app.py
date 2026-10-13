"""Explicit entrypoint for the repository's src layout."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.vercel")

from config.asgi import application  # noqa: E402,F401
from vercel.integrations.celery import install_vercel_celery_integration  # noqa: E402

# Register after Django is initialized, so management command discovery and
# collectstatic do not recursively initialize the queue adapter through settings.
install_vercel_celery_integration(
    set_default_broker=False,
    set_default_result_backend=False,
)
