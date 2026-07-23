"""Regression tests for query_peer_topology merge + auth helpers."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "bin"
    / "orama-system"
    / "skills"
    / "hermes-harness"
    / "scripts"
    / "query_peer_topology.py"
)


@pytest.fixture
def topo_mod(monkeypatch):
    pt_root = Path(__file__).resolve().parents[1].parent / "Perpetua-Tools"
    monkeypatch.syspath_prepend(str(pt_root))
    spec = importlib.util.spec_from_file_location("query_peer_topology", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, mod)
    spec.loader.exec_module(mod)
    return mod


def test_merge_bootstrap_uses_local_hostname_not_peer_payload(topo_mod):
    peer_data = {
        "local_node": "win-rtx3080",
        "fleet_mode": "PAIR",
        "peers": ["mac-studio"],
        "cross_reachable": False,
    }
    with patch.object(topo_mod.socket, "gethostname", return_value="mac-studio"):
        merged, events = topo_mod._merge_peer_topology(None, peer_data, "10.0.0.50")

    assert merged is not None
    assert merged.local_node == "mac-studio"
    assert merged.local_node != peer_data["local_node"]
    assert merged.peers == ["win-rtx3080"]
    assert events == []


def test_http_get_retries_second_token_on_401(topo_mod, monkeypatch):
    calls: list[str] = []

    def fake_urlopen(req, timeout=2):
        token = req.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        calls.append(token)
        if token == "bad":
            raise topo_mod.urllib.error.HTTPError(
                req.full_url, 401, "Unauthorized", hdrs=None, fp=None
            )
        body = json.dumps({"ok": True}).encode("utf-8")

        class Resp:
            def read(self):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Resp()

    monkeypatch.setattr(
        topo_mod.probe, "collect_control_plane_token_candidates", lambda: ["bad", "good"]
    )
    monkeypatch.setattr(topo_mod.urllib.request, "urlopen", fake_urlopen)

    result = topo_mod._http_get("http://10.0.0.50:8002/api/fleet-topology")
    assert result == {"ok": True}
    assert calls == ["bad", "good"]
