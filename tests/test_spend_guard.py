"""Orama's adapter to the shared spend guard in Perpetua-Tools, and its use by the live cycle.

The adapter tests need a Perpetua-Tools checkout (PERPETUA_TOOLS_ROOT) and skip without one. The live
cycle tests use a fake guard and need nothing.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "c" * 64
HOLD = 60.0


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _pt_available() -> bool:
    """True when the adapter can resolve a Perpetua-Tools checkout (argument, variable or symlink)."""
    try:
        probe = _load("bin/agents/spend_guard.py", "spend_guard_probe")
        probe.resolve_pt_root(os.environ.get("ORAMA_TEST_PT_ROOT"))
        return True
    except Exception:
        return False


# In CI a missing guard must fail loudly, never skip to a green check that proves nothing.
needs_pt = pytest.mark.skipif(
    not _pt_available() and not os.environ.get("CI"),
    reason="needs a Perpetua-Tools checkout: ORAMA_TEST_PT_ROOT, PERPETUA_TOOLS_ROOT or the .local symlink",
)


@pytest.fixture()
def sg():
    return _load("bin/agents/spend_guard.py", "spend_guard")


@pytest.fixture()
def sg_isolated(sg, tmp_path_factory):
    # For tests that assert "no guard anywhere" or pick the candidate themselves. CI really has a checkout
    # at CI_CHECKOUT, which would otherwise satisfy them. Tests that need the real guard use `sg`, which
    # keeps that fallback, because in CI it is the only way they find the guard.
    sg.CI_CHECKOUT = tmp_path_factory.getbasetemp() / "no-ci-checkout"
    return sg


@pytest.fixture()
def cycle():
    return _load("bin/agents/biafra_cycle.py", "biafra_cycle")


# --- the adapter --------------------------------------------------------------------------------


def test_a_missing_perpetua_tools_checkout_fails_closed(sg_isolated, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(state_dir=tmp_path)
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(pt_root=tmp_path / "nowhere", state_dir=tmp_path)


def _attest(tmp_path: Path, **over) -> None:
    path = tmp_path / "provider-attestations" / "wandb-inference.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "provider": "wandb-inference", "attested_at": datetime.now(timezone.utc).isoformat(),
        "attested_by": "operator", "plan_is_free": True, "payg_inactive": True, "allowance_remaining": True,
    }
    record.update(over)
    path.write_text(json.dumps(record))


@needs_pt
def test_no_attestation_means_no_request(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    r = g.preflight(10_000, HOLD)
    assert r["ok"] is False and r["reason"] == "attestation-required" and r["stop"] is True
    assert any("missing" in x for x in r["reasons"])


@needs_pt
@pytest.mark.parametrize("over", [{"payg_inactive": False}, {"allowance_remaining": False}, {"plan_is_free": "yes"}])
def test_an_attestation_that_does_not_clear_every_field_is_refused(sg, tmp_path, monkeypatch, over) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path, **over)
    assert sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend").preflight(1000, HOLD)["reason"] == "attestation-required"


@needs_pt
def test_a_valid_attestation_reserves_and_settling_records_a_size_only_audit_row(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    pre = g.preflight(10_000, HOLD)
    assert pre["ok"] is True and pre["projected_usd"] > 0
    usd = g.settle(pre["reservation"], input_chars=10_000, output_chars=40_000, outcome="ok", seat="inner", mode="inner")
    assert usd > 0
    rows = [json.loads(x) for x in (tmp_path / "spend" / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["input_chars"] == 10_000 and rows[0]["outcome"] == "ok"
    assert not ({"prompt", "answer", "api_key"} & set(rows[0]))
    snap = g.snapshot()
    assert snap["period"] == "monthly" and snap["daily_budget"] == 90 and snap["daily_spend"] == pytest.approx(usd)


@needs_pt
def test_the_budget_stops_the_next_request(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    g.gate.guard.record_spend(89.999)
    r = g.preflight(10_000, HOLD)
    assert r["ok"] is False and r["reason"] == "budget-exhausted" and r["stop"] is True


@needs_pt
def test_a_released_reservation_frees_the_budget(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    g.gate.guard.record_spend(89.9)
    first = g.preflight(10_000, HOLD)
    assert first["ok"] is True
    assert g.preflight(10_000, HOLD)["ok"] is False          # the first reservation still holds the budget
    g.release(first["reservation"])
    assert g.preflight(10_000, HOLD)["ok"] is True


@needs_pt
def test_the_guard_classifies_provider_failures_with_the_shared_policy(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    assert g.classify("You exceeded your current quota") == "provider-payment-required"
    assert g.classify("429 Concurrency limit reached") == "provider-rate-limited"
    assert g.classify("error: Invalid request") is None


# --- the live cycle with a fake guard (no Perpetua-Tools needed) --------------------------------


class FakeGuard:
    def __init__(self, pre=None, classify=None):
        self.pre = pre or {"ok": True, "reservation": "r1", "projected_usd": 0.05}
        self.settled = []
        self.released = []
        self.unknown = []
        self._classify = classify

    def preflight(self, prompt_chars, hold_seconds):
        self.prompt_chars = prompt_chars
        self.hold_seconds = hold_seconds
        return self.pre

    def settle(self, reservation, input_chars, output_chars, outcome, seat, mode):
        self.settled.append((reservation, input_chars, output_chars, outcome, seat, mode))
        return 0.0123

    def settle_unknown(self, reservation, input_chars, outcome, seat, mode):
        self.unknown.append((reservation, input_chars, outcome, seat, mode))
        return 0.05

    def release(self, reservation):
        self.released.append(reservation)

    def classify(self, text):
        return self._classify(text) if self._classify else None


def _fake_run(stdout="ANSWER", stderr="", returncode=0, calls=None):
    def run(argv, **kwargs):
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout.encode(), stderr=stderr.encode())

    return run


def _arm(monkeypatch, cycle) -> None:
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")


def _kwargs(tmp_path: Path, **over):
    base = dict(
        seat="inner", task_type="harden", prompt="Improve X.", log_dir=tmp_path / "log",
        evaluate=lambda a: {"metric_after": 1.0}, metric_before=3.0, artifact="a.b",
        evaluator_digest=DIGEST, hypothesis="h", metric_name="m", ledger_path=tmp_path / "ledger.jsonl",
    )
    base.update(over)
    return base


def test_a_refusing_guard_stops_the_cycle_before_any_launch_or_marker(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(calls=calls))
    guard = FakeGuard(pre={"ok": False, "reason": "attestation-required", "stop": True, "reasons": ["missing"]})
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["ok"] is False and r["reason"] == "attestation-required" and r["stop"] is True
    assert calls == [] and not list((tmp_path / "log").glob("*.once")) and guard.settled == []


def test_a_request_is_settled_with_sizes_and_the_estimate_is_returned(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(stdout="x" * 5000, stderr="y" * 100))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["ok"] is True and r["estimated_usd"] == 0.0123
    assert guard.prompt_chars == len("Improve X.")
    assert guard.settled == [("r1", len("Improve X."), 5100, "ok", "inner", "inner")]


def test_a_failed_launch_is_still_settled_as_spent(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(stdout="partial", returncode=2))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-failed" and r["estimated_usd"] == 0.0123
    assert guard.settled[0][3] == "failed"


def test_the_shared_classifier_decides_a_provider_stop(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run(stderr="weird provider text", returncode=1))
    guard = FakeGuard(classify=lambda text: "provider-payment-required")
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "provider-payment-required" and r["stop"] is True and r["retries"] == 0


def test_an_already_spent_attempt_releases_its_reservation(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    first = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=FakeGuard()))
    assert first["ok"] is True
    guard = FakeGuard()
    again = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert again["reason"] == "already-ran" and guard.released == ["r1"] and guard.settled == []


def test_a_timeout_settles_as_unknown_output_never_as_zero(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "run", boom)
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-timeout" and r["spent"] is True and r["called_launcher"] is True
    assert guard.settled == [] and guard.released == []
    assert guard.unknown == [("r1", len("Improve X."), "timeout", "inner", "inner")]


def test_the_old_ledger_parameters_are_gone(cycle) -> None:
    import inspect

    params = inspect.signature(cycle.live_cycle).parameters
    assert "spend_guard" in params and "spend_ledger" not in params and "budget_usd" not in params



# --- resolving the Perpetua-Tools checkout: argument, environment, then one documented symlink ----------


def _fake_pt(root: Path) -> Path:
    (root / "orchestrator").mkdir(parents=True)
    for name in ("provider_limits.py", "cost_guard.py", "spend_gate.py"):
        (root / "orchestrator" / name).write_text("# stub\n")
    return root


def test_the_root_resolves_argument_then_environment_then_the_symlink(sg_isolated, tmp_path, monkeypatch) -> None:
    arg, env, link = _fake_pt(tmp_path / "arg"), _fake_pt(tmp_path / "env"), _fake_pt(tmp_path / "link")
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "linkname")
    (tmp_path / "linkname").symlink_to(link)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(env))
    assert sg_isolated.resolve_pt_root(arg) == arg.resolve()
    assert sg_isolated.resolve_pt_root(None) == env.resolve()
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT")
    assert sg_isolated.resolve_pt_root(None) == link.resolve()


def test_no_argument_no_variable_and_no_symlink_fails_closed(sg_isolated, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(None)


def test_the_ci_checkout_is_the_last_resort(sg_isolated, tmp_path, monkeypatch) -> None:
    ci = _fake_pt(tmp_path / "ci")
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    monkeypatch.setattr(sg_isolated, "CI_CHECKOUT", ci)
    assert sg_isolated.resolve_pt_root(None) == ci.resolve()
    env = _fake_pt(tmp_path / "env")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(env))
    assert sg_isolated.resolve_pt_root(None) == env.resolve()


def test_a_dangling_or_wrong_symlink_is_refused(sg_isolated, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "link")
    (tmp_path / "link").symlink_to(tmp_path / "nowhere")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(None)
    (tmp_path / "link").unlink()
    (tmp_path / "empty").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "empty")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(None)


def test_an_environment_checkout_without_the_guard_falls_through_to_the_symlink(sg, tmp_path, monkeypatch) -> None:
    stale = tmp_path / "stale"
    (stale / "orchestrator").mkdir(parents=True)          # an older checkout: no shared guard in it yet
    link = _fake_pt(tmp_path / "link")
    monkeypatch.setattr(sg, "LOCAL_LINK", tmp_path / "linkname")
    (tmp_path / "linkname").symlink_to(link)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(stale))
    assert sg.resolve_pt_root(None) == link.resolve()


def test_an_explicit_root_must_be_valid_and_never_falls_through(sg, tmp_path, monkeypatch) -> None:
    good = _fake_pt(tmp_path / "good")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(good))
    with pytest.raises(sg.SpendGuardUnavailable):
        sg.resolve_pt_root(tmp_path / "typo")


def test_when_no_candidate_holds_the_guard_every_reason_is_reported(sg_isolated, tmp_path, monkeypatch) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(stale))
    with pytest.raises(sg_isolated.SpendGuardUnavailable) as info:
        sg_isolated.resolve_pt_root(None)
    assert "PERPETUA_TOOLS_ROOT" in str(info.value)


@needs_pt
def test_releasing_a_reservation_that_is_already_closed_is_a_no_op(sg, tmp_path) -> None:
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    g.release("never-reserved")  # must not raise: cleanup may follow a settle that already closed it


@needs_pt
def test_the_adapter_loads_the_producer_gate_and_adds_no_ledger_of_its_own(sg, tmp_path) -> None:
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    assert g.gate.__class__.__name__ == "SpendGate" and g.gate.guard is g.guard
    assert g.audit_path == g.gate.audit_path and g.policy is g.gate.policy
    assert not hasattr(g, "_ledger") and not hasattr(g, "reservations")


@needs_pt
def test_two_adapter_instances_share_one_ceiling(sg, tmp_path, monkeypatch) -> None:
    """Review finding 2 through the adapter: independent instances must not both spend the last dollars."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    one = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    two = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    one.gate.guard.record_spend(89.9)
    a = one.preflight(10_000, HOLD)
    b = two.preflight(10_000, HOLD)
    assert a["ok"] is True
    assert b["ok"] is False and b["reason"] == "budget-exhausted"
    one.release(a["reservation"])
    assert two.preflight(10_000, HOLD)["ok"] is True


