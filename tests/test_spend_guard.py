"""Orama's adapter to the shared spend guard in Perpetua-Tools, and its use by the live cycle.

The adapter tests need a Perpetua-Tools checkout (PERPETUA_TOOLS_ROOT) and skip without one. The live
cycle tests use a fake guard and need nothing.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import pytest
from _fake_popen import as_popen

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "c" * 64
HOLD = 60.0


pytestmark = pytest.mark.usefixtures("offline_guard")

def _load(rel: str, name: str):
    """Test helper or fixture: load."""
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
def sg() -> ModuleType:
    """Test helper or fixture: sg."""
    return _load("bin/agents/spend_guard.py", "spend_guard")


@pytest.fixture()
def sg_isolated(sg: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> ModuleType:
    # For tests that assert "no guard anywhere" or pick the candidate themselves. CI really has a checkout
    # at CI_CHECKOUT, which would otherwise satisfy them. Tests that need the real guard use `sg`, which
    # keeps that fallback, because in CI it is the only way they find the guard.
    """Test helper or fixture: sg isolated."""
    sg.CI_CHECKOUT = tmp_path_factory.getbasetemp() / "no-ci-checkout"
    return sg


@pytest.fixture()
def cycle():
    """Test helper or fixture: cycle."""
    return _load("bin/agents/biafra_cycle.py", "biafra_cycle")


# --- the adapter --------------------------------------------------------------------------------


def test_a_missing_perpetua_tools_checkout_fails_closed(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that a missing perpetua tools checkout fails closed."""
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(state_dir=tmp_path)
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(pt_root=tmp_path / "nowhere", state_dir=tmp_path)


def _attest(tmp_path: Path, **over) -> None:
    """Test helper or fixture: attest."""
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
    """Check that no attestation means no request."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    r = g.preflight(10_000, HOLD)
    assert r["ok"] is False and r["reason"] == "attestation-required" and r["stop"] is True
    assert any("missing" in x for x in r["reasons"])


@needs_pt
@pytest.mark.parametrize("over", [{"payg_inactive": False}, {"allowance_remaining": False}, {"plan_is_free": "yes"}])
def test_an_attestation_that_does_not_clear_every_field_is_refused(sg, tmp_path, monkeypatch, over) -> None:
    """Check that an attestation that does not clear every field is refused."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path, **over)
    assert sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend").preflight(1000, HOLD)["reason"] == "attestation-required"


@needs_pt
def test_a_valid_attestation_reserves_and_settling_records_a_size_only_audit_row(sg, tmp_path, monkeypatch) -> None:
    """Check that a valid attestation reserves and settling records a size only audit row."""
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
    """Check that the budget stops the next request."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    g.gate.guard.record_spend(89.999)
    r = g.preflight(10_000, HOLD)
    assert r["ok"] is False and r["reason"] == "budget-exhausted" and r["stop"] is True


@needs_pt
def test_a_released_reservation_frees_the_budget(sg, tmp_path, monkeypatch) -> None:
    """Check that a released reservation frees the budget."""
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
    """Check that the guard classifies provider failures with the shared policy."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    assert g.classify("You exceeded your current quota") == "provider-payment-required"
    assert g.classify("429 Concurrency limit reached") == "provider-rate-limited"
    assert g.classify("error: Invalid request") is None


# --- the live cycle with a fake guard (no Perpetua-Tools needed) --------------------------------


class FakeGuard:
    """Recording fake spend guard with a canned preflight result and optional classifier."""
    def __init__(
        self, pre: dict[str, Any] | None = None, classify: Callable[[str], str | None] | None = None,
    ) -> None:
        """Test helper or fixture: init  ."""
        self.pre = pre or {"ok": True, "reservation": "r1", "projected_usd": 0.05}
        self.settled = []
        self.released = []
        self.unknown = []
        self._classify = classify

    def preflight(self, prompt_chars: int, hold_seconds: float) -> dict[str, Any]:
        """Test helper or fixture: preflight."""
        self.prompt_chars = prompt_chars
        self.hold_seconds = hold_seconds
        return self.pre

    def settle(
        self, reservation: str, input_chars: int, output_chars: int, outcome: str, seat: str, mode: str,
    ) -> float:
        """Test helper or fixture: settle."""
        self.settled.append((reservation, input_chars, output_chars, outcome, seat, mode))
        return 0.0123

    def settle_unknown(
        self, reservation: str, input_chars: int, outcome: str, seat: str, mode: str,
    ) -> float:
        """Test helper or fixture: settle unknown."""
        self.unknown.append((reservation, input_chars, outcome, seat, mode))
        return 0.05

    def release(self, reservation: str) -> None:
        """Test helper or fixture: release."""
        self.released.append(reservation)

    def classify(self, text: str) -> str | None:
        """Test helper or fixture: classify."""
        return self._classify(text) if self._classify else None


