"""Contract tests for utils/ip_resolver.py's public API.

Regression guard for the 2026-07-19 truncation incident: commit ed1ad8e9
replaced the whole file with a ~98-line patch fragment (a literal "rest of
file unchanged (truncated for patch safety)" comment included), silently
deleting get_win_ip(), the P1-P6 priority chain, the TTL cache, and
write_win_ip_to_openclaw_json() while portal_server.py still imported all
of them.  Nothing failed at the time because no test asserted these names
exist.  These tests make that class of deletion loud: they lock the public
surface and the offline-verifiable behaviors (env priority, scheme-aware
URL building, cache invalidation) without any network dependency.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from utils import ip_resolver  # noqa: E402


PUBLIC_API = [
    "get_win_ip",
    "invalidate_win_ip_cache",
    "get_win_lms_url",
    "get_win_ollama_url",
    "write_win_ip_to_openclaw_json",
]


@pytest.mark.parametrize("name", PUBLIC_API)
def test_public_api_surface_exists(name):
    """Every name portal_server.py (and others) import must exist and be callable."""
    assert callable(getattr(ip_resolver, name, None)), (
        f"ip_resolver.{name} missing or not callable -- if this fails after a "
        "patch, check whether the file was truncated (see module docstring)"
    )


def test_env_var_priority_and_cache_invalidation(monkeypatch):
    """P5 env source wins when higher-priority sources are empty; the TTL
    cache must be invalidated to observe a change."""
    monkeypatch.setattr(ip_resolver, "_from_alphaclaw", lambda: "")
    monkeypatch.setattr(ip_resolver, "_from_openclaw_json", lambda: "")
    monkeypatch.setattr(ip_resolver, "_from_discovery_json", lambda: "")
    monkeypatch.setattr(ip_resolver, "_from_pt_tilting", lambda: "")
    monkeypatch.setenv("LM_STUDIO_WIN_ENDPOINTS", "http://10.9.8.7:1234")
    ip_resolver.invalidate_win_ip_cache()
    try:
        assert ip_resolver.get_win_ip() == "10.9.8.7"
    finally:
        ip_resolver.invalidate_win_ip_cache()  # do not poison other tests' cache


def test_url_builders_handle_bare_ip(monkeypatch):
    monkeypatch.setattr(ip_resolver, "get_win_ip", lambda: "10.1.2.3")
    assert ip_resolver.get_win_lms_url() == "http://10.1.2.3:1234"
    assert ip_resolver.get_win_ollama_url() == "http://10.1.2.3:11434"


def test_url_builders_preserve_scheme(monkeypatch):
    """ed1ad8e9's legitimate change: a scheme-bearing resolver value keeps its
    scheme instead of being wrapped in a second http:// prefix."""
    monkeypatch.setattr(ip_resolver, "get_win_ip", lambda: "https://10.1.2.3")
    assert ip_resolver.get_win_lms_url() == "https://10.1.2.3:1234"
    assert ip_resolver.get_win_ollama_url(port=9999) == "https://10.1.2.3:9999"


def test_write_win_ip_rejects_loopback(tmp_path, monkeypatch):
    """Loopback/empty IPs must never be persisted as the Win provider URL."""
    assert ip_resolver.write_win_ip_to_openclaw_json("") is False
    assert ip_resolver.write_win_ip_to_openclaw_json("localhost") is False
    assert ip_resolver.write_win_ip_to_openclaw_json("127.0.0.1") is False


def test_write_win_ip_roundtrip_idempotent(tmp_path, monkeypatch):
    """Writer persists a new IP once, then no-ops on the identical value."""
    cfg_path = tmp_path / "openclaw.json"
    cfg_path.write_text("{}")
    monkeypatch.setattr(ip_resolver, "OPENCLAW_JSON", cfg_path)
    assert ip_resolver.write_win_ip_to_openclaw_json("10.4.5.6") is True
    import json
    written = json.loads(cfg_path.read_text())
    assert (
        written["models"]["providers"]["lmstudio-win"]["baseUrl"]
        == "http://10.4.5.6:1234/v1"
    )
    # Second write with the same IP is an explicit no-op
    assert ip_resolver.write_win_ip_to_openclaw_json("10.4.5.6") is False


def test_write_win_ip_normalizes_scheme_bearing_input(tmp_path, monkeypatch):
    """get_win_ip() can legitimately return a scheme-bearing value (its own
    documented shape, e.g. "https://10.1.2.3") -- the writer must strip
    that scheme rather than embed it, or the persisted baseUrl becomes a
    broken double-scheme string ("http://https://10.1.2.3:1234/v1")."""
    cfg_path = tmp_path / "openclaw.json"
    cfg_path.write_text("{}")
    monkeypatch.setattr(ip_resolver, "OPENCLAW_JSON", cfg_path)

    assert ip_resolver.write_win_ip_to_openclaw_json("https://10.1.2.3") is True

    import json
    written = json.loads(cfg_path.read_text())
    base_url = written["models"]["providers"]["lmstudio-win"]["baseUrl"]
    assert base_url == "http://10.1.2.3:1234/v1"
    assert base_url.count("://") == 1
