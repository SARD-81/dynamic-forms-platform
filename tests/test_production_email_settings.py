import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))


def _production_env(**overrides):
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": os.path.join(PROJECT_ROOT, "src"),
            "DJANGO_SECRET_KEY": "test-production-secret",
            "POSTGRES_DB": "dynamic_forms",
            "POSTGRES_USER": "dynamic_forms",
            "POSTGRES_PASSWORD": "database-password",
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "REDIS_CACHE_URL": "redis://127.0.0.1:6379/0",
            "CELERY_BROKER_URL": "redis://127.0.0.1:6379/1",
            "DJANGO_ALLOWED_HOSTS": "example.com",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.com",
            "DJANGO_EMAIL_HOST": "smtp.example.com",
            "DJANGO_EMAIL_PORT": "587",
            "DJANGO_EMAIL_HOST_USER": "mailer",
            "DJANGO_EMAIL_HOST_PASSWORD": "smtp-secret",
            "DJANGO_EMAIL_TIMEOUT": "10",
            "DJANGO_DEFAULT_FROM_EMAIL": "no-reply@example.com",
        }
    )
    env.pop("DJANGO_EMAIL_USE_TLS", None)
    env.update(overrides)
    return env


def _run_settings(code, *, env):
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_production_email_settings_map_authorized_contract():
    result = _run_settings(
        (
            "from config.settings import production as s; "
            "print(s.EMAIL_BACKEND); print(s.EMAIL_HOST); print(s.EMAIL_PORT); "
            "print(s.EMAIL_HOST_USER); print(s.EMAIL_USE_TLS); print(s.EMAIL_TIMEOUT); "
            "print(s.DEFAULT_FROM_EMAIL)"
        ),
        env=_production_env(),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "django.core.mail.backends.smtp.EmailBackend",
        "smtp.example.com",
        "587",
        "mailer",
        "True",
        "10",
        "no-reply@example.com",
    ]


@pytest.mark.parametrize(
    "missing_name",
    [
        "DJANGO_EMAIL_HOST",
        "DJANGO_EMAIL_PORT",
        "DJANGO_EMAIL_HOST_USER",
        "DJANGO_EMAIL_HOST_PASSWORD",
        "DJANGO_EMAIL_TIMEOUT",
        "DJANGO_DEFAULT_FROM_EMAIL",
    ],
)
def test_production_email_settings_fail_fast_when_required_value_is_missing(missing_name):
    env = _production_env()
    env[missing_name] = ""

    result = _run_settings(
        "from config.settings import production",
        env=env,
    )

    assert result.returncode != 0
    assert missing_name in result.stderr


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DJANGO_EMAIL_PORT", "not-a-number"),
        ("DJANGO_EMAIL_PORT", "0"),
        ("DJANGO_EMAIL_PORT", "-1"),
        ("DJANGO_EMAIL_TIMEOUT", "not-a-number"),
        ("DJANGO_EMAIL_TIMEOUT", "0"),
        ("DJANGO_EMAIL_TIMEOUT", "-1"),
    ],
)
def test_production_email_numeric_settings_require_positive_integers(name, value):
    result = _run_settings(
        "from config.settings import production",
        env=_production_env(**{name: value}),
    )

    assert result.returncode != 0
    assert name in result.stderr
    assert "positive integer" in result.stderr


def test_production_email_tls_defaults_to_enabled():
    result = _run_settings(
        "from config.settings import production as s; print(s.EMAIL_USE_TLS)",
        env=_production_env(),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_production_email_tls_can_be_disabled_explicitly():
    result = _run_settings(
        "from config.settings import production as s; print(s.EMAIL_USE_TLS)",
        env=_production_env(DJANGO_EMAIL_USE_TLS="false"),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_development_email_backend_does_not_require_production_smtp_variables():
    env = _production_env()
    for name in (
        "DJANGO_EMAIL_HOST",
        "DJANGO_EMAIL_PORT",
        "DJANGO_EMAIL_HOST_USER",
        "DJANGO_EMAIL_HOST_PASSWORD",
        "DJANGO_EMAIL_TIMEOUT",
        "DJANGO_DEFAULT_FROM_EMAIL",
    ):
        env[name] = ""

    result = _run_settings(
        "from config.settings import development as s; print(s.EMAIL_BACKEND)",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "django.core.mail.backends.console.EmailBackend"
