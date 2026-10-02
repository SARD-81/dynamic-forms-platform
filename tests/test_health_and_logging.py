import importlib
import logging
import sys

import pytest
from django.urls import reverse

from apps.core.health import check_database, check_redis
from apps.core.logging import SensitiveDataFilter, scrub_sensitive_text


def test_health_live_endpoint_returns_200(client):
    response = client.get(reverse("health_live"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response["Content-Type"] == "application/json"


def test_health_ready_endpoint_success_when_dependencies_healthy(client, monkeypatch):
    monkeypatch.setattr("apps.core.health.check_database", lambda: True)
    monkeypatch.setattr("apps.core.health.check_redis", lambda: True)

    response = client.get(reverse("health_ready"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_endpoint_fails_when_postgres_unhealthy(client, monkeypatch):
    monkeypatch.setattr("apps.core.health.check_database", lambda: False)
    monkeypatch.setattr("apps.core.health.check_redis", lambda: True)

    response = client.get(reverse("health_ready"))
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_health_ready_endpoint_fails_when_redis_unhealthy(client, monkeypatch):
    monkeypatch.setattr("apps.core.health.check_database", lambda: True)
    monkeypatch.setattr("apps.core.health.check_redis", lambda: False)

    response = client.get(reverse("health_ready"))
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_health_ready_does_not_leak_sensitive_information(client, monkeypatch):
    def failing_db():
        raise RuntimeError(
            "Internal secret database password postgres://user:secretpass@10.0.0.5:5432"
        )

    monkeypatch.setattr("apps.core.health.check_database", failing_db)
    monkeypatch.setattr("apps.core.health.check_redis", lambda: True)

    response = client.get(reverse("health_ready"))
    assert response.status_code == 503
    body = response.content.decode("utf-8")
    assert body == '{"status": "not_ready"}'
    assert "secretpass" not in body
    assert "postgres" not in body
    assert "10.0.0.5" not in body


@pytest.mark.django_db
def test_check_database_unit_healthy():
    assert check_database() is True


def test_check_database_unit_failure(monkeypatch):
    class FailingCursor:
        def __enter__(self):
            raise RuntimeError("Database connection dropped")

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    class FailingConnection:
        def cursor(self):
            return FailingCursor()

    monkeypatch.setattr("apps.core.health.connection", FailingConnection())
    assert check_database() is False


def test_check_redis_unit_healthy():
    assert check_redis() is True


def test_check_redis_unit_failure(monkeypatch):
    class FailingCache:
        def set(self, *args, **kwargs):
            raise ConnectionError("Redis cache unavailable")

    monkeypatch.setattr("apps.core.health.cache", FailingCache())
    assert check_redis() is False


def test_sensitive_data_filter_redacts_credentials():
    log_filter = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User login failed with password=super_secret_password and token=tok_abc123456",
        args=(),
        exc_info=None,
    )
    assert log_filter.filter(record) is True
    assert "super_secret_password" not in record.msg
    assert "tok_abc123456" not in record.msg
    assert "[REDACTED]" in record.msg


def test_sensitive_data_filter_redacts_parameterized_logging():
    log_filter = SensitiveDataFilter()
    secret_value = "super_secret_cleartext_password"
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=12,
        msg="Login attempt with password=%s and token=%s",
        args=(secret_value, "Bearer secret_api_token_123"),
        exc_info=None,
    )
    assert log_filter.filter(record) is True
    assert secret_value not in record.msg
    assert "secret_api_token_123" not in record.msg
    assert record.args == ()
    assert "[REDACTED]" in record.msg


def test_sensitive_data_filter_redacts_exception_traceback():
    log_filter = SensitiveDataFilter()
    try:
        raise ValueError("Failed connecting to redis://user:hidden_auth_pwd@redis:6379/0")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=20,
        msg="Unexpected error occurred",
        args=(),
        exc_info=exc_info,
    )
    assert log_filter.filter(record) is True
    assert "hidden_auth_pwd" not in record.exc_text
    assert "[REDACTED]" in record.exc_text


def test_sensitive_data_scrubbing_functions():
    sample_text = "Bearer eyJhbGciOiJIUzI1Ni.secret redis://user:secret123@redis:6379/0 otp: 654321"
    cleaned = scrub_sensitive_text(sample_text)
    assert "secret123" not in cleaned
    assert "654321" not in cleaned
    assert "Bearer [REDACTED]" in cleaned


def test_logging_configuration_imports_cleanly(monkeypatch):
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost")
    monkeypatch.setenv("DJANGO_EMAIL_HOST", "smtp.example.com")
    monkeypatch.setenv("DJANGO_EMAIL_PORT", "587")
    monkeypatch.setenv("DJANGO_EMAIL_HOST_USER", "user")
    monkeypatch.setenv("DJANGO_EMAIL_HOST_PASSWORD", "pass")
    monkeypatch.setenv("DJANGO_EMAIL_TIMEOUT", "10")
    monkeypatch.setenv("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@example.com")

    for settings_module in [
        "config.settings.development",
        "config.settings.test",
        "config.settings.production",
    ]:
        mod = importlib.import_module(settings_module)
        assert hasattr(mod, "LOGGING")
        assert "sensitive_data_filter" in mod.LOGGING["filters"]