def _fake_run(stdout="ANSWER", stderr="", returncode=0, calls=None):
    """Test helper or fixture: fake run."""
    def run(argv, **kwargs):
        """Test helper or fixture: run."""
        if calls is not None:
            calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout.encode(), stderr=stderr.encode())

    return as_popen(run)


def _arm(monkeypatch, cycle) -> None:
    """Test helper or fixture: arm."""
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    # Historical lifecycle tests exercise an explicitly simulated supported launcher.
    monkeypatch.setattr(cycle, "_launcher_boundary_problem", lambda: None)


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
        seat="inner", task_type="harden", prompt="Improve X.", log_dir=tmp_path / "log",
        evaluate=lambda a: {"metric_after": 1.0}, metric_before=3.0, artifact="a.b",
        evaluator_digest=DIGEST, hypothesis="h", metric_name="metric", ledger_path=tmp_path / "ledger.jsonl",
    )
    base.update(over)
    return base


def test_a_refusing_guard_stops_the_cycle_before_any_launch_or_marker(cycle, tmp_path, monkeypatch) -> None:
    """Check that a refusing guard stops the cycle before any launch or marker."""
    _arm(monkeypatch, cycle)
    calls: list = []
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(calls=calls))
    guard = FakeGuard(pre={"ok": False, "reason": "attestation-required", "stop": True, "reasons": ["missing"]})
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["ok"] is False and r["reason"] == "attestation-required" and r["stop"] is True
    assert calls == [] and not list((tmp_path / "log").glob("*.once")) and guard.settled == []


def test_a_request_is_settled_with_sizes_and_the_estimate_is_returned(cycle, tmp_path, monkeypatch) -> None:
    """Check that a request is settled with sizes and the estimate is returned."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(stdout="x" * 5000, stderr="y" * 100))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["ok"] is True and r["estimated_usd"] == 0.0123
    assert guard.prompt_chars == len("Improve X.")
    assert guard.settled == [("r1", len("Improve X."), 5100, "ok", "inner", "inner")]


def test_a_failed_launch_is_still_settled_as_spent(cycle, tmp_path, monkeypatch) -> None:
    """Check that a failed launch is still settled as spent."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(stdout="partial", returncode=2))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-failed" and r["estimated_usd"] == 0.0123
    assert guard.settled[0][3] == "failed"


def test_the_shared_classifier_decides_a_provider_stop(cycle, tmp_path, monkeypatch) -> None:
    """Check that the shared classifier decides a provider stop."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(stderr="weird provider text", returncode=1))
    guard = FakeGuard(classify=lambda text: "provider-payment-required")
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "provider-payment-required" and r["stop"] is True and r["retries"] == 0


def test_an_already_spent_attempt_releases_its_reservation(cycle, tmp_path, monkeypatch) -> None:
    """Check that an already spent attempt releases its reservation."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
    first = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=FakeGuard()))
    assert first["ok"] is True
    guard = FakeGuard()
    again = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert again["reason"] == "already-ran" and guard.released == ["r1"] and guard.settled == []


def test_a_timeout_settles_as_unknown_output_never_as_zero(cycle, tmp_path, monkeypatch) -> None:
    """Check that a timeout settles as unknown output never as zero."""
    _arm(monkeypatch, cycle)

    def boom(argv, **kwargs):
        """Test helper or fixture: boom."""
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(boom))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-timeout" and r["spent"] is True and r["called_launcher"] is True
    assert guard.settled == [] and guard.released == []
    assert guard.unknown == [("r1", len("Improve X."), "timeout", "inner", "inner")]


