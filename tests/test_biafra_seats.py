"""The outer seat mirrors Scout's two modes and does not launch either one."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CYCLE = ROOT / "bin" / "agents" / "biafra_cycle.py"


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load():
    """Load the cycle module directly from the repository for an isolated test."""
    spec = importlib.util.spec_from_file_location("biafra_cycle", CYCLE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["biafra_cycle"] = module
    spec.loader.exec_module(module)
    return module


def test_outer_seat_uses_plugin_reading_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A hardening dry run keeps an improvement without launching the plugin."""
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
    """An ML experiment selects GPU verification and reverts a worse metric without dispatch."""
    cycle = _load()
    result = cycle.dry_cycle("outer", "ml-experiment", 0.10, 0.20, tmp_path)
    assert result["mode"] == "gpu-verify"
    assert result["decision"] == "revert"
    assert result["dispatches_gpu"] is False


def test_second_cycle_does_not_retry(tmp_path: Path) -> None:
    """A second dry cycle in the same directory is refused without retrying."""
    cycle = _load()
    first = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path)
    second = cycle.dry_cycle("outer", "harden", 0.20, 0.05, tmp_path)
    assert first["ok"] is True
    assert second["reason"] == "already-ran"
    assert second["retries"] == 0


def test_outer_seat_cannot_edit_a_test(tmp_path: Path) -> None:
    """The outer seat refuses to modify an artifact under the test directory."""
    cycle = _load()
    result = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path, artifact="tests/test_metric.py")
    assert result["reason"] == "verifier-protected"


def test_programs_name_the_launcher_and_stay_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Both dry programs name a parseable launcher command without calling it."""
    cycle = _load()
    monkeypatch.delenv(cycle.GATE_ENV, raising=False)
    monkeypatch.delenv(cycle.ARM_ENV, raising=False)
    inner = cycle.run_program("inner", "harden", 0.20, 0.10, tmp_path / "inner", artifact="train.py")
    outer = cycle.run_program("outer", "harden", 0.20, 0.30, tmp_path / "outer")
    assert inner["decision"] == "keep"
    assert outer["decision"] == "revert"
    assert inner["called_launcher"] is False
    assert outer["called_launcher"] is False
    assert Path(inner["argv"][1]).name == "launch_cline_wandb.py"
    assert "--program" not in inner["argv"]
    assert inner["argv"][2] == "--"
    _launcher().parse_args(inner["argv"][2:])
    _launcher().parse_args(outer["argv"][2:])


def test_armed_legacy_program_refuses_before_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy callers must use live_cycle to obtain spend and evidence checks."""
    cycle = _load()
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    result = cycle.run_program("outer", "harden", 0.20, 0.30, tmp_path)
    assert result["reason"] == "legacy-live-path-disabled"
    assert not result["called_launcher"]
    assert not list(tmp_path.glob("*.once"))


def test_concurrent_calls_get_one_cycle(tmp_path: Path) -> None:
    """Concurrent dry cycles share a marker so exactly one attempt succeeds."""
    cycle = _load()
    barrier = threading.Barrier(8)
    results: list[dict] = []
    lock = threading.Lock()

    def _once() -> None:
        """Race one dry cycle at the barrier and collect its result safely."""
        barrier.wait()
        outcome = cycle.dry_cycle("outer", "harden", 0.20, 0.10, tmp_path)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=_once) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(item["ok"] is True for item in results) == 1
    assert sum(item.get("reason") == "already-ran" for item in results) == 7


def _launcher():
    """Load the W&B launcher parser without invoking the launcher."""
    script = ROOT / "bin" / "orama-system" / "skills" / "cline-wandb" / "scripts" / "launch_cline_wandb.py"
    spec = importlib.util.spec_from_file_location("launch_cline_wandb", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registry_and_skill_name_both_modes() -> None:
    """The registry names both seats and the skill describes Scout's two reading modes."""
    registry = (ROOT / "bin" / "agents" / "REGISTRY.yml").read_text(encoding="utf-8")
    skill = (ROOT / "bin" / "orama-system" / "skills" / "metaresearcher" / "SKILL.md").read_text(encoding="utf-8")
    assert "staging_folder: metaresearch-outer" in registry
    assert "staging_folder: autoresearcher" in registry
    assert "Primary mode: plugin-loop reading" in skill
    assert "Secondary mode: GPU-verify reading" in skill
    assert "Scout" in skill
