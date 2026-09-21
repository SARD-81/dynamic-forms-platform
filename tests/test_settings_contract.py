from django.conf import settings


def test_pytest_uses_isolated_test_settings():
    assert settings.DEBUG is False
    assert settings.CELERY_BROKER_URL == "memory://"
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"
