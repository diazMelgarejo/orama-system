from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from oramaclaw.target import (
    TargetCatalog,
    TargetNotFound,
    _DEFAULT_OPENCLAW_HOME,
    _DEFAULT_STATE_SUBDIR,
    resolve_target,
)
from oramaclaw.types import ConfigTarget


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_target(tmp_path: Path, suffix: str = "") -> ConfigTarget:
    return ConfigTarget(
        workspace_root=tmp_path / f"workspace{suffix}",
        config_path=tmp_path / f"openclaw{suffix}.json",
        state_dir=tmp_path / f"state{suffix}",
    )


class _FakeManifest:
    def __init__(self, target: ConfigTarget | None) -> None:
        self.target = target


# ── resolve_target: explicit CLI args ────────────────────────────────────────

def test_explicit_args_take_priority(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    ws = tmp_path / "ws"
    cfg = tmp_path / "oc.json"
    sd = tmp_path / "state"
    result = resolve_target(workspace=ws, config_path=cfg, state_dir=sd)
    assert result.workspace_root == ws.resolve()
    assert result.config_path == cfg.resolve()
    assert result.state_dir == sd.resolve()


def test_explicit_args_partial_raises():
    with pytest.raises(ValueError, match="all three are required"):
        resolve_target(workspace="/tmp/ws")


def test_explicit_args_override_manifest(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    ws = tmp_path / "ws"
    cfg = tmp_path / "oc.json"
    sd = tmp_path / "state"
    manifest_target = _make_target(tmp_path, "-manifest")
    manifest = _FakeManifest(manifest_target)
    result = resolve_target(workspace=ws, config_path=cfg, state_dir=sd, manifest=manifest)
    assert result.workspace_root == ws.resolve()


# ── resolve_target: manifest target ──────────────────────────────────────────

def test_manifest_target_used_when_no_explicit_args(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    expected = _make_target(tmp_path)
    manifest = _FakeManifest(expected)
    result = resolve_target(manifest=manifest)
    assert result == expected


def test_manifest_without_target_falls_through_to_default(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    manifest = _FakeManifest(None)
    result = resolve_target(manifest=manifest)
    assert result.config_path == (_DEFAULT_OPENCLAW_HOME / "openclaw.json")


# ── resolve_target: named catalog target ─────────────────────────────────────

def test_named_target_from_explicit_catalog(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    ws = tmp_path / "named-ws"
    cfg = tmp_path / "named.json"
    sd = tmp_path / "named-state"
    named = ConfigTarget(
        workspace_root=ws.resolve(),
        config_path=cfg.resolve(),
        state_dir=sd.resolve(),
    )
    catalog = TargetCatalog({"my-target": named}, tmp_path / "targets.json")
    result = resolve_target(target_name="my-target", catalog=catalog)
    assert result == named


def test_unknown_named_target_raises(tmp_path):
    catalog = TargetCatalog({}, tmp_path / "targets.json")
    with pytest.raises(TargetNotFound, match="missing"):
        catalog.get("missing")


# ── resolve_target: OPENCLAW_HOME legacy migration ───────────────────────────

def test_openclaw_home_env_var_used_as_fallback(tmp_path, monkeypatch):
    home = tmp_path / "legacy-home"
    monkeypatch.setenv("OPENCLAW_HOME", str(home))
    result = resolve_target()
    assert result.workspace_root == home.resolve()
    assert result.config_path == home.resolve() / "openclaw.json"
    assert result.state_dir == home.resolve() / _DEFAULT_STATE_SUBDIR


def test_openclaw_home_emits_deprecation_warning(tmp_path, monkeypatch, caplog):
    home = tmp_path / "legacy-home"
    monkeypatch.setenv("OPENCLAW_HOME", str(home))
    with caplog.at_level(logging.WARNING, logger="oramaclaw.target"):
        resolve_target()
    assert any("OPENCLAW_HOME is deprecated" in r.message for r in caplog.records)


def test_default_layout_when_no_env_or_manifest(monkeypatch):
    monkeypatch.delenv("OPENCLAW_HOME", raising=False)
    result = resolve_target()
    assert result.workspace_root == _DEFAULT_OPENCLAW_HOME
    assert result.config_path == _DEFAULT_OPENCLAW_HOME / "openclaw.json"
    assert result.state_dir == _DEFAULT_OPENCLAW_HOME / _DEFAULT_STATE_SUBDIR


# ── TargetCatalog.default_path ────────────────────────────────────────────────

def test_catalog_default_path_reads_env_var(tmp_path, monkeypatch):
    custom = tmp_path / "custom-targets.json"
    monkeypatch.setenv("ORAMACLAW_TARGETS_PATH", str(custom))
    assert TargetCatalog.default_path() == custom.resolve()


def test_catalog_default_path_without_env_var(monkeypatch):
    monkeypatch.delenv("ORAMACLAW_TARGETS_PATH", raising=False)
    expected = _DEFAULT_OPENCLAW_HOME / "oramaclaw-targets.json"
    assert TargetCatalog.default_path() == expected


# ── TargetCatalog.load ────────────────────────────────────────────────────────

def test_catalog_load_nonexistent_file_returns_empty(tmp_path):
    catalog = TargetCatalog.load(tmp_path / "does-not-exist.json")
    assert len(catalog) == 0
    assert catalog.names() == []


def test_catalog_load_valid_file(tmp_path):
    catalog_path = tmp_path / "targets.json"
    ws = tmp_path / "ws"
    cfg = tmp_path / "oc.json"
    sd = tmp_path / "sd"
    catalog_path.write_text(json.dumps({
        "targets": {
            "dev": {
                "workspace_root": str(ws),
                "config_path": str(cfg),
                "state_dir": str(sd),
            }
        }
    }))
    catalog = TargetCatalog.load(catalog_path)
    assert catalog.names() == ["dev"]
    t = catalog.get("dev")
    assert t.workspace_root == ws.resolve()
    assert t.config_path == cfg.resolve()
    assert t.state_dir == sd.resolve()


def test_catalog_load_skips_malformed_entry(tmp_path, caplog):
    catalog_path = tmp_path / "targets.json"
    catalog_path.write_text(json.dumps({
        "targets": {
            "ok": {
                "workspace_root": str(tmp_path),
                "config_path": str(tmp_path / "oc.json"),
                "state_dir": str(tmp_path / "state"),
            },
            "bad": "not-a-dict",
        }
    }))
    with caplog.at_level(logging.WARNING, logger="oramaclaw.target"):
        catalog = TargetCatalog.load(catalog_path)
    assert catalog.names() == ["ok"]
    assert any("bad" in r.message for r in caplog.records)


def test_catalog_load_invalid_json_returns_empty(tmp_path, caplog):
    catalog_path = tmp_path / "targets.json"
    catalog_path.write_bytes(b"{not valid json")
    with caplog.at_level(logging.WARNING, logger="oramaclaw.target"):
        catalog = TargetCatalog.load(catalog_path)
    assert len(catalog) == 0


def test_catalog_get_missing_target_raises(tmp_path):
    catalog = TargetCatalog({}, tmp_path / "t.json")
    with pytest.raises(TargetNotFound) as exc_info:
        catalog.get("nonexistent")
    assert "nonexistent" in str(exc_info.value)
    assert str(tmp_path / "t.json") in str(exc_info.value)
