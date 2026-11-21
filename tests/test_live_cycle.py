"""The live cycle: gate and arm, one attempt, answer extraction, evaluation, trace. No real model."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType

import pytest
from _fake_popen import as_popen

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "b" * 64
DIM = "\x1b[2m"
RESET = "\x1b[0m"


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(path: Path, name: str):
    """Test helper or fixture: load."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cycle():
    """Test helper or fixture: cycle."""
    module = _load(ROOT / "bin/agents/biafra_cycle.py", "biafra_cycle")
    _Guard.stop = staticmethod(module._provider_stop)
    return module


def _fake_run(stdout: str = DIM + "thinking..." + RESET + "ANSWER TEXT", returncode: int = 0, calls=None):
    """Test helper or fixture: fake run."""
    def run(argv, **kwargs):
        """Test helper or fixture: run."""
        if calls is not None:
            calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout.encode(), stderr=b"")

    return as_popen(run)


def _arm(monkeypatch, cycle) -> None:
    """Test helper or fixture: arm."""
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    # Historical lifecycle tests exercise an explicitly simulated supported launcher.
    monkeypatch.setattr(cycle, "_launcher_boundary_problem", lambda: None)


class _Guard:
    """A recording spend guard: every reservation must end settled or released, never left open."""

    def __init__(self) -> None:
        """Test helper or fixture: init  ."""
        self.preflights = 0
        self.settled: list = []
        self.released: list = []

    def preflight(self, n, hold_seconds):
        """Test helper or fixture: preflight."""
        self.preflights += 1
        return {"ok": True, "reservation": f"r{self.preflights}", "projected_usd": 0.0}

    def settle(self, reservation, *a, **k):
        """Test helper or fixture: settle."""
        self.settled.append(reservation)
        return 0.0

    def settle_unknown(self, reservation, *a, **k):
        """Test helper or fixture: settle unknown."""
        self.settled.append(reservation)
        return 0.0

    def release(self, reservation):
        """Test helper or fixture: release."""
        self.released.append(reservation)

    stop = staticmethod(lambda text: None)  # set by the `cycle` fixture to the real classifier

    def classify(self, text):
        """Test helper or fixture: classify."""
        return type(self).stop(text)

    def open_reservations(self) -> list:
        """Test helper or fixture: open reservations."""
        return [f"r{i}" for i in range(1, self.preflights + 1) if f"r{i}" not in self.settled + self.released]


def _kwargs(tmp_path: Path, **over):
    """Test helper or fixture: kwargs."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    pin = tmp_path / "evaluator-pin.json"
    pin.write_text(json.dumps({"version": 1, "evaluator_digest": DIGEST, "covers": ["verifier.py"]}))
    probe = {"date": datetime.now(timezone.utc).date().isoformat(),
             "provider": "https://api.inference.wandb.ai/v1",
             "models": ["deepseek-ai/DeepSeek-V4.1-Flash-1017"],
             "efforts": {"deepseek-ai/DeepSeek-V4.1-Flash-1017": ["high", "low"]}}
    base = dict(pin_path=pin, probe_record=probe,
        seat="inner", task_type="harden", prompt="Improve X. Return only code.", log_dir=tmp_path,
        evaluate=lambda answer: {"metric_after": 1.0, "detail": answer}, metric_before=3.0,
        artifact="seat_contracts._owner_folded", evaluator_digest=DIGEST,
        hypothesis="handle leetspeak", metric_name="metric", spend_guard=_Guard(),
        ledger_path=tmp_path / "default-ledger.jsonl",
    )
    base.update(over)
    return base


def test_extract_answer_drops_the_thinking_stream_and_ansi(cycle) -> None:
    """Check that extract answer drops the thinking stream and ansi."""
    raw = DIM + "plan the reply" + RESET + "\x1b[1mFinal\x1b[0m answer" + DIM + "more" + RESET
    assert cycle.extract_answer(raw) == "Final answer"


def test_launcher_argv_carries_the_task_prompt_and_an_explicit_effort(cycle) -> None:
    """Check that launcher argv carries the task prompt and an explicit effort."""
    argv = cycle.launcher_argv("inner", prompt="Do the thing", effort="high")
    assert argv[argv.index("--") + 1] == "Do the thing"
    assert argv[argv.index("--effort") + 1] == "high"
    assert "--effort" not in cycle.launcher_argv("inner", prompt="Do the thing")


@pytest.mark.parametrize("effort", ["xhigh", "max", "ultra", ""])
def test_launcher_argv_refuses_a_forbidden_effort(cycle, effort: str) -> None:
    """Check that launcher argv refuses a forbidden effort."""
    with pytest.raises(ValueError):
        cycle.launcher_argv("inner", prompt="p", effort=effort)


def test_a_closed_gate_refuses_before_any_marker_or_launch(cycle, tmp_path, monkeypatch) -> None:
    """Check that a closed gate refuses before any marker or launch."""
    monkeypatch.delenv(cycle.GATE_ENV, raising=False)
    monkeypatch.delenv(cycle.ARM_ENV, raising=False)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
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
    """Check that refusals happen before the marker and the launch."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, **over))
    assert r["ok"] is False and r["reason"] == reason and calls == []
    assert not list(tmp_path.glob("*.once"))


