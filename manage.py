"""Root Django entrypoint for Vercel's framework discovery."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.vercel")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
