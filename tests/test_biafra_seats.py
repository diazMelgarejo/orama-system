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


def test_programs_name_the_launcher_and_stay_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_armed_program_is_the_only_path_that_calls_the_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cycle = _load()
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    calls: list[list[str]] = []

    def _fake_run(argv: list[str], check: bool = False) -> object:
        calls.append(argv)
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr("subprocess.run", _fake_run)
    result = cycle.run_program("outer", "harden", 0.20, 0.30, tmp_path)
    assert result["called_launcher"] is True
    assert result["launched"] is True
    assert result["returncode"] == 0
    assert Path(calls[0][1]).name == "launch_cline_wandb.py"


def test_a_failed_launch_is_not_reported_as_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cycle = _load()
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")

    def _fail(argv: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2)

    monkeypatch.setattr("subprocess.run", _fail)
    result = cycle.run_program("inner", "harden", 0.20, 0.10, tmp_path)
    assert result["called_launcher"] is True
    assert result["launched"] is False
    assert result["ok"] is False
    assert result["returncode"] == 2
    assert result["reason"] == "launcher-failed"


def test_concurrent_calls_get_one_cycle(tmp_path: Path) -> None:
    cycle = _load()
    barrier = threading.Barrier(8)
    results: list[dict] = []
    lock = threading.Lock()

    def _once() -> None:
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
    script = ROOT / "bin" / "orama-system" / "skills" / "cline-wandb" / "scripts" / "launch_cline_wandb.py"
    spec = importlib.util.spec_from_file_location("launch_cline_wandb", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registry_and_skill_name_both_modes() -> None:
    registry = (ROOT / "bin" / "agents" / "REGISTRY.yml").read_text(encoding="utf-8")
    skill = (ROOT / "bin" / "orama-system" / "skills" / "metaresearcher" / "SKILL.md").read_text(encoding="utf-8")
    assert "staging_folder: metaresearch-outer" in registry
    assert "staging_folder: autoresearcher" in registry
    assert "Primary mode: plugin-loop reading" in skill
    assert "Secondary mode: GPU-verify reading" in skill
    assert "Scout" in skill
