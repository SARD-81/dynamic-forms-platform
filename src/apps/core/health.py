import logging
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """
    Verifies PostgreSQL database connectivity with a lightweight query.
    Uses settings-owned timeouts and a disposable connection, so probe-only
    statement/TCP bounds never mutate a business transaction's session.
    Returns True if healthy, False otherwise without leaking internal details.
    """
    probe = None
    try:
        probe = connection.copy(alias="readiness")
        options = probe.settings_dict.get("OPTIONS", {}).copy()
        existing_options = options.get("options", "")
        options.update(settings.READINESS_DATABASE_OPTIONS)
        options["options"] = f"{existing_options} {options['options']}".strip()
        probe.settings_dict["OPTIONS"] = options
        with probe.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            return bool(row and row[0] == 1)
    except Exception:
        logger.warning("PostgreSQL readiness check failed", exc_info=False)
        return False
    finally:
        if probe is not None:
            probe.close()


def check_redis() -> bool:
    """
    Verifies Redis connectivity via Django Cache abstraction.
    Performs a lightweight, non-destructive probe (set, get, delete)
    using an isolated unique key per check to prevent collisions during concurrent probes.
    """
    probe_token = uuid.uuid4().hex
    probe_key = f"health:ready:probe:{probe_token}"
    try:
        cache.set(probe_key, probe_token, timeout=5)
        val = cache.get(probe_key)
        cache.delete(probe_key)
        return val == probe_token
    except Exception:
        logger.warning("Redis readiness check failed", exc_info=False)
        return False


@csrf_exempt  # Unsafe methods are rejected before any probe, even without a CSRF cookie.
@require_safe
def health_live(request):
    """
    Liveness probe: verifies that the web process is running and responding.
    Intentionally decoupled from external dependencies like database or cache.
    """
    return JsonResponse({"status": "ok"}, status=200)


@csrf_exempt
@require_safe
def health_ready(request):
    """
    Readiness probe: verifies that critical backing services (PostgreSQL, Redis)
    are reachable and responsive within bounded timeouts.
    """
    try:
        if check_database() and check_redis():
            return JsonResponse({"status": "ok"}, status=200)
    except Exception:
        logger.warning("Unexpected error in readiness check", exc_info=False)

    return JsonResponse({"status": "not_ready"}, status=503)
