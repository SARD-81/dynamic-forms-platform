import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

FORM_REPORT_CACHE_VERSION = "v1"
FORM_REPORT_CACHE_TIMEOUT_SECONDS = 5 * 60


def form_report_cache_key(*, form_public_id):
    return f"report:form:{form_public_id}:{FORM_REPORT_CACHE_VERSION}"


def get_cached_form_report(*, form_public_id):
    try:
        return cache.get(form_report_cache_key(form_public_id=form_public_id))
    except Exception:
        logger.warning("Form report cache read failed; falling back to database.", exc_info=True)
        return None


def set_cached_form_report(*, form_public_id, payload):
    try:
        cache.set(
            form_report_cache_key(form_public_id=form_public_id),
            payload,
            timeout=FORM_REPORT_CACHE_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("Form report cache write failed; continuing without cache.", exc_info=True)


def invalidate_form_report_cache(*, form_public_id):
    try:
        cache.delete(form_report_cache_key(form_public_id=form_public_id))
    except Exception:
        logger.warning("Form report cache invalidation failed; continuing safely.", exc_info=True)
