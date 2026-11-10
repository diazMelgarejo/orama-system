"""Opt-in evidence with the REAL Cline CLI on Windows (spends a few ClinePass credits, so it is off by default).

Run with RUN_REAL_CLINE=1 and CLINE_MODEL set to a current model slug (for example the ClinePass default coding
lane). One plan-mode call from a scratch directory. It documents the finding of 2026-11-10: without a pinned model
the global Cline configuration can name a retired default, and the CLI answers "model not found" after a
misleading hook-dispatch error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cline_autoresearcher as car  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or os.getenv("RUN_REAL_CLINE") != "1" or not os.getenv("CLINE_MODEL", "").strip(),
    reason="real Cline evidence is opt-in: Windows, RUN_REAL_CLINE=1 and CLINE_MODEL set",
)


def test_real_cline_plan_mode_round_trip(tmp_path, monkeypatch):
    """One real plan-mode call completes and echoes the requested marker; nothing is written to the scratch dir."""
    monkeypatch.setenv("CLINE_WORKDIR", str(tmp_path))
    monkeypatch.delenv("CLINE_ALLOW_ACT", raising=False)
    assert car.cline_available()["available"] is True
    res = car.dispatch_cline("Reply with exactly: REAL-CLINE-OK")
    assert res["outcome"] == "completed" and res["ok"] is True, res["output"][:400]
    assert "REAL-CLINE-OK" in res["output"]
    assert list(tmp_path.iterdir()) == [], "plan mode must not create files in the scratch directory"
