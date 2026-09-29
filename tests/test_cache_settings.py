from django.conf import settings


def test_test_settings_use_deterministic_local_memory_cache():
    cache_settings = settings.CACHES["default"]

    assert cache_settings["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache"
