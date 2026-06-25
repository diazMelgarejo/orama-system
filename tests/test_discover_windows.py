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


def _load_discover():
    spec = importlib.util.spec_from_file_location("discover_win_test", DISCOVER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
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
        mac_ip_env="192.168.254.103",
    )
    assert result["mac"] is not None
    assert result["mac"]["ip"] == "192.168.254.103"
    assert result["mac"]["models"] == mac_models
    # Mac IP probe must have been called with the env var IP
    assert any("192.168.254.103" in url for url in call_log)


def test_windows_mac_not_set_when_mac_ip_unreachable(tmp_path):
    """On Windows, $MAC_IP unreachable → result['mac'] stays None."""
    # mac_models=None means probe_models returns None for that IP
    result, _, _ = _discover_as_windows(
        None,
        win_models=["qwen3.5-27b-distilled"],
        mac_models=None,
        mac_ip_env="192.168.254.103",
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
    "mac_only": ["qwen3.5-9b-mlx"],
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
        "text-embedding-nomic-embed-text-v1.5",                 # shared/embedding
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

    cached_mac_ip = "192.168.254.103"
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

    # Prevent the full subnet scan from running
    import asyncio
    D.asyncio = MagicMock()
    D.asyncio.run = lambda coro: []

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
        "mac_only": ["qwen3.5-9b-mlx"],
        "shared": [],
    }
    filtered = D.filter_endpoints_for_policy(endpoints, policy)
    win_models = filtered["win"]["models"]
    assert "qwen3.5-27b-distilled" in win_models   # windows_only → allowed on win
    assert "qwen3.5-9b-mlx" not in win_models       # mac_only → forbidden on win