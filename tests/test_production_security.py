import json
import os
import subprocess
import sys

import pytest


def production_env(**overrides):
    env = os.environ.copy()
    env.update(
        PYTHONPATH="src",
        DJANGO_SETTINGS_MODULE="config.settings.production",
        DJANGO_SECRET_KEY="production-security-test-placeholder",
        POSTGRES_DB="unused",
        POSTGRES_USER="unused",
        POSTGRES_PASSWORD="test-placeholder",
        POSTGRES_HOST="127.0.0.1",
        POSTGRES_PORT="5432",
        REDIS_CACHE_URL="redis://127.0.0.1:6379/0",
        CELERY_BROKER_URL="redis://127.0.0.1:6379/1",
        DJANGO_ALLOWED_HOSTS="example.test",
        DJANGO_CSRF_TRUSTED_ORIGINS="https://example.test",
        DJANGO_EMAIL_HOST="smtp.invalid",
        DJANGO_EMAIL_PORT="587",
        DJANGO_EMAIL_HOST_USER="test-placeholder",
        DJANGO_EMAIL_HOST_PASSWORD="test-placeholder",
        DJANGO_EMAIL_TIMEOUT="2",
        DJANGO_DEFAULT_FROM_EMAIL="test@example.invalid",
    )
    for name in ("DJANGO_SECURE_SSL_REDIRECT", "DJANGO_TRUST_NGINX_PROXY"):
        env.pop(name, None)
    env.update(overrides)
    return env


@pytest.mark.parametrize(
    ("overrides", "forwarded_proto", "expected"),
    [
        ({}, "", 301),
        ({}, "https", 301),
        ({"DJANGO_SECURE_SSL_REDIRECT": "false"}, "", 200),
        ({"DJANGO_TRUST_NGINX_PROXY": "true"}, "https", 200),
        ({"DJANGO_TRUST_NGINX_PROXY": "true"}, "http", 301),
    ],
)
def test_production_https_redirect_requires_explicit_proxy_trust(
    overrides, forwarded_proto, expected
):
    code = (
        "import django; django.setup(); "
        "from django.test import Client; "
        "from django.conf import settings as s; "
        "r=Client().get('/health/live/',HTTP_HOST='example.test',"
        f"HTTP_X_FORWARDED_PROTO={forwarded_proto!r}); "
        "import json; print(json.dumps([r.status_code,s.DEBUG,s.SESSION_COOKIE_SECURE,"
        "s.CSRF_COOKIE_SECURE,str(s.STATIC_ROOT)]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=production_env(**overrides),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    status, debug, session_secure, csrf_secure, static_root = json.loads(result.stdout)
    assert status == expected
    assert debug is False
    assert session_secure is True and csrf_secure is True
    assert static_root.endswith("/staticfiles")


def test_production_disallowed_host_is_rejected():
    code = (
        "import django; django.setup(); from django.test import Client; "
        "print(Client().get('/health/live/',HTTP_HOST='attacker.invalid').status_code)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=production_env(DJANGO_SECURE_SSL_REDIRECT="false"),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "400"
