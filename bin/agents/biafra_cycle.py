"""Dry cycles for the inner seat and the dual-mode outer seat.

Neither cycle launches a model. The outer seat mirrors Scout's two modes:
plugin-loop reading, and GPU-verify reading. It does not take Scout's commands.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import signal
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
    """True for a verifier path (under tests/ or named test_*) that the seats may not edit."""
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
    names a fixed-wall owner is refused (`invalid-card`) before anything is recorded. This cycle is handed
    its measurement, so the proposing agent must run `validate_mechanism_card` before it measures; without
    a card the result says `card_checked: false`, so a reviewer can tell checked from unchecked.
    """
    contracts = _contracts()
    log_dir.mkdir(parents=True, exist_ok=True)
    mode = select_mode(task_type) if seat == "outer" else "inner"
    marker = log_dir / f"{seat}-{mode}.once"

    def refuse(reason: str, **extra: object) -> dict:
        """A refused cycle: nothing launched, nothing retried."""
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
    if mechanism_card is not None:
        result["card_id"] = contracts.card_id(mechanism_card)  # the validated card this run checked
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
# Seconds added to the launcher timeout when declaring the spend reservation's hold. The hold must cover
# the whole allowed launch (timeout, kill, output decode, settle) or another reservation could sweep an
# attempt that is still running; an over-long hold only keeps budget reserved a little longer.
SETTLE_MARGIN_S = 120
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


def _append_trace(ledger_path: Path, trace: dict) -> None:
    """Append one validated trace as a JSON line. Only traces go here; failures are in the spend audit."""
    import json

    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(trace, sort_keys=True) + "\n")


def _settle(spend_guard, reservation, input_chars, output_chars, outcome, seat, mode) -> dict:
    """Settle a reservation with the estimated actual cost; {} when no guard is in use."""
    if spend_guard is None:
        return {}
    usd = spend_guard.settle(reservation, input_chars, output_chars, outcome, seat, mode)
    return {"estimated_usd": usd}


def _settle_unknown(spend_guard, reservation, input_chars, outcome, seat, mode) -> dict:
    """Charge the whole reservation for a possibly sent request with no usable output; {} without a guard."""
    if spend_guard is None:
        return {}
    usd = spend_guard.settle_unknown(reservation, input_chars, outcome, seat, mode)
    return {"estimated_usd": usd}


REAP_WAIT_S = 5.0


def _reap(proc) -> None:
    """Kill a launcher and everything it started, then wait for it a bounded time.

    The launcher runs in its own session, so the whole process group is killed while the leader is still
    unreaped (its pid cannot yet be reused). A grandchild holding the pipes cannot keep the wait open: the
    reap is bounded and the pipes are closed regardless. Never raises an ordinary error: cleanup must not
    mask the failure that led here or skip the settle.
    """
    try:
        pid = getattr(proc, "pid", None)
        if isinstance(pid, int) and proc.poll() is None:
            try:
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                pass
        if proc.poll() is None:
            proc.kill()
    except Exception:
        pass
    try:
        proc.communicate(timeout=REAP_WAIT_S)
    except Exception:
        for stream in (getattr(proc, "stdout", None), getattr(proc, "stderr", None)):
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass
        try:
            proc.wait(timeout=REAP_WAIT_S)
        except Exception:
            pass


def _decode(raw: bytes | str | None) -> str:
    """Launcher output as text. Invalid UTF-8 is replaced, never raised: the request was already sent."""
    if raw is None:
        return ""
    return raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")


def _launch_decision(
    gate_open: bool, has_digest: bool, metric_ok: bool, protected: bool, prompt_ok: bool,
    card_errors: list, trace_problems: list, effort: str, efforts: tuple, has_guard: bool, has_ledger: bool,
) -> dict:
    """Pure decision table: {} when a live attempt may start, else {"reason": ..., **extra} for the first
    failing check, in this order. It reads facts the caller computed and has no side effect."""
    if not gate_open:
        return {"reason": "gate-closed"}
    if not has_digest:
        return {"reason": "no-evaluator-digest"}
    if not metric_ok:
        return {"reason": "non-finite-metric"}
    if protected:
        return {"reason": "verifier-protected"}
    if not prompt_ok:
        return {"reason": "empty-prompt"}
    if card_errors:
        return {"reason": "invalid-card", "errors": card_errors}
    if trace_problems:
        return {"reason": "invalid-trace", "errors": trace_problems}
    if not has_guard:
        return {"reason": "spend-guard-required"}
    if effort is not None and effort not in efforts:
        return {"reason": "invalid-effort"}
    if not has_ledger:
        return {"reason": "ledger-required"}
    return {}


