"""Tests for the live model/effort resolver in switch_cline_provider.py.

Rules under test (operator, 2026-11-12): effort order medium -> high -> low,
never xhigh or max; model order is the first candidate the provider serves;
a route with no acceptable choice is reported blocked, never guessed.
The HTTP wrappers are exercised against a loopback stub server, no network.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "bin", "orama-system", "scripts", "cline-provider-profiles", "switch_cline_provider.py",
)
_spec = importlib.util.spec_from_file_location("switch_cline_provider", _MODULE_PATH)
scp = importlib.util.module_from_spec(_spec)
sys.modules["switch_cline_provider"] = scp
_spec.loader.exec_module(scp)

W_AND_B = [
    "deepseek-ai/DeepSeek-V4.1-Flash-1017",
    "deepseek-ai/DeepSeek-V4.1-Flash",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
]


def test_first_available_keeps_candidate_order() -> None:
    live = ["x", W_AND_B[2], W_AND_B[1], W_AND_B[0]]
    assert scp.choose_first_available(W_AND_B, live) == W_AND_B[0]


def test_first_available_skips_candidates_the_provider_does_not_serve() -> None:
    assert scp.choose_first_available(W_AND_B, [W_AND_B[2]]) == W_AND_B[2]


def test_first_available_returns_none_when_nothing_is_served() -> None:
    assert scp.choose_first_available(W_AND_B + ["deepseek-ai/deepseek-flash"], ["other"]) is None


def test_effort_prefers_medium() -> None:
    assert scp.choose_effort(["medium", "high", "low"], lambda level: True) == "medium"


def test_effort_falls_back_to_high_when_medium_is_rejected() -> None:
    assert scp.choose_effort(["medium", "high", "low"], lambda level: level != "medium") == "high"


def test_effort_last_fallback_is_low() -> None:
    assert scp.choose_effort(["medium", "high", "low"], lambda level: level == "low") == "low"


def test_effort_returns_none_when_nothing_is_accepted() -> None:
    assert scp.choose_effort(["medium", "high", "low"], lambda level: False) is None


@pytest.mark.parametrize("forbidden", ["xhigh", "max"])
def test_effort_never_tries_forbidden_levels(forbidden: str) -> None:
    tried: list[str] = []

    def probe(level: str) -> bool:
        tried.append(level)
        return level == forbidden

    assert scp.choose_effort([forbidden, "medium", "high", "low"], probe) is None
    assert forbidden not in tried


def test_effort_propagates_an_inconclusive_probe_instead_of_falling_through() -> None:
    def probe(level: str) -> bool:
        raise scp.ProbeError("balance")

    with pytest.raises(scp.ProbeError):
        scp.choose_effort(["medium", "high", "low"], probe)


def test_route_falls_to_next_model_when_every_effort_is_rejected() -> None:
    def probe(model: str, level: str) -> bool:
        return model == W_AND_B[1] and level == "high"

    assert scp.resolve_route(W_AND_B, W_AND_B, ["medium", "high", "low"], probe) == (W_AND_B[1], "high")


def test_route_is_blocked_when_no_model_has_an_acceptable_effort() -> None:
    assert scp.resolve_route(W_AND_B, W_AND_B, ["medium", "high", "low"], lambda m, e: False) is None


def test_route_without_probe_uses_first_served_model_and_first_effort() -> None:
    assert scp.resolve_route(W_AND_B, [W_AND_B[1], W_AND_B[2]], ["high", "low"], None) == (W_AND_B[1], "high")


def test_with_model_and_effort_returns_a_new_dict() -> None:
    original = {"model": "a", "reasoning": {"enabled": True, "effort": "high"}, "timeout": 1}
    updated = scp.with_model_and_effort(original, "b", "medium")
    assert updated["model"] == "b" and updated["reasoning"] == {"enabled": True, "effort": "medium"}
    assert original["model"] == "a" and original["reasoning"]["effort"] == "high"


def test_read_resolution_returns_models_and_efforts(tmp_path: Path) -> None:
    tmpl = tmp_path / "p.json.tmpl"
    tmpl.write_text(json.dumps({"settings": {}, "resolution": {"models": ["a"], "efforts": ["medium", "high", "low"]}}))
    assert scp.read_resolution(str(tmpl)) == {"models": ["a"], "efforts": ["medium", "high", "low"]}


def test_read_resolution_rejects_forbidden_efforts(tmp_path: Path) -> None:
    tmpl = tmp_path / "p.json.tmpl"
    tmpl.write_text(json.dumps({"settings": {}, "resolution": {"models": ["a"], "efforts": ["medium", "max"]}}))
    with pytest.raises(ValueError):
        scp.read_resolution(str(tmpl))


def test_read_resolution_defaults_to_empty_when_absent(tmp_path: Path) -> None:
    tmpl = tmp_path / "p.json.tmpl"
    tmpl.write_text(json.dumps({"settings": {}}))
    assert scp.read_resolution(str(tmpl)) == {}


def test_switch_provider_applies_a_resolved_model_and_effort(tmp_path: Path) -> None:
    providers = tmp_path / "providers.json"
    providers.write_text(json.dumps({"providers": {}}))
    history = tmp_path / "history"
    history.mkdir()
    tmpl = tmp_path / "p.json.tmpl"
    tmpl.write_text(json.dumps({"settings": {"provider": "openai-compatible", "apiKey": "${K}", "model": "a",
                                              "reasoning": {"enabled": True, "effort": "high"}}}))
    status = scp.switch_provider(str(providers), str(tmpl), "p", str(history), env={"K": "k"},
                                 resolution=("b", "medium"))
    live = json.loads(providers.read_text())["providers"]["openai-compatible"]["settings"]
    assert status == "activated" and live["model"] == "b" and live["reasoning"]["effort"] == "medium"


class _Stub(BaseHTTPRequestHandler):
    """Loopback provider stub: /models lists ids; chat completions answer by model/effort."""

    routes: dict[str, Any] = {}

    def log_message(self, *args: Any) -> None:  # silence
        pass

    def _send(self, code: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        self._send(200, {"data": [{"id": i} for i in self.routes.get("ids", [])]})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self.routes.setdefault("seen", []).append(body)
        code = self.routes.get("status", {}).get(body.get("reasoning_effort"), 200)
        self._send(code, {"choices": []})


@pytest.fixture
def stub() -> Any:
    _Stub.routes = {"ids": ["m1", "m2"], "status": {}}
    server = HTTPServer(("localhost", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://localhost:{server.server_port}", _Stub.routes
    server.shutdown()


def test_list_live_models_reads_ids(stub: Any) -> None:
    base, _ = stub
    assert scp.list_live_models(base, "k") == ["m1", "m2"]


@pytest.mark.parametrize("body", ["[]", '{"data": null}', '{"data": [null]}', "{", "not-json"])
def test_list_live_models_rejects_malformed_bodies(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    monkeypatch.setattr(scp, "_request", lambda *_args, **_kwargs: (200, body))
    with pytest.raises(scp.ProbeError, match="malformed|not valid JSON"):
        scp.list_live_models("https://example.test/v1", "k")


def test_probe_accepts_200_and_sends_the_requested_effort(stub: Any) -> None:
    base, routes = stub
    assert scp.probe_effort(base, "k", "m1", "medium") is True
    assert routes["seen"][0]["reasoning_effort"] == "medium"


@pytest.mark.parametrize("code", [400, 404, 422])
def test_probe_treats_validation_errors_as_rejected(stub: Any, code: int) -> None:
    base, routes = stub
    routes["status"]["medium"] = code
    assert scp.probe_effort(base, "k", "m1", "medium") is False


@pytest.mark.parametrize("code", [401, 402, 429, 500, 503])
def test_probe_raises_on_inconclusive_status(stub: Any, code: int) -> None:
    base, routes = stub
    routes["status"]["medium"] = code
    with pytest.raises(scp.ProbeError):
        scp.probe_effort(base, "k", "m1", "medium")


def test_probe_refuses_forbidden_levels_without_a_request(stub: Any) -> None:
    base, routes = stub
    with pytest.raises(ValueError):
        scp.probe_effort(base, "k", "m1", "max")
    assert "seen" not in routes
