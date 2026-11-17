"""The live cycle: gate and arm, one attempt, answer extraction, evaluation, trace. No real model."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "b" * 64
DIM = "\x1b[2m"
RESET = "\x1b[0m"


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cycle():
    module = _load(ROOT / "bin/agents/biafra_cycle.py", "biafra_cycle")
    _Guard.stop = staticmethod(module._provider_stop)
    return module


def _fake_run(stdout: str = DIM + "thinking..." + RESET + "ANSWER TEXT", returncode: int = 0, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")

    return run


def _arm(monkeypatch, cycle) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")


class _Guard:
    """A recording spend guard: every reservation must end settled or released, never left open."""

    def __init__(self) -> None:
        self.preflights = 0
        self.settled: list = []
        self.released: list = []

    def preflight(self, n):
        self.preflights += 1
        return {"ok": True, "reservation": f"r{self.preflights}", "projected_usd": 0.0}

    def settle(self, reservation, *a, **k):
        self.settled.append(reservation)
        return 0.0

    def release(self, reservation):
        self.released.append(reservation)

    stop = staticmethod(lambda text: None)  # set by the `cycle` fixture to the real classifier

    def classify(self, text):
        return type(self).stop(text)

    def open_reservations(self) -> list:
        return [f"r{i}" for i in range(1, self.preflights + 1) if f"r{i}" not in self.settled + self.released]


def _kwargs(tmp_path: Path, **over):
    base = dict(
        seat="inner", task_type="harden", prompt="Improve X. Return only code.", log_dir=tmp_path,
        evaluate=lambda answer: {"metric_after": 1.0, "detail": answer}, metric_before=3.0,
        artifact="seat_contracts._owner_folded", evaluator_digest=DIGEST,
        hypothesis="handle leetspeak", metric_name="heldout_wrong", spend_guard=_Guard(),
    )
    base.update(over)
    return base


def test_extract_answer_drops_the_thinking_stream_and_ansi(cycle) -> None:
    raw = DIM + "plan the reply" + RESET + "\x1b[1mFinal\x1b[0m answer" + DIM + "more" + RESET
    assert cycle.extract_answer(raw) == "Final answer"


def test_launcher_argv_carries_the_task_prompt_and_an_explicit_effort(cycle) -> None:
    argv = cycle.launcher_argv("inner", prompt="Do the thing", effort="high")
    assert argv[argv.index("--") + 1] == "Do the thing"
    assert argv[argv.index("--effort") + 1] == "high"
    assert "--effort" not in cycle.launcher_argv("inner", prompt="Do the thing")


@pytest.mark.parametrize("effort", ["xhigh", "max", "ultra", ""])
def test_launcher_argv_refuses_a_forbidden_effort(cycle, effort: str) -> None:
    with pytest.raises(ValueError):
        cycle.launcher_argv("inner", prompt="p", effort=effort)


def test_a_closed_gate_refuses_before_any_marker_or_launch(cycle, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(cycle.GATE_ENV, raising=False)
    monkeypatch.delenv(cycle.ARM_ENV, raising=False)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "gate-closed" and r["launched"] is False
    assert calls == [] and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        ({"evaluator_digest": None}, "no-evaluator-digest"),
        ({"metric_before": float("nan")}, "non-finite-metric"),
        ({"artifact": "tests/test_x.py"}, "verifier-protected"),
        ({"prompt": "  "}, "empty-prompt"),
    ],
)
def test_refusals_happen_before_the_marker_and_the_launch(cycle, tmp_path, monkeypatch, over, reason) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, **over))
    assert r["ok"] is False and r["reason"] == reason and calls == []
    assert not list(tmp_path.glob("*.once"))


def test_a_live_cycle_keeps_a_better_metric_and_records_a_trace(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, effort="high"))
    assert r["ok"] is True and r["decision"] == "keep" and r["launched"] is True and r["retries"] == 0
    assert r["recorded"] is True and r["answer"] == "ANSWER TEXT" and r["called_launcher"] is True
    assert r["trace"]["metric_before"] == 3.0 and r["trace"]["metric_after"] == 1.0
    assert len(calls) == 1 and calls[0][1]["stdin"] is subprocess.DEVNULL and calls[0][1]["timeout"] > 0


def test_a_worse_metric_is_reverted(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=lambda a: {"metric_after": 9.0}))
    assert r["ok"] is True and r["decision"] == "revert"


def test_the_single_attempt_is_spent_by_a_launch_and_is_never_retried(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(returncode=2, calls=calls))
    first = cycle.live_cycle(**_kwargs(tmp_path))
    assert first["ok"] is False and first["reason"] == "launcher-failed" and first["returncode"] == 2
    second = cycle.live_cycle(**_kwargs(tmp_path))
    assert second["reason"] == "already-ran" and len(calls) == 1 and second["retries"] == 0


def test_a_timeout_is_reported_not_raised(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "run", boom)
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "launcher-timeout"


@pytest.mark.parametrize("bad", [None, "x", float("nan"), True])
def test_an_unusable_evaluation_is_reported_after_the_request_was_spent(cycle, tmp_path, monkeypatch, bad) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=lambda a: {"metric_after": bad}))
    assert r["ok"] is False and r["reason"] == "evaluation-failed" and r["launched"] is True
    assert r["answer"] == "ANSWER TEXT"


def test_an_evaluator_that_raises_is_reported(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())

    def bad(answer):
        raise RuntimeError("boom")

    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=bad))
    assert r["ok"] is False and r["reason"] == "evaluation-failed" and "boom" in r["error"]


@pytest.mark.parametrize("name", ["autoresearch-inner", "metaresearch-outer"])
def test_both_programs_expose_run_live(name: str) -> None:
    module = _load(ROOT / "bin/agents" / name / "program.py", name.replace("-", "_") + "_p")
    assert callable(module.run_live)


# --- Biafra's triage of CodeRabbit comment 3: wire the card check into measurement (real turn) ---

PHYLAX_CARD = {
    "version": 1, "mechanism_id": "m-test", "revision": 1, "parent": None, "hypothesis": "h",
    "evidence_ids": ["a-1"], "inner_metric": "m", "held_out_metric": "h", "evaluator_digest": DIGEST,
    "dry_run_receipt": {}, "delta": -1.0, "reverted": False, "scope_record": {"authorizes": "nothing"},
    "owner_slices": ["kungfu"], "status": "candidate",
}


def _card(**over):
    card = dict(PHYLAX_CARD)
    card.update(over)
    return card


def test_dry_cycle_refuses_a_fixed_wall_card_before_measurement(cycle, tmp_path: Path) -> None:
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST,
                        mechanism_card=_card(owner_slices=["phylax"]))
    assert r["ok"] is False and r["reason"] == "invalid-card" and r["launched"] is False
    assert any("E_OWNER" in e for e in r["errors"])
    assert not list(tmp_path.glob("*.once"))  # the attempt was not consumed


def test_dry_cycle_runs_with_a_valid_card_and_says_it_was_checked(cycle, tmp_path: Path) -> None:
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST, mechanism_card=_card())
    assert r["ok"] is True and r["card_checked"] is True


def test_the_no_card_path_is_unchanged_and_says_nothing_was_checked(cycle, tmp_path: Path) -> None:
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST)
    assert r["ok"] is True and r["card_checked"] is False


def test_live_cycle_refuses_a_fixed_wall_card_before_any_launch(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=_card(owner_slices=["telos"])))
    assert r["ok"] is False and r["reason"] == "invalid-card" and calls == []
    assert not list(tmp_path.glob("*.once"))


def test_live_cycle_with_a_valid_card_reports_it_was_checked(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=_card()))
    assert r["ok"] is True and r["card_checked"] is True
    r2 = cycle.live_cycle(**_kwargs(tmp_path / "b"))
    assert r2["ok"] is True and r2["card_checked"] is False


@pytest.mark.parametrize("name", ["autoresearch-inner", "metaresearch-outer"])
def test_the_programs_pass_the_card_through(name: str, tmp_path: Path) -> None:
    module = _load(ROOT / "bin/agents" / name / "program.py", name.replace("-", "_") + "_card")
    r = module.run("harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST, mechanism_card=_card(owner_slices=["agate"]))
    assert r["ok"] is False and r["reason"] == "invalid-card"


# --- billing and rate-limit signals: stop, never retry, never activate pay-as-you-go ----------------


def _fake_run_err(stderr: str, stdout: str = "", returncode: int = 1, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    return run


@pytest.mark.parametrize(
    "text",
    [
        "error: 402 Payment Required",
        "API error code 402: you exceeded your current spending cap",
        "HTTP 402",
        "Error: payment required",
        "you have exceeded your current quota",
    ],
)
def test_a_402_style_failure_is_a_payment_stop(cycle, tmp_path, monkeypatch, text: str) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run_err(text, calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "provider-payment-required" and r["stop"] is True
    assert r["retries"] == 0 and len(calls) == 1
    again = cycle.live_cycle(**_kwargs(tmp_path))
    assert again["reason"] == "already-ran" and len(calls) == 1


@pytest.mark.parametrize(
    "text", ["429 Concurrency limit reached for requests", "HTTP 429 Too Many Requests", "rate limit exceeded"],
)
def test_a_429_style_failure_is_a_rate_limit_stop(cycle, tmp_path, monkeypatch, text: str) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run_err("", stdout=text))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "provider-rate-limited" and r["stop"] is True


def test_an_ordinary_launcher_failure_is_not_a_stop(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run_err("error: Invalid request"))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["reason"] == "launcher-failed" and not r.get("stop")


def test_a_successful_answer_that_merely_mentions_a_limit_is_not_misread(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle.subprocess, "run", _fake_run(stdout="ANSWER: note the 429 and 402 status codes in the docs", returncode=0),
    )
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is True and "stop" not in r


# --- redesign: validate everything knowable before a request is spent; record everything spent ------


@pytest.mark.parametrize(
    "over",
    [
        {"evaluator_digest": "not-a-digest"},
        {"evaluator_digest": "A" * 64},
        {"evaluator_digest": "a" * 64 + "\n"},
        {"hypothesis": ""},
        {"artifact": "  "},
        {"metric_name": ""},
        {"attempt_id": "  "},
    ],
)
def test_malformed_trace_fields_are_refused_before_anything_is_spent(cycle, tmp_path, monkeypatch, over) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))

    class Guard:
        preflights = 0

        def preflight(self, n):
            Guard.preflights += 1
            return {"ok": True, "reservation": "r", "projected_usd": 0.0}

        def release(self, r):
            pass

        def settle(self, *a, **k):
            return 0.0

        def classify(self, t):
            return None

    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=Guard(), **over))
    assert r["ok"] is False and r["reason"] == "invalid-trace" and r["launched"] is False
    assert calls == [] and Guard.preflights == 0, "nothing may be reserved or launched"
    assert not list(tmp_path.glob("*.once"))


def test_a_timeout_reports_that_the_launcher_was_called(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "run", boom)
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True and r["spent"] is True


def test_a_spent_measurement_is_appended_to_the_ledger(cycle, tmp_path, monkeypatch) -> None:
    import json

    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    ledger = tmp_path / "evidence" / "ledger.jsonl"
    r = cycle.live_cycle(**_kwargs(tmp_path, ledger_path=ledger))
    assert r["ok"] is True
    rows = [json.loads(x) for x in ledger.read_text().splitlines()]
    assert rows == [r["trace"]]


def test_refusals_and_unmeasured_attempts_leave_the_ledger_alone(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(returncode=2))
    assert cycle.live_cycle(**_kwargs(tmp_path, ledger_path=ledger))["reason"] == "launcher-failed"
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    assert cycle.live_cycle(**_kwargs(tmp_path / "b", ledger_path=ledger, evaluator_digest="bad"))["ok"] is False
    assert not ledger.exists()


def test_without_a_ledger_path_nothing_is_written(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    cycle.live_cycle(**_kwargs(tmp_path))
    assert not list(tmp_path.rglob("*.jsonl"))


def test_a_live_launch_without_a_spend_guard_is_refused_before_the_marker(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=None))
    assert r["ok"] is False and r["reason"] == "spend-guard-required" and r["launched"] is False
    assert calls == [] and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("effort", ["xhigh", "max", "ultra", ""])
def test_an_invalid_effort_is_refused_before_anything_is_reserved(cycle, tmp_path, monkeypatch, effort) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, effort=effort))
    assert r["reason"] == "invalid-effort" and r["launched"] is False
    assert calls == [] and guard.preflights == 0 and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("effort", ["medium", "high", "low", None])
def test_a_valid_effort_still_launches(cycle, tmp_path, monkeypatch, effort) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, effort=effort))
    assert r["ok"] is True and guard.open_reservations() == []


def test_the_decision_table_is_pure_and_ordered(cycle) -> None:
    ok = dict(gate_open=True, has_digest=True, metric_ok=True, protected=False, prompt_ok=True,
              card_errors=[], trace_problems=[], effort="high", efforts=cycle.EFFORTS, has_guard=True)
    assert cycle._launch_decision(**ok) == {}
    assert cycle._launch_decision(**{**ok, "gate_open": False, "has_guard": False, "effort": "xhigh"})["reason"] == "gate-closed"
    assert cycle._launch_decision(**{**ok, "has_guard": False, "effort": "xhigh"})["reason"] == "spend-guard-required"


def test_an_oserror_from_the_launcher_releases_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        raise OSError("exec failed")

    monkeypatch.setattr(cycle.subprocess, "run", boom)
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and r["called_launcher"] is False
    assert guard.open_reservations() == [] and guard.released == ["r1"]


def test_an_interrupt_during_the_run_settles_the_possibly_sent_request(cycle, tmp_path, monkeypatch) -> None:
    """The request may already have been sent, so the spend is recorded (settled), not released."""
    _arm(monkeypatch, cycle)

    def interrupted(argv, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cycle.subprocess, "run", interrupted)
    guard = _Guard()
    with pytest.raises(KeyboardInterrupt):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.open_reservations() == [] and guard.settled == ["r1"] and guard.released == []


def test_a_nul_byte_in_the_prompt_is_refused_before_the_marker(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, prompt="hi\x00there"))
    assert r["ok"] is False and r["launched"] is False
    assert calls == [] and guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_a_valueerror_from_the_launcher_frees_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def refuses(argv, **kwargs):
        raise ValueError("embedded null byte")

    monkeypatch.setattr(cycle.subprocess, "run", refuses)
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and guard.open_reservations() == [] and guard.released == ["r1"]