def test_a_live_cycle_keeps_a_better_metric_and_records_a_trace(cycle, tmp_path, monkeypatch) -> None:
    """Check that a live cycle keeps a better metric and records a trace."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, effort="high"))
    assert r["ok"] is True and r["decision"] == "keep" and r["launched"] is True and r["retries"] == 0
    assert r["recorded"] is True and r["answer"] == "ANSWER TEXT" and r["called_launcher"] is True
    argv = calls[0][0]
    assert argv[argv.index("--model") + 1] == cycle._contracts().WANDB_MODEL_ORDER[0]
    assert argv[argv.index("--effort") + 1] == "high"
    assert r["trace"]["metric_before"] == 3.0 and r["trace"]["metric_after"] == 1.0
    assert len(calls) == 1 and calls[0][1]["stdin"] is subprocess.DEVNULL and calls[0][1]["timeout"] > 0


def test_a_worse_metric_is_reverted(cycle, tmp_path, monkeypatch) -> None:
    """Check that a worse metric is reverted."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=lambda a: {"metric_after": 9.0}))
    assert r["ok"] is True and r["decision"] == "revert"


def test_the_single_attempt_is_spent_by_a_launch_and_is_never_retried(cycle, tmp_path, monkeypatch) -> None:
    """Check that the single attempt is spent by a launch and is never retried."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(returncode=2, calls=calls))
    first = cycle.live_cycle(**_kwargs(tmp_path))
    assert first["ok"] is False and first["reason"] == "launcher-failed" and first["returncode"] == 2
    second = cycle.live_cycle(**_kwargs(tmp_path))
    assert second["reason"] == "already-ran" and len(calls) == 1 and second["retries"] == 0


def test_a_timeout_is_reported_not_raised(cycle, tmp_path, monkeypatch) -> None:
    """Check that a timeout is reported not raised."""
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        """Test helper or fixture: boom."""
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(boom))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "launcher-timeout"


@pytest.mark.parametrize("bad", [None, "x", float("nan"), True])
def test_an_unusable_evaluation_is_reported_after_the_request_was_spent(cycle, tmp_path, monkeypatch, bad) -> None:
    """Check that an unusable evaluation is reported after the request was spent."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=lambda a: {"metric_after": bad}))
    assert r["ok"] is False and r["reason"] == "evaluation-failed" and r["launched"] is True
    assert r["answer"] == "ANSWER TEXT"


