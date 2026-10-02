import hashlib
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SPEC = importlib.util.spec_from_file_location(
    "production_verifier_extensions",
    Path(__file__).resolve().parents[1] / "scripts/verify_production.py",
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.mark.parametrize("body", [b"html fallback private-body", b"x" * (2 * 1024 * 1024 + 1)])
def test_static_digest_rejects_fallback_and_oversized_body_without_output(
    monkeypatch, capsys, body
):
    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response
    response.read.return_value = body
    opener = MagicMock()
    opener.open.return_value = response
    monkeypatch.setattr(verifier, "build_opener", lambda *args: opener)
    assert (
        verifier.check_route(
            "static",
            "https://example.test/static/file.css",
            200,
            1,
            expected_sha256=hashlib.sha256(b"real css").hexdigest(),
        )
        is False
    )
    assert "private-body" not in capsys.readouterr().out
    response.read.assert_called_once_with(2 * 1024 * 1024 + 1)


def test_static_digest_accepts_matching_asset_and_passes_headers(monkeypatch):
    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response
    response.read.return_value = b"real css"
    opener = MagicMock()
    opener.open.return_value = response
    monkeypatch.setattr(verifier, "build_opener", lambda *args: opener)
    assert (
        verifier.request_status(
            "https://example.test/static/file.css",
            1,
            headers={"X-Forwarded-Proto": "https"},
            expected_sha256=hashlib.sha256(b"real css").hexdigest(),
        )
        == 200
    )
    request = opener.open.call_args.args[0]
    assert request.get_header("X-forwarded-proto") == "https"


@pytest.mark.parametrize(
    "value", ["missing-colon-secret", "Bad Header:secret", "X-Test:secret\r\nX:1"]
)
def test_invalid_header_arguments_are_secret_safe(value, capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main(["--base-url", "https://example.test", "--header", value])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "secret" not in captured.out + captured.err


def test_static_digest_arguments_require_selected_success_asset(capsys):
    with pytest.raises(SystemExit) as error:
        verifier.main(["--base-url", "https://example.test", "--static-sha256", "a" * 64])
    assert error.value.code == 2


def test_headers_and_digest_are_opt_in_and_only_static_is_read(monkeypatch):
    requester = MagicMock(return_value=200)
    monkeypatch.setattr(verifier, "request_status", requester)
    assert (
        verifier.main(
            [
                "--base-url",
                "https://example.test",
                "--static-path",
                "/static/a.css",
                "--static-sha256",
                "a" * 64,
                "--header",
                "X-Test:test-value",
            ]
        )
        == 0
    )
    assert requester.call_count == 4
    calls = requester.call_args_list
    assert all(c.kwargs.get("expected_sha256") is None for c in calls[:3])
    assert calls[3].kwargs["expected_sha256"] == "a" * 64
