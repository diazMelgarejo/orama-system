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
        if url.endswith("/api/v0/models"):
            return FakeResp(
                json.dumps(
                    {
                        "data": [
                            {"id": "test-model", "type": "vlm", "state": "loaded"},
                        ]
                    }
                ).encode()
            )
        return FakeResp(
            json.dumps(
                {"choices": [{"message": {"content": "LM_READY"}}]}
            ).encode()
        )

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    result = canaries.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == canaries.Status.PASS
    assert any("/api/v0/models" in c for c in calls)
    assert any("/v1/chat/completions" in c for c in calls)


def test_loaded_lmstudio_chat_model_skips_not_loaded(canaries, monkeypatch):
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
        if url.endswith("/api/v0/models"):
            return FakeResp(
                json.dumps(
                    {
                        "data": [
                            {"id": "gemma-4-e4b-it", "type": "vlm", "state": "not-loaded"},
                            {"id": "loaded-chat", "type": "vlm", "state": "loaded"},
                        ]
                    }
                ).encode()
            )
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    mid, count = canaries._loaded_lmstudio_chat_model("http://localhost:1234/v1", timeout=5)
    assert mid == "loaded-chat"
    assert count == 2


def test_check_lm_studio_passes_on_reasoning_content(canaries, monkeypatch):
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
        if url.endswith("/api/v0/models"):
            return FakeResp(
                json.dumps(
                    {
                        "data": [
                            {"id": "reasoning-model", "type": "vlm", "state": "loaded"},
                        ]
                    }
                ).encode()
            )
        return FakeResp(
            json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "reasoning_content": "thinking… LM_READY",
                            }
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    result = canaries.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == canaries.Status.PASS


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
        if url.endswith("/api/v0/models"):
            return FakeResp(
                json.dumps(
                    {
                        "data": [
                            {"id": "m", "type": "vlm", "state": "loaded"},
                        ]
                    }
                ).encode()
            )
        return FakeResp(
            json.dumps({"choices": [{"message": {"content": "nope"}}]}).encode()
        )

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    result = canaries.check_lm_studio("http://localhost:1234/v1", timeout=5)
    assert result.status == canaries.Status.FAIL


def test_loaded_lmstudio_chat_model_skips_embeddings(canaries, monkeypatch):
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
        if url.endswith("/api/v0/models"):
            return FakeResp(
                json.dumps(
                    {
                        "data": [
                            {"id": "text-embedding-nomic", "type": "embeddings", "state": "loaded"},
                            {"id": "chat-model", "type": "vlm", "state": "loaded"},
                        ]
                    }
                ).encode()
            )
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(canaries.urllib.request, "urlopen", fake_urlopen)
    mid, count = canaries._loaded_lmstudio_chat_model("http://localhost:1234/v1", timeout=5)
    assert mid == "chat-model"
    assert count == 2


def test_lm_completion_timeout_reasoning_model(canaries):
    assert canaries._lm_completion_timeout("qwen3.5-27b-reasoning-distilled", 90) == 180


def test_check_hermes_accepts_hermes_ready_in_stderr(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: "/usr/bin/hermes")
    monkeypatch.setattr(canaries, "_run_partner", lambda *a, **k: (0, "", "HERMES_READY"))
    result = canaries.check_hermes(timeout=5)
    assert result.status == canaries.Status.PASS


def test_check_hermes_uses_canary_model(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: "/usr/bin/hermes")
    captured: list[list[str]] = []

    def fake_run(name, args, timeout=30):
        captured.append([name, *args])
        return 0, "HERMES_READY", ""

    monkeypatch.setattr(canaries, "_run_partner", fake_run)
    canaries.check_hermes(timeout=5)
    assert canaries.HERMES_CANARY_MODEL in captured[0]
    assert "--provider" in captured[0]
    assert "nous" in captured[0]


def test_check_agy_unavailable_on_timeout(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: "/usr/bin/agy")
    monkeypatch.setattr(canaries, "_run_partner", lambda *a, **k: (-1, "", "timed out"))
    result = canaries.check_agy(timeout=5)
    assert result.status == canaries.Status.UNAVAILABLE


def test_check_agy_unavailable_not_on_path(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: None)
    result = canaries.check_agy(timeout=5)
    assert result.status == canaries.Status.UNAVAILABLE


def test_check_codex_unavailable_not_on_path(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: None)
    result = canaries.check_codex(timeout=5)
    assert result.status == canaries.Status.UNAVAILABLE


def test_check_codex_unavailable_on_timeout(canaries, monkeypatch):
    monkeypatch.setattr(canaries, "_resolve_partner_cli", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(canaries, "_run_partner", lambda *a, **k: (-1, "", "timed out"))
    result = canaries.check_codex(timeout=5)
    assert result.status == canaries.Status.UNAVAILABLE


def test_check_cursor_agent_passes_on_version(canaries, monkeypatch):
    monkeypatch.setattr(
        canaries, "_resolve_partner_cli", lambda name: "/bin/cursor-agent" if name == "cursor-agent" else None
    )
    monkeypatch.setattr(canaries, "_run_partner", lambda *a, **k: (0, "2026.06.24-00-45-58-9f61de7", ""))
    result = canaries.check_cursor_agent(5)
    assert result.status == canaries.Status.PASS