def test_an_evaluator_that_raises_is_reported(cycle, tmp_path, monkeypatch) -> None:
    """Check that an evaluator that raises is reported."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())

    def bad(answer):
        """Test helper or fixture: bad."""
        raise RuntimeError("boom")

    r = cycle.live_cycle(**_kwargs(tmp_path, evaluate=bad))
    assert r["ok"] is False and r["reason"] == "evaluation-failed" and "boom" in r["error"]


@pytest.mark.parametrize("name", ["autoresearch-inner", "metaresearch-outer"])
def test_both_programs_expose_run_live(name: str) -> None:
    """Check that both programs expose run live."""
    module = _load(ROOT / "bin/agents" / name / "program.py", name.replace("-", "_") + "_p")
    assert callable(module.run_live)


# --- Biafra's triage of CodeRabbit comment 3: wire the card check into measurement (real turn) ---

PHYLAX_CARD = {
    "version": 1, "mechanism_id": "m-test", "revision": 1, "parent": None, "hypothesis": "h",
    "evidence_ids": ["a-1"], "inner_metric": "metric", "held_out_metric": "val_bpb_heldout", "evaluator_digest": DIGEST,
    "dry_run_receipt": {}, "delta": -1.0, "reverted": False, "scope_record": {"authorizes": "nothing"},
    "owner_slices": ["kungfu"], "status": "candidate",
}


def _card(**over):
    """Test helper or fixture: card."""
    card = dict(PHYLAX_CARD)
    card.update(over)
    return card


def test_dry_cycle_refuses_a_fixed_wall_card_before_measurement(cycle, tmp_path: Path) -> None:
    """Check that dry cycle refuses a fixed wall card before measurement."""
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST,
                        mechanism_card=_card(owner_slices=["phylax"]))
    assert r["ok"] is False and r["reason"] == "invalid-card" and r["launched"] is False
    assert any("E_OWNER" in e for e in r["errors"])
    assert not list(tmp_path.glob("*.once"))  # the attempt was not consumed


def test_dry_cycle_runs_with_a_valid_card_and_says_it_was_checked(cycle, tmp_path: Path) -> None:
    """Check that dry cycle runs with a valid card and says it was checked."""
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST, mechanism_card=_card())
    assert r["ok"] is True and r["card_checked"] is True


def test_the_no_card_path_is_unchanged_and_says_nothing_was_checked(cycle, tmp_path: Path) -> None:
    """Check that the no card path is unchanged and says nothing was checked."""
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST)
    assert r["ok"] is True and r["card_checked"] is False


def test_live_cycle_refuses_a_fixed_wall_card_before_any_launch(cycle, tmp_path, monkeypatch) -> None:
    """Check that live cycle refuses a fixed wall card before any launch."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=_card(owner_slices=["telos"])))
    assert r["ok"] is False and r["reason"] == "invalid-card" and calls == []
    assert not list(tmp_path.glob("*.once"))


def test_live_cycle_with_a_valid_card_reports_it_was_checked(cycle, tmp_path, monkeypatch) -> None:
    """Check that live cycle with a valid card reports it was checked."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=_card()))
    assert r["ok"] is True and r["card_checked"] is True
    r2 = cycle.live_cycle(**_kwargs(tmp_path / "b"))
    assert r2["ok"] is True and r2["card_checked"] is False


def test_g9_dry_cycle_names_the_card_it_checked(cycle, tmp_path: Path) -> None:
    """A dry cycle returns card_id only when a card was passed."""
    r = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST, mechanism_card=_card())
    assert r["card_id"] == "m-test@1"
    r2 = cycle.dry_cycle("outer", "harden", 0.3, 0.1, tmp_path / "b", evaluator_digest=DIGEST)
    assert "card_id" not in r2


def test_g9_live_cycle_names_the_card_it_checked(cycle, tmp_path, monkeypatch) -> None:
    """A live cycle returns card_id only when a card was passed."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    r = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=_card(revision=4)))
    assert r["ok"] is True and r["card_id"] == "m-test@4"
    r2 = cycle.live_cycle(**_kwargs(tmp_path / "b"))
    assert "card_id" not in r2


@pytest.mark.parametrize("name", ["autoresearch-inner", "metaresearch-outer"])
def test_the_programs_pass_the_card_through(name: str, tmp_path: Path) -> None:
    """Check that the programs pass the card through."""
    module = _load(ROOT / "bin/agents" / name / "program.py", name.replace("-", "_") + "_card")
    r = module.run("harden", 0.3, 0.1, tmp_path, evaluator_digest=DIGEST, mechanism_card=_card(owner_slices=["agate"]))
    assert r["ok"] is False and r["reason"] == "invalid-card"


