"""Explicit entrypoint for the repository's src layout."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.vercel")

from config.asgi import application  # noqa: E402,F401
