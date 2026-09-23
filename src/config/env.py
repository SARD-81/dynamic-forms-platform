import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Local convenience only. Existing shell/container environment variables win.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def required_env(name: str) -> str:
    value = os.getenv(name)

    if value is None or not value.strip():
        raise ImproperlyConfigured(f"Required environment variable {name!r} is missing or empty.")

    return value


def env_list(name: str, *, required: bool = False) -> list[str]:
    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        if required:
            raise ImproperlyConfigured(
                f"Required environment variable {name!r} is missing or empty."
            )
        return []

    return [item.strip() for item in raw_value.split(",") if item.strip()]


def env_bool(name: str, *, default: bool = False) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ImproperlyConfigured(f"Environment variable {name!r} must be a boolean value.")


def required_positive_int_env(name: str) -> int:
    raw_value = required_env(name)

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"Environment variable {name!r} must be a positive integer."
        ) from exc

    if value <= 0:
        raise ImproperlyConfigured(
            f"Environment variable {name!r} must be a positive integer."
        )

    return value
