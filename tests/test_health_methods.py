from unittest.mock import Mock

import pytest
from django.test import Client


def test_liveness_get_and_head_ignore_dependencies(client, monkeypatch):
    database = Mock(side_effect=AssertionError("Liveness queried the database"))
    cache = Mock(side_effect=AssertionError("Liveness queried the cache"))
    monkeypatch.setattr("apps.core.health.check_database", database)
    monkeypatch.setattr("apps.core.health.check_redis", cache)

    get = client.get("/health/live/")
    head = client.head("/health/live/")
    assert get.status_code == head.status_code == 200
    assert get.json() == {"status": "ok"}
    assert head.content == b""
    assert head["Content-Type"] == get["Content-Type"] == "application/json"
    database.assert_not_called()
    cache.assert_not_called()


@pytest.mark.parametrize(
    ("database_ok", "cache_ok", "status"),
    [(True, True, 200), (False, True, 503), (True, False, 503)],
)
def test_readiness_head_matches_get(client, monkeypatch, database_ok, cache_ok, status):
    monkeypatch.setattr("apps.core.health.check_database", lambda: database_ok)
    monkeypatch.setattr("apps.core.health.check_redis", lambda: cache_ok)

    get = client.get("/health/ready/")
    head = client.head("/health/ready/")
    assert get.status_code == head.status_code == status
    assert head.content == b""
    assert head["Content-Type"] == get["Content-Type"] == "application/json"


@pytest.mark.parametrize("path", ["/health/live/", "/health/ready/"])
@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_health_rejects_unsafe_methods_without_probing(monkeypatch, path, method):
    client = Client(enforce_csrf_checks=True)
    database = Mock()
    cache = Mock()
    monkeypatch.setattr("apps.core.health.check_database", database)
    monkeypatch.setattr("apps.core.health.check_redis", cache)

    response = getattr(client, method)(path)
    assert response.status_code == 405
    assert set(response["Allow"].split(", ")) == {"GET", "HEAD"}
    database.assert_not_called()
    cache.assert_not_called()
