"""Tests for hermes-harness verify_partner_canaries.py (offline / mocked)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "verify_partner_canaries.py"
)


@pytest.fixture
def canaries(monkeypatch):
    spec = importlib.util.spec_from_file_location("verify_partner_canaries", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_prepare_mode_exits_zero_without_network(canaries, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_partner_canaries.py", "--prepare"])
    assert canaries.main() == 0
    out = capsys.readouterr().out
    assert "localhost:1234" in out


def test_prepare_json_mode(canaries, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_partner_canaries.py", "--prepare", "--json"])
    assert canaries.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["prepare"] is True
    assert any("install_hermes_thin_skills" in line for line in data["checklist"])


def test_check_lm_studio_passes_on_models_and_completion(canaries, monkeypatch):
    class FakeResp:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    calls: list[str] = []

    def fake_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        calls.append(url)
        if url.endswith("/v1/models"):
            return FakeResp(
                json.dumps({"data": [{"id": "test-model"}]}).encode()
            )
        return FakeResp(
            json.dumps(
                {"choices": [{"message": {"content": "LM_READY"}}]}
            ).encode()
        )

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    result = canaries.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == canaries.Status.PASS
    assert len(calls) == 2


def test_check_lm_studio_fails_when_completion_missing_marker(canaries, monkeypatch):
    class FakeResp:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/v1/models"):
            return FakeResp(json.dumps({"data": [{"id": "m"}]}).encode())
        return FakeResp(
            json.dumps({"choices": [{"message": {"content": "nope"}}]}).encode()
        )

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    result = canaries.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == canaries.Status.FAIL
