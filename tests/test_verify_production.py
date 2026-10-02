import importlib.util
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_production.py"
SPEC = importlib.util.spec_from_file_location("verify_production", SCRIPT_PATH)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_all_checks_succeed(monkeypatch, capsys):
    requester = MagicMock(return_value=200)
    monkeypatch.setattr(verifier, "request_status", requester)

    result = verifier.main(
        [
            "--base-url",
            "https://example.test",
            "--liveness-path",
            "/live/",
            "--readiness-path",
            "/ready/",
            "--static-path",
            "/static/example.css",
            "--require-all",
        ]
    )

    assert result == 0
    assert requester.call_count == 6
    assert "SKIP" not in capsys.readouterr().out


def test_one_failed_route_returns_nonzero(monkeypatch, capsys):
    def check(name, url, expected_status, timeout):
        return name != "api"

    monkeypatch.setattr(verifier, "check_route", check)

    result = verifier.main(["--base-url", "https://example.test"])

    assert result == 1
    assert "HTTP verification failed." in capsys.readouterr().out


@pytest.mark.parametrize("status", [301, 401, 404, 500])
def test_unexpected_status_is_reported(status, capsys):
    requester = MagicMock(return_value=status)

    result = verifier.check_route(
        "api",
        "https://example.test/api/v1/",
        200,
        2.0,
        requester=requester,
    )

    assert result is False
    assert f"HTTP {status}, expected 200" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (TimeoutError("private-timeout-secret"), "timeout"),
        (URLError(TimeoutError("private-timeout-secret")), "timeout"),
        (URLError("private-connection-secret"), "connection error"),
        (OSError("private-network-secret"), "connection error"),
    ],
)
def test_network_errors_are_secret_safe(error, message, capsys):
    requester = MagicMock(side_effect=error)

    result = verifier.check_route(
        "api",
        "https://example.test/api/v1/?token=private-url-secret",
        200,
        2.0,
        requester=requester,
    )

    output = capsys.readouterr().out

    assert result is False
    assert f"FAIL api: {message}" in output
    assert "private-" not in output


def test_request_timeout_is_passed_to_http_client(monkeypatch):
    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response

    opener = MagicMock()
    opener.open.return_value = response
    monkeypatch.setattr(verifier, "build_opener", MagicMock(return_value=opener))

    assert verifier.request_status("https://example.test/", 1.5) == 200
    assert opener.open.call_args.kwargs["timeout"] == 1.5

    response.read.assert_not_called()
    response.__exit__.assert_called_once()


def test_http_error_body_is_not_read(monkeypatch):
    body = MagicMock()
    error = HTTPError(
        "https://example.test/",
        503,
        "private-error-secret",
        {},
        body,
    )
    opener = MagicMock()
    opener.open.side_effect = error
    monkeypatch.setattr(verifier, "build_opener", MagicMock(return_value=opener))

    assert verifier.request_status("https://example.test/", 2.0) == 503
    body.read.assert_not_called()
    body.close.assert_called_once()


def test_static_path_is_configurable(monkeypatch):
    check = MagicMock(return_value=True)
    monkeypatch.setattr(verifier, "check_route", check)

    result = verifier.main(
        [
            "--base-url",
            "https://example.test",
            "--static-path",
            "/assets/known.css",
        ]
    )

    assert result == 0
    check.assert_any_call(
        "static",
        "https://example.test/assets/known.css",
        expected_status=200,
        timeout=5.0,
    )


def test_require_all_rejects_missing_paths(monkeypatch):
    check = MagicMock()
    monkeypatch.setattr(verifier, "check_route", check)

    with pytest.raises(SystemExit) as error:
        verifier.main(["--base-url", "https://example.test", "--require-all"])

    assert error.value.code == 2
    check.assert_not_called()


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeout_is_rejected(value):
    with pytest.raises(SystemExit) as error:
        verifier.main(["--base-url", "https://example.test", f"--timeout={value}"])

    assert error.value.code == 2


def test_redirect_is_not_followed():
    handler = verifier.NoRedirect()

    assert handler.redirect_request(None, None, 302, "Found", {}, "https://another.test/") is None


def test_expected_status_is_configurable(monkeypatch):
    check = MagicMock(return_value=True)
    monkeypatch.setattr(verifier, "check_route", check)

    result = verifier.main(
        [
            "--base-url",
            "https://example.test",
            "--readiness-path",
            "/ready/",
            "--readiness-status",
            "204",
        ]
    )

    assert result == 0
    check.assert_any_call(
        "readiness",
        "https://example.test/ready/",
        expected_status=204,
        timeout=5.0,
    )


@pytest.mark.parametrize("value", ["99", "600", "invalid"])
def test_invalid_expected_status_is_rejected(value):
    with pytest.raises(SystemExit) as error:
        verifier.main(
            [
                "--base-url",
                "https://example.test",
                "--api-status",
                value,
            ]
        )

    assert error.value.code == 2


@pytest.mark.parametrize(
    "value",
    [
        "ftp://example.test",
        "https://",
        "https://example.test/application",
        "https://example.test?token=secret",
        "https://example.test#fragment",
        "https://example.test:0",
    ],
)
def test_invalid_base_url_is_rejected(value):
    with pytest.raises(SystemExit) as error:
        verifier.main(["--base-url", value])

    assert error.value.code == 2


@pytest.mark.parametrize(
    "value",
    [
        "api/v1/",
        "//another.test/api/",
        "https://another.test/api/",
        "/api/#fragment",
        "/api/with space",
        "/api\\path",
    ],
)
def test_invalid_route_path_is_rejected(value):
    with pytest.raises(SystemExit) as error:
        verifier.main(
            [
                "--base-url",
                "https://example.test",
                "--api-path",
                value,
            ]
        )

    assert error.value.code == 2


def test_missing_health_and_static_are_reported_as_partial(monkeypatch, capsys):
    monkeypatch.setattr(
        verifier,
        "check_route",
        MagicMock(return_value=True),
    )

    result = verifier.main(["--base-url", "https://example.test"])

    output = capsys.readouterr().out
    assert result == 0
    assert "SKIP liveness" in output
    assert "SKIP readiness" in output
    assert "SKIP static" in output
    assert "coverage is incomplete" in output


def test_unknown_argument_does_not_expose_secret(capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main(
            [
                "--base-url",
                "https://example.test",
                "--unknown",
                "private-input-secret",
            ]
        )

    captured = capsys.readouterr()

    assert error.value.code == 2
    assert "private-input-secret" not in captured.out + captured.err


def test_base_url_credentials_are_not_printed(capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main(
            [
                "--base-url",
                "https://user:private-password@example.test",
            ]
        )

    captured = capsys.readouterr()

    assert error.value.code == 2
    assert "private-password" not in captured.out + captured.err


def test_cli_against_real_http_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/missing/":
                self.send_response(404)
            else:
                self.send_response(200)

            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{server.server_port}"
    command = [
        sys.executable,
        str(SCRIPT_PATH),
        "--base-url",
        base,
        "--timeout",
        "1",
        "--liveness-path",
        "/test-live/",
        "--readiness-path",
        "/test-ready/",
        "--static-path",
        "/test-assets/example.css",
        "--require-all",
    ]

    try:
        success = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert success.returncode == 0
        assert "PASS static: HTTP 200" in success.stdout
        assert "SKIP" not in success.stdout

        failure = subprocess.run(
            command + ["--api-path", "/missing/"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert failure.returncode == 1
        assert "FAIL api: HTTP 404, expected 200" in failure.stdout
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
