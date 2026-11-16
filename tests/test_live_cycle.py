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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def cycle():
    return _load(ROOT / "bin/agents/biafra_cycle.py", "biafra_cycle")


def _fake_run(stdout: str = DIM + "thinking..." + RESET + "ANSWER TEXT", returncode: int = 0, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")

    return run


def _arm(monkeypatch, cycle) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")


def _kwargs(tmp_path: Path, **over):
    base = dict(
        seat="inner", task_type="harden", prompt="Improve X. Return only code.", log_dir=tmp_path,
        evaluate=lambda answer: {"metric_after": 1.0, "detail": answer}, metric_before=3.0,
        artifact="seat_contracts._owner_folded", evaluator_digest=DIGEST,
        hypothesis="handle leetspeak", metric_name="heldout_wrong",
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