def test_the_old_ledger_parameters_are_gone(cycle) -> None:
    """Check that the old ledger parameters are gone."""
    import inspect

    params = inspect.signature(cycle.live_cycle).parameters
    assert "spend_guard" in params and "spend_ledger" not in params and "budget_usd" not in params



# --- resolving the Perpetua-Tools checkout: argument, environment, then one documented symlink ----------


def _fake_pt(root: Path) -> Path:
    """Test helper or fixture: fake pt."""
    (root / "orchestrator").mkdir(parents=True)
    for name in ("provider_limits.py", "cost_guard.py", "spend_gate.py"):
        (root / "orchestrator" / name).write_text("# stub\n")
    return root


def test_the_root_resolves_argument_then_environment_then_the_symlink(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that the root resolves argument then environment then the symlink."""
    arg, env, link = _fake_pt(tmp_path / "arg"), _fake_pt(tmp_path / "env"), _fake_pt(tmp_path / "link")
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "linkname")
    (tmp_path / "linkname").symlink_to(link)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(env))
    assert sg_isolated.resolve_pt_root(arg) == arg.resolve()
    assert sg_isolated.resolve_pt_root(None) == env.resolve()
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT")
    assert sg_isolated.resolve_pt_root(None) == link.resolve()


def test_no_argument_no_variable_and_no_symlink_fails_closed(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that no argument no variable and no symlink fails closed."""
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(None)


def test_the_ci_checkout_is_the_last_resort(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that the ci checkout is the last resort."""
    ci = _fake_pt(tmp_path / "ci")
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    monkeypatch.setattr(sg_isolated, "CI_CHECKOUT", ci)
    assert sg_isolated.resolve_pt_root(None) == ci.resolve()
    env = _fake_pt(tmp_path / "env")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(env))
    assert sg_isolated.resolve_pt_root(None) == env.resolve()


def test_a_dangling_or_wrong_symlink_is_refused(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that a dangling or wrong symlink is refused."""
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
    """Check that an environment checkout without the guard falls through to the symlink."""
    stale = tmp_path / "stale"
    (stale / "orchestrator").mkdir(parents=True)          # an older checkout: no shared guard in it yet
    link = _fake_pt(tmp_path / "link")
    monkeypatch.setattr(sg, "LOCAL_LINK", tmp_path / "linkname")
    (tmp_path / "linkname").symlink_to(link)
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(stale))
    assert sg.resolve_pt_root(None) == link.resolve()


def test_symlink_loop_falls_through_only_for_optional_roots(sg_isolated, tmp_path, monkeypatch) -> None:
    """A broken optional candidate cannot hide a valid one; explicit roots must refuse."""
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    good = _fake_pt(tmp_path / "good")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(loop))
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", good)
    assert sg_isolated.resolve_pt_root() == good.resolve()
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(loop)


def test_mixed_producer_modules_are_refused_before_guard_construction(sg, tmp_path, monkeypatch) -> None:
    """An older cached producer must not supply another checkout's policy or store."""
    import importlib

    gate = """import importlib, importlib.util, sys
from pathlib import Path
name = 'pt_orchestrator_spend_gate'
if name not in sys.modules:
    here = Path(__file__).parent
    spec = importlib.util.spec_from_file_location(name, here / '__init__.py',
                                               submodule_search_locations=[str(here)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
_cg = importlib.import_module(name + '.cost_guard')
_pl = importlib.import_module(name + '.provider_limits')
"""
    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        directory = root / "orchestrator"
        directory.mkdir(parents=True)
        for filename in ("__init__.py", "cost_guard.py", "provider_limits.py"):
            (directory / filename).write_text("")
        (directory / "spend_gate.py").write_text(gate)
    name = "pt_orchestrator_spend_gate"
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            monkeypatch.delitem(sys.modules, key)
    prior = sg._load(a, "orchestrator/spend_gate.py", "pt_spend_gate")
    try:
        with pytest.raises(sg.SpendGuardUnavailable, match="checkout"):
            sg._load(b, "orchestrator/spend_gate.py", "pt_spend_gate")
        assert sys.modules["pt_spend_gate"] is prior
    finally:
        for key in list(sys.modules):
            if key == name or key.startswith(name + "."):
                sys.modules.pop(key, None)
        importlib.invalidate_caches()