# --- billing and rate-limit signals: stop, never retry, never activate pay-as-you-go ----------------


def _fake_run_err(stderr: str, stdout: str = "", returncode: int = 1, calls=None):
    """Test helper or fixture: fake run err."""
    def run(argv, **kwargs):
        """Test helper or fixture: run."""
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    return as_popen(run)


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
    """Check that a 402 style failure is a payment stop."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run_err(text, calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "provider-payment-required" and r["stop"] is True
    assert r["retries"] == 0 and len(calls) == 1
    again = cycle.live_cycle(**_kwargs(tmp_path))
    assert again["reason"] == "already-ran" and len(calls) == 1


@pytest.mark.parametrize(
    "text", ["429 Concurrency limit reached for requests", "HTTP 429 Too Many Requests", "rate limit exceeded"],
)
def test_a_429_style_failure_is_a_rate_limit_stop(cycle, tmp_path, monkeypatch, text: str) -> None:
    """Check that a 429 style failure is a rate limit stop."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run_err("", stdout=text))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is False and r["reason"] == "provider-rate-limited" and r["stop"] is True


def test_an_ordinary_launcher_failure_is_not_a_stop(cycle, tmp_path, monkeypatch) -> None:
    """Check that an ordinary launcher failure is not a stop."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run_err("error: Invalid request"))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["reason"] == "launcher-failed" and not r.get("stop")


def test_a_successful_answer_that_merely_mentions_a_limit_is_not_misread(cycle, tmp_path, monkeypatch) -> None:
    """Check that a successful answer that merely mentions a limit is not misread."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle.subprocess, "Popen", _fake_run(stdout="ANSWER: note the 429 and 402 status codes in the docs", returncode=0),
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
    """Check that malformed trace fields are refused before anything is spent."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))

    class Guard:
        """Fake spend guard that counts preflights and always approves."""
        preflights = 0

        def preflight(self, n, hold_seconds):
            """Test helper or fixture: preflight."""
            Guard.preflights += 1
            return {"ok": True, "reservation": "r", "projected_usd": 0.0}

        def release(self, r):
            """Test helper or fixture: release."""
            pass

        def settle(self, *a, **k):
            """Test helper or fixture: settle."""
            return 0.0

        def classify(self, t):
            """Test helper or fixture: classify."""
            return None

    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=Guard(), **over))
    assert r["ok"] is False and r["reason"] == ("invalid-metric-name" if "metric_name" in over else "invalid-trace")
    assert r["launched"] is False
    assert calls == [] and Guard.preflights == 0, "nothing may be reserved or launched"
    assert not list(tmp_path.glob("*.once"))


def test_a_timeout_reports_that_the_launcher_was_called(cycle, tmp_path, monkeypatch) -> None:
    """Check that a timeout reports that the launcher was called."""
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        """Test helper or fixture: boom."""
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(boom))
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True and r["spent"] is True


def test_a_spent_measurement_is_appended_to_the_ledger(cycle, tmp_path, monkeypatch) -> None:
    """Check that a spent measurement is appended to the ledger."""
    import json

    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    ledger = tmp_path / "evidence" / "ledger.jsonl"
    r = cycle.live_cycle(**_kwargs(tmp_path, ledger_path=ledger))
    assert r["ok"] is True
    rows = [json.loads(x) for x in ledger.read_text().splitlines()]
    assert rows == [r["trace"]]


def test_refusals_and_unmeasured_attempts_leave_the_ledger_alone(cycle, tmp_path, monkeypatch) -> None:
    """Check that refusals and unmeasured attempts leave the ledger alone."""
    _arm(monkeypatch, cycle)
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(returncode=2))
    assert cycle.live_cycle(**_kwargs(tmp_path, ledger_path=ledger))["reason"] == "launcher-failed"
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    assert cycle.live_cycle(**_kwargs(tmp_path / "b", ledger_path=ledger, evaluator_digest="bad"))["ok"] is False
    assert not ledger.exists()


def test_a_live_launch_without_a_ledger_is_refused_before_anything_is_reserved(cycle, tmp_path, monkeypatch) -> None:
    """Check that a live launch without a ledger is refused before anything is reserved."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, ledger_path=None))
    assert r["reason"] == "ledger-required" and r["launched"] is False
    assert calls == [] and guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_an_unwritable_marker_releases_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    """Check that an unwritable marker releases the reservation."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))

    def denied(marker):
        """Test helper or fixture: denied."""
        raise PermissionError("log_dir is not writable")

    monkeypatch.setattr(cycle, "_claim_once", denied)
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "marker-error" and r["launched"] is False
    assert calls == [] and guard.open_reservations() == [] and guard.released == ["r1"]


def test_a_failed_ledger_write_hands_the_spent_trace_back(cycle, tmp_path, monkeypatch) -> None:
    """Check that a failed ledger write hands the spent trace back."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    (tmp_path / "blocker").write_text("a file where a directory is needed")
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, ledger_path=tmp_path / "blocker" / "ledger.jsonl"))
    assert r["ok"] is False and r["reason"] == "ledger-write-failed" and r["recorded"] is False
    assert r["trace"]["decision"] in ("keep", "revert") and guard.settled == ["r1"]


