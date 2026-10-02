from django.conf import settings

from config.settings import base


def test_pytest_uses_isolated_test_settings():
    assert settings.DEBUG is False
    assert settings.CELERY_BROKER_URL == "memory://"
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"


def test_production_redis_cache_has_bounded_connect_and_read_timeouts():
    cache_settings = base.CACHES["default"]

    assert cache_settings["BACKEND"] == "django.core.cache.backends.redis.RedisCache"
    assert cache_settings["OPTIONS"]["socket_connect_timeout"] == 1
    assert cache_settings["OPTIONS"]["socket_timeout"] == 1