def test_an_explicit_root_must_be_valid_and_never_falls_through(sg, tmp_path, monkeypatch) -> None:
    """Check that an explicit root must be valid and never falls through."""
    good = _fake_pt(tmp_path / "good")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(good))
    with pytest.raises(sg.SpendGuardUnavailable):
        sg.resolve_pt_root(tmp_path / "typo")


def test_when_no_candidate_holds_the_guard_every_reason_is_reported(sg_isolated, tmp_path, monkeypatch) -> None:
    """Check that when no candidate holds the guard every reason is reported."""
    stale = tmp_path / "stale"
    stale.mkdir()
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    monkeypatch.setenv("PERPETUA_TOOLS_ROOT", str(stale))
    with pytest.raises(sg_isolated.SpendGuardUnavailable) as info:
        sg_isolated.resolve_pt_root(None)
    assert "PERPETUA_TOOLS_ROOT" in str(info.value)


@needs_pt
def test_releasing_a_reservation_that_is_already_closed_is_a_no_op(sg, tmp_path) -> None:
    """Check that releasing a reservation that is already closed is a no op."""
    g = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    g.release("never-reserved")  # must not raise: cleanup may follow a settle that already closed it


@needs_pt
def test_the_adapter_loads_the_producer_gate_and_adds_no_ledger_of_its_own(sg, tmp_path) -> None:
    """Check that the adapter loads the producer gate and adds no ledger of its own."""
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
def test_adapters_use_their_own_checkout_ceilings(
    sg: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each checkout's policy applies to its own test ledger in the same process."""
    source = sg.resolve_pt_root(os.environ.get("ORAMA_TEST_PT_ROOT"))
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    timestamp = now.timestamp()
    monkeypatch.setattr(time, "time", lambda: timestamp)
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path, attested_at=now.isoformat())
    monkeypatch.delitem(sys.modules, "pt_spend_gate", raising=False)
    existing_modules = set(sys.modules)
    guards = []
    try:
        for ceiling in (80, 90):
            root = tmp_path / f"pt-{ceiling}"
            shutil.copytree(source / "orchestrator", root / "orchestrator", ignore=shutil.ignore_patterns("__pycache__"))
            policy_dir = Path("config/provider-policies")
            shutil.copytree(source / policy_dir, root / policy_dir)
            policy_path = root / policy_dir / "wandb-inference.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["budget"]["operator_estimate_ceiling_usd"] = ceiling
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            guard = sg.SpendGuard(pt_root=root, state_dir=tmp_path / f"spend-{ceiling}", now=lambda: now)
            assert guard.policy["budget"]["operator_estimate_ceiling_usd"] == ceiling
            guard.guard.record_spend(79.95)
            guards.append(guard)

        limited, roomy = guards
        assert limited.preflight(10_000, HOLD)["reason"] == "budget-exhausted"
        allowed = roomy.preflight(10_000, HOLD)
        assert allowed["ok"]
        roomy.release(allowed["reservation"])
    finally:
        sys.modules.pop("pt_spend_gate", None)
        for name in set(sys.modules) - existing_modules:
            if name.startswith("pt_orchestrator_spend_gate"):
                sys.modules.pop(name, None)


@needs_pt
def test_settle_unknown_charges_the_whole_reservation_and_marks_the_output_unknown(sg, tmp_path, monkeypatch) -> None:
    """Check that settle unknown charges the whole reservation and marks the output unknown."""
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
    """Check that a checkout without the spend gate is not a guard."""
    root = _fake_pt(tmp_path / "old")
    (root / "orchestrator" / "spend_gate.py").unlink()
    monkeypatch.delenv("PERPETUA_TOOLS_ROOT", raising=False)
    monkeypatch.setattr(sg_isolated, "LOCAL_LINK", tmp_path / "absent")
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.resolve_pt_root(root)
    with pytest.raises(sg_isolated.SpendGuardUnavailable):
        sg_isolated.SpendGuard(pt_root=root, state_dir=tmp_path)


