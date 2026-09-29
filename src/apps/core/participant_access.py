import hashlib
import logging
import time

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache

logger = logging.getLogger(__name__)

PARTICIPANT_GRANTS_SESSION_KEY = "participant_access_grants"
PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY = "participant_unlock_failures"
PARTICIPANT_CACHE_TIMEOUT_SECONDS = 5 * 60
PARTICIPANT_CACHE_VERSION = "v1"
PARTICIPANT_UNLOCK_RATE_LIMIT_VERSION = "v1"


class ParticipantUnlockThrottleUnavailable(Exception):
    """Raised when shared unlock throttling cannot be enforced safely."""


def participant_grant_key(*, resource_type, public_id):
    return f"{resource_type}:{public_id}"


def has_participant_grant(*, session, resource_type, public_id):
    grants = session.get(PARTICIPANT_GRANTS_SESSION_KEY, {})
    return (
        grants.get(participant_grant_key(resource_type=resource_type, public_id=public_id)) is True
    )


def grant_participant_access(*, session, resource_type, public_id):
    grants = dict(session.get(PARTICIPANT_GRANTS_SESSION_KEY, {}))
    grants[participant_grant_key(resource_type=resource_type, public_id=public_id)] = True
    session[PARTICIPANT_GRANTS_SESSION_KEY] = grants
    session.modified = True


def verify_participant_password(*, password_hash, password):
    if not password_hash or not password:
        return False
    return check_password(password, password_hash)


def participant_cache_key(*, resource_type, public_id):
    return f"participant:{resource_type}:{public_id}:{PARTICIPANT_CACHE_VERSION}"


def safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        logger.warning("Participant cache read failed; falling back to database.", exc_info=True)
        return None


def safe_cache_set(key, value):
    try:
        cache.set(key, value, timeout=PARTICIPANT_CACHE_TIMEOUT_SECONDS)
    except Exception:
        logger.warning("Participant cache write failed; continuing without cache.", exc_info=True)


def invalidate_participant_read_model(*, resource_type, public_id):
    key = participant_cache_key(resource_type=resource_type, public_id=public_id)
    try:
        cache.delete(key)
    except Exception:
        logger.warning("Participant cache invalidation failed; continuing safely.", exc_info=True)


def participant_client_id(request):
    return request.META.get("REMOTE_ADDR") or "unknown"


def participant_unlock_retry_after_seconds():
    return int(getattr(settings, "PARTICIPANT_UNLOCK_RATE_LIMIT_WINDOW_SECONDS", 15 * 60))


def _participant_unlock_limit_count():
    return int(getattr(settings, "PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT", 5))


def participant_unlock_rate_limit_key(*, resource_type, public_id, client_id):
    client_digest = hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:24]
    return (
        f"participant-unlock:{resource_type}:{public_id}:{client_digest}:"
        f"{PARTICIPANT_UNLOCK_RATE_LIMIT_VERSION}"
    )


def _unlock_failure_session_key(*, resource_type, public_id):
    return participant_grant_key(resource_type=resource_type, public_id=public_id)


def _session_failure_count(*, session, resource_type, public_id, now=None):
    now = time.time() if now is None else now
    failures = dict(session.get(PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY, {}))
    key = _unlock_failure_session_key(resource_type=resource_type, public_id=public_id)
    record = failures.get(key)

    if not record:
        return 0

    started_at = float(record.get("started_at", 0))
    if now - started_at >= participant_unlock_retry_after_seconds():
        failures.pop(key, None)
        session[PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY] = failures
        session.modified = True
        return 0

    return int(record.get("count", 0))


def _record_session_unlock_attempt(*, session, resource_type, public_id):
    now = time.time()
    failures = dict(session.get(PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY, {}))
    key = _unlock_failure_session_key(resource_type=resource_type, public_id=public_id)
    existing_count = _session_failure_count(
        session=session,
        resource_type=resource_type,
        public_id=public_id,
        now=now,
    )
    current = failures.get(key, {})
    started_at = float(current.get("started_at", now))
    if existing_count == 0:
        started_at = now

    failures = dict(session.get(PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY, {}))
    failures[key] = {
        "count": existing_count + 1,
        "started_at": started_at,
    }
    session[PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY] = failures
    session.modified = True


def reserve_participant_unlock_attempt(
    *,
    session,
    resource_type,
    public_id,
    client_id,
):
    """Reserve one shared attempt before password hashing.

    Redis-backed shared state is authoritative for cross-session throttling.
    If that shared state cannot be read or updated, callers must fail closed
    and must not continue to password verification.
    """

    limit = _participant_unlock_limit_count()
    session_count = _session_failure_count(
        session=session,
        resource_type=resource_type,
        public_id=public_id,
    )
    if session_count >= limit:
        return True

    key = participant_unlock_rate_limit_key(
        resource_type=resource_type,
        public_id=public_id,
        client_id=client_id,
    )

    try:
        current = cache.get(key)
        if current is not None and int(current) >= limit:
            return True

        if current is None:
            added = cache.add(
                key,
                1,
                timeout=participant_unlock_retry_after_seconds(),
            )
            if added:
                shared_count = 1
            else:
                shared_count = int(cache.incr(key))
        else:
            shared_count = int(cache.incr(key))
    except Exception as exc:
        logger.warning(
            "Participant unlock shared throttle is unavailable; failing closed.",
            exc_info=True,
        )
        raise ParticipantUnlockThrottleUnavailable from exc

    if shared_count > limit:
        return True

    _record_session_unlock_attempt(
        session=session,
        resource_type=resource_type,
        public_id=public_id,
    )
    return False


def clear_participant_unlock_failures(
    *,
    session,
    resource_type,
    public_id,
    client_id,
):
    cache_key = participant_unlock_rate_limit_key(
        resource_type=resource_type,
        public_id=public_id,
        client_id=client_id,
    )
    try:
        cache.delete(cache_key)
    except Exception as exc:
        logger.warning(
            "Participant unlock shared throttle could not be cleared; failing closed.",
            exc_info=True,
        )
        raise ParticipantUnlockThrottleUnavailable from exc

    failures = dict(session.get(PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY, {}))
    session_key = _unlock_failure_session_key(
        resource_type=resource_type,
        public_id=public_id,
    )
    if session_key in failures:
        failures.pop(session_key, None)
        session[PARTICIPANT_UNLOCK_FAILURES_SESSION_KEY] = failures
        session.modified = True
