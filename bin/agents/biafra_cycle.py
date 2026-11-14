"""Dry cycles for the inner seat and the dual-mode outer seat.

Neither cycle launches a model. The outer seat mirrors Scout's two modes:
plugin-loop reading, and GPU-verify reading. It does not take Scout's commands.
"""

from __future__ import annotations

import os
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
    if marker.exists():
        return {"ok": False, "seat": seat, "mode": mode, "reason": "already-ran", "retries": 0, "launched": False}
    if _forbidden(artifact):
        return {"ok": False, "seat": seat, "mode": mode, "reason": "verifier-protected", "retries": 0, "launched": False}
    improved = metric_after < metric_before
    decision = "keep" if improved else "revert"
    marker.write_text("1\n", encoding="utf-8")
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


def launch_allowed() -> bool:
    """Live summon needs both the operator gate and an explicit arm. Neither is the default."""
    return os.environ.get(GATE_ENV) == "approved" and os.environ.get(ARM_ENV) == "1"
