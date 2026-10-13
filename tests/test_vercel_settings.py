import json
import os
import subprocess
import sys

import pytest

from tests.test_production_security import production_env

pytest.importorskip("vercel.integrations.celery")


def vercel_env(**overrides):
    env = production_env(
        DJANGO_SETTINGS_MODULE="config.settings.vercel",
        DJANGO_CACHE_BACKEND="postgresql",
        CELERY_BROKER_URL="vercel://",
        POSTGRES_DIRECT_HOST="127.0.0.1",
        CRON_SECRET="test-cron-placeholder",
        VERCEL_REGION="fra1",
    )
    for name in ("VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL"):
        env.pop(name, None)
    env.update(overrides)
    return env


def run_profile(code, **overrides):
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=vercel_env(**overrides),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    "variable", ["VERCEL_URL", "VERCEL_BRANCH_URL", "VERCEL_PROJECT_PRODUCTION_URL"]
)
def test_vercel_platform_alias_accepts_https_and_csrf_origin(variable):
    status, origins = run_profile(
        "import django; django.setup(); import json; "
        "from django.test import Client; from django.conf import settings; "
        "r=Client().get('/health/live/',HTTP_HOST='deployment.vercel.app',"
        "HTTP_X_FORWARDED_PROTO='https'); "
        "print(json.dumps([r.status_code,settings.CSRF_TRUSTED_ORIGINS]))",
        **{variable: "deployment.vercel.app"},
    )
    assert status == 200
    assert "https://deployment.vercel.app" in origins


@pytest.mark.parametrize(
    "host", ["attacker.invalid", "https://attacker.vercel.app", "evil.vercel.app/path"]
)
def test_vercel_platform_url_does_not_admit_invalid_hosts(host):
    status = run_profile(
        "import django; django.setup(); import json; from django.test import Client; "
        "print(json.dumps(Client().get('/health/live/',HTTP_HOST='attacker.invalid',"
        "HTTP_X_FORWARDED_PROTO='https').status_code))",
        VERCEL_PROJECT_PRODUCTION_URL=host,
    )
    assert status == 400


def test_vercel_retry_publish_keeps_original_task_id_without_deduplication():
    calls = run_profile(
        "import vercel_app; import json; from unittest.mock import patch; "
        "from config.celery import app; "
        "from vercel.queue.sync import QueueClient; "
        "code = '''with patch.object(QueueClient, 'send') as send:\n"
        "    app.send_task('apps.reports.tasks.deliver_report_subscription_task', "
        "args=[1], task_id='same-task', retries=0)\n"
        "    app.send_task('apps.reports.tasks.deliver_report_subscription_task', "
        "args=[1], task_id='same-task', retries=1, countdown=30)\n"
        "    print(json.dumps([[c.args[1]['headers']['id'], "
        "c.args[1]['headers']['retries'], c.kwargs['idempotency_key']] "
        "for c in send.call_args_list]))'''; exec(code)"
    )
    assert calls == [["same-task", 0, None], ["same-task", 1, None]]


def test_vercel_root_manage_collectstatic_discovers_static_command():
    result = subprocess.run(
        [sys.executable, "manage.py", "collectstatic", "--noinput", "--dry-run"],
        env=vercel_env(VERCEL="1"),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_vercel_worker_runs_django_guarded_code_outside_async_loop():
    result = run_profile(
        "import asyncio, json, vercel_app; from config.celery import app; "
        "from django.utils.asyncio import async_unsafe; "
        "worker=app.WorkController(app=app, pool='solo', concurrency=1, "
        "without_gossip=True, without_heartbeat=True, without_mingle=True); "
        "code='''@async_unsafe\ndef guarded():\n    return 'sync-safe'\n"
        "async def check():\n"
        "    values=[]\n"
        "    result = worker.pool.apply_async(guarded, callback=values.append)\n"
        "    await asyncio.to_thread(result.get, timeout=5)\n"
        "    return values\n"
        "print(json.dumps(asyncio.run(check())))\nworker.pool.stop()'''; exec(code)"
    )
    assert result == ["sync-safe"]
