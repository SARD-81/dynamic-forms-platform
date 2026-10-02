import logging
import os
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager

import pytest
from django.core.cache.backends.redis import RedisCache
from django.db.backends.postgresql.base import DatabaseWrapper

from apps.core import health
from apps.core.logging import SensitiveDataFilter, scrub_sensitive_text
from config.env import bounded_int_env


@contextmanager
def silent_tcp_peer():
    """Accept a TCP connection but never answer its protocol handshake."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    server.settimeout(0.1)
    stopped = threading.Event()

    def serve():
        while not stopped.is_set():
            try:
                peer, _ = server.accept()
            except TimeoutError:
                continue
            with peer:
                stopped.wait(8)
            break

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield server.getsockname()[1]
    finally:
        stopped.set()
        thread.join(timeout=1)
        server.close()


def test_liveness_never_calls_dependencies(client, monkeypatch):
    def unexpected():
        pytest.fail("Liveness coupled to backing services")

    monkeypatch.setattr(health, "check_database", unexpected)
    monkeypatch.setattr(health, "check_redis", unexpected)
    assert client.get("/health/live/").status_code == 200


def test_database_silent_handshake_is_bounded_and_secret_safe(
    client, monkeypatch, settings, caplog, django_db_blocker
):
    with silent_tcp_peer() as port:
        config = settings.DATABASES["default"].copy()
        config.update(HOST="127.0.0.1", PORT=str(port), PASSWORD="hidden-db-credential")
        config["OPTIONS"] = {"connect_timeout": 2}
        monkeypatch.setattr(health, "connection", DatabaseWrapper(config, alias="silent-peer"))
        monkeypatch.setattr(health, "check_redis", lambda: True)
        start = time.monotonic()
        with django_db_blocker.unblock():
            response = client.get("/health/ready/")
        assert 1 <= time.monotonic() - start < 5
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "hidden-db-credential" not in caplog.text + response.content.decode()
    assert "127.0.0.1" not in caplog.text + response.content.decode()


def test_cache_silent_socket_is_bounded_and_secret_safe(client, monkeypatch, caplog):
    with silent_tcp_peer() as port:
        backend = RedisCache(
            f"redis://:hidden-cache-credential@127.0.0.1:{port}/0",
            {
                "OPTIONS": {
                    "socket_connect_timeout": 1,
                    "socket_timeout": 1,
                    "retry_on_timeout": False,
                    "retry_on_error": [],
                }
            },
        )
        monkeypatch.setattr(health, "cache", backend)
        monkeypatch.setattr(health, "check_database", lambda: True)
        start = time.monotonic()
        response = client.get("/health/ready/")
        assert 0.5 <= time.monotonic() - start < 4
        backend.close()
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "hidden-cache-credential" not in caplog.text + response.content.decode()
    assert "127.0.0.1" not in caplog.text + response.content.decode()


def test_database_probe_closes_and_preserves_business_connection_options(monkeypatch, settings):
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql):
            assert sql == "SELECT 1;"

        def fetchone(self):
            return (1,)

    class Probe:
        def __init__(self):
            self.settings_dict = {"OPTIONS": {"connect_timeout": 2}}
            self.closed = False

        def cursor(self):
            assert "statement_timeout=" in self.settings_dict["OPTIONS"]["options"]
            return Cursor()

        def close(self):
            self.closed = True

    probe = Probe()

    class Connection:
        def copy(self, *, alias):
            assert alias == "readiness"
            return probe

    monkeypatch.setattr(health, "connection", Connection())
    assert health.check_database()
    assert probe.closed
    assert "options" not in settings.DATABASES["default"]["OPTIONS"]


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "1.5", "11", "", "secret"])
def test_timeout_configuration_rejects_invalid_values_without_echo(monkeypatch, value):
    from django.core.exceptions import ImproperlyConfigured

    monkeypatch.setenv("PROBE_TEST_TIMEOUT", value)
    with pytest.raises(ImproperlyConfigured) as error:
        bounded_int_env("PROBE_TEST_TIMEOUT", default=2, minimum=2, maximum=10)
    assert "PROBE_TEST_TIMEOUT" in str(error.value)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "Bearer",
        "api_key",
        "api-key",
        "otp",
        "SMTP_PASSWORD",
        "DJANGO_EMAIL_HOST_PASSWORD",
        "access_secret",
        "resume_token",
        "delivery_secret",
        "credentials",
        "refresh_token",
    ],
)
def test_secret_labels_are_redacted_in_formatted_records(key):
    message = "%s %s" if key == "Bearer" else "%s='%s'"
    record = logging.LogRecord(
        "apps.test",
        logging.ERROR,
        __file__,
        1,
        message,
        (key, "fake-sensitive-value"),
        None,
    )
    SensitiveDataFilter().filter(record)
    assert "fake-sensitive-value" not in logging.Formatter("%(message)s").format(record)


def test_url_credentials_query_tokens_and_multiline_secrets_are_redacted():
    value = (
        "postgresql://alice:uri-private@db:5432/app "
        "redis://:cache-private@redis/0 "
        "https://example.com/resume?resume_token=query-private&safe=yes "
        'password="first-private\nsecond-private" Authorization: Bearer a+/=private'
    )
    cleaned = scrub_sensitive_text(value)
    for secret in (
        "uri-private",
        "cache-private",
        "query-private",
        "first-private",
        "second-private",
        "a+/=private",
    ):
        assert secret not in cleaned
    assert "safe=yes" in cleaned


def test_exception_and_stack_are_safe_for_multiple_formatters():
    try:
        raise ValueError("resume_token=exception-private")
    except ValueError:
        record = logging.LogRecord(
            "apps.test",
            logging.ERROR,
            __file__,
            1,
            "failure password=%s",
            ("message-private",),
            sys.exc_info(),
        )
    record.stack_info = "access_secret=stack-private"
    SensitiveDataFilter().filter(record)
    for formatter in (
        logging.Formatter("%(message)s"),
        logging.Formatter("%(levelname)s %(message)s"),
    ):
        text = formatter.format(record)
        assert "ValueError" in text
        for secret in ("exception-private", "message-private", "stack-private"):
            assert secret not in text
    assert record.exc_info is None


def test_malformed_parameterized_record_has_safe_fallback():
    record = logging.LogRecord(
        "apps.test", logging.ERROR, __file__, 1, "password=%d", ("format-private",), None
    )
    SensitiveDataFilter().filter(record)
    assert "format-private" not in logging.Formatter().format(record)


def test_settings_map_timeout_environment_and_preserve_celery_logging():
    env = os.environ.copy()
    env.update(
        PYTHONPATH="src",
        DJANGO_SECRET_KEY="settings-test-placeholder",
        REDIS_CACHE_URL="redis://127.0.0.1:6379/0",
        CELERY_BROKER_URL="redis://127.0.0.1:6379/1",
        POSTGRES_CONNECT_TIMEOUT_SECONDS="3",
        READINESS_DB_QUERY_TIMEOUT_MS="800",
        REDIS_CONNECT_TIMEOUT_SECONDS="2",
        REDIS_SOCKET_TIMEOUT_SECONDS="3",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from config.settings import base as s; "
                "assert s.DATABASES['default']['OPTIONS']['connect_timeout'] == 3; "
                "assert s.READINESS_DATABASE_OPTIONS['options'] == '-c statement_timeout=800'; "
                "assert s.CACHES['default']['OPTIONS']['socket_connect_timeout'] == 2; "
                "assert s.CACHES['default']['OPTIONS']['socket_timeout'] == 3; "
                "assert s.CELERY_WORKER_HIJACK_ROOT_LOGGER is False"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