@pytest.mark.parametrize("previous", [False, True])
def test_failed_producer_import_restores_module_and_refuses(sg, tmp_path, monkeypatch, previous: bool) -> None:
    """A broken producer cannot leak a partial module or an untyped import error."""
    from types import ModuleType

    path = tmp_path / "orchestrator" / "spend_gate.py"
    path.parent.mkdir()
    path.write_text("import missing_review_test_dependency\n")
    name = "pt_review_broken_gate"
    old = ModuleType(name)
    if previous:
        monkeypatch.setitem(sys.modules, name, old)
    else:
        monkeypatch.delitem(sys.modules, name, raising=False)
    with pytest.raises(sg.SpendGuardUnavailable) as error:
        sg._load(tmp_path, "orchestrator/spend_gate.py", name)
    assert isinstance(error.value.__cause__, ModuleNotFoundError)
    assert sys.modules.get(name) is (old if previous else None)


# --- review finding 3: the reservation outlives the whole allowed launch -------------------------------


def test_live_cycle_declares_a_hold_longer_than_the_launcher_timeout(cycle, tmp_path, monkeypatch) -> None:
    """Check that live cycle declares a hold longer than the launcher timeout."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run())
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
    clock = {"now": datetime(2026, 11, 15, tzinfo=timezone.utc).timestamp()}
    monkeypatch.setattr(real_time, "time", lambda: clock["now"])
    first = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=spend)
    other = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=spend)
    first.gate.guard.record_spend(89.9)  # room for exactly one request
    base = clock["now"]
    seen: dict = {}

    def slow_launch(argv, **kwargs):
        """Test helper or fixture: slow launch."""
        clock["now"] = base + 100 + 1  # the launcher is still inside its 100 s timeout, plus one second
        seen["second"] = other.preflight(10_000, 60.0)
        clock["now"] = base + 100 + cycle.SETTLE_MARGIN_S - 1
        return subprocess.CompletedProcess(argv, 0, stdout="ANSWER", stderr="")

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(slow_launch))
    result = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=first, timeout_s=100, prompt="x" * 10_000))
    assert seen["second"]["ok"] is False and seen["second"]["reason"] == "budget-exhausted"
    assert result["ok"] is True
    rows = [json.loads(x) for x in (spend / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and "basis" not in rows[0]  # settled in time, not as a late commit


# --- review finding 4: a post-start output problem is not a pre-start failure ---------------------------


def _child(code: str) -> list[str]:
    """Test helper or fixture: child."""
    return [sys.executable, "-c", code]


def test_invalid_utf8_output_is_settled_decoded_with_replacement_and_counts_as_a_launch(cycle, tmp_path, monkeypatch) -> None:
    """Check that invalid utf8 output is settled decoded with replacement and counts as a launch."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle, "launcher_argv",
        lambda seat, prompt=None, effort=None, model=None: _child("import sys; sys.stdout.buffer.write(b'AB\\xffCD')"),
    )
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["called_launcher"] is True and r.get("reason") != "launcher-error"
    assert guard.released == [] and len(guard.settled) == 1 and guard.settled[0][3] == "ok"
    assert r["ok"] is True and r["answer"] == "AB\ufffdCD"


def test_a_launcher_that_cannot_start_still_releases_the_reservation(cycle, tmp_path, monkeypatch) -> None:
    """Check that a launcher that cannot start still releases the reservation."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(
        cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: [str(tmp_path / "no-such-launcher")]
    )
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and r["called_launcher"] is False
    assert guard.released == ["r1"] and guard.settled == [] and guard.unknown == []


def test_an_interrupt_settles_unknown_and_reraises(cycle, tmp_path, monkeypatch) -> None:
    """Check that an interrupt settles unknown and reraises."""
    _arm(monkeypatch, cycle)

    def interrupted(argv, **kwargs):
        """Test helper or fixture: interrupted."""
        raise KeyboardInterrupt

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(interrupted))
    guard = FakeGuard()
    with pytest.raises(KeyboardInterrupt):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.settled == [] and guard.released == []
    assert guard.unknown == [("r1", len("Improve X."), "interrupted", "inner", "inner")]


@needs_pt
def test_a_timeout_commits_the_full_reservation_on_the_real_gate(sg, cycle, tmp_path, monkeypatch) -> None:
    """Check that a timeout commits the full reservation on the real gate."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    _arm(monkeypatch, cycle)
    guard = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    monkeypatch.setattr(
        cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: _child("import time; time.sleep(30)")
    )
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, timeout_s=1, prompt="x" * 10_000))
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True
    rows = [json.loads(x) for x in (tmp_path / "spend" / "wandb-inference-spend-audit.jsonl").read_text().splitlines()]
    assert rows[0]["outcome"] == "timeout" and rows[0]["basis"] == "output-unknown" and "output_chars" not in rows[0]
    assert guard.snapshot()["daily_spend"] == pytest.approx(guard.gate.pl.projected_usd(guard.policy, 10_000))


