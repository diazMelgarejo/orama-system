"""Tests for the Windows platform-aware changes in scripts/discover.py.

PR: feat(hermes-harness) — Tier A onboarding phases + Windows gstack brain-sync shim

The key change: discover_endpoints() now uses RUNNING_ON_WINDOWS to flip the
role of localhost:

  • On Mac/Linux → localhost is the Mac box, LAN scan finds Windows.
  • On Windows   → localhost is the Windows box, $MAC_IP env var (or cache)
                   finds the Mac.

This also fixes the bug where `windows_only` models were being filtered OUT
when running the discovery script from a Windows host (because the old code
always assigned localhost to `result["mac"]` and then applied the mac-platform
filter to it — stripping every `windows_only` model).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
DISCOVER_SCRIPT = ROOT / "scripts" / "discover.py"


def _load_discover(stub_policy: bool = True):
    spec = importlib.util.spec_from_file_location("discover_win_test", DISCOVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if stub_policy:
        stub = MagicMock()
        with patch.dict(sys.modules, {"utils.hardware_policy": stub}):
            spec.loader.exec_module(module)
        module.filter_models_for_platform = module._filter_models_for_platform_local
    else:
        spec.loader.exec_module(module)
    return module


# ── RUNNING_ON_WINDOWS flag ───────────────────────────────────────────────────

def test_running_on_windows_is_bool():
    D = _load_discover()
    assert isinstance(D.RUNNING_ON_WINDOWS, bool)


def test_running_on_windows_reflects_sys_platform():
    D = _load_discover()
    expected = sys.platform == "win32"
    assert D.RUNNING_ON_WINDOWS == expected


# ── discover_endpoints() on Windows ──────────────────────────────────────────

def _discover_as_windows(monkeypatch_or_none, win_models, mac_models=None, mac_ip_env=""):
    """Helper: load discover.py and simulate a Windows host.

    Patches RUNNING_ON_WINDOWS=True, probe_models to return the given
    model lists, and sets the MAC_IP env var.
    """
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True

    call_log = []

    def fake_probe(base_url):
        call_log.append(base_url)
        if "localhost" in base_url:
            return win_models
        if mac_ip_env and mac_ip_env in base_url:
            return mac_models
        return None

    D.probe_models = fake_probe

    # No last-discovery cache by default
    D._load_json = lambda path: None

    import os
    orig_getenv = os.getenv

    def patched_getenv(key, default=""):
        if key == "MAC_IP":
            return mac_ip_env
        return orig_getenv(key, default)

    D.os = MagicMock()
    D.os.getenv = patched_getenv

    result = D.discover_endpoints()
    return result, call_log, D


def test_windows_localhost_assigned_to_win(tmp_path):
    """On Windows, localhost LM Studio models go into result['win']."""
    win_models = ["qwen3.5-27b-distilled", "gemma-4-26b"]
    result, _, _ = _discover_as_windows(None, win_models=win_models)
    assert result["win"] is not None
    assert result["win"]["ip"] == "localhost"
    assert result["win"]["models"] == win_models


def test_windows_mac_is_none_without_mac_ip(tmp_path):
    """On Windows, without $MAC_IP set and no cache, result['mac'] must be None."""
    win_models = ["qwen3.5-27b-distilled"]
    result, _, _ = _discover_as_windows(None, win_models=win_models, mac_ip_env="")
    assert result["mac"] is None


def test_windows_mac_probed_from_mac_ip_env(tmp_path):
    """On Windows, if $MAC_IP is set and reachable, result['mac'] is populated."""
    win_models = ["qwen3.5-27b-distilled"]
    mac_models = ["qwen3.5-9b-mlx"]
    result, call_log, _ = _discover_as_windows(
        None,
        win_models=win_models,
        mac_models=mac_models,
        mac_ip_env="192.0.2.103",
    )
    assert result["mac"] is not None
    assert result["mac"]["ip"] == "192.0.2.103"
    assert result["mac"]["models"] == mac_models
    # Mac IP probe must have been called with the env var IP
    assert any("192.0.2.103" in url for url in call_log)


def test_windows_mac_not_set_when_mac_ip_unreachable(tmp_path):
    """On Windows, $MAC_IP unreachable → result['mac'] stays None."""
    # mac_models=None means probe_models returns None for that IP
    result, _, _ = _discover_as_windows(
        None,
        win_models=["qwen3.5-27b-distilled"],
        mac_models=None,
        mac_ip_env="192.0.2.103",
    )
    assert result["mac"] is None


def test_windows_localhost_not_assigned_to_mac(tmp_path):
    """On Windows, localhost must NOT appear in result['mac']."""
    win_models = ["qwen3.5-27b-distilled", "gemma-4-26b"]
    result, _, _ = _discover_as_windows(None, win_models=win_models, mac_ip_env="")
    if result["mac"]:
        assert result["mac"].get("ip") not in ("localhost", "127.0.0.1")


def test_windows_win_entry_absent_when_lm_studio_unreachable():
    """On Windows, if localhost LM Studio is down, result['win'] is None."""
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True
    D.probe_models = lambda url: None  # everything unreachable
    D._load_json = lambda path: None

    import os
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": ""

    result = D.discover_endpoints()
    assert result["win"] is None


# ── Windows policy filter: windows_only models are NOT filtered on Windows ────

POLICY_WIN_MODELS = {
    "windows_only": ["qwen3.5-27b-distilled", "gemma-4-26b"],
    # Ollama mac_only models must not appear on win platform filter
    "mac_only": ["qwen3.5:9b-nvfp4", "bge-m3", "qwen3.5-9b-mlx"],
    "shared": [],
}


def test_win_platform_does_not_filter_windows_only_models():
    """filter_models_for_platform('win') must pass through windows_only models."""
    D = _load_discover()
    models = ["qwen3.5-27b-distilled", "gemma-4-26b", "text-embedding-nomic"]
    result = D.filter_models_for_platform(models, "win", POLICY_WIN_MODELS)
    assert "qwen3.5-27b-distilled" in result
    assert "gemma-4-26b" in result


def test_win_platform_filters_mac_only_models():
    """filter_models_for_platform('win') must strip mac_only models."""
    D = _load_discover()
    models = ["qwen3.5-27b-distilled", "qwen3.5-9b-mlx", "gemma-4-26b"]
    result = D.filter_models_for_platform(models, "win", POLICY_WIN_MODELS)
    assert "qwen3.5-9b-mlx" not in result
    assert "qwen3.5-27b-distilled" in result


def test_mac_platform_filters_windows_only_models():
    """filter_models_for_platform('mac') must strip windows_only models."""
    D = _load_discover()
    models = ["qwen3.5-27b-distilled", "qwen3.5-9b-mlx", "gemma-4-26b"]
    result = D.filter_models_for_platform(models, "mac", POLICY_WIN_MODELS)
    assert "qwen3.5-27b-distilled" not in result
    assert "gemma-4-26b" not in result
    assert "qwen3.5-9b-mlx" in result


# ── Regression: the old Mac-centric bug ──────────────────────────────────────

def test_regression_windows_only_models_not_removed_on_windows_host():
    """
    Regression guard for the bug fixed in this PR:
    Previously, discover_endpoints() ALWAYS assigned localhost to result['mac']
    and applied the Mac platform filter to it — which stripped ALL windows_only
    models when running on a Windows host, leaving only the embedding model.

    After the fix, localhost on Windows → result['win'], and the win platform
    filter is applied instead, keeping windows_only models.
    """
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True

    all_models = [
        "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2",  # windows_only
        "gemma-4-26b-a4b-it",                                   # windows_only
        "text-embedding-qwen3-embedding-8b-i1-gguf-q6-k",       # windows_only embedding
    ]

    D.probe_models = lambda url: all_models if "localhost" in url else None
    D._load_json = lambda path: None

    import os
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": ""

    result = D.discover_endpoints()

    assert result["win"] is not None, "Win entry must be present"
    assert result["mac"] is None, "Mac entry must be absent without $MAC_IP"

    # The win entry must contain the windows_only models — they must NOT be filtered
    win_models = result["win"]["models"]
    assert "qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2" in win_models, (
        "windows_only model was incorrectly stripped from win result on Windows host"
    )
    assert "gemma-4-26b-a4b-it" in win_models, (
        "windows_only model was incorrectly stripped from win result on Windows host"
    )


# ── Windows: cached mac IP fallback ──────────────────────────────────────────

def test_windows_falls_back_to_cached_mac_ip():
    """On Windows without $MAC_IP, if last_discovery has a mac IP, probe it."""
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True

    cached_mac_ip = "192.0.2.103"
    cached_state = {
        "endpoints": {"mac": {"ip": cached_mac_ip}, "win": {"ip": "localhost"}},
        "models": {"mac": ["qwen3.5-9b-mlx"], "win": ["qwen3.5-27b"]},
    }

    probed_urls = []

    def fake_probe(base_url):
        probed_urls.append(base_url)
        if "localhost" in base_url:
            return ["qwen3.5-27b"]
        if cached_mac_ip in base_url:
            return ["qwen3.5-9b-mlx"]
        return None

    D.probe_models = fake_probe
    D._load_json = lambda path: cached_state

    import os
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": ""  # $MAC_IP not set

    result = D.discover_endpoints()

    # Must have probed the cached mac IP
    assert any(cached_mac_ip in url for url in probed_urls), (
        "Expected probe of cached mac IP when $MAC_IP is not set"
    )
    assert result["mac"] is not None
    assert result["mac"]["ip"] == cached_mac_ip


def test_windows_skips_loopback_as_cached_mac_ip():
    """localhost/127.0.0.1 from cache must not be re-probed as the Mac IP on Windows."""
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True

    cached_state = {
        "endpoints": {"mac": {"ip": "localhost"}, "win": {"ip": "localhost"}},
        "models": {"mac": [], "win": []},
    }

    probed_urls = []

    def fake_probe(base_url):
        probed_urls.append(base_url)
        if "localhost" in base_url:
            return ["qwen3.5-27b"]
        return None

    D.probe_models = fake_probe
    D._load_json = lambda path: cached_state

    import os
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": ""

    result = D.discover_endpoints()

    # Must NOT have probed localhost as the Mac address
    # (localhost:1234 probe is only for Win; a second "mac" probe of localhost is wrong)
    assert result["mac"] is None, (
        "Cached mac IP of 'localhost' must not result in a Mac entry on Windows host"
    )


def test_windows_subnet_scan_finds_mac_when_cache_is_loopback():
    """On Windows, subnet scan must find Mac when cache only has localhost."""
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True

    cached_state = {
        "endpoints": {"mac": {"ip": "localhost"}, "win": {"ip": "localhost"}},
        "models": {"mac": [], "win": []},
    }

    probed_urls = []

    def fake_probe(base_url):
        probed_urls.append(base_url)
        if "localhost" in base_url:
            return ["qwen3.5-27b"]
        if "192.0.2.102" in base_url:
            return ["qwen3.5-9b-mlx"]
        return None

    D.probe_models = fake_probe
    D._load_json = lambda path: cached_state
    D._win_lan_ip = lambda: "192.0.2.100"
    # Must be mocked: the real implementation enumerates this host's actual
    # network interfaces, so on a machine with real LAN subnets this test
    # would scan the host's live subnet instead of exercising the intended
    # fallback-to-SUBNET-constant path the assertion below checks.
    D.get_local_subnets = lambda: []

    async def fake_scan(subnet, port, exclude):
        assert subnet == "192.0.2"
        return ["192.0.2.102"]

    D.scan_subnet_async = fake_scan

    import os
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": ""

    result = D.discover_endpoints()

    assert result["mac"] is not None
    assert result["mac"]["ip"] == "192.0.2.102"
    assert any("192.0.2.102" in url for url in probed_urls)


# ── Mac/Linux path unchanged ──────────────────────────────────────────────────

def test_mac_host_localhost_assigned_to_mac():
    """On Mac/Linux (RUNNING_ON_WINDOWS=False), localhost → result['mac'] (unchanged)."""
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = False

    probed = []

    def fake_probe(base_url):
        probed.append(base_url)
        if "localhost" in base_url:
            return ["qwen3.5-9b-mlx"]
        return None

    D.probe_models = fake_probe
    D._mac_lan_ip = lambda: None
    D._load_json = lambda path: None

    async def _empty_scan(*_args, **_kwargs):
        return []

    D.scan_subnet_async = _empty_scan

    result = D.discover_endpoints()

    assert result["mac"] is not None
    assert result["mac"]["ip"] == "localhost"


# ── filter_endpoints_for_policy on Windows endpoint data ──────────────────────

def test_filter_endpoints_for_policy_win_entry():
    """filter_endpoints_for_policy must apply 'win' filter to result['win']."""
    D = _load_discover()
    endpoints = {
        "mac": None,
        "win": {
            "ip": "localhost",
            "models": ["qwen3.5-27b-distilled", "qwen3.5-9b-mlx"],
        },
    }
    policy = {
        "windows_only": ["qwen3.5-27b-distilled"],
        # Ollama mac_only models must not appear on win platform filter
    "mac_only": ["qwen3.5:9b-nvfp4", "bge-m3", "qwen3.5-9b-mlx"],
        "shared": [],
    }
    filtered = D.filter_endpoints_for_policy(endpoints, policy)
    win_models = filtered["win"]["models"]
    assert "qwen3.5-27b-distilled" in win_models   # windows_only → allowed on win
    assert "qwen3.5-9b-mlx" not in win_models       # mac_only → forbidden on win


def test_endpoints_for_hash_resolves_win_lan_without_mutating_runtime():
    """Hash snapshot uses LAN IP; runtime endpoints keep localhost on Windows."""
    D = _load_discover()
    endpoints = {
        "mac": None,
        "win": {"ip": "localhost", "models": ["qwen3.5-27b"]},
    }
    with patch.object(D, "RUNNING_ON_WINDOWS", True), patch.object(
        D.os, "getenv", side_effect=lambda k, d="": "192.0.2.103" if k == "WIN_IP" else d
    ):
        hashed = D._endpoints_for_hash(endpoints)
    assert endpoints["win"]["ip"] == "localhost"
    assert hashed["win"]["ip"] == "192.0.2.103"


# ── PR 4: Windows Peer Discovery Hardening & Disambiguation (F12/F13) ─────────
# All network addresses are TEST-NET-1 (RFC 5737 192.0.2.0/24).
# Network scans and socket probes are strictly mocked.

LOCAL_NET_IP = "192.0.2.10"      # this Windows host
WIN2_NET_IP  = "192.0.2.20"      # a second Windows LM Studio box
MAC_NET_IP   = "192.0.2.50"      # the remote Mac
EXTRA_A_NET  = "192.0.2.21"
EXTRA_B_NET  = "192.0.2.22"

PEER_MAC_MODELS = ["qwen3.5-9b-mlx", "text-embedding-nomic"]
PEER_WIN_MODELS = ["qwen3.5-27b-q4_k_m-gguf", "gemma-4-26b-gguf"]


def _windows_peer_host(env=None, probes=None, cache=None, scan_hits=None, local=(LOCAL_NET_IP,)):
    """A Windows-host discover module with probes, env, cache and scan faked."""
    env = dict(env or {})
    probes = dict(probes or {})
    D = _load_discover()
    D.RUNNING_ON_WINDOWS = True
    D._local_ipv4s = lambda: set(local)
    D._win_lan_ip = lambda: LOCAL_NET_IP
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


def test_win2_on_1234_is_never_labelled_mac():
    D = _windows_peer_host(
        probes={f"http://{WIN2_NET_IP}:1234": PEER_WIN_MODELS},
        scan_hits=[WIN2_NET_IP],
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [WIN2_NET_IP]
    assert result["win"] == {"ip": "localhost", "models": ["qwen3.5-27b-distilled"]}


def test_scan_hit_without_any_evidence_is_not_mac():
    D = _windows_peer_host(
        probes={f"http://{WIN2_NET_IP}:1234": ["some-unknown-model"]},
        scan_hits=[WIN2_NET_IP],
    )
    assert D.discover_endpoints()["mac"] is None


def test_scan_hit_with_mac_evidence_is_mac_and_known_windows_ips_not_scanned():
    D = _windows_peer_host(
        env={"WIN_PEER_IPS": WIN2_NET_IP},
        probes={f"http://{MAC_NET_IP}:1234": PEER_MAC_MODELS},
        scan_hits=[WIN2_NET_IP, MAC_NET_IP],
    )
    result = D.discover_endpoints()
    assert result["mac"]["ip"] == MAC_NET_IP
    assert result["mac"]["models"] == PEER_MAC_MODELS
    exclude = D.scan_calls[0][1]
    assert {LOCAL_NET_IP, WIN2_NET_IP} <= exclude


def test_explicit_mac_ip_in_windows_set_is_refused(capsys):
    D = _windows_peer_host(
        env={"MAC_IP": WIN2_NET_IP, "WIN_PEER_IPS": WIN2_NET_IP},
        probes={f"http://{WIN2_NET_IP}:1234": PEER_MAC_MODELS},
    )
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert "known Windows address" in capsys.readouterr().err


def test_explicit_mac_ip_equal_to_local_ip_is_refused():
    D = _windows_peer_host(env={"MAC_IP": LOCAL_NET_IP}, probes={f"http://{LOCAL_NET_IP}:1234": PEER_MAC_MODELS})
    assert D.discover_endpoints()["mac"] is None


def test_explicit_mac_ip_equal_to_loopback_is_refused():
    for host in ("localhost",):
        D = _windows_peer_host(env={"MAC_IP": host}, probes={f"http://{host}:1234": PEER_MAC_MODELS})
        assert D.discover_endpoints()["mac"] is None


def test_explicit_mac_ip_accepted_without_evidence():
    D = _windows_peer_host(env={"MAC_IP": MAC_NET_IP}, probes={f"http://{MAC_NET_IP}:1234": ["plain-model"]})
    assert D.discover_endpoints()["mac"] == {"ip": MAC_NET_IP, "models": ["plain-model"]}


def test_explicit_mac_ip_with_windows_evidence_goes_to_win_peers():
    D = _windows_peer_host(env={"MAC_IP": MAC_NET_IP}, probes={f"http://{MAC_NET_IP}:1234": PEER_WIN_MODELS})
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert [p["ip"] for p in result["win_peers"]] == [MAC_NET_IP]


def test_ollama_answer_adds_optional_key_and_counts_as_evidence():
    D = _windows_peer_host(
        env={"MAC_IP": MAC_NET_IP},
        probes={
            f"http://{MAC_NET_IP}:1234": ["plain-model"],
            f"http://{MAC_NET_IP}:11434": ["bge-m3:latest", "qwen3.5:9b-nvfp4"],
        },
    )
    mac = D.discover_endpoints()["mac"]
    assert mac["ip"] == MAC_NET_IP and mac["models"] == ["plain-model"]
    assert mac["ollama"] == ["bge-m3:latest", "qwen3.5:9b-nvfp4"]


def test_cached_mac_in_windows_set_is_not_probed_or_used():
    cache = {"endpoints": {"mac": {"ip": WIN2_NET_IP}, "win": {"ip": "localhost"}},
             "models": {"mac": PEER_MAC_MODELS, "win": []}}
    D = _windows_peer_host(env={"WIN_PEER_IPS": WIN2_NET_IP},
                           probes={f"http://{WIN2_NET_IP}:1234": PEER_MAC_MODELS}, cache=cache)
    result = D.discover_endpoints()
    assert result["mac"] is None
    assert not any(url == f"http://{WIN2_NET_IP}:11434" for url in D.probe_calls)


def test_cached_mac_needs_mac_evidence():
    cache = {"endpoints": {"mac": {"ip": MAC_NET_IP}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_peer_host(probes={f"http://{MAC_NET_IP}:1234": ["plain-model"]}, cache=cache)
    assert D.discover_endpoints()["mac"] is None


def test_cached_mac_with_tagged_mac_only_model_is_accepted():
    cache = {"endpoints": {"mac": {"ip": MAC_NET_IP}, "win": {"ip": "localhost"}},
             "models": {"mac": [], "win": []}}
    D = _windows_peer_host(probes={f"http://{MAC_NET_IP}:11434": ["bge-m3:latest"]}, cache=cache)
    assert D.discover_endpoints()["mac"]["ip"] == MAC_NET_IP


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


def test_win_peers_from_env_minus_local():
    D = _windows_peer_host(
        env={"WIN_PEER_IPS": EXTRA_A_NET, "WIN_3080_IP": LOCAL_NET_IP, "WIN_5080_IP": EXTRA_B_NET},
        probes={
            f"http://{EXTRA_A_NET}:1234": PEER_WIN_MODELS,
            f"http://{EXTRA_B_NET}:1234": PEER_WIN_MODELS,
            f"http://{LOCAL_NET_IP}:1234": PEER_WIN_MODELS,
        },
    )
    result = D.discover_endpoints()
    assert sorted(p["ip"] for p in result["win_peers"]) == [EXTRA_A_NET, EXTRA_B_NET]
    assert not any(url == f"http://{LOCAL_NET_IP}:1234" for url in D.probe_calls)


def test_mac_path_win_peers_ignores_node_ips():
    D = _load_discover()
    D.os = MagicMock()
    D.os.getenv = lambda key, default="": {"WIN_PEER_IPS": EXTRA_A_NET, "WIN_5080_IP": EXTRA_B_NET}.get(key, default)
    D.probe_models = lambda url: PEER_WIN_MODELS
    assert [p["ip"] for p in D.probe_extra_win_peers(set())] == [EXTRA_A_NET]


def _run_discovery_host(tmp_path, last, tier2=None, live=None, env=None):
    D = _windows_peer_host(env=env or {"WIN_PEER_IPS": WIN2_NET_IP})
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
        "endpoints": {"mac": {"ip": WIN2_NET_IP, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": PEER_MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None


def test_backfill_does_not_preserve_loopback_as_mac(tmp_path):
    for loopback in ("localhost",):
        last = {
            "endpoints": {"mac": {"ip": loopback, "reachable": True},
                          "win": {"ip": "localhost", "reachable": True}},
            "models": {"mac": PEER_MAC_MODELS, "win": ["m"]},
        }
        D = _run_discovery_host(tmp_path, last)
        assert D.run_discovery() == 0
        assert D.saved["endpoints"]["mac"] is None


def test_backfill_still_preserves_a_real_mac(tmp_path):
    last = {
        "endpoints": {"mac": {"ip": MAC_NET_IP, "reachable": True},
                      "win": {"ip": "localhost", "reachable": True}},
        "models": {"mac": PEER_MAC_MODELS, "win": ["m"]},
    }
    D = _run_discovery_host(tmp_path, last)
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"]["ip"] == MAC_NET_IP


def test_recovery_tier_drops_windows_ip_mac(tmp_path):
    tier2 = {"mac": {"ip": WIN2_NET_IP, "models": PEER_MAC_MODELS}, "win": {"ip": "localhost", "models": ["m"]}}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 0
    assert D.saved["endpoints"]["mac"] is None
    assert D.saved["tier"] == 2


def test_recovery_tier_drops_loopback_mac(tmp_path):
    for loopback in ("localhost",):
        tier2 = {"mac": {"ip": loopback, "models": PEER_MAC_MODELS}, "win": {"ip": "localhost", "models": ["m"]}}
        D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
        assert D.run_discovery() == 0
        assert D.saved["endpoints"]["mac"] is None
        assert D.saved["tier"] == 2


def test_recovery_tier_with_only_windows_mac_fails(tmp_path):
    tier2 = {"mac": {"ip": WIN2_NET_IP, "models": PEER_MAC_MODELS}, "win": None}
    D = _run_discovery_host(tmp_path, None, tier2=tier2, live={"mac": None, "win": None})
    assert D.run_discovery() == 1


def test_status_tolerates_win_peers_list(tmp_path, capsys):
    D = _load_discover()
    state = {
        "recovery_tier": 1,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "endpoints": {
            "mac": {"ip": MAC_NET_IP, "port": 1234, "reachable": True},
            "win": {"ip": LOCAL_NET_IP, "port": 1234, "reachable": True},
            "win_peers": [{"ip": WIN2_NET_IP, "port": 1234, "reachable": True}],
        },
        "models": {"mac": ["a"], "win": ["b"], "win_peers": []},
    }
    D._load_json = lambda path: state
    D.RECOVERY_SOURCE_TXT = tmp_path / "missing.txt"
    D._cmd_status()
    out = capsys.readouterr().out
    assert "mac:" in out and "win:" in out and "win_peers: 1 peer(s)" in out


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
    D._local_ipv4s = lambda: {LOCAL_NET_IP}
    D.load_policy = lambda policy_path=None: {"mac_only": [], "windows_only": [], "shared": []}
    return D, oc


def test_patch_openclaw_skips_local_box_as_mac_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    for ip in ("localhost", LOCAL_NET_IP):
        D.patch_openclaw_json({"mac": {"ip": ip, "models": PEER_MAC_MODELS}, "win": None})
        url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
        assert url == OLD_MAC_URL


def test_patch_openclaw_uses_discovered_mac_ip_on_windows(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.patch_openclaw_json({"mac": {"ip": MAC_NET_IP, "models": PEER_MAC_MODELS}, "win": None})
    prov = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]
    assert prov["baseUrl"] == f"http://{MAC_NET_IP}:1234/v1"
    assert [m["id"] for m in prov["models"]] == ["qwen3.5-9b-mlx"]


def test_patch_openclaw_mac_host_still_uses_localhost(tmp_path, monkeypatch):
    D, oc = _patch_host(tmp_path, monkeypatch)
    D.RUNNING_ON_WINDOWS = False
    D.patch_openclaw_json({"mac": {"ip": MAC_NET_IP, "models": PEER_MAC_MODELS}, "win": None})
    url = json.loads(oc.read_text())["models"]["providers"]["lmstudio-mac"]["baseUrl"]
    assert "localhost" in url
