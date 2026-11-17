"""The offline guard: tests that must never launch a real model, whatever the shell exports."""

from __future__ import annotations

import subprocess
import sys

import pytest

import _offline  # tests/_offline.py: tests/ is on sys.path (no package)


def test_the_guard_clears_inherited_approval_variables(monkeypatch) -> None:
    monkeypatch.setenv("BIAFRA_ORCHESTRATOR_GATE", "approved")
    monkeypatch.setenv("BIAFRA_ALLOW_LAUNCH", "1")
    _offline.install(monkeypatch)
    import os

    assert "BIAFRA_ORCHESTRATOR_GATE" not in os.environ and "BIAFRA_ALLOW_LAUNCH" not in os.environ


@pytest.mark.parametrize("call", ["run", "Popen", "check_output", "call"])
def test_a_real_launcher_call_is_refused_through_every_subprocess_entry_point(monkeypatch, call) -> None:
    _offline.install(monkeypatch)
    argv = [sys.executable, "/x/skills/cline-wandb/scripts/launch_cline_wandb.py", "--", "prompt"]
    with pytest.raises(AssertionError, match="real launcher"):
        getattr(subprocess, call)(argv)


def test_other_subprocess_calls_still_work(monkeypatch) -> None:
    _offline.install(monkeypatch)
    out = subprocess.run([sys.executable, "-c", "print(41 + 1)"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "42"


def test_the_guard_applies_to_the_biafra_modules() -> None:
    import importlib

    for name in ("test_biafra_seats", "test_live_cycle", "test_pair_dogfood", "test_seat_contracts",
                 "test_spend_guard", "test_sandbox_run"):
        mod = importlib.import_module(name)
        raw = getattr(mod, "pytestmark", [])
        marks = raw if isinstance(raw, list) else [raw]
        assert any(m.name == "usefixtures" and "offline_guard" in m.args for m in marks), name