# --- the wait is explicit: only a failed start means nothing was sent -----------------------------------


def test_an_oserror_while_waiting_settles_as_unknown_and_counts_as_a_launch(cycle, tmp_path, monkeypatch) -> None:
    """Check that an oserror raised while waiting settles unknown, kills the child and reports a launch."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: _child("pass"))
    procs: list = []

    def broken_pipe(argv, **kwargs):
        """Fail the way a pipe read fails after the process started."""
        raise OSError("pipe read failed")

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(broken_pipe, procs))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["ok"] is False and r["reason"] == "launcher-error"
    assert r["called_launcher"] is True and r["spent"] is True and "OSError" in r["error"]
    assert guard.released == [] and guard.settled == []
    assert guard.unknown == [("r1", len("Improve X."), "launcher-io-error", "inner", "inner")]
    assert procs[0].killed is True and procs[0].communicate_calls == 2  # killed, then reaped


def test_a_timeout_kills_and_reaps_the_child_before_settling(cycle, tmp_path, monkeypatch) -> None:
    """Check that a timeout kills and reaps the process and then settles unknown."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: _child("pass"))
    procs: list = []

    def slow(argv, **kwargs):
        """Time out the wait."""
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(slow, procs))
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True
    assert procs[0].killed is True and procs[0].communicate_calls == 2
    assert len(guard.unknown) == 1 and guard.settled == [] and guard.released == []


def test_an_interrupt_kills_and_reaps_the_child_and_still_reraises(cycle, tmp_path, monkeypatch) -> None:
    """Check that an interrupt kills and reaps the process, settles unknown and is re-raised."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: _child("pass"))
    procs: list = []

    def interrupted(argv, **kwargs):
        """Interrupt the wait."""
        raise KeyboardInterrupt

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(interrupted, procs))
    guard = FakeGuard()
    with pytest.raises(KeyboardInterrupt):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert procs[0].killed is True and procs[0].communicate_calls == 2
    assert guard.unknown[0][2] == "interrupted" and guard.settled == [] and guard.released == []


def test_a_failure_to_start_the_process_releases_and_reports_no_launch(cycle, tmp_path, monkeypatch) -> None:
    """Check that an exception raised by Popen itself releases the reservation."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: _child("pass"))

    def no_start(argv, **kwargs):
        """Fail to start."""
        raise OSError("exec failed")

    monkeypatch.setattr(cycle.subprocess, "Popen", no_start)
    guard = FakeGuard()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert r["reason"] == "launcher-error" and r["called_launcher"] is False
    assert guard.released == ["r1"] and guard.settled == [] and guard.unknown == []


# --- review items 11 and 12: process-group reap and the sent flag ---------------------------------------


