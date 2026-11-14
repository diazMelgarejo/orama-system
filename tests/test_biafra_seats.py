"""The outer seat mirrors Scout's two modes and does not launch either one."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CYCLE = ROOT / "bin" / "agents" / "biafra_cycle.py"


def _load():
    spec = importlib.util.spec_from_file_location("biafra_cycle", CYCLE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["biafra_cycle"] = module
    spec.loader.exec_module(module)
    return module


def test_outer_seat_uses_plugin_reading_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cycle = _load()
    monkeypatch.delenv(cycle.GATE_ENV, raising=False)
    monkeypatch.delenv(cycle.ARM_ENV, raising=False)
    result = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path)
    assert result["mode"] == "plugin-loop"
    assert result["decision"] == "keep"
    assert result["calls_plugin"] is False
    assert result["launched"] is False
    assert cycle.launch_allowed() is False


def test_outer_seat_reads_the_gpu_metric_for_an_ml_experiment(tmp_path: Path) -> None:
    cycle = _load()
    result = cycle.dry_cycle("outer", "ml-experiment", 0.10, 0.20, tmp_path)
    assert result["mode"] == "gpu-verify"
    assert result["decision"] == "revert"
    assert result["dispatches_gpu"] is False


def test_second_cycle_does_not_retry(tmp_path: Path) -> None:
    cycle = _load()
    first = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path)
    second = cycle.dry_cycle("outer", "harden", 0.20, 0.05, tmp_path)
    assert first["ok"] is True
    assert second["reason"] == "already-ran"
    assert second["retries"] == 0


def test_outer_seat_cannot_edit_a_test(tmp_path: Path) -> None:
    cycle = _load()
    result = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path, artifact="tests/test_metric.py")
    assert result["reason"] == "verifier-protected"


def test_registry_and_skill_name_both_modes() -> None:
    registry = (ROOT / "bin" / "agents" / "REGISTRY.yml").read_text(encoding="utf-8")
    skill = (ROOT / "bin" / "orama-system" / "skills" / "metaresearcher" / "SKILL.md").read_text(encoding="utf-8")
    assert "staging_folder: metaresearch-outer" in registry
    assert "staging_folder: autoresearcher" in registry
    assert "Primary mode: plugin-loop reading" in skill
    assert "Secondary mode: GPU-verify reading" in skill
    assert "Scout" in skill
