"""Dry cycles for the inner seat and the dual-mode outer seat.

Neither cycle launches a model. The outer seat mirrors Scout's two modes:
plugin-loop reading, and GPU-verify reading. It does not take Scout's commands.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PRIMARY_MODE = "plugin-loop"
SECONDARY_MODE = "gpu-verify"
GATE_ENV = "BIAFRA_ORCHESTRATOR_GATE"
ARM_ENV = "BIAFRA_ALLOW_LAUNCH"


def select_mode(task_type: str) -> str:
    """Match Scout: ML experiments use the verify substrate; everything else uses the plugin loop."""
    if task_type == "ml-experiment":
        return SECONDARY_MODE
    return PRIMARY_MODE


def _forbidden(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    return "tests" in parts or name.startswith("test_")


def dry_cycle(
    seat: str,
    task_type: str,
    metric_before: float,
    metric_after: float,
    log_dir: Path,
    artifact: str = "search-rule",
) -> dict:
    """Run one cycle. A lower metric is better. A second call does not retry."""
    log_dir.mkdir(parents=True, exist_ok=True)
    mode = select_mode(task_type) if seat == "outer" else "inner"
    marker = log_dir / f"{seat}-{mode}.once"
    if _forbidden(artifact):
        return {"ok": False, "seat": seat, "mode": mode, "reason": "verifier-protected", "retries": 0, "launched": False}
    if not _claim_once(marker):
        return {"ok": False, "seat": seat, "mode": mode, "reason": "already-ran", "retries": 0, "launched": False}
    improved = metric_after < metric_before
    decision = "keep" if improved else "revert"
    return {
        "ok": True,
        "seat": seat,
        "mode": mode,
        "decision": decision,
        "calls_plugin": False,
        "dispatches_gpu": False,
        "retries": 0,
        "launched": False,
        "gate": os.environ.get(GATE_ENV, ""),
        "armed": os.environ.get(ARM_ENV, ""),
    }


def _claim_once(marker: Path) -> bool:
    """Create the one-cycle marker or lose the race. Existence is checked by the create."""
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    try:
        os.write(fd, b"1\n")
    finally:
        os.close(fd)
    return True


def launch_allowed() -> bool:
    """Live summon needs both the operator gate and an explicit arm. Neither is the default."""
    return os.environ.get(GATE_ENV) == "approved" and os.environ.get(ARM_ENV) == "1"


def launcher_argv(seat: str) -> list[str]:
    """Name the W&B summon. Naming it is not a call."""
    script = (
        Path(__file__).resolve().parents[1]
        / "orama-system"
        / "skills"
        / "cline-wandb"
        / "scripts"
        / "launch_cline_wandb.py"
    )
    prompt = (
        "Inner seat. Propose one change, measure it, and keep it only when the metric falls."
        if seat == "inner"
        else "Outer seat. Read the log, propose one search rule, and revert it when the metric rises."
    )
    return [sys.executable, str(script), "--", prompt]


def run_program(
    seat: str,
    task_type: str,
    metric_before: float,
    metric_after: float,
    log_dir: Path,
    artifact: str = "search-rule",
) -> dict:
    """One dry cycle. The launcher runs only when the operator gate and the arm are both set."""
    result = dry_cycle(seat, task_type, metric_before, metric_after, log_dir, artifact)
    result["argv"] = launcher_argv(seat)
    result["called_launcher"] = False
    if result.get("ok") and launch_allowed():
        import subprocess

        completed = subprocess.run(result["argv"], check=False)
        result["called_launcher"] = True
        result["returncode"] = completed.returncode
        result["launched"] = completed.returncode == 0
        if completed.returncode != 0:
            result["ok"] = False
            result["reason"] = "launcher-failed"
    return result