def test_a_grandchild_holding_the_pipes_cannot_hang_the_cycle_past_the_timeout(cycle, tmp_path, monkeypatch) -> None:
    """Check that a real grandchild holding the pipes is killed with its group and the cycle still settles."""
    import time

    _arm(monkeypatch, cycle)
    # A harmless real shell child: it backgrounds a sleeping grandchild that inherits the pipes.
    monkeypatch.setattr(
        cycle, "launcher_argv", lambda seat, prompt=None, effort=None, model=None: ["sh", "-c", "sleep 8 & sleep 8"]
    )
    guard = FakeGuard()
    started = time.monotonic()
    r = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, timeout_s=1))
    elapsed = time.monotonic() - started
    assert r["reason"] == "launcher-timeout" and r["called_launcher"] is True
    assert guard.unknown[0][2] == "timeout" and guard.released == []
    assert elapsed < 5, f"the group was not killed: the cycle waited {elapsed:.1f}s"


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux subreaper semantics")
def test_exited_launcher_descendant_is_killed_before_settlement(tmp_path: Path) -> None:
    """An exited leader cannot leave its pipe-holding descendant running after settlement."""
    script = r"""
import ctypes, importlib.util, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import test_spend_guard as t
import pytest
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
cycle = t._load("bin/agents/biafra_cycle.py", "cycle_descendant_test")
patch = pytest.MonkeyPatch()
t._arm(patch, cycle)
pidfile = Path(sys.argv[2]) / "leaf.pid"
code = "import os,time; open(%r, 'w').write(str(os.getpid())); time.sleep(60)" % str(pidfile)
root = '''import os, subprocess, sys, time
subprocess.Popen([sys.executable, '-c', sys.argv[1]])
deadline = time.monotonic() + 8
while not os.path.exists(sys.argv[2]) or not os.path.getsize(sys.argv[2]):
    if time.monotonic() >= deadline:
        raise RuntimeError('descendant was not ready')
    time.sleep(0.01)
'''
patch.setattr(cycle, "launcher_argv", lambda *args, **kwargs: [sys.executable, "-c", root, code, str(pidfile)])
original_reap = cycle._reap

def reap_after_leader_exit(proc):
    # WNOWAIT preserves the leader's PID and process group identity for cleanup.
    try:
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None:
                return
            time.sleep(0.01)
        raise AssertionError("launcher did not exit before cleanup")
    finally:
        original_reap(proc)

patch.setattr(cycle, "_reap", reap_after_leader_exit)
guard = t.FakeGuard()
pid = None
try:
    result = cycle.live_cycle(**t._kwargs(Path(sys.argv[2]), spend_guard=guard, timeout_s=1))
    assert result["reason"] == "launcher-timeout"
    pid = int(pidfile.read_text())
    deadline = time.monotonic() + 2
    waited, status = os.waitpid(pid, os.WNOHANG)
    while waited == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
        waited, status = os.waitpid(pid, os.WNOHANG)
    assert waited == pid, "descendant survived cycle settlement"
    pid = None  # waitpid reaped it; do not signal a potentially reused PID.
    assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == 9
    assert guard.unknown[0][2] == "timeout"
finally:
    if pid is None and pidfile.exists():
        # If the assertion failed before the PID was read, it may still be our child.
        try:
            candidate = int(pidfile.read_text())
            os.waitid(os.P_PID, candidate, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except (ChildProcessError, ValueError):
            pass
        else:
            pid = candidate
    if pid is not None:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
    patch.undo()
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "tests"), str(tmp_path)],
        capture_output=True, text=True, timeout=25,
    )
    assert result.returncode == 0, result.stderr


class _SettleBoom(FakeGuard):
    """A guard whose settle calls fail, to model a store error after the request was sent."""

    def settle(
        self, reservation: str, input_chars: int, output_chars: int, outcome: str, seat: str, mode: str,
    ) -> float:
        """Fail like a store error."""
        raise RuntimeError("settle failed")

    def settle_unknown(
        self, reservation: str, input_chars: int, outcome: str, seat: str, mode: str,
    ) -> float:
        """Fail like a store error."""
        raise RuntimeError("settle failed")


@pytest.mark.parametrize("returncode", [0, 1])
def test_a_settle_failure_after_a_successful_launch_never_releases(cycle, tmp_path, monkeypatch, returncode) -> None:
    """Check that a sent request whose settle raises keeps its reservation and surfaces the error."""
    _arm(monkeypatch, cycle)
    monkeypatch.setattr(cycle.subprocess, "Popen", _fake_run(returncode=returncode))
    guard = _SettleBoom()
    with pytest.raises(RuntimeError, match="settle failed"):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.released == []


def test_adapter_forwards_declared_output_limit(sg: ModuleType) -> None:
    """The PT gate receives the exact declared limit, while legacy calls remain compatible."""
    class RecordingGate:
        """Record the producer call without loading credentials or a ledger."""
        def preflight(self, *args: object, **kwargs: object) -> dict:
            """Return the received arguments for inspection."""
            return {"args": args, "kwargs": kwargs}

    adapter = sg.SpendGuard.__new__(sg.SpendGuard)
    adapter.gate = RecordingGate()
    assert adapter.preflight(10, 60, max_tokens=123) == {"args": (10, 60), "kwargs": {"max_tokens": 123}}
    assert adapter.preflight(10, 60) == {"args": (10, 60), "kwargs": {}}


def test_unbounded_cline_refuses_before_reservation_or_marker(cycle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A fully eligible governed attempt cannot launch unbounded Cline or consume a reservation."""
    monkeypatch.setenv(cycle.GATE_ENV, "approved")
    monkeypatch.setenv(cycle.ARM_ENV, "1")
    guard = FakeGuard()
    def forbidden(*args: object, **kwargs: object) -> None:
        """Catch any attempt to reserve or start a process."""
        pytest.fail("unbounded Cline must not reserve or launch")
    monkeypatch.setattr(guard, "preflight", forbidden)
    monkeypatch.setattr(cycle.subprocess, "Popen", forbidden)
    result = cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert result["reason"] == "launcher-output-bound-unsupported"
    assert not result["called_launcher"]
    assert not list((tmp_path / "log").glob("*.once"))