def test_a_live_launch_without_a_spend_guard_is_refused_before_the_marker(cycle, tmp_path, monkeypatch) -> None:
    """Check that a live launch without a spend guard is refused before the marker."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=None))
    assert r["ok"] is False and r["reason"] == "spend-guard-required" and r["launched"] is False
    assert calls == [] and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("effort", ["xhigh", "max", "ultra", ""])
def test_an_invalid_effort_is_refused_before_anything_is_reserved(cycle, tmp_path, monkeypatch, effort) -> None:
    """Check that an invalid effort is refused before anything is reserved."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, effort=effort))
    assert r["reason"] == "invalid-effort" and r["launched"] is False
    assert calls == [] and guard.preflights == 0 and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("effort", ["medium", "high", "low", None])
def test_a_valid_effort_still_launches(cycle, tmp_path, monkeypatch, effort) -> None:
    """Check that a valid effort still launches."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard, effort=effort)
    if effort == "medium":
        model = cycle._contracts().WANDB_MODEL_ORDER[2]
        args["probe_record"]["models"] = [model]
        args["probe_record"]["efforts"] = {model: ["medium", "high", "low"]}
    elif effort == "low":
        args["probe_record"]["efforts"][cycle._contracts().WANDB_MODEL_ORDER[0]] = ["low"]
    r = cycle.live_cycle(**args)
    assert r["ok"] is True and guard.open_reservations() == []


def test_the_decision_table_is_pure_and_ordered(cycle) -> None:
    """Check that the decision table is pure and ordered."""
    ok = dict(gate_open=True, has_digest=True, metric_ok=True, protected=False, prompt_ok=True,
              card_errors=[], trace_problems=[], effort="high", efforts=cycle.EFFORTS, has_guard=True,
              has_ledger=True)
    assert cycle._launch_decision(**ok) == {}
    assert cycle._launch_decision(**{**ok, "gate_open": False, "has_guard": False, "effort": "xhigh"})["reason"] == "gate-closed"
    assert cycle._launch_decision(**{**ok, "has_guard": False, "effort": "xhigh"})["reason"] == "spend-guard-required"
    assert cycle._launch_decision(**{**ok, "has_ledger": False, "effort": "xhigh"})["reason"] == "invalid-effort"
    assert cycle._launch_decision(**{**ok, "has_ledger": False})["reason"] == "ledger-required"


def test_an_oserror_from_the_launcher_releases_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    """Check that an oserror from the launcher releases the reservation."""
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        """Test helper or fixture: boom."""
        raise OSError("exec failed")

    monkeypatch.setattr(cycle.subprocess, "Popen", boom)
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and r["called_launcher"] is False
    assert guard.open_reservations() == [] and guard.released == ["r1"]


def test_an_interrupt_during_the_run_settles_the_possibly_sent_request(cycle, tmp_path, monkeypatch) -> None:
    """The request may already have been sent, so the spend is recorded (settled), not released."""
    _arm(monkeypatch, cycle)

    def interrupted(argv, **kwargs):
        """Test helper or fixture: interrupted."""
        raise KeyboardInterrupt

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(interrupted))
    guard = _Guard()
    with pytest.raises(KeyboardInterrupt):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.open_reservations() == [] and guard.settled == ["r1"] and guard.released == []


def test_a_nul_byte_in_the_prompt_is_refused_before_the_marker(cycle, tmp_path, monkeypatch) -> None:
    """Check that a nul byte in the prompt is refused before the marker."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, prompt="hi\x00there"))
    assert r["ok"] is False and r["launched"] is False
    assert calls == [] and guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_a_valueerror_from_the_launcher_frees_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    """Check that a valueerror from the launcher frees the reservation."""
    _arm(monkeypatch, cycle)

    def refuses(argv, **kwargs):
        """Test helper or fixture: refuses."""
        raise ValueError("embedded null byte")

    monkeypatch.setattr(cycle.subprocess, "Popen", refuses)
    guard = _Guard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and guard.open_reservations() == [] and guard.released == ["r1"]


