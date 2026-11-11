"""Tests for probe_lan_peer.py (offline / mocked)."""
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
    / "probe_lan_peer.py"
)


@pytest.fixture
def peer_mod(monkeypatch):
    """Load a fresh copy of probe_lan_peer from its file path for each test."""
    spec = importlib.util.spec_from_file_location("probe_lan_peer", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_peer_from_discovery_mac_role(peer_mod):
    """In the mac role the peer is the win endpoint from discovery."""
    discovery = {"endpoints": {"win": {"ip": "10.0.0.50", "port": 1234}}}
    ip, port = peer_mod.peer_from_discovery(discovery, "mac")
    assert ip == "10.0.0.50"
    assert port == 1234


def test_run_checks_lmstudio_pass(peer_mod, monkeypatch):
    """With a healthy portal and LM Studio, health and models pass and status is skipped without tokens."""
    def fake_get(url: str, token: str = "", timeout: int = 8):
        """Fake http_get answering health and models successfully."""
        if url.endswith("/health"):
            return 200, '{"status":"ok"}'
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": [{"id": "m1"}]})
        return 404, "nope"

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    checks = peer_mod.run_checks("10.0.0.50", 1234, 8002, tokens=[])
    by_name = {c.name: c.status for c in checks}
    assert by_name["portal-health"] == peer_mod.Status.PASS
    assert by_name["peer-lmstudio"] == peer_mod.Status.PASS
    assert by_name["portal-status"] == peer_mod.Status.SKIP


def test_resolve_control_plane_token_from_pt_state(peer_mod, monkeypatch, tmp_path):
    """The control-plane token is resolved from the Perpetua-Tools state file."""
    token_file = tmp_path / ".state" / "control_plane_token"
    token_file.parent.mkdir(parents=True)
    token_file.write_text("pt-secret-token\n", encoding="utf-8")
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path))
    assert peer_mod.resolve_control_plane_token() == "pt-secret-token"


def test_load_repo_env_uses_env_local_without_overriding_shell(peer_mod, monkeypatch, tmp_path):
    """Repo .env.local overrides .env but neither overrides the shell environment."""
    (tmp_path / ".env").write_text(
        "ORAMA_CONTROL_PLANE_TOKEN=base-token\n"
        "ORAMA_CONTROL_PLANE_TOKEN_PEER=base-peer\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "ORAMA_CONTROL_PLANE_TOKEN=local-token\n"
        "ORAMA_CONTROL_PLANE_TOKEN_PEER=local-peer\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ORAMA_CONTROL_PLANE_TOKEN", raising=False)
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", "shell-peer")

    peer_mod.load_repo_env(tmp_path)

    assert peer_mod.resolve_control_plane_token() == "shell-peer"
    assert peer_mod.orama_lane_token_candidates() == ["local-token"]


def test_outbound_peer_token_tried_first(peer_mod, monkeypatch):
    """The peer token is tried before the local lane token."""
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN", "local-symmetric")
    monkeypatch.setenv("ORAMA_CONTROL_PLANE_TOKEN_PEER", "peer-handoff")
    for var in ("PERPETUA_TOOLS_ROOT", "PERPETUATOOLSROOT", "PERPETUA_TOOLS_PATH", "PT_HOME"):
        monkeypatch.delenv(var, raising=False)
    tokens = peer_mod.outbound_control_plane_tokens()
    assert tokens[:2] == ["peer-handoff", "local-symmetric"]


