"""Policy tests for discovery-derived LM link watcher URLs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lm_link_watch.py"
_SPEC = importlib.util.spec_from_file_location("lm_link_watch_test", _SCRIPT_PATH)
assert _SPEC and _SPEC.loader
lm_link_watch = importlib.util.module_from_spec(_SPEC)
sys.modules["lm_link_watch_test"] = lm_link_watch
_SPEC.loader.exec_module(lm_link_watch)

pytestmark = pytest.mark.unit


def test_peer_url_rejects_public_discovery_endpoint(tmp_path, monkeypatch) -> None:
    discovery = tmp_path / "last_discovery.json"
    discovery.write_text('{"endpoints": {"win": {"ip": "1.1.1.1"}}}', encoding="utf-8")
    monkeypatch.setattr(lm_link_watch, "DISCOVERY_FILE", discovery)

    assert lm_link_watch.peer_url("macos") is None


def test_peer_url_preserves_approved_secure_scheme(tmp_path, monkeypatch) -> None:
    discovery = tmp_path / "last_discovery.json"
    discovery.write_text(
        '{"endpoints": {"win": {"ip": "https://192.168.254.107:9443"}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(lm_link_watch, "DISCOVERY_FILE", discovery)

    assert lm_link_watch.peer_url("macos") == "https://192.168.254.107:1234/v1/models"