def _prelaunch(
    seat: str, mode: str, artifact: str, prompt: object, evaluator_digest: str | None, metric_before: object,
    hypothesis: str, metric_name: str, attempt_id: str | None, log_dir: Path, mechanism_card: dict | None,
    effort: str | None, spend_guard: object | None, ledger_path: Path | None = None,
) -> tuple[dict | None, dict | None]:
    """Decide, with no side effect, whether a live attempt may start.

    Returns (None, trace_base) when it may, else ({"reason": ..., **extra}, None). Nothing here reserves
    budget, claims the marker or calls the launcher: every refusal that can be known up front is made
    here, in one place, before anything is spent. The ordering lives in `_launch_decision`.
    """
    contracts = _contracts()
    has_digest = evaluator_digest is not None
    metric_ok = contracts.is_finite_number(metric_before)
    prompt_ok = isinstance(prompt, str) and bool(prompt.strip()) and "\x00" not in prompt  # NUL cannot be an argv
    card_errors = contracts.validate_mechanism_card(mechanism_card) if mechanism_card is not None else []
    # The trace is built with a placeholder metric_after; only the measured value and the decision it
    # implies remain to be checked after the request.
    trace_base = None
    trace_problems: list = []
    if has_digest and metric_ok:
        trace_base = {
            "version": 1, "seat": seat,
            "attempt_id": attempt_id if attempt_id is not None
            else _attempt_id(seat, mode, log_dir, artifact, metric_name, metric_before, hypothesis),
            "hypothesis": hypothesis, "artifact": artifact, "metric_name": metric_name,
            "metric_before": metric_before, "evaluator_digest": evaluator_digest,
        }
        trace_problems = contracts.validate_trace_entry({**trace_base, "metric_after": metric_before, "decision": "revert"})
    decision = _launch_decision(
        launch_allowed(), has_digest, metric_ok, _forbidden(artifact), prompt_ok, card_errors, trace_problems,
        effort, EFFORTS, spend_guard is not None, ledger_path is not None,
    )
    if decision:
        return decision, None
    return None, trace_base


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
    spend_guard: object | None = None,
    ledger_path: Path | None = None,
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
        """Build the refusal result for ``reason``: nothing was launched and no retry is allowed."""
        return {
            "ok": False, "seat": seat, "mode": mode, "reason": reason, "retries": 0,
            "launched": False, "called_launcher": False, **extra,
        }

    problem, trace_base = _prelaunch(
        seat, mode, artifact, prompt, evaluator_digest, metric_before, hypothesis, metric_name, attempt_id,
        log_dir, mechanism_card, effort, spend_guard, ledger_path,
    )
    if problem is not None:
        return refuse(problem["reason"], **{k: v for k, v in problem.items() if k != "reason"})
    argv = launcher_argv(seat, prompt=prompt, effort=effort)  # effort was validated by the decision table
    pre = spend_guard.preflight(len(prompt), timeout_s + SETTLE_MARGIN_S)
    if not pre.get("ok"):
        extra = {k: v for k, v in pre.items() if k not in ("ok", "reason", "stop")}
        return refuse(pre.get("reason", "spend-guard-refused"), stop=True, **extra)
    reservation = pre["reservation"]

    # From here the reservation must end settled or released on every exit, including an interrupt and a
    # marker that cannot be written (an unwritable log_dir).
    closed = False
    sent = False
    try:
        try:
            claimed = _claim_once(marker)
        except OSError as exc:
            spend_guard.release(reservation)
            closed = True
            return refuse("marker-error", error=f"{type(exc).__name__}: {exc}")
        if not claimed:
            spend_guard.release(reservation)
            closed = True
            return refuse("already-ran")
        try:
            # Only a failure of Popen itself means nothing was sent (bad argv, missing or unrunnable file).
            proc = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except (OSError, ValueError) as exc:
            spend_guard.release(reservation)
            closed = True
            return refuse("launcher-error", error=f"{type(exc).__name__}: {exc}")
        sent = True  # from here a release would record a sent request as zero spend
        # From here the request may have been sent. Output is bytes, decoded below, so a decode problem
        # can never be mistaken for a launcher that never started.
        try:
            raw_out, raw_err = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            # Unavailable output is not evidence of zero billed output: charge the whole reservation.
            try:
                _reap(proc)
            finally:
                spent = _settle_unknown(spend_guard, reservation, len(prompt), "timeout", seat, mode)
                closed = True
            return refuse("launcher-timeout", spent=True, called_launcher=True, **spent)
        except Exception as exc:
            # The wait itself failed (for example a pipe read): the request was sent, so charge it.
            try:
                _reap(proc)
            finally:
                spent = _settle_unknown(spend_guard, reservation, len(prompt), "launcher-io-error", seat, mode)
                closed = True
            return refuse(
                "launcher-error", spent=True, called_launcher=True, error=f"{type(exc).__name__}: {exc}", **spent,
            )
        except BaseException:
            # An interrupt may have landed after the request was sent: record the spend, never release it.
            try:
                _reap(proc)
            finally:
                _settle_unknown(spend_guard, reservation, len(prompt), "interrupted", seat, mode)
                closed = True
            raise
        completed = subprocess.CompletedProcess(argv, proc.returncode, raw_out, raw_err)
        stdout_text = _decode(completed.stdout)
        stderr_text = _decode(completed.stderr)
        out_text = stdout_text + stderr_text
        extra_spend = _settle(
            spend_guard, reservation, len(prompt), len(out_text), "ok" if completed.returncode == 0 else "failed",
            seat, mode,
        )
        closed = True
    finally:
        if not closed and not sent:
            # A settle that raised after the send leaves the reservation to its declared hold.
            spend_guard.release(reservation)
    if completed.returncode != 0:
        tail = stderr_text[-300:]
        failure_text = f"{stderr_text}\n{stdout_text}"
        stop_reason = spend_guard.classify(failure_text)
        if stop_reason:
            # Never retry and never activate pay-as-you-go: report and stop the loop.
            return refuse(
                stop_reason, spent=True, stop=True, returncode=completed.returncode,
                called_launcher=True, stderr=tail, **extra_spend,
            )
        return refuse(
            "launcher-failed", spent=True, returncode=completed.returncode, called_launcher=True, stderr=tail,
            **extra_spend,
        )
    answer = extract_answer(stdout_text)
    base = {
        "seat": seat, "mode": mode, "retries": 0, "launched": True, "called_launcher": True,
        "answer": answer, "card_checked": mechanism_card is not None, **extra_spend,
    }
    if mechanism_card is not None:
        base["card_id"] = contracts.card_id(mechanism_card)  # validated by _prelaunch before launch
    try:
        measured = evaluate(answer)
        metric_after = measured["metric_after"]
        if not contracts.is_finite_number(metric_after):
            raise ValueError("metric_after is not a finite number")
    except Exception as exc:  # the request is spent; report instead of raising
        return {"ok": False, "reason": "evaluation-failed", "error": f"{type(exc).__name__}: {exc}",
                "recorded": False, "trace": None, **base}
    decision = "keep" if metric_after < metric_before else "revert"
    trace = {**trace_base, "metric_after": metric_after, "decision": decision}
    problems = contracts.validate_trace_entry(trace)
    if problems:
        return {"ok": False, "reason": "invalid-trace", "errors": problems, "recorded": False, "trace": None, **base}
    try:
        _append_trace(ledger_path, trace)
    except OSError as exc:  # the request is spent: hand the trace back so the caller can still persist it
        return {"ok": False, "reason": "ledger-write-failed", "error": f"{type(exc).__name__}: {exc}",
                "recorded": False, "trace": trace, **base}
    return {"ok": True, "decision": decision, "recorded": True, "trace": trace,
            "detail": measured.get("detail"), **base}