def test_portal_status_tries_second_token(peer_mod, monkeypatch):
    """Portal status moves on to the second token after the first is rejected."""
    calls: list[str] = []

    def fake_get(url: str, token: str = "", timeout: int = 8):
        """Fake http_get that rejects the bad token and accepts the good one."""
        if token:
            calls.append(token)
        if url.endswith("/health"):
            return 200, '{"status":"ok"}'
        if "/api/status" in url:
            if token == "bad-token":
                return 401, "Unauthorized"
            if token == "good-token":
                return 200, "{}"
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": []})
        return 404, "nope"

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    monkeypatch.setattr(
        peer_mod,
        "check_ws_peer",
        lambda peer_ip, portal_port, tokens, **kwargs: peer_mod.Check(
            "ws-peer", peer_mod.Status.SKIP, ""
        ),
    )
    # Token candidates only travel over https (see test_probe_status_transport_guard.py).
    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    checks = peer_mod.run_checks("10.0.0.50", 1234, 8002, ["bad-token", "good-token"])
    by_name = {c.name: c for c in checks}
    assert by_name["portal-status"].status == peer_mod.Status.PASS
    assert calls[:2] == ["bad-token", "good-token"]


def test_run_checks_uses_configured_timeouts(peer_mod, monkeypatch):
    """run_checks passes each configured timeout to the matching probe and uses https for the portal."""
    calls: list[tuple[str, int]] = []

    def fake_get(url: str, token: str = "", timeout: int = 8):
        """Fake http_get that records URLs and timeouts."""
        calls.append((url, timeout))
        if url.endswith("/health"):
            return 200, '{"status":"ok"}'
        if "/api/status" in url:
            return 200, "{}"
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": []})
        return 404, "nope"

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    monkeypatch.setattr(
        peer_mod,
        "check_ws_peer",
        lambda peer_ip, portal_port, tokens, timeout=10: peer_mod.Check(
            "ws-peer", peer_mod.Status.PASS, f"timeout={timeout}"
        ),
    )

    monkeypatch.setenv("PEER_PORTAL_TLS_ENABLED", "1")
    checks = peer_mod.run_checks(
        "10.0.0.50",
        1234,
        8002,
        ["good-token"],
        timeout=3,
        status_timeout=4,
        ws_timeout=5,
    )

    host = calls[-1][0].split("//", 1)[1].split(":", 1)[0]
    assert calls == [
        (f"https://{host}:8002/health", 3),
        (f"https://{host}:8002/api/status", 4),
        ("http://10.0.0.50:1234/v1/models", 3),
    ]
    assert checks[-1].detail == "timeout=5"


def test_write_probe_result_on_success(peer_mod, monkeypatch, tmp_path):
    """write_probe_result writes the payload to the result path and returns it."""
    out = tmp_path / "last_lan_peer_probe.json"
    monkeypatch.setattr(peer_mod, "probe_result_path", lambda: out)
    written = peer_mod.write_probe_result({"status": "success", "peer_ip": "10.0.0.50"})
    assert written == out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "success"


def test_main_json_exit_zero_when_lmstudio_ok(peer_mod, monkeypatch, capsys, tmp_path):
    """main --json exits 0 and reports success with the result path when the peer is healthy."""
    disc = tmp_path / "last_discovery.json"
    disc.write_text(
        json.dumps({"endpoints": {"win": {"ip": "10.0.0.50", "port": 1234}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(peer_mod, "discovery_path", lambda: disc)
    monkeypatch.setattr(peer_mod, "local_role", lambda: "mac")
    result_file = tmp_path / "last_lan_peer_probe.json"
    monkeypatch.setattr(peer_mod, "probe_result_path", lambda: result_file)

    def fake_get(url: str, token: str = "", timeout: int = 8):
        """Fake http_get answering health and models successfully."""
        if "/health" in url:
            return 200, "ok"
        return 200, json.dumps({"data": []})

    monkeypatch.setattr(peer_mod, "http_get", fake_get)
    monkeypatch.setattr(
        peer_mod,
        "check_ws_peer",
        lambda peer_ip, portal_port, tokens, **kwargs: peer_mod.Check(
            "ws-peer", peer_mod.Status.PASS, "mocked"
        ),
    )
    rc = peer_mod.main(["--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["peer_ip"] == "10.0.0.50"
    assert out["status"] == "success"
    assert out["result_path"] == str(result_file)
    assert result_file.is_file()