@needs_pt
def test_settle_unknown_charges_the_whole_reservation_and_marks_the_output_unknown(sg, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    pre = g.preflight(10_000, HOLD)
    usd = g.settle_unknown(pre["reservation"], 10_000, "timeout", "inner", "inner")
    assert usd == pytest.approx(pre["projected_usd"])
    rows = [json.loads(x) for x in (tmp_path / "spend" / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert rows[0]["outcome"] == "timeout" and "output_chars" not in rows[0]
    assert g.snapshot()["daily_spend"] == pytest.approx(usd)


def test_a_checkout_without_the_spend_gate_is_not_a_guard(sg_isolated, tmp_path, monkeypatch) -> None:
    root = _fake_pt(tmp_path / "old")
    (root / "orchestrator" / "spend_gate.py").unlink()
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(root)
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(pt_root=root, state_dir=tmp_path)


# --- review finding 3: the reservation outlives the whole allowed launch -------------------------------


def test_live_cycle_declares_a_hold_longer_than_the_launcher_timeout(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "run", _fake_run())
    guard = FakeGuard()
    cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, timeout_s=900))
    assert guard.hold_seconds == 900 + cycle.SETTLE_MARGIN_S and cycle.SETTLE_MARGIN_S > 0


@needs_pt
def test_a_running_launch_cannot_be_swept_by_another_reservation(sg, cycle, tmp_path, monkeypatch) -> None:
    """Finding 3 on the real gate: a second reservation just past the timeout must not free the first."""
    import time as real_time

    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    _arm(monkeypatch, cycle)
    spend = tmp_path / "spend"
    first = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=spend)
    other = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=spend)
    first.gate.guard.record_spend(89.9)  # room for exactly one request
    clock = {"skew": 0.0}
    base = real_time.time
    monkeypatch.setattr(real_time, "time", lambda: base() + clock["skew"])
    seen: dict = {}

    def slow_launch(argv, **kwargs):
        clock["skew"] = 100 + 1  # the launcher is still inside its 100 s timeout, plus one second
        seen["second"] = other.preflight(10_000, 60.0)
        clock["skew"] = 100 + cycle.SETTLE_MARGIN_S - 1
        return subprocess.CompletedProcess(argv, 0, stdout="ANSWER", stderr="")

    monkeypatch.setattr(cycle.subprocess, "run", slow_launch)
    result = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=first, timeout_s=100, prompt="x" * 10_000))
    assert seen["second"]["ok"] is False and seen["second"]["reason"] == "budget-exhausted"
    assert result["ok"] is True
    rows = [json.loads(x) for x in (spend / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and "basis" not in rows[0]  # settled in time, not as a late commit


# --- review finding 4: a post-start output problem is not a pre-start failure ---------------------------


def _child(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_invalid_utf8_output_is_settled_decoded_with_replacement_and_counts_as_a_launch(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle, "launcher_argv",
        lambda seat, prompt=None, effort=None: _child("import sys; sys.stdout.buffer.write(b'AB\\xffCD')"),
    )
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["called_launcher"] is True and r.get("reason") != "launcher-error"
    assert guard.released == [] and len(guard.settled) == 1 and guard.settled[0][3] == "ok"
    assert r["ok"] is True and r["answer"] == "AB\ufffdCD"


def test_a_launcher_that_cannot_start_still_releases_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle, "launcher_argv", lambda seat, prompt=None, effort=None: [str(tmp_path / "no-such-launcher")]
    )
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and r["called_launcher"] is False
    assert guard.released == ["r1"] and guard.settled == [] and guard.unknown == []


def test_an_interrupt_settles_unknown_and_reraises(cycle, tmp_path, monkeypatch) -> None:
    _arm(monkeypatch, cycle)

    def interrupted(argv, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cycle.subprocess, "run", interrupted)
    guard = FakeGuard()
    with pytest.raises(KeyboardInterrupt):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.settled == [] and guard.released == []
    assert guard.unknown == [("r1", len("Improve X."), "interrupted", "inner", "inner")]


@needs_pt
def test_a_timeout_commits_the_full_reservation_on_the_real_gate(sg, cycle, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    _arm(monkeypatch, cycle)
    guard = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    monkeypatch.setattr(
        cycle, "launcher_argv", lambda seat, prompt=None, effort=None: _child("import time; time.sleep(30)")
    )
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, timeout_s=1, prompt="x" * 10_000))
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True
    rows = [json.loads(x) for x in (tmp_path / "spend" / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert rows[0]["outcome"] == "timeout" and rows[0]["basis"] == "output-unknown" and "output_chars" not in rows[0]
    assert guard.snapshot()["daily_spend"] == pytest.approx(guard.gate.pl.projected_usd(guard.policy, 10_000))
