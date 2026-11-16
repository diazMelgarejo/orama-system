"""Dry cycles for the inner seat and the dual-mode outer seat.

Neither cycle launches a model. The outer seat mirrors Scout's two modes:
plugin-loop reading, and GPU-verify reading. It does not take Scout's commands.
"""

from __future__ import annotations

import hashlib
import importlib.util
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


def _contracts():
    """Load the shared seat contracts by path, as the programs load this module."""
    path = Path(__file__).resolve().parent / "seat_contracts.py"
    spec = importlib.util.spec_from_file_location("seat_contracts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _forbidden(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    return "tests" in parts or name.startswith("test_")


def _attempt_id(seat: str, mode: str, log_dir: Path, *parts: object) -> str:
    """A run-varying, deterministic id: the same call in the same directory cannot run twice."""
    basis = "|".join([seat, mode, str(log_dir.resolve()), *map(repr, parts)])
    return f"{seat}-{mode}-{hashlib.sha256(basis.encode()).hexdigest()[:12]}"


def dry_cycle(
    seat: str,
    task_type: str,
    metric_before: float,
    metric_after: float,
    log_dir: Path,
    artifact: str = "search-rule",
    evaluator_digest: str | None = None,
    hypothesis: str = "dry cycle",
    metric_name: str = "metric",
    attempt_id: str | None = None,
) -> dict:
    """Run one cycle. A lower metric is better. A second call does not retry.

    With `evaluator_digest` the result carries a validated trace entry and `recorded: true`.
    Without it the cycle still runs but reports `recorded: false` and a warning. Everything that
    can refuse the attempt is checked before the one-cycle marker is claimed, so a refusal never
    consumes the single attempt.
    """
    contracts = _contracts()
    log_dir.mkdir(parents=True, exist_ok=True)
    mode = select_mode(task_type) if seat == "outer" else "inner"
    marker = log_dir / f"{seat}-{mode}.once"

    def refuse(reason: str, **extra: object) -> dict:
        return {"ok": False, "seat": seat, "mode": mode, "reason": reason, "retries": 0, "launched": False, **extra}

    if not (contracts.is_finite_number(metric_before) and contracts.is_finite_number(metric_after)):
        return refuse("non-finite-metric")
    if _forbidden(artifact):
        return refuse("verifier-protected")
    decision = "keep" if metric_after < metric_before else "revert"
    trace = None
    if evaluator_digest is not None:
        trace = {
            "version": 1,
            "seat": seat,
            "attempt_id": attempt_id
            or _attempt_id(seat, mode, log_dir, artifact, metric_name, metric_before, metric_after, hypothesis),
            "hypothesis": hypothesis,
            "artifact": artifact,
            "metric_name": metric_name,
            "metric_before": metric_before,
            "metric_after": metric_after,
            "decision": decision,
            "evaluator_digest": evaluator_digest,
        }
        problems = contracts.validate_trace_entry(trace)
        if problems:
            return refuse("invalid-trace", errors=problems)
    if not _claim_once(marker):
        return refuse("already-ran")
    result = {
        "trace": trace,
        "recorded": trace is not None,
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
    if trace is None:
        result["warning"] = "no-evaluator-digest"
    return result


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
    evaluator_digest: str | None = None,
    hypothesis: str = "dry cycle",
    metric_name: str = "metric",
    attempt_id: str | None = None,
) -> dict:
    """One dry cycle. The launcher runs only when the operator gate and the arm are both set."""
    result = dry_cycle(
        seat, task_type, metric_before, metric_after, log_dir, artifact, evaluator_digest,
        hypothesis, metric_name, attempt_id,
    )
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
