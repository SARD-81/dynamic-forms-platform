from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from config.cache import AtomicDatabaseCache


@pytest.fixture
def shared_cache(transactional_db):
    call_command("createcachetable", "test_atomic_cache", verbosity=0)
    backend = AtomicDatabaseCache("test_atomic_cache", {})
    backend.clear()
    yield backend
    backend.clear()


def test_parallel_increments_preserve_count_and_original_expiry(shared_cache):
    shared_cache.add("counter", 0, timeout=60)
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT expires FROM test_atomic_cache")
        before = cursor.fetchone()[0]

    def increment(_):
        try:
            return shared_cache.incr("counter")
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as workers:
        assert sorted(workers.map(increment, range(24))) == list(range(1, 25))
    assert shared_cache.get("counter") == 24
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT expires FROM test_atomic_cache")
        assert cursor.fetchone()[0] == before


def test_parallel_add_has_one_winner_for_expired_key(shared_cache):
    shared_cache.set("counter", 100, timeout=60)
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "UPDATE test_atomic_cache SET expires = %s", [timezone.now() - timedelta(seconds=1)]
        )

    def add(_):
        try:
            return shared_cache.add("counter", 1, timeout=60)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as workers:
        assert list(workers.map(add, range(16))).count(True) == 1
    assert shared_cache.get("counter") == 1


def test_incr_rejects_expired_and_missing_keys(shared_cache):
    with pytest.raises(ValueError):
        shared_cache.incr("missing")
    shared_cache.set("expired", 1, timeout=60)
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "UPDATE test_atomic_cache SET expires = %s", [timezone.now() - timedelta(seconds=1)]
        )
    with pytest.raises(ValueError):
        shared_cache.incr("expired")


def test_cache_pressure_does_not_evict_active_throttle(shared_cache):
    shared_cache._max_entries = 1
    shared_cache.add("throttle", 5, timeout=900)
    for number in range(4):
        shared_cache.set(f"read-model-{number}", number, timeout=300)
    assert shared_cache.get("throttle") == 5
