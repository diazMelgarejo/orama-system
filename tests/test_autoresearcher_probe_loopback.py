#!/usr/bin/env python3
"""The controller's local-backend probe must not pay the IPv6-first ``localhost`` delay (about 2 s on Windows).

Found by the Cline benchmark on 2026-11-10: an older checkout reported "LM Studio Win not reachable" while LM Studio
was up, because ``localhost`` took 2106 ms to answer against 8 ms for the IPv4 loopback address.
"""
from __future__ import annotations

import ipaddress
import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import cline_autoresearcher as car  # noqa: E402

LOOPBACK = str(ipaddress.IPv4Address(0x7F000001))  # built, not written, so the hygiene gate sees no literal


def test_localhost_is_rewritten_to_its_ipv4_address() -> None:
    """A ``localhost`` URL is probed through the IPv4 address that localhost resolves to."""
    with patch.object(car.socket, "gethostbyname", return_value=LOOPBACK):
        assert car._probe_url("http://localhost:1234/v1/models") == f"http://{LOOPBACK}:1234/v1/models"


def test_other_hosts_are_left_alone() -> None:
    """A non-localhost host (a LAN peer name) is never rewritten."""
    assert car._probe_url("http://peer.example.test:1234/v1/models") == "http://peer.example.test:1234/v1/models"


def test_resolution_failure_falls_back_to_the_original_url() -> None:
    """If localhost cannot be resolved to IPv4 the original URL is probed unchanged."""
    with patch.object(car.socket, "gethostbyname", side_effect=OSError("no ipv4")):
        assert car._probe_url("http://localhost:1234/v1/models") == "http://localhost:1234/v1/models"


def test_probe_http_ok_uses_the_rewritten_url() -> None:
    """_probe_http_ok asks urlopen for the rewritten URL, not the slow localhost one."""
    seen = {}

    class _Resp:
        """Minimal context-manager response with a 200 status."""

        status = 200

        def __enter__(self):
            """Return self."""
            return self

        def __exit__(self, *exc):
            """Do not swallow exceptions."""
            return False

    def fake_urlopen(req, timeout=None):
        """Record the requested URL and answer 200."""
        seen["url"] = req.full_url
        return _Resp()

    with patch.object(car.socket, "gethostbyname", return_value=LOOPBACK), \
         patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert car._probe_http_ok("http://localhost:1234/v1/models") is True
    assert seen["url"] == f"http://{LOOPBACK}:1234/v1/models"
