from io import StringIO
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.management.commands import production_preflight


@pytest.fixture
def healthy(settings, monkeypatch):
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ["example.test"]
    settings.STATIC_URL = "/static/"
    settings.STATIC_ROOT = "/unused-preflight-static"
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.test"

    database = MagicMock()
    database.is_usable.return_value = True

    values = {}
    cache = MagicMock()

    def set_value(key, value, timeout):
        values[key] = value

    cache.set.side_effect = set_value
    cache.get.side_effect = lambda key: values.get(key)
    cache.delete.side_effect = lambda key: values.pop(key, None)

    monkeypatch.setattr(
        production_preflight,
        "connections",
        {"default": database},
    )
    monkeypatch.setattr(
        production_preflight,
        "caches",
        {"default": cache},
    )

    monkeypatch.setattr(
        production_preflight,
        "import_string",
        MagicMock(return_value=MagicMock()),
    )

    return database, cache, values


def test_success(healthy):
    output = StringIO()

    call_command("production_preflight", stdout=output)

    assert "FAIL" not in output.getvalue()
    assert "Production preflight passed." in output.getvalue()


@pytest.mark.parametrize(
    ("name", "value", "check"),
    [
        ("DEBUG", True, "debug"),
        ("ALLOWED_HOSTS", [], "hosts"),
        ("ALLOWED_HOSTS", ["   "], "hosts"),
        ("STATIC_URL", None, "static"),
        ("STATIC_ROOT", None, "static"),
    ],
)
def test_invalid_settings(healthy, settings, name, value, check):
    setattr(settings, name, value)
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    assert f"FAIL {check}" in output.getvalue()


@pytest.mark.parametrize("component", ["database", "cache"])
def test_backend_failure_is_secret_safe(healthy, component):
    database, cache, _ = healthy
    secret = "private-backend-password"
    output = StringIO()

    if component == "database":
        database.ensure_connection.side_effect = RuntimeError(secret)
    else:
        cache.get.side_effect = RuntimeError(secret)

    with pytest.raises(CommandError) as error:
        call_command("production_preflight", stdout=output)

    assert f"FAIL {component}" in output.getvalue()
    assert secret not in output.getvalue()
    assert secret not in str(error.value)

    if component == "cache":
        cache.delete.assert_called_once()


def test_unusable_database_fails(healthy):
    database, _, _ = healthy
    database.is_usable.return_value = False

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=StringIO())


def test_cache_probe_is_cleaned_up(healthy):
    _, cache, values = healthy

    call_command("production_preflight", stdout=StringIO())

    key = cache.set.call_args.args[0]

    assert key.startswith("production_preflight:")
    assert cache.set.call_args.kwargs["timeout"] == 30
    cache.delete.assert_called_once_with(key)
    assert values == {}


def test_cache_wrong_value_fails_and_cleans_up(healthy):
    _, cache, values = healthy
    cache.get.side_effect = None
    cache.get.return_value = "wrong-value"

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=StringIO())

    cache.delete.assert_called_once()
    assert values == {}


def test_configured_secrets_are_not_printed(healthy, settings):
    secrets = {
        "SECRET_KEY": "private-django-secret",
        "EMAIL_HOST_USER": "private-smtp-user",
        "EMAIL_HOST_PASSWORD": "private-smtp-password",
        "CELERY_BROKER_URL": "redis://user:private-password@host/1",
    }

    for name, value in secrets.items():
        setattr(settings, name, value)

    output = StringIO()
    call_command("production_preflight", stdout=output)

    for value in secrets.values():
        assert value not in output.getvalue()


def test_no_unexpected_database_access(healthy):
    # Without django_db, pytest-django blocks real database access.
    call_command("production_preflight", stdout=StringIO())


def test_runtime_import_failure_is_secret_safe(healthy, monkeypatch):
    output = StringIO()
    importer = MagicMock(side_effect=RuntimeError("private-runtime-secret"))
    monkeypatch.setattr(production_preflight, "import_string", importer)

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    assert "FAIL runtime" in output.getvalue()
    assert "private-runtime-secret" not in output.getvalue()


def test_runtime_application_must_be_callable(healthy, monkeypatch):
    monkeypatch.setattr(
        production_preflight,
        "import_string",
        MagicMock(return_value=object()),
    )
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    assert "FAIL runtime" in output.getvalue()


def test_cache_set_failure_attempts_cleanup(healthy):
    _, cache, _ = healthy
    cache.set.side_effect = RuntimeError("private-cache-secret")
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    cache.delete.assert_called_once()
    assert "FAIL cache" in output.getvalue()
    assert "private-cache-secret" not in output.getvalue()


def test_cache_cleanup_failure_is_secret_safe(healthy):
    _, cache, _ = healthy
    cache.delete.side_effect = RuntimeError("private-cleanup-secret")
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    assert "FAIL cache" in output.getvalue()
    assert "private-cleanup-secret" not in output.getvalue()


def test_email_backend_failure_is_secret_safe(healthy, monkeypatch):
    backend = MagicMock(side_effect=RuntimeError("private-email-secret"))
    monkeypatch.setattr(production_preflight, "get_connection", backend)
    output = StringIO()

    with pytest.raises(CommandError):
        call_command("production_preflight", stdout=output)

    assert "FAIL email" in output.getvalue()
    assert "private-email-secret" not in output.getvalue()
