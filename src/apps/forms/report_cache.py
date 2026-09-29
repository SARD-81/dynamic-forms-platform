import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

FORM_REPORT_CACHE_VERSION = "v2"
FORM_REPORT_CACHE_TIMEOUT_SECONDS = 5 * 60


def form_report_cache_key(
    *,
    form_public_id,
    submission_count,
    latest_submission_id,
):
    latest_submission_token = latest_submission_id or 0
    return (
        f"report:form:{form_public_id}:{FORM_REPORT_CACHE_VERSION}:"
        f"{submission_count}:{latest_submission_token}"
    )


def get_cached_form_report(
    *,
    form_public_id,
    submission_count,
    latest_submission_id,
):
    try:
        return cache.get(
            form_report_cache_key(
                form_public_id=form_public_id,
                submission_count=submission_count,
                latest_submission_id=latest_submission_id,
            )
        )
    except Exception:
        logger.warning("Form report cache read failed; falling back to database.", exc_info=True)
        return None


def set_cached_form_report(
    *,
    form_public_id,
    submission_count,
    latest_submission_id,
    payload,
):
    try:
        cache.set(
            form_report_cache_key(
                form_public_id=form_public_id,
                submission_count=submission_count,
                latest_submission_id=latest_submission_id,
            ),
            payload,
            timeout=FORM_REPORT_CACHE_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("Form report cache write failed; continuing without cache.", exc_info=True)


def invalidate_form_report_cache(
    *,
    form_public_id,
    submission_count,
    latest_submission_id,
):
    try:
        cache.delete(
            form_report_cache_key(
                form_public_id=form_public_id,
                submission_count=submission_count,
                latest_submission_id=latest_submission_id,
            )
        )
    except Exception:
        logger.warning(
            "Form report cache cleanup failed; revisioned reads remain safe.",
            exc_info=True,
        )
