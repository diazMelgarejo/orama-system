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
    """Load discover."""
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
        """Fake probe."""
        D.probe_calls.append(url)
        if "localhost" in url:
            return ["qwen3.5-27b-distilled"] if url.endswith(":1234") else None
        return probes.get(url)

    D.probe_models = fake_probe
    D.scan_calls = []

    async def fake_scan(subnet, port, exclude):
        """Fake scan."""
        D.scan_calls.append((subnet, set(exclude)))
        return [ip for ip in (scan_hits or []) if ip not in exclude]

    D.scan_subnet_async = fake_scan
    return D


# ── F12: Mac vs Windows identification ───────────────────────────────────────

def test_win2_on_1234_is_never_labelled_mac():
    """Check that win2 on 1234 is never labelled mac."""
    D = _windows_host(
        probes={f"http://{WIN2}:1234": WIN_MODELS},
        scan_hits=[WIN2],
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [WIN2]
    assert result["win"] == {"ip": "localhost", "models": ["qwen3.5-27b-distilled"]}


def test_scan_hit_without_any_evidence_is_not_mac():
    """Check that scan hit without any evidence is not mac."""
    D = _windows_host(
        probes={f"http://{WIN2}:1234": ["some-unknown-model"]},
        scan_hits=[WIN2],
    )
    assert D.discover_endpoints()["mac"] is None


def test_scan_hit_with_mac_evidence_is_mac_and_known_windows_ips_not_scanned():
    """Check that scan hit with mac evidence is mac and known windows ips not scanned."""
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
    """Check that explicit mac ip in windows set is refused."""
    D = _windows_host(
        env={"MAC_IP": WIN2, "WIN_PEER_IPS": WIN2},
        probes={f"http://{WIN2}:1234": MAC_MODELS},  # even with Mac-looking models
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert "known Windows address" in capsys.readouterr().err


def test_explicit_mac_ip_equal_to_local_ip_is_refused():
    """Check that explicit mac ip equal to local ip is refused."""
    D = _windows_host(env={"MAC_IP": LOCAL}, probes={f"http://{LOCAL}:1234": MAC_MODELS})
    assert D.discover_endpoints()["mac"] is None


def test_explicit_mac_ip_accepted_without_evidence():
    """Check that explicit mac ip accepted without evidence."""
    D = _windows_host(env={"MAC_IP": MAC}, probes={f"http://{MAC}:1234": ["plain-model"]})
    assert D.discover_endpoints()["mac"] == {"ip": MAC, "models": ["plain-model"]}


def test_explicit_mac_ip_with_windows_evidence_goes_to_win_peers():
    """Check that explicit mac ip with windows evidence goes to win peers."""
    D = _windows_host(env={"MAC_IP": MAC}, probes={f"http://{MAC}:1234": WIN_MODELS})
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [MAC]


def test_ollama_answer_adds_optional_key_and_counts_as_evidence():
    """Check that ollama answer adds optional key and counts as evidence."""
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
    """Check that cached mac in windows set is not probed or used."""
    cache = {"endpoints": {"mac": {"ip": WIN2}, "win": {"ip": "localhost"}},
             "models": {"mac": MAC_MODELS, "win": []}}
    D = _windows_host(env={"WIN_PEER_IPS": WIN2},
                      probes={f"http://{WIN2}:1234": MAC_MODELS}, cache=cache)
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert not any(url == f"http://{WIN2}:11434" for url in D.probe_calls)


def test_cached_mac_needs_mac_evidence():
    """Check that cached mac needs mac evidence."""
    cache = {"endpoints": {"mac": {"ip": MAC}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_host(probes={f"http://{MAC}:1234": ["plain-model"]}, cache=cache)
    assert D.discover_endpoints()["mac"] is None


def test_cached_mac_with_tagged_mac_only_model_is_accepted():
    """Check that cached mac with tagged mac only model is accepted."""
    cache = {"endpoints": {"mac": {"ip": MAC}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_host(probes={f"http://{MAC}:11434": ["bge-m3:latest"]}, cache=cache)
    assert D.discover_endpoints()["mac"]["ip"] == MAC


# ── evidence helpers ─────────────────────────────────────────────────────────

def test_mac_evidence_is_tag_insensitive():
    """Check that mac evidence is tag insensitive."""
    D = _load_discover()
    assert D._has_mac_evidence(["bge-m3:latest"], {"bge-m3"})
    assert D._has_mac_evidence(["BGE-M3"], {"bge-m3"})
    assert D._has_mac_evidence(["qwen3.5:9b-nvfp4"], {"qwen3.5:9b-nvfp4"})
    assert not D._has_mac_evidence(["qwen3.5:27b"], {"qwen3.5:9b-nvfp4"})


@pytest.mark.parametrize("name", ["foo-mlx", "mlx-community/bar", "baz-4bit", "baz-8bit"])
def test_mac_evidence_mlx_markers(name):
    """Check that mac evidence mlx markers."""
    D = _load_discover()
    assert D._has_mac_evidence([name], set())


def test_win_evidence_markers():
    """Check that win evidence markers."""
    D = _load_discover()
    assert D._has_win_evidence(["Foo-GGUF"], set())
    assert D._has_win_evidence(["gemma-4-26b:latest"], {"gemma-4-26b"})
    assert not D._has_win_evidence(["foo-mlx"], set())


# ── win_peers on a Windows host ──────────────────────────────────────────────

def test_win_peers_from_env_minus_local():
    """Check that win peers from env minus local."""
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
    """Check that mac path win peers ignores node ips."""
    D = _load_discover()
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": {"WIN_PEER_IPS": EXTRA_A, "WIN_5080_IP": EXTRA_B}.get(key, default)
    D.probe_models = lambda url: WIN_MODELS
    assert [p["ip"] for p in D.probe_extra_win_peers(set())] == [EXTRA_A]


# ── run_discovery back-fill / recovery tiers ─────────────────────────────────

def _run_discovery_host(tmp_path, last, tier2=None, live=None, env=None):
    """Run discovery host."""
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
        """Helper: NoLock."""
        def __enter__(self):
            """Enter the context manager."""
            return self

        def __exit__(self, *a):
            """Exit the context manager."""
            return False

    D._Lock = _NoLock
    D.saved = {}
    D.save_discovery_state = lambda endpoints, tier=1: D.saved.update(endpoints=endpoints, tier=tier)
    return D


def test_backfill_does_not_preserve_windows_ip_as_mac(tmp_path):
    """Check that backfill does not preserve windows ip as mac."""
    last = {
        "endpoints": {"mac": {"ip": WIN2, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None


def test_backfill_still_preserves_a_real_mac(tmp_path):
    """Check that backfill still preserves a real mac."""
    last = {
        "endpoints": {"mac": {"ip": MAC, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"]["ip"] == MAC


def test_recovery_tier_drops_windows_ip_mac(tmp_path):
    """Check that recovery tier drops windows ip mac."""
    tier2 = {"mac": {"ip": WIN2, "models": MAC_MODELS}, "win": {"ip": "localhost", "models": ["m"]}}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None
    assert D.saved["tier"] == 2


def test_recovery_tier_with_only_windows_mac_fails(tmp_path):
    """Check that recovery tier with only windows mac fails."""
    tier2 = {"mac": {"ip": WIN2, "models": MAC_MODELS}, "win": None}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 1


# ── --status ─────────────────────────────────────────────────────────────────

def test_status_tolerates_win_peers_list(tmp_path, capsys):
    """Check that status tolerates win peers list."""
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
    """Fake pt root."""
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
    """Check that import pt hardware policy loads by path."""
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
    """Check that import pt hardware policy missing file falls back."""
    monkeypatch.delenv("PERPETUATOOLSROOT", raising=False)
    monkeypatch.delenv("PERPETUA_TOOLS_PATH", raising=False)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(tmp_path / "nothing"))
    D = _load_discover(stub_policy=False)
    assert D.filter_models_for_platform is D._filter_models_for_platform_local
    with pytest.raises(ImportError):
        D._import_pt_hardware_policy()


def test_broken_pt_policy_module_falls_back(tmp_path, monkeypatch):
    """Check that broken pt policy module falls back."""
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
    """Patch host."""
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
    """Check that patch openclaw skips local box as mac on windows."""
    D, oc = _patch_host(tmp_path, monkeypatch)
    for ip in ("localhost", LOCAL):
        D.patch_openclaw_json({"mac": {"ip": ip, "models": MAC_MODELS}, "win": None})
        url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
        assert url == OLD_MAC_URL


def test_patch_openclaw_uses_discovered_mac_ip_on_windows(tmp_path, monkeypatch):
    """Check that patch openclaw uses discovered mac ip on windows."""
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.patch_openclaw_json({"mac": {"ip": MAC, "models": MAC_MODELS}, "win": None})
    prov = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]
    assert prov["baseUrl"] == f"http://{MAC}:1234/v1"
    assert [m["id"] for m in prov["models"]] == ["qwen3.5-9b-mlx"]


def test_patch_openclaw_mac_host_still_uses_localhost(tmp_path, monkeypatch):
    """Check that patch openclaw mac host still uses localhost."""
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.RUNNING_ON_WINDOWS = False
    D.patch_openclaw_json({"mac": {"ip": MAC, "models": MAC_MODELS}, "win": None})
    url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
    assert "localhost" in url


# ── LM Link ambiguity, same-run Windows evidence, stale lmstudio-mac ─────────

LMLINK_MODELS = ["qwen3.5-9b-mlx", "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"]


def _lmlink_host(env=None, cache=None, scan_hits=None):
    D = _windows_host(
        env=env,
        probes={f"http://{MAC}:1234": LMLINK_MODELS},
        cache=cache,
        scan_hits=scan_hits,
    )
    D.load_policy = lambda policy_path=None: {
        "mac_only": [], "windows_only": ["qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2"],
    }
    return D


def test_explicit_mac_ip_with_lm_link_models_is_still_the_mac():
    D = _lmlink_host(env={"MAC_IP": MAC})
    result = D.discover_endpoints()
    assert result["mac"]["ip"] == MAC
    assert result["win_peers"] == []


def test_scan_hit_with_both_evidence_is_the_mac():
    # LM Link mirrors the peer's models: Mac evidence wins over Windows ids.
    D = _lmlink_host(scan_hits=[MAC])
    result = D.discover_endpoints()
    assert result["mac"]["ip"] == MAC
    assert result["win_peers"] == []


def test_cached_mac_with_both_evidence_is_kept_and_probed_once(capsys):
    cache = {"endpoints": {"mac": {"ip": MAC}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _lmlink_host(cache=cache)
    result = D.discover_endpoints()
    assert result["mac"]["ip"] == MAC
    assert result["win_peers"] == []
    assert D.probe_calls.count(f"http://{MAC}:1234") == 1


def test_cache_probed_address_is_excluded_from_scan():
    cache = {"endpoints": {"mac": {"ip": WIN2}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_host(probes={f"http://{WIN2}:1234": WIN_MODELS}, cache=cache, scan_hits=[WIN2])
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [WIN2]
    assert all(WIN2 in excl for _, excl in D.scan_calls)
    assert D.probe_calls.count(f"http://{WIN2}:1234") == 1


def test_known_windows_address_with_mac_evidence_is_never_the_mac():
    D = _lmlink_host(env={"WIN_PEER_IPS": MAC}, scan_hits=[MAC])
    assert D.discover_endpoints()["mac"] is None


def test_run_discovery_keeps_cached_lm_link_mac_when_mac_ip_unset(tmp_path):
    last = {
        "endpoints": {"mac": {"ip": MAC, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": LMLINK_MODELS, "win": ["m"]},
    }
    D = _lmlink_host(cache=last, env={})
    live = D.discover_endpoints()
    assert live["mac"]["ip"] == MAC
    D2 = _run_discovery_host(tmp_path, last, live=live, env={})
    assert D2.run_discovery() == 0
    assert D2.saved["endpoints"]["mac"]["ip"] == MAC


def test_backfill_preserves_last_good_mac_not_known_windows(tmp_path):
    last = {
        "endpoints": {"mac": {"ip": MAC, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": LMLINK_MODELS, "win": ["m"]},
    }
    live = {"mac": None, "win": {"ip": "localhost", "models": ["m"]}, "win_peers": []}
    D = _run_discovery_host(tmp_path, last, live=live, env={})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"]["ip"] == MAC


def test_backfill_ignores_stale_mac_that_is_a_win_peer_this_run(tmp_path):
    # WIN_PEER_IPS unset: Win-2 is only known as Windows from this run's probes.
    last = {
        "endpoints": {"mac": {"ip": WIN2, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": WIN_MODELS, "win": ["m"]},
    }
    live = {"mac": None, "win": {"ip": "localhost", "models": ["m"]},
            "win_peers": [{"ip": WIN2, "models": WIN_MODELS}]}
    D = _run_discovery_host(tmp_path, last, live=live, env={})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None
    assert [p["ip"] for p in D.saved["endpoints"]["win_peers"]] == [WIN2]


def test_recovery_tier_ignores_stale_mac_seen_as_win_peer_this_run(tmp_path):
    tier2 = {"mac": {"ip": WIN2, "models": WIN_MODELS}, "win": {"ip": "localhost", "models": ["m"]}}
    live = {"mac": None, "win": None, "win_peers": [{"ip": WIN2, "models": WIN_MODELS}]}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live=live, env={})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None
    assert D.saved["tier"] == 2


def test_patch_openclaw_clears_stale_localhost_lmstudio_mac_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    cfg = json.loads(oc.read_text())
    cfg["models"]["providers"]["lmstudio-mac"]["baseUrl"] = "http://localhost:1234/v1"
    oc.write_text(json.dumps(cfg))
    D.patch_openclaw_json({"mac": None, "win": None})
    assert "lmstudio-mac" not in json.loads(oc.read_text())["models"]["providers"]


def test_patch_openclaw_clears_known_windows_lmstudio_mac_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    cfg = json.loads(oc.read_text())
    cfg["models"]["providers"]["lmstudio-mac"]["baseUrl"] = f"http://{LOCAL}:1234/v1"
    oc.write_text(json.dumps(cfg))
    D.patch_openclaw_json({"mac": None, "win": None})
    assert "lmstudio-mac" not in json.loads(oc.read_text())["models"]["providers"]


def test_patch_openclaw_keeps_remote_lmstudio_mac_when_mac_down_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.patch_openclaw_json({"mac": None, "win": None})
    url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
    assert url == OLD_MAC_URL


def test_write_env_never_falls_back_to_localhost_mac_on_windows(tmp_path):
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True
    D._local_ipv4s = lambda: {LOCAL}
    D._load_json = lambda path: None
    D.filter_endpoints_for_policy = lambda endpoints, policy=None: endpoints
    D.write_env_lmstudio({"mac": None, "win": None}, {"r": str(tmp_path)})
    assert "LM_STUDIO_MAC_ENDPOINT=\n" in (tmp_path / ".env.lmstudio").read_text()
    D.write_env_lmstudio({"mac": {"ip": MAC, "models": []}, "win": None}, {"r": str(tmp_path)})
    assert f"LM_STUDIO_MAC_ENDPOINT=http://{MAC}:1234\n" in (tmp_path / ".env.lmstudio").read_text()


def _real_patch(D):
    """Return the module's real patch_openclaw_json (the harness stubs it)."""
    return _bind(D, "patch_openclaw_json")


def _real_env(D):
    """Return the module's real write_env_lmstudio."""
    return _bind(D, "write_env_lmstudio")


def _bind(D, name):
    """Rebuild a function from the pristine module source bound to D's globals."""
    import types
    pristine = _load_discover()
    fn = getattr(pristine, name)
    import os
    D.os.replace = os.replace  # the harness mocks D.os; the real writers need replace()
    return types.FunctionType(fn.__code__, D.__dict__, name, fn.__defaults__, fn.__closure__)


def test_no_change_path_repairs_stale_localhost_lmstudio_mac(tmp_path, monkeypatch):
    oc = tmp_path / "openclaw.json"
    oc.write_text(json.dumps({
        "models": {"providers": {"lmstudio-mac": {"baseUrl": "http://localhost:1234/v1", "models": []}}},
        "meta": {},
    }))
    env_dir = tmp_path / "repo"
    env_dir.mkdir()
    (env_dir / ".env.lmstudio").write_text("LM_STUDIO_MAC_ENDPOINT=http://localhost:1234\n")
    live = {"mac": {"ip": MAC, "models": MAC_MODELS}, "win": {"ip": "localhost", "models": ["m"]},
            "win_peers": []}
    D = _run_discovery_host(tmp_path, None, live=live, env={})
    first = D.compute_hash(D._endpoints_for_hash(live))
    state = {"hash": first, "timestamp": "2026-01-01T00:00:00+00:00", "recovery_tier": 1,
             "endpoints": {"mac": {"ip": MAC, "reachable": True},
                           "win": {"ip": "localhost", "reachable": True}},
             "models": {"mac": MAC_MODELS, "win": ["m"]}}
    D._load_json = lambda path: json.loads(oc.read_text()) if path == oc else state
    D.OPENCLAW_JSON = oc
    D.LAST_DISCOVERY_JSON = tmp_path / "last.json"
    D.DISCOVERY_JSON = tmp_path / "disc.json"
    D.get_repo_paths = lambda: {"r": str(env_dir)}
    D.patch_openclaw_json = _real_patch(D)
    D.write_env_lmstudio = _real_env(D)
    assert D.run_discovery() == 0
    url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
    assert url == f"http://{MAC}:1234/v1"
    assert f"LM_STUDIO_MAC_ENDPOINT=http://{MAC}:1234\n" in (env_dir / ".env.lmstudio").read_text()
    # Second run: nothing stale, so nothing is rewritten.
    before = oc.read_text()
    assert D.run_discovery() == 0
    assert oc.read_text() == before


def test_no_change_path_removes_localhost_lmstudio_mac_when_mac_down(tmp_path):
    oc = tmp_path / "openclaw.json"
    oc.write_text(json.dumps({
        "models": {"providers": {"lmstudio-mac": {"baseUrl": "http://localhost:1234/v1", "models": []}}},
        "meta": {},
    }))
    live = {"mac": None, "win": {"ip": "localhost", "models": ["m"]}, "win_peers": []}
    D = _run_discovery_host(tmp_path, None, live=live, env={})
    state = {"hash": D.compute_hash(D._endpoints_for_hash(live)), "timestamp": "2026-01-01T00:00:00+00:00",
             "recovery_tier": 1,
             "endpoints": {"mac": {"ip": "", "reachable": False},
                           "win": {"ip": "localhost", "reachable": True}},
             "models": {"mac": [], "win": ["m"]}}
    D._load_json = lambda path: json.loads(oc.read_text()) if path == oc else state
    D.OPENCLAW_JSON = oc
    D.LAST_DISCOVERY_JSON = tmp_path / "last.json"
    D.DISCOVERY_JSON = tmp_path / "disc.json"
    D.patch_openclaw_json = _real_patch(D)
    assert D.run_discovery() == 0
    assert "lmstudio-mac" not in json.loads(oc.read_text())["models"]["providers"]
