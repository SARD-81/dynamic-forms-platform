import importlib.util
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_production.py"
SPEC = importlib.util.spec_from_file_location("interrupt_verifier", SCRIPT)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_interrupt_stops_checks_with_fixed_safe_message(monkeypatch, capsys):
    requester = Mock(side_effect=KeyboardInterrupt("private-interrupt-secret"))
    monkeypatch.setattr(verifier, "request_status", requester)

    assert verifier.cli(["--base-url", "https://example.test"]) == 130
    requester.assert_called_once()
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Production verification interrupted.\n"


@pytest.mark.parametrize(("http_status", "exit_status"), [(200, 0), (503, 1)])
def test_cli_preserves_verification_exit_status(monkeypatch, http_status, exit_status):
    monkeypatch.setattr(verifier, "request_status", Mock(return_value=http_status))
    assert verifier.cli(["--base-url", "https://example.test"]) == exit_status


def test_cli_preserves_argument_error_status():
    with pytest.raises(SystemExit) as error:
        verifier.cli([])
    assert error.value.code == 2


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal delivery")
def test_real_cli_interrupt_exits_130_without_traceback():
    started = threading.Event()
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            started.set()
            release.wait(10)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--base-url", f"http://127.0.0.1:{server.server_port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert started.wait(5), "Verifier never reached the HTTP boundary"
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 130
        assert stdout == ""
        assert stderr == "Production verification interrupted.\n"
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
