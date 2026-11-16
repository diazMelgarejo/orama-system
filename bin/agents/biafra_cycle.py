"""Dry cycles for the inner seat and the dual-mode outer seat.

Neither cycle launches a model. The outer seat mirrors Scout's two modes:
plugin-loop reading, and GPU-verify reading. It does not take Scout's commands.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import subprocess
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
    mechanism_card: dict | None = None,
) -> dict:
    """Run one cycle. A lower metric is better. A second call does not retry.

    With `evaluator_digest` the result carries a validated trace entry and `recorded: true`.
    Without it the cycle still runs but reports `recorded: false` and a warning. Everything that
    can refuse the attempt is checked before the one-cycle marker is claimed, so a refusal never
    consumes the single attempt. A `mechanism_card`, when given, is validated first and a card that
    names a fixed-wall owner is refused (`invalid-card`) before anything is measured; without one
    the result says `card_checked: false`, so a reviewer can tell checked from unchecked.
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
    if mechanism_card is not None:
        card_errors = contracts.validate_mechanism_card(mechanism_card)
        if card_errors:
            return refuse("invalid-card", errors=card_errors)
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
        "card_checked": mechanism_card is not None,
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


EFFORTS = ("medium", "high", "low")  # never xhigh or max; mirrors launch_cline_wandb.py
_DIM_SPAN = re.compile(r"\x1b\[2m.*?\x1b\[0m", re.S)
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
LIVE_TIMEOUT_S = 900
# Provider limit signals in a FAILED launch. Best effort: matched on the launcher's text, not guaranteed.
_PAYMENT = re.compile(r"\b402\b|payment required|spending cap|exceeded your current|insufficient (?:credit|fund)", re.I)
_RATE = re.compile(r"\b429\b|too many requests|rate.?limit|concurrency limit", re.I)


def _provider_stop(text: str) -> str | None:
    """Reason for a payment or rate-limit failure, or None. Payment wins over rate limit."""
    if _PAYMENT.search(text):
        return "provider-payment-required"
    if _RATE.search(text):
        return "provider-rate-limited"
    return None


def extract_answer(raw: str) -> str:
    """The model's answer from launcher output: drop the dim thinking spans, then ANSI codes."""
    return _ANSI.sub("", _DIM_SPAN.sub("", raw))


def launcher_argv(seat: str, prompt: str | None = None, effort: str | None = None) -> list[str]:
    """Name the W&B summon. Naming it is not a call. `effort` is explicit or left to the launcher."""
    if effort is not None and effort not in EFFORTS:
        raise ValueError(f"effort must be one of {EFFORTS}, got {effort!r}")
    script = (
        Path(__file__).resolve().parents[1]
        / "orama-system"
        / "skills"
        / "cline-wandb"
        / "scripts"
        / "launch_cline_wandb.py"
    )
    default = (
        "Inner seat. Propose one change, measure it, and keep it only when the metric falls."
        if seat == "inner"
        else "Outer seat. Read the log, propose one search rule, and revert it when the metric rises."
    )
    argv = [sys.executable, str(script)]
    if effort is not None:
        argv += ["--effort", effort]
    return [*argv, "--", prompt if prompt is not None else default]


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
    mechanism_card: dict | None = None,
) -> dict:
    """One dry cycle. The launcher runs only when the operator gate and the arm are both set."""
    result = dry_cycle(
        seat, task_type, metric_before, metric_after, log_dir, artifact, evaluator_digest,
        hypothesis, metric_name, attempt_id, mechanism_card,
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


def live_cycle(
    seat: str,
    task_type: str,
    prompt: str,
    log_dir: Path,
    evaluate,
    metric_before: float,
    artifact: str = "search-rule",
    evaluator_digest: str | None = None,
    hypothesis: str = "live cycle",
    metric_name: str = "metric",
    attempt_id: str | None = None,
    effort: str | None = None,
    timeout_s: int = LIVE_TIMEOUT_S,
    mechanism_card: dict | None = None,
) -> dict:
    """One live attempt: launch the seat's model once, evaluate its answer, record the trace.

    Needs the operator gate and the arm together. Every refusal that can be known up front happens
    before the one-attempt marker is claimed; once a request is made the attempt is spent and is
    never retried. `evaluate(answer)` is the fixed evaluator and returns {"metric_after": number}.
    """
    contracts = _contracts()
    log_dir.mkdir(parents=True, exist_ok=True)
    mode = select_mode(task_type) if seat == "outer" else "inner"
    marker = log_dir / f"{seat}-{mode}-live.once"

    def refuse(reason: str, **extra: object) -> dict:
        return {
            "ok": False, "seat": seat, "mode": mode, "reason": reason, "retries": 0,
            "launched": False, "called_launcher": False, **extra,
        }

    if not launch_allowed():
        return refuse("gate-closed")
    if evaluator_digest is None:
        return refuse("no-evaluator-digest")
    if not contracts.is_finite_number(metric_before):
        return refuse("non-finite-metric")
    if _forbidden(artifact):
        return refuse("verifier-protected")
    if not isinstance(prompt, str) or not prompt.strip():
        return refuse("empty-prompt")
    if mechanism_card is not None:
        card_errors = contracts.validate_mechanism_card(mechanism_card)
        if card_errors:
            return refuse("invalid-card", errors=card_errors)
    argv = launcher_argv(seat, prompt=prompt, effort=effort)
    if not _claim_once(marker):
        return refuse("already-ran")

    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired:
        return refuse("launcher-timeout", spent=True)
    if completed.returncode != 0:
        tail = (completed.stderr or "")[-300:]
        stop_reason = _provider_stop(f"{completed.stderr or ''}\n{completed.stdout or ''}")
        if stop_reason:
            # Never retry and never activate pay-as-you-go: report and stop the loop.
            return refuse(
                stop_reason, spent=True, stop=True, returncode=completed.returncode,
                called_launcher=True, stderr=tail,
            )
        return refuse(
            "launcher-failed", spent=True, returncode=completed.returncode, called_launcher=True, stderr=tail,
        )
    answer = extract_answer(completed.stdout or "")
    base = {
        "seat": seat, "mode": mode, "retries": 0, "launched": True, "called_launcher": True,
        "answer": answer, "card_checked": mechanism_card is not None,
    }
    try:
        measured = evaluate(answer)
        metric_after = measured["metric_after"]
        if not contracts.is_finite_number(metric_after):
            raise ValueError("metric_after is not a finite number")
    except Exception as exc:  # the request is spent; report instead of raising
        return {"ok": False, "reason": "evaluation-failed", "error": f"{type(exc).__name__}: {exc}",
                "recorded": False, "trace": None, **base}
    decision = "keep" if metric_after < metric_before else "revert"
    trace = {
        "version": 1, "seat": seat,
        "attempt_id": attempt_id
        or _attempt_id(seat, mode, log_dir, artifact, metric_name, metric_before, metric_after, hypothesis),
        "hypothesis": hypothesis, "artifact": artifact, "metric_name": metric_name,
        "metric_before": metric_before, "metric_after": metric_after, "decision": decision,
        "evaluator_digest": evaluator_digest,
    }
    problems = contracts.validate_trace_entry(trace)
    if problems:
        return {"ok": False, "reason": "invalid-trace", "errors": problems, "recorded": False, "trace": None, **base}
    return {"ok": True, "decision": decision, "recorded": True, "trace": trace,
            "detail": measured.get("detail"), **base}