def test_missing_live_evidence_refuses_before_reservation(cycle, tmp_path, monkeypatch) -> None:
    """An armed cycle without a pin and probe cannot reserve or claim the attempt."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    result = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, pin_path=None))
    assert result["reason"] == "evaluator-pin-invalid"
    assert guard.preflights == 0
    assert not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("change", ["missing", "stale", "provider", "model", "effort", "malformed", "credentials"])
def test_invalid_probe_refuses_before_reservation(cycle, tmp_path, monkeypatch, change: str) -> None:
    """Probe evidence must match today's actual target, model, and accepted effort."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard)
    record = args["probe_record"]
    if change == "missing":
        args["probe_record"] = None
    elif change == "stale":
        record["date"] = "2000-01-01"
    elif change == "provider":
        record["provider"] = "https://example.com"
    elif change == "model":
        record["models"] = ["other"]
    elif change == "effort":
        record["efforts"][cycle._contracts().WANDB_MODEL_ORDER[0]] = []
    elif change == "malformed":
        record["models"] = [None]
    else:
        record["key"] = "never-store-credentials"
    result = cycle.live_cycle(**args)
    assert result["reason"] == "provider-probe-invalid"
    assert guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_mismatched_pin_refuses_before_reservation(cycle, tmp_path, monkeypatch) -> None:
    """A well-formed pin for a different evaluator cannot authorize a cycle."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard)
    args["pin_path"].write_text(json.dumps({"version": 1, "evaluator_digest": "a" * 64, "covers": ["v"]}))
    result = cycle.live_cycle(**args)
    assert result["reason"] == "evaluator-pin-invalid"
    assert guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_unknown_metric_without_digest_refuses_before_marker(cycle, tmp_path) -> None:
    """Dry cycles enforce the registry even when they do not record a trace."""
    result = cycle.dry_cycle("inner", "harden", 1.0, 0.5, tmp_path, metric_name="not_declared")
    assert result["reason"] == "invalid-metric-name"
    assert not list(tmp_path.glob("*.once"))


def test_malformed_pin_refuses_before_reservation(cycle, tmp_path, monkeypatch) -> None:
    """A corrupt pin cannot authorize the evaluator."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard)
    args["pin_path"].write_text("not json")
    result = cycle.live_cycle(**args)
    assert result["reason"] == "evaluator-pin-invalid"
    assert guard.preflights == 0 and not list(tmp_path.glob("*.once"))


def test_unknown_live_metric_refuses_before_reservation(cycle, tmp_path, monkeypatch) -> None:
    """A live cycle cannot reserve for an undeclared metric."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    result = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, metric_name="not_declared"))
    assert result["reason"] == "invalid-metric-name"
    assert guard.preflights == 0 and not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("bad_model", ["paid-model", "invalid\x00model"])
def test_unlisted_model_is_refused_before_reservation(cycle, tmp_path, monkeypatch, bad_model: str) -> None:
    """An injected probe cannot authorize models outside the free policy."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard, model=bad_model)
    args["probe_record"]["models"] = [bad_model]
    args["probe_record"]["efforts"] = {bad_model: ["high"]}
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    result = cycle.live_cycle(**args)
    assert not result["ok"] and guard.preflights == 0
    assert not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("wrap", [dict, MappingProxyType])
