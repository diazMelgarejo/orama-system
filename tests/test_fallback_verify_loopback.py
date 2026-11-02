"""fallback-chain-verify.ps1 Tier 2 must see a loopback-only LM Studio behind a LAN-address endpoint."""
from __future__ import annotations

import http.server
import ipaddress
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "platform" / "windows" / "fallback-chain-verify.ps1"
LOOPBACK = str(ipaddress.IPv4Address(0x7F000001))
UNROUTABLE_ENDPOINT_HOST = "192.0.2.1"  # TEST-NET-1: never answers

pytestmark = pytest.mark.skipif(
    os.name != "nt" or shutil.which("powershell.exe") is None,
    reason="Windows PowerShell 5.1 is required",
)


class _Models(http.server.BaseHTTPRequestHandler):
    """Answer GET /v1/models like a running LM Studio."""

    def do_GET(self) -> None:
        """Return an empty model list."""
        body = b'{"data": []}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Keep the test output quiet."""


@pytest.fixture
def loopback_lm_studio() -> Iterator[int]:
    """Serve a loopback-only fake LM Studio on an ephemeral port and yield the port."""
    server = http.server.ThreadingHTTPServer((LOOPBACK, 0), _Models)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _status_only(endpoints: str) -> subprocess.CompletedProcess[str]:
    """Run the verifier in status-only mode with the given LM_STUDIO_WIN_ENDPOINTS."""
    env = {**os.environ, "LM_STUDIO_WIN_ENDPOINTS": endpoints}
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(SCRIPT), "-StatusOnly"],
        capture_output=True, text=True, env=env, timeout=120, check=False,
    )


def test_loopback_server_counts_when_endpoint_is_a_lan_address(loopback_lm_studio: int) -> None:
    """A loopback-only server is AVAILABLE even though the configured endpoint never answers."""
    result = _status_only(f"http://{UNROUTABLE_ENDPOINT_HOST}:{loopback_lm_studio}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[AVAILABLE]" in result.stdout


def test_tier_is_offline_when_nothing_answers() -> None:
    """With no listener on loopback or the configured port the hard-required tier stays DOWN."""
    probe = http.server.ThreadingHTTPServer((LOOPBACK, 0), _Models)
    closed_port = probe.server_address[1]
    probe.server_close()
    result = _status_only(f"http://{LOOPBACK}:{closed_port}")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "[OFFLINE]" in result.stdout
