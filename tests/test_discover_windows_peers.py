"""Windows-host peer identification in scripts/discover.py (F12/F13 + latent fixes).

All addresses are TEST-NET (RFC 5737). Network scans are always mocked.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
DISCOVER_SCRIPT = ROOT / "scripts" / "discover.py"

LOCAL = "192.0.2.10"      # this Windows host
WIN2 = "192.0.2.20"       # a second Windows LM Studio box
MAC = "192.0.2.50"      # the Mac
EXTRA_A = "192.0.2.21"
EXTRA_B = "192.0.2.22"

MAC_MODELS = ["qwen3.5-9b-mlx", "text-embedding-nomic"]
WIN_MODELS = ["qwen3.5-27b-q4_k_m-gguf", "gemma-4-26b-gguf"]


def _load_discover(stub_policy: bool = True):
    spec = importlib.util.spec_from_file_location("discover_win_peers_test", DISCOVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if stub_policy:
        with patch.dict(sys.modules, {"utils.hardware_policy": MagicMock()}):
            spec.loader.exec_module(module)
        module.filter_models_for_platform = module._filter_models_for_platform_local
    else:
        spec.loader.exec_module(module)
    return module


def _windows_host(env=None, probes=None, cache=None, scan_hits=None, local=(LOCAL,)):
    """A Windows-host discover module with probes, env, cache and scan faked."""
    env = dict(env or {})
    probes = dict(probes or {})
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True
    D._local_ipv4s = lambda: set(local)
    D._win_lan_ip = lambda: LOCAL
    D.load_policy = lambda policy_path=None: {"mac_only": [], "windows_only": []}
    D.get_local_subnets = lambda: []
    D._load_json = lambda path: cache
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": env.get(key, default)
    D.probe_calls = []

    def fake_probe(url):
        D.probe_calls.append(url)
        if "localhost" in url:
            return ["qwen3.5-27b-distilled"] if url.endswith(":1234") else None
        return probes.get(url)

    D.probe_models = fake_probe
    D.scan_calls = []

    async def fake_scan(subnet, port, exclude):
        D.scan_calls.append((subnet, set(exclude)))
        return [ip for ip in (scan_hits or []) if ip not in exclude]

    D.scan_subnet_async = fake_scan
    return D


# ── F12: Mac vs Windows identification ───────────────────────────────────────

def test_win2_on_1234_is_never_labelled_mac():
    D = _windows_host(
        probes={f"http://{WIN2}:1234": WIN_MODELS},
        scan_hits=[WIN2],
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [WIN2]
    assert result["win"] == {"ip": "localhost", "models": ["qwen3.5-27b-distilled"]}


def test_scan_hit_without_any_evidence_is_not_mac():
    D = _windows_host(
        probes={f"http://{WIN2}:1234": ["some-unknown-model"]},
        scan_hits=[WIN2],
    )
    assert D.discover_endpoints()["mac"] is None


def test_scan_hit_with_mac_evidence_is_mac_and_known_windows_ips_not_scanned():
    D = _windows_host(
        env={"WIN_PEER_IPS": WIN2},
        probes={f"http://{MAC}:1234": MAC_MODELS},
        scan_hits=[WIN2, MAC],
    )
    result = D.discover_endpoints()
    assert result["mac"]["ip"] == MAC
    assert result["mac"]["models"] == MAC_MODELS
    exclude = D.scan_calls[0][1]
    assert {LOCAL, WIN2} <= exclude


def test_explicit_mac_ip_in_windows_set_is_refused(capsys):
    D = _windows_host(
        env={"MAC_IP": WIN2, "WIN_PEER_IPS": WIN2},
        probes={f"http://{WIN2}:1234": MAC_MODELS},  # even with Mac-looking models
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert "known Windows address" in capsys.readouterr().err


def test_explicit_mac_ip_equal_to_local_ip_is_refused():
    D = _windows_host(env={"MAC_IP": LOCAL}, probes={f"http://{LOCAL}:1234": MAC_MODELS})
    assert D.discover_endpoints()["mac"] is None


def test_explicit_mac_ip_accepted_without_evidence():
    D = _windows_host(env={"MAC_IP": MAC}, probes={f"http://{MAC}:1234": ["plain-model"]})
    assert D.discover_endpoints()["mac"] == {"ip": MAC, "models": ["plain-model"]}


def test_explicit_mac_ip_with_windows_evidence_goes_to_win_peers():
    D = _windows_host(env={"MAC_IP": MAC}, probes={f"http://{MAC}:1234": WIN_MODELS})
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [MAC]


def test_ollama_answer_adds_optional_key_and_counts_as_evidence():
    D = _windows_host(
        env={"MAC_IP": MAC},
        probes={
            f"http://{MAC}:1234": ["plain-model"],
            f"http://{MAC}:11434": ["bge-m3:latest", "qwen3.5:9b-nvfp4"],
        },
    )
    mac = D.discover_endpoints()["mac"]
    assert mac["ip"] == MAC and mac["models"] == ["plain-model"]
    assert mac["ollama"] == ["bge-m3:latest", "qwen3.5:9b-nvfp4"]


def test_cached_mac_in_windows_set_is_not_probed_or_used():
    cache = {"endpoints": {"mac": {"ip": WIN2}, "win": {"ip": "localhost"}},
             "models": {"mac": MAC_MODELS, "win": []}}
    D = _windows_host(env={"WIN_PEER_IPS": WIN2},
                      probes={f"http://{WIN2}:1234": MAC_MODELS}, cache=cache)
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert not any(url == f"http://{WIN2}:11434" for url in D.probe_calls)


def test_cached_mac_needs_mac_evidence():
    cache = {"endpoints": {"mac": {"ip": MAC}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_host(probes={f"http://{MAC}:1234": ["plain-model"]}, cache=cache)
    assert D.discover_endpoints()["mac"] is None


def test_cached_mac_with_tagged_mac_only_model_is_accepted():
    cache = {"endpoints": {"mac": {"ip": MAC}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_host(probes={f"http://{MAC}:11434": ["bge-m3:latest"]}, cache=cache)
    assert D.discover_endpoints()["mac"]["ip"] == MAC


# ── evidence helpers ─────────────────────────────────────────────────────────

def test_mac_evidence_is_tag_insensitive():
    D = _load_discover()
    assert D._has_mac_evidence(["bge-m3:latest"], {"bge-m3"})
    assert D._has_mac_evidence(["BGE-M3"], {"bge-m3"})
    assert D._has_mac_evidence(["qwen3.5:9b-nvfp4"], {"qwen3.5:9b-nvfp4"})
    assert not D._has_mac_evidence(["qwen3.5:27b"], {"qwen3.5:9b-nvfp4"})


@pytest.mark.parametrize("name", ["foo-mlx", "mlx-community/bar", "baz-4bit", "baz-8bit"])
def test_mac_evidence_mlx_markers(name):
    D = _load_discover()
    assert D._has_mac_evidence([name], set())


def test_win_evidence_markers():
    D = _load_discover()
    assert D._has_win_evidence(["Foo-GGUF"], set())
    assert D._has_win_evidence(["gemma-4-26b:latest"], {"gemma-4-26b"})
    assert not D._has_win_evidence(["foo-mlx"], set())


# ── win_peers on a Windows host ──────────────────────────────────────────────

def test_win_peers_from_env_minus_local():
    D = _windows_host(
        env={"WIN_PEER_IPS": EXTRA_A, "WIN_3080_IP": LOCAL, "WIN_5080_IP": EXTRA_B},
        probes={
            f"http://{EXTRA_A}:1234": WIN_MODELS,
            f"http://{EXTRA_B}:1234": WIN_MODELS,
            f"http://{LOCAL}:1234": WIN_MODELS,
        },
    )
    result = D.discover_endpoints()
    assert sorted(p["ip"] for p in result["win_peers"]) == [EXTRA_A, EXTRA_B]
    assert not any(url == f"http://{LOCAL}:1234" for url in D.probe_calls)


def test_mac_path_win_peers_ignores_node_ips():
    D = _load_discover()
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": {"WIN_PEER_IPS": EXTRA_A, "WIN_5080_IP": EXTRA_B}.get(key, default)
    D.probe_models = lambda url: WIN_MODELS
    assert [p["ip"] for p in D.probe_extra_win_peers(set())] == [EXTRA_A]


# ── run_discovery back-fill / recovery tiers ─────────────────────────────────

def _run_discovery_host(tmp_path, last, tier2=None, live=None, env=None):
    D = _windows_host(env=env or {"WIN_PEER_IPS": WIN2})
    live = live if live is not None else {"mac": None, "win": {"ip": "localhost", "models": ["m"]}}
    D.discover_endpoints = lambda: dict(live)
    D._load_json = lambda path: last
    D._load_tier2 = lambda: tier2
    D._load_tier3 = lambda: None
    D._load_tier4 = lambda profile="lan-full": None
    D.RECOVERY_SOURCE_TXT = tmp_path / "recovery.txt"
    D.filter_endpoints_for_policy = lambda endpoints, policy=None: endpoints
    D.filter_endpoints_for_trust = lambda endpoints: (endpoints, [])
    D.backup_current_state = lambda: None
    D.get_repo_paths = lambda: {}
    D.patch_openclaw_json = lambda endpoints: None
    D.write_env_lmstudio = lambda endpoints, paths: None

    class _NoLock:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    D._Lock = _NoLock
    D.saved = {}
    D.save_discovery_state = lambda endpoints, tier=1: D.saved.update(endpoints=endpoints, tier=tier)
    return D


def test_backfill_does_not_preserve_windows_ip_as_mac(tmp_path):
    last = {
        "endpoints": {"mac": {"ip": WIN2, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None


def test_backfill_still_preserves_a_real_mac(tmp_path):
    last = {
        "endpoints": {"mac": {"ip": MAC, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"]["ip"] == MAC


def test_recovery_tier_drops_windows_ip_mac(tmp_path):
    tier2 = {"mac": {"ip": WIN2, "models": MAC_MODELS}, "win": {"ip": "localhost", "models": ["m"]}}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None
    assert D.saved["tier"] == 2


def test_recovery_tier_with_only_windows_mac_fails(tmp_path):
    tier2 = {"mac": {"ip": WIN2, "models": MAC_MODELS}, "win": None}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 1


# ── --status ─────────────────────────────────────────────────────────────────

def test_status_tolerates_win_peers_list(tmp_path, capsys):
    D = _load_discover()
    state = {
        "recovery_tier": 1,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "endpoints": {
            "mac": {"ip": MAC, "port": 1234, "reachable": True},
            "win": {"ip": LOCAL, "port": 1234, "reachable": True},
            "win_peers": [{"ip": WIN2, "port": 1234, "reachable": True}],
        },
        "models": {"mac": ["a"], "win": ["b"], "win_peers": []},
    }
    D._load_json = lambda path: state
    D.RECOVERY_SOURCE_TXT = tmp_path / "missing.txt"
    D._cmd_status()
    out = capsys.readouterr().out
    assert "mac:" in out and "win:" in out and "win_peers: 1 peer(s)" in out


# ── F13: load PT hardware_policy by path ─────────────────────────────────────

def _fake_pt_root(tmp_path: Path) -> Path:
    utils = tmp_path / "pt" / "src" / "utils"
    utils.mkdir(parents=True)
    (utils / "hardware_policy.py").write_text(
        "MARKER = 'from-pt'\n"
        "def filter_models_for_platform(models, platform, policy):\n"
        "    return [m for m in models if m != 'dropped-by-pt']\n",
        encoding="utf-8",
    )
    return tmp_path / "pt"


def test_import_pt_hardware_policy_loads_by_path(tmp_path, monkeypatch):
    root = _fake_pt_root(tmp_path)
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(root))
    D = _load_discover(stub_policy=False)
    # orama's own utils package must not have shadowed PT's module
    assert D.filter_models_for_platform(["a", "dropped-by-pt"], "win", {}) == ["a"]
    mod = D._import_pt_hardware_policy()
    assert mod.MARKER == "from-pt"
    assert sys.modules["_pt_hardware_policy"] is mod


def test_import_pt_hardware_policy_missing_file_falls_back(tmp_path, monkeypatch):
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path / "nothing"))
    D = _load_discover(stub_policy=False)
    assert D.filter_models_for_platform is D._filter_models_for_platform_local
    with pytest.raises(ImportError):
        D._import_pt_hardware_policy()


def test_broken_pt_policy_module_falls_back(tmp_path, monkeypatch):
    root = _fake_pt_root(tmp_path)
    (root / "src" / "utils" / "hardware_policy.py").write_text("raise RuntimeError('boom')\n")
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(root))
    D = _load_discover(stub_policy=False)
    assert D.filter_models_for_platform is D._filter_models_for_platform_local
    assert "_pt_hardware_policy" not in sys.modules


# ── patch_openclaw_json on a Windows host ────────────────────────────────────

OLD_MAC_URL = "http://mac.invalid:1234/v1"


def _patch_host(tmp_path, monkeypatch):
    oc = tmp_path / "openclaw.json"
    oc.write_text(json.dumps({
        "models": {"providers": {"lmstudio-mac": {"baseUrl": OLD_MAC_URL, "models": []}}},
        "meta": {},
    }))
    for key in ("WIN_PEER_IPS", "WIN_3080_IP", "WIN_5080_IP"):
        monkeypatch.delenv(key, raising=False)
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True
    D.OPENCLAW_JSON = oc
    D._local_ipv4s = lambda: {LOCAL}
    D.load_policy = lambda policy_path=None: {"mac_only": [], "windows_only": [], "shared": []}
    return D, oc


def test_patch_openclaw_skips_local_box_as_mac_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    for ip in ("localhost", LOCAL):
        D.patch_openclaw_json({"mac": {"ip": ip, "models": MAC_MODELS}, "win": None})
        url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
        assert url == OLD_MAC_URL


def test_patch_openclaw_uses_discovered_mac_ip_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.patch_openclaw_json({"mac": {"ip": MAC, "models": MAC_MODELS}, "win": None})
    prov = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]
    assert prov["baseUrl"] == f"http://{MAC}:1234/v1"
    assert [m["id"] for m in prov["models"]] == ["qwen3.5-9b-mlx"]


def test_patch_openclaw_mac_host_still_uses_localhost(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.RUNNING_ON_WINDOWS = False
    D.patch_openclaw_json({"mac": {"ip": MAC, "models": MAC_MODELS}, "win": None})
    url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
    assert "localhost" in url