def test_live_cycle_checks_card_digest_before_launch(cycle, tmp_path, monkeypatch, wrap) -> None:
    """A card from another evaluator cannot consume a live attempt."""
    _arm(monkeypatch, cycle)
    calls = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    card = wrap(_card(evaluator_digest="c" * 64))
    result = cycle.live_cycle(**_kwargs(tmp_path, mechanism_card=card))
    assert result["reason"] == "invalid-card" and not calls
    assert not list(tmp_path.glob("*.once"))


def test_live_cycle_accepts_graduated_card_only_with_matching_real_pin(cycle, tmp_path, monkeypatch) -> None:
    """Live validation uses the separately read pin, not the supplied run digest."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    candidate = _card()
    checked = cycle.dry_cycle("inner", "harden", 2.0, 1.0, tmp_path / "dry", evaluator_digest=DIGEST, mechanism_card=candidate)
    graduated = {**candidate, "status": "graduated", "dry_run_receipt": checked}
    result = cycle.live_cycle(**_kwargs(tmp_path / "good", mechanism_card=graduated))
    assert result["ok"]
    args = _kwargs(tmp_path / "bad", mechanism_card=graduated)
    args["pin_path"].write_text(json.dumps({"version": 1, "evaluator_digest": "c" * 64, "covers": ["verifier.py"]}))
    result = cycle.live_cycle(**args)
    assert not result["ok"] and not list((tmp_path / "bad").glob("*.once"))


def test_lower_effort_refused_when_higher_is_supported(cycle, tmp_path, monkeypatch) -> None:
    """An explicit low effort cannot bypass the free effort ladder."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard, effort="low")
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    result = cycle.live_cycle(**args)
    assert not result["ok"] and guard.preflights == 0
    assert not list(tmp_path.glob("*.once"))


@pytest.mark.parametrize("index,effort", [(1, "high"), (2, "medium")])
def test_default_selects_first_available_model_and_effort(cycle, tmp_path, monkeypatch, index: int, effort: str) -> None:
    """Missing earlier models cause a free-policy fallback with the right launcher arguments."""
    _arm(monkeypatch, cycle)
    contracts = cycle._contracts()
    model = contracts.WANDB_MODEL_ORDER[index]
    args = _kwargs(tmp_path)
    args["probe_record"]["models"] = [model]
    args["probe_record"]["efforts"] = {model: list(contracts.WANDB_EFFORTS[model])}
    calls = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    result = cycle.live_cycle(**args)
    assert result["ok"]
    argv = calls[0][0]
    assert argv[argv.index("--model") + 1] == model
    assert argv[argv.index("--effort") + 1] == effort


def test_explicit_later_model_cannot_skip_available_first(cycle, tmp_path, monkeypatch) -> None:
    """Explicit selections cannot skip an available earlier free model."""
    _arm(monkeypatch, cycle)
    order = cycle._contracts().WANDB_MODEL_ORDER
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard, model=order[1])
    args["probe_record"]["models"] = [order[1], order[0]]
    args["probe_record"]["efforts"][order[1]] = ["high"]
    result = cycle.live_cycle(**args)
    assert not result["ok"] and guard.preflights == 0
    assert not list(tmp_path.glob("*.once"))


def test_probe_cannot_expand_canonical_effort_support(cycle, tmp_path, monkeypatch) -> None:
    """A new provider capability requires a canonical policy update before use."""
    _arm(monkeypatch, cycle)
    guard = _Guard()
    args = _kwargs(tmp_path, spend_guard=guard)
    args["probe_record"]["efforts"][cycle._contracts().WANDB_MODEL_ORDER[0]] = ["medium", "high"]
    result = cycle.live_cycle(**args)
    assert not result["ok"] and guard.preflights == 0
    assert not list(tmp_path.glob("*.once"))
