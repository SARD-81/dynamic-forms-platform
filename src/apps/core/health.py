import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def check_database() -> bool:
    """
    Verifies PostgreSQL database connectivity with a lightweight bounded query.
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
    Verifies Redis connectivity with bounded connection and socket timeouts.
    Returns True if healthy, False otherwise without leaking credentials or URLs.
    """
    redis_url = getattr(settings, "REDIS_CACHE_URL", None)
    if not redis_url:
        cache_conf = settings.CACHES.get("default", {})
        if "redis" in cache_conf.get("BACKEND", "").lower():
            redis_url = cache_conf.get("LOCATION")

    if not redis_url:
        broker_url = getattr(settings, "CELERY_BROKER_URL", None)
        if broker_url and str(broker_url).startswith(("redis://", "rediss://")):
            redis_url = broker_url

    if not redis_url or not str(redis_url).startswith(("redis://", "rediss://")):
        return False

    client = None
    try:
        client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        return bool(client.ping())
    except Exception:
        logger.warning("Redis readiness check failed", exc_info=False)
        return False
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


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
