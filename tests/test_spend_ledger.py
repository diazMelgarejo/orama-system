"""A monthly spend estimate and guard for live provider requests. Estimates, not billing."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "c" * 64


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sl():
    return _load("bin/agents/spend_ledger.py", "spend_ledger")


@pytest.fixture()
def cycle():
    return _load("bin/agents/biafra_cycle.py", "biafra_cycle")


NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def test_the_estimate_uses_chars_over_four_and_conservative_list_rates(sl) -> None:
    usd = sl.estimate_usd(input_chars=4_000_000, output_chars=4_000_000)  # 1M tokens each
    assert usd == pytest.approx(sl.INPUT_USD_PER_M + sl.OUTPUT_USD_PER_M)
    assert sl.INPUT_USD_PER_M == 0.50 and sl.OUTPUT_USD_PER_M == 1.50


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), True, None, "10"])
def test_the_estimate_refuses_nonsense_sizes(sl, bad) -> None:
    with pytest.raises(ValueError):
        sl.estimate_usd(input_chars=bad, output_chars=10)
    with pytest.raises(ValueError):
        sl.estimate_usd(input_chars=10, output_chars=bad)


def test_append_and_month_total_sum_only_the_requested_month(sl, tmp_path: Path) -> None:
    led = tmp_path / "spend.jsonl"
    sl.append(led, {"ts": "2026-10-31T23:59:00+00:00", "estimated_usd": 5.0, "seat": "inner"})
    sl.append(led, {"ts": "2026-11-02T01:00:00+00:00", "estimated_usd": 1.25, "seat": "inner"})
    sl.append(led, {"ts": "2026-11-16T01:00:00+00:00", "estimated_usd": 0.75, "seat": "outer"})
    assert sl.month_total(led, NOW) == pytest.approx(2.0)
    assert sl.month_total(tmp_path / "missing.jsonl", NOW) == 0.0


def test_a_corrupt_or_foreign_row_is_refused_not_ignored(sl, tmp_path: Path) -> None:
    led = tmp_path / "spend.jsonl"
    led.write_text('{"ts": "2026-11-02T01:00:00+00:00", "estimated_usd": "free"}\n')
    with pytest.raises(ValueError):
        sl.month_total(led, NOW)
    led.write_text("not json\n")
    with pytest.raises(ValueError):
        sl.month_total(led, NOW)


def test_the_guard_refuses_when_the_projection_would_pass_the_budget(sl, tmp_path: Path) -> None:
    led = tmp_path / "spend.jsonl"
    sl.append(led, {"ts": NOW.isoformat(), "estimated_usd": 89.99, "seat": "inner"})
    verdict = sl.check_budget(led, budget_usd=90.0, projected_usd=0.05, now=NOW)
    assert verdict["ok"] is False and verdict["reason"] == "budget-exhausted"
    assert verdict["month_total_usd"] == pytest.approx(89.99)
    assert sl.check_budget(led, budget_usd=90.0, projected_usd=0.005, now=NOW)["ok"] is True


@pytest.mark.parametrize("bad", [0, -5, float("nan"), True, None])
def test_a_bad_budget_is_refused(sl, tmp_path: Path, bad) -> None:
    with pytest.raises(ValueError):
        sl.check_budget(tmp_path / "x.jsonl", budget_usd=bad, projected_usd=1.0, now=NOW)


# --- wired into the live cycle -------------------------------------------------------------


def _fake(stdout="ANSWER", returncode=0, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr="")

    return run


def _kwargs(tmp_path: Path, **over):
    base = dict(
        seat="inner", task_type="harden", prompt="Improve X.", log_dir=tmp_path / "log",
        evaluate=lambda a: {"metric_after": 1.0}, metric_before=3.0, artifact="a.b",
        evaluator_digest=DIGEST, hypothesis="h", metric_name="m",
    )
    base.update(over)
    return base


def test_live_cycle_refuses_before_any_launch_when_the_budget_is_spent(cycle, sl, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    led = tmp_path / "spend.jsonl"
    sl.append(led, {"ts": NOW.isoformat(), "estimated_usd": 89.999, "seat": "inner"})
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake(calls=calls))
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_ledger=led, budget_usd=90.0, now=NOW))
    assert r["ok"] is False and r["reason"] == "budget-exhausted" and r["stop"] is True
    assert calls == [] and not list((tmp_path / "log").glob("*.once"))


def test_live_cycle_records_an_estimate_after_a_request(cycle, sl, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    led = tmp_path / "spend.jsonl"
    monkeypatch.setattr(cycle.subprocess, "run", _fake(stdout="x" * 40_000))
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_ledger=led, budget_usd=90.0, now=NOW))
    assert r["ok"] is True and r["estimated_usd"] > 0
    rows = [json.loads(line) for line in led.read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["seat"] == "inner" and rows[0]["estimated"] is True
    assert rows[0]["output_chars"] >= 40_000 and "prompt" not in rows[0] and "answer" not in rows[0]
    assert sl.month_total(led, NOW) == pytest.approx(r["estimated_usd"])


def test_a_failed_request_is_still_recorded_as_spent(cycle, sl, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    led = tmp_path / "spend.jsonl"
    monkeypatch.setattr(cycle.subprocess, "run", _fake(stdout="partial " * 1000, returncode=2))
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_ledger=led, budget_usd=90.0, now=NOW))
    assert r["reason"] == "launcher-failed" and len(led.read_text().splitlines()) == 1


def test_without_a_ledger_nothing_changes(cycle, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    monkeypatch.setattr(cycle.subprocess, "run", _fake())
    r = cycle.live_cycle(**_kwargs(tmp_path))
    assert r["ok"] is True and "estimated_usd" not in r


def test_a_ledger_without_a_budget_is_refused(cycle, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_ledger=tmp_path / "s.jsonl"))
    assert r["ok"] is False and r["reason"] == "budget-required"
