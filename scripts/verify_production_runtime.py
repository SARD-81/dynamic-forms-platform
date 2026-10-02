"""Verify the internal Compose contract; public HTTP checks stay in verify_production.py."""

import argparse
import json
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.production")
    parser.add_argument("--project-name", default="dynamic-forms-production")
    args = parser.parse_args(argv)
    command = [
        "docker",
        "compose",
        "--project-name",
        args.project_name,
        "--env-file",
        args.env_file,
        "-f",
        "compose.production.yaml",
    ]

    def run(*items):
        result = subprocess.run(
            command + list(items), capture_output=True, text=True, timeout=45, check=False
        )
        if result.returncode:
            # Never display raw Docker configuration/inspect output: it contains env secrets.
            raise RuntimeError("Compose verification command failed")
        return result.stdout

    try:
        config = json.loads(run("config", "--format", "json"))
        required = {"app-init", "web", "nginx", "celery-worker", "celery-beat", "postgres", "redis"}
        services = config["services"]
        assert set(services) == required
        for name, service in services.items():
            assert not any(v["type"] == "bind" for v in service.get("volumes", []))
            if name != "nginx":
                assert not service.get("ports")
        assert len(services["nginx"]["ports"]) == 1
        assert services["nginx"]["ports"][0]["target"] == 80
        assert services["web"]["command"][0] == "daphne"
        for name in ("web", "app-init", "celery-worker", "celery-beat"):
            assert (
                services[name]["environment"]["DJANGO_SETTINGS_MODULE"]
                == "config.settings.production"
            )
            assert "runserver" not in " ".join(services[name].get("command", []))
        print("PASS production config: seven roles, Daphne, one Nginx boundary, no bind mounts")

        ids = run("ps", "--all", "--quiet").split()
        result = subprocess.run(
            ["docker", "inspect", *ids], capture_output=True, text=True, timeout=15, check=False
        )
        if result.returncode:
            raise RuntimeError("Container inspection failed")
        containers = json.loads(result.stdout)
        by_service = {c["Config"]["Labels"]["com.docker.compose.service"]: c for c in containers}
        assert set(by_service) == required
        init = by_service["app-init"]["State"]
        assert init["Status"] == "exited" and init["ExitCode"] == 0
        for name in required - {"app-init"}:
            assert by_service[name]["State"]["Running"]
            if name != "nginx":
                assert not any(by_service[name]["NetworkSettings"]["Ports"].values())
        for name in ("postgres", "redis", "web"):
            assert by_service[name]["State"]["Health"]["Status"] == "healthy"
        assert by_service["web"]["Config"]["Cmd"][0] == "daphne"
        assert "beat" in by_service["celery-beat"]["Config"]["Cmd"]
        print(
            "PASS runtime: init completed, internal dependencies healthy, worker and Beat running"
        )

        code = (
            "from pathlib import Path; from django.conf import settings as s; "
            "from django.db import connection; "
            "from django.db.migrations.executor import MigrationExecutor; "
            "assert s.SETTINGS_MODULE == 'config.settings.production'; assert s.DEBUG is False; "
            "assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; "
            "assert s.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https'); "
            "executor=MigrationExecutor(connection); "
            "assert not executor.migration_plan(executor.loader.graph.leaf_nodes()); "
            "assert (Path(s.STATIC_ROOT)/'core/app.css').is_file(); "
            "assert (Path(s.STATIC_ROOT)/'admin/css/base.css').is_file(); "
            "print('PASS production settings, applied migrations and collected static files')"
        )
        print(run("exec", "-T", "web", "python", "src/manage.py", "shell", "-c", code).strip())
        print(run("exec", "-T", "web", "python", "src/manage.py", "production_preflight").strip())
        ping = run(
            "exec",
            "-T",
            "celery-worker",
            "celery",
            "--workdir=src",
            "-A",
            "config",
            "inspect",
            "ping",
            "--timeout=10",
        )
        assert "pong" in ping
        registered = run(
            "exec",
            "-T",
            "celery-worker",
            "celery",
            "--workdir=src",
            "-A",
            "config",
            "inspect",
            "registered",
            "--timeout=10",
        )
        assert "apps.reports.tasks.dispatch_due_report_subscriptions" in registered
        print("PASS Celery worker response and scheduled report task registration")
    except (AssertionError, KeyError, ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
        print(
            "FAIL production runtime contract (configuration/runtime output withheld)",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
