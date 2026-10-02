import logging
import uuid

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """
    Verifies PostgreSQL database connectivity with a lightweight query.
    PostgreSQL connection timeouts are governed by the settings contract (#78).
    Returns True if healthy, False otherwise without leaking internal details.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            return bool(row and row[0] == 1)
    except Exception:
        logger.warning("PostgreSQL readiness check failed", exc_info=False)
        return False


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


@require_GET
def health_live(request):
    """
    Liveness probe: verifies that the web process is running and responding.
    Intentionally decoupled from external dependencies like database or cache.
    """
    return JsonResponse({"status": "ok"}, status=200)


@require_GET
def health_ready(request):
    """
    Readiness probe: verifies that critical backing services (PostgreSQL, Redis)
    are reachable and responsive within bounded timeouts.
    """
    try:
        db_healthy = check_database()
        redis_healthy = check_redis()
        if db_healthy and redis_healthy:
            return JsonResponse({"status": "ok"}, status=200)
    except Exception:
        logger.exception("Unexpected error in readiness check")

    return JsonResponse({"status": "not_ready"}, status=503)
