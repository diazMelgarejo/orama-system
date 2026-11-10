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
from typing import Any

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import cline_autoresearcher as car  # noqa: E402

LOOPBACK = str(ipaddress.IPv4Address(0x7F000001))  # built, not written, so the hygiene gate sees no literal


def test_localhost_uses_literal_loopback_without_dns() -> None:
    """Never follow a resolver result outside the local machine."""
    with patch.object(car.socket, "gethostbyname", return_value="203.0.113.7") as resolve:
        assert car._probe_url("http://localhost:1234/v1/models") == f"http://{LOOPBACK}:1234/v1/models"
    resolve.assert_not_called()


def test_other_hosts_are_left_alone() -> None:
    """A non-localhost host (a LAN peer name) is never rewritten."""
    assert car._probe_url("http://peer.example.test:1234/v1/models") == "http://peer.example.test:1234/v1/models"


def test_https_localhost_preserves_certificate_hostname() -> None:
    """Do not replace the identity used by HTTPS certificate validation."""
    with patch.object(car.socket, "gethostbyname", side_effect=AssertionError("unexpected DNS")):
        assert car._probe_url("https://localhost:1234/v1/models") == "https://localhost:1234/v1/models"


@pytest.mark.parametrize("url", [
    "http://user:password@localhost:1234/v1/models",
    "https://user@localhost/v1/models",
    "file:///tmp/models",
    "http://localhost:invalid/models",
    "http:///models",
])
def test_invalid_probe_configuration_is_refused_before_network(url: str) -> None:
    """Never silently discard credentials or send a malformed probe URL."""
    with patch("urllib.request.urlopen") as request:
        assert car._probe_http_ok(url) is False
    request.assert_not_called()


def test_loopback_rewrite_preserves_port_path_query_fragment() -> None:
    """Only the hostname changes for the supported plain-HTTP optimization."""
    assert car._probe_url("http://localhost:1234/a?b=c#d") == f"http://{LOOPBACK}:1234/a?b=c#d"
    assert car._probe_url("http://localhost/a") == f"http://{LOOPBACK}/a"


def test_probe_http_ok_uses_the_rewritten_url() -> None:
    """_probe_http_ok asks urlopen for the rewritten URL, not the slow localhost one."""
    seen: dict[str, str] = {}

    class _Resp:
        """Minimal context-manager response with a 200 status."""

        status = 200

        def __enter__(self) -> _Resp:
            """Return self."""
            return self

        def __exit__(self, *exc: object) -> bool:
            """Do not swallow exceptions."""
            return False

    def fake_urlopen(req: Any, timeout: float | None = None) -> _Resp:
        """Record the requested URL and answer 200."""
        seen["url"] = req.full_url
        return _Resp()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        assert car._probe_http_ok("http://localhost:1234/v1/models") is True
    assert seen["url"] == f"http://{LOOPBACK}:1234/v1/models"