@needs_pt
def test_adapter_reserves_declared_limit_with_new_pt(
    sg: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real producer reserves more when a larger output limit is forwarded."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    guard = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=tmp_path / "spend")
    legacy = guard.preflight(100, HOLD)
    assert legacy["ok"]
    guard.release(legacy["reservation"])
    bounded = guard.preflight(100, HOLD, max_tokens=100_000)
    assert bounded["ok"]
    assert bounded["projected_usd"] > legacy["projected_usd"]
    guard.release(bounded["reservation"])


def test_a_settle_failure_after_a_timeout_never_releases(cycle, tmp_path, monkeypatch) -> None:
    """Check that a failing settle_unknown after a timeout leaves the reservation to its hold."""
    _arm(monkeypatch, cycle)

    def slow(argv, **kwargs):
        """Time out the wait."""
        raise subprocess.TimeoutExpired(argv, 1)

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(slow))
    guard = _SettleBoom()
    with pytest.raises(RuntimeError, match="settle failed"):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard))
    assert guard.released == []


@needs_pt
def test_live_cycle_retains_uncertain_liability_through_expiry_and_reconciliation(
    sg: Any, cycle: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mocked sent timeout leaves real PT liability rather than reusable budget."""
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    _attest(tmp_path)
    _arm(monkeypatch, cycle)
    state = tmp_path / "spend"
    guard = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=state)
    before = guard.guard.snapshot()["daily_spend"]
    now = datetime.now(timezone.utc).timestamp()
    admitted: list[dict[str, Any]] = []
    producer_preflight = guard.preflight

    def preflight(prompt_chars: int, hold_seconds: float) -> dict[str, Any]:
        """Observe the real admission contract without replacing its producer."""
        result = producer_preflight(prompt_chars, hold_seconds)
        admitted.append(result)
        return result

    def timeout(argv: list[str], **kwargs: Any) -> None:
        """Model an already-started launcher whose response times out."""
        raise subprocess.TimeoutExpired(argv, 1)

    def unavailable(*args: Any, **kwargs: Any) -> None:
        """Refuse settlement before the SQLite charge can commit."""
        raise OSError("offline settlement failure")

    monkeypatch.setattr(cycle.subprocess, "Popen", as_popen(timeout))
    monkeypatch.setattr(guard, "preflight", preflight)
    monkeypatch.setattr(guard.guard, "commit_sync", unavailable)
    with pytest.raises(OSError, match="offline settlement failure"):
        cycle.live_cycle(**_kwargs(tmp_path, spend_guard=guard, timeout_s=1))
    assert len(admitted) == 1 and admitted[0]["ok"]
    reservation, amount = admitted[0]["reservation"], admitted[0]["projected_usd"]
    assert amount > 0
    assert guard.guard.snapshot()["daily_spend"] == before

    monkeypatch.setattr(guard.gate.cg.time, "time", lambda: now + 3600)
    reopened = sg.SpendGuard(pt_root=os.environ.get("ORAMA_TEST_PT_ROOT"), state_dir=state)
    assert reopened.guard.in_flight() == pytest.approx(amount)
    refusal = reopened.preflight(100, HOLD)
    assert refusal["reason"] == "spend-reconciliation-required" and refusal["stop"]
    assert reopened.guard.snapshot()["daily_spend"] == before
    reopened.settle_unknown(reservation, len("Improve X."), "reconciled", "inner", "inner")
    assert reopened.guard.snapshot()["daily_spend"] == pytest.approx(before + amount, abs=5e-7)
    assert reopened.guard.in_flight() == 0
