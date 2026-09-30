import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

PROCESS_REPORT_CACHE_VERSION = "v1"
PROCESS_REPORT_CACHE_TIMEOUT_SECONDS = 5 * 60


def _completion_token(value):
    if value is None:
        return 0
    return int(value.timestamp() * 1_000_000)


def process_report_cache_key(
    *,
    process_public_id,
    run_count,
    latest_run_id,
    completed_run_count,
    completed_step_count,
    latest_step_completed_at,
):
    return (
        f"report:process:{process_public_id}:{PROCESS_REPORT_CACHE_VERSION}:"
        f"{run_count}:{latest_run_id or 0}:{completed_run_count}:"
        f"{completed_step_count}:{_completion_token(latest_step_completed_at)}"
    )


def get_cached_process_report(**revision):
    try:
        return cache.get(process_report_cache_key(**revision))
    except Exception:
        logger.warning("Process report cache read failed; falling back to database.", exc_info=True)
        return None


def set_cached_process_report(*, payload, **revision):
    try:
        cache.set(
            process_report_cache_key(**revision),
            payload,
            timeout=PROCESS_REPORT_CACHE_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("Process report cache write failed; continuing without cache.", exc_info=True)
