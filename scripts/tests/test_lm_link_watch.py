"""Tests for lm_link_watch.py's peer_url() discovery-file handling."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("lm_link_watch", _SCRIPTS_DIR / "lm_link_watch.py")
lm_link_watch = importlib.util.module_from_spec(_SPEC)
sys.modules["lm_link_watch"] = lm_link_watch
_SPEC.loader.exec_module(lm_link_watch)


def _write_discovery(monkeypatch, tmp_path: Path, role_key: str, ip_value: str) -> None:
    discovery_file = tmp_path / "last_discovery.json"
    discovery_file.write_text(
        json.dumps({"endpoints": {role_key: {"ip": ip_value}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(lm_link_watch, "DISCOVERY_FILE", discovery_file)


def test_peer_url_windows_passes_through_bare_ip(monkeypatch, tmp_path):
    _write_discovery(monkeypatch, tmp_path, "mac", "192.168.254.107")
    assert lm_link_watch.peer_url("windows") == "http://192.168.254.107:11434/api/tags"


def test_peer_url_macos_passes_through_bare_ip(monkeypatch, tmp_path):
    _write_discovery(monkeypatch, tmp_path, "win", "192.168.254.101")
    assert lm_link_watch.peer_url("macos") == "http://192.168.254.101:1234/v1/models"


def test_peer_url_windows_normalizes_scheme_contaminated_value(monkeypatch, tmp_path):
    """Regression: the discovery file's "ip" field is written by a separate
    process (scripts/discover.py) and read here with zero validation before
    direct f-string interpolation into a URL that urllib then fetches. If
    that field is ever accidentally scheme-prefixed, this constructs and
    fetches a double-scheme URL. Must normalize to a bare hostname."""
    _write_discovery(monkeypatch, tmp_path, "mac", "http://192.168.254.107")
    result = lm_link_watch.peer_url("windows")
    assert result == "http://192.168.254.107:11434/api/tags"
    assert "http://http://" not in (result or "")


def test_peer_url_rejects_malformed_value(monkeypatch, tmp_path):
    _write_discovery(monkeypatch, tmp_path, "mac", "http://user:pass@192.168.254.107")
    assert lm_link_watch.peer_url("windows") is None


def test_peer_url_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(lm_link_watch, "DISCOVERY_FILE", tmp_path / "does-not-exist.json")
    assert lm_link_watch.peer_url("windows") is None
