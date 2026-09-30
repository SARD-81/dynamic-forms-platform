from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.core.cache import cache
from django.test import override_settings

from apps.core.participant_access import (
    PARTICIPANT_GRANTS_SESSION_KEY,
    ParticipantUnlockThrottleUnavailable,
    clear_participant_unlock_failures,
    grant_participant_access,
    has_participant_grant,
    participant_cache_key,
    reserve_participant_unlock_attempt,
    safe_cache_get,
    safe_cache_set,
)


@pytest.mark.django_db
def test_participant_grant_is_scoped_by_resource_type_and_public_id():
    session = SessionStore()
    shared_public_id = uuid4()

    grant_participant_access(
        session=session,
        resource_type="form",
        public_id=shared_public_id,
    )

    assert has_participant_grant(
        session=session,
        resource_type="form",
        public_id=shared_public_id,
    )
    assert not has_participant_grant(
        session=session,
        resource_type="process",
        public_id=shared_public_id,
    )
    assert not has_participant_grant(
        session=session,
        resource_type="form",
        public_id=uuid4(),
    )
    assert list(session[PARTICIPANT_GRANTS_SESSION_KEY].values()) == [True]


def test_participant_cache_key_is_resource_scoped_and_versioned():
    public_id = uuid4()

    form_key = participant_cache_key(resource_type="form", public_id=public_id)
    process_key = participant_cache_key(resource_type="process", public_id=public_id)

    assert form_key != process_key
    assert str(public_id) in form_key
    assert form_key.endswith(":v1")


def test_safe_cache_helpers_tolerate_backend_outage():
    with patch("apps.core.participant_access.cache.get", side_effect=RuntimeError("down")):
        assert safe_cache_get("missing") is None

    with patch("apps.core.participant_access.cache.set", side_effect=RuntimeError("down")):
        safe_cache_set("key", {"safe": True})


@pytest.mark.django_db
@override_settings(
    PARTICIPANT_UNLOCK_RATE_LIMIT_COUNT=3,
    PARTICIPANT_UNLOCK_RATE_LIMIT_WINDOW_SECONDS=900,
)
def test_unlock_rate_limit_is_resource_scoped_and_clears_after_success():
    cache.clear()
    session = SessionStore()
    public_id = uuid4()
    args = {
        "session": session,
        "resource_type": "form",
        "public_id": public_id,
        "client_id": "127.0.0.1",
    }

    assert not reserve_participant_unlock_attempt(**args)
    assert not reserve_participant_unlock_attempt(**args)
    assert not reserve_participant_unlock_attempt(**args)
    assert reserve_participant_unlock_attempt(**args)

    other_resource_args = {**args, "public_id": uuid4()}
    assert not reserve_participant_unlock_attempt(**other_resource_args)

    clear_participant_unlock_failures(**args)
    assert not reserve_participant_unlock_attempt(**args)


@pytest.mark.django_db
def test_unlock_rate_limit_fails_closed_when_shared_cache_read_is_down():
    session = SessionStore()
    args = {
        "session": session,
        "resource_type": "process",
        "public_id": uuid4(),
        "client_id": "127.0.0.1",
    }

    with patch("apps.core.participant_access.cache.get", side_effect=RuntimeError("down")):
        with pytest.raises(ParticipantUnlockThrottleUnavailable):
            reserve_participant_unlock_attempt(**args)


@pytest.mark.django_db
def test_unlock_rate_limit_fails_closed_when_shared_cache_write_is_down():
    session = SessionStore()
    args = {
        "session": session,
        "resource_type": "form",
        "public_id": uuid4(),
        "client_id": "127.0.0.1",
    }

    with (
        patch("apps.core.participant_access.cache.get", return_value=None),
        patch("apps.core.participant_access.cache.add", side_effect=RuntimeError("down")),
    ):
        with pytest.raises(ParticipantUnlockThrottleUnavailable):
            reserve_participant_unlock_attempt(**args)
