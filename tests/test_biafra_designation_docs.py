"""Pin doc 76, the handoff and Wanda's card to the incomplete bounded-launcher contract.

The Biafra seats are designated to use Cline under the shared spend gate once the launcher can enforce
both total output and request count. While `_launcher_boundary_problem()` refuses, the docs must name
the remaining gate rather than claim the route runs. The armed legacy path stays fail-closed, and the
Cline prohibition remains scoped to Wanda. When the boundary is lifted this test fails, so the wording
changes with the code.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md"
HANDOFF = ROOT / "docs/v2/references/biafra/handoff-open-gaps-2026-11-17.md"
WANDA = ROOT / "bin/agents/wanda/SOUL.md"
BOTH_BOUNDS = "total output and request count"
CHECKPOINT_DATE = "2026-11-26"
LEGACY_REFUSAL = "legacy-live-path-disabled"
PRESENT_TENSE_CLAIMS = ("seats use Cline", "already launches", "already runs")


def _cycle_module():
    """Load the cycle module without importing package-level runtime state."""
    spec = importlib.util.spec_from_file_location("biafra_cycle_designation_docs", ROOT / "bin/agents/biafra_cycle.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _boundary_reason() -> str | None:
    """Return the refusal reason the launcher boundary gives today."""
    return _cycle_module()._launcher_boundary_problem()


def _flat(text: str) -> str:
    """Collapse whitespace so a wrapped sentence can be matched."""
    return " ".join(text.split())


def _g11_handoff_row(text: str) -> str:
    """Return the flattened G11 status-table row from the handoff."""
    for line in text.splitlines():
        if line.startswith("| G11 |"):
            return _flat(line)
    raise AssertionError("handoff is missing a | G11 | status row")


def test_section_15_matches_the_launcher_boundary() -> None:
    """Section 15 names the refusal, both bounds and the fail-closed legacy contract."""
    reason = _boundary_reason()
    assert reason is not None, "the launcher boundary was lifted: rewrite doc 76 section 15, then update this test"
    text = PLAN.read_text(encoding="utf-8")
    section = _flat(text.split("## 15.", 1)[1].split("\n## ", 1)[0])
    assert reason in section
    assert "designated" in section
    assert BOTH_BOUNDS in section, "section 15 must name both launcher bounds"
    assert "fail-closed" in section
    assert LEGACY_REFUSAL in section
    assert CHECKPOINT_DATE in section
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in section, claim


def test_handoff_g11_row_names_both_launcher_bounds() -> None:
    """The handoff G11 row keeps the same both-bounds designation as section 15 and Wanda."""
    row = _g11_handoff_row(HANDOFF.read_text(encoding="utf-8"))
    assert "designated" in row
    assert BOTH_BOUNDS in row, "handoff G11 must name both launcher bounds"
    assert "live_cycle()" in row
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in row, claim


def test_wanda_card_calls_the_biafra_cline_route_a_designation() -> None:
    """Wanda's card scopes the Cline ban to her and does not say the Biafra route runs."""
    card = _flat(WANDA.read_text(encoding="utf-8"))
    assert "binds Wanda only" in card and "designated" in card
    assert BOTH_BOUNDS in card, "the designation needs both bounds, as doc 76 section 15 says"
    assert "the Cline CLI for this W&B route" in card
    assert "Cline CLI remains forbidden for Wanda's W&B route" in card
    assert CHECKPOINT_DATE in card
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in card, claim


def test_handoff_has_a_dated_lane_1b_gate_note() -> None:
    """Section 9.1 records the dated checkpoint without rewriting its historical table."""
    text = HANDOFF.read_text(encoding="utf-8")
    section = text.split("### 9.1 ", 1)[1].split("### 9.2 ", 1)[0]
    flat = _flat(section).lower()
    assert CHECKPOINT_DATE in flat
    assert "implementation is incomplete" in flat
    assert "launcher-output-bound-unsupported" in flat
    assert "before any spend-gate reservation" in flat
    assert LEGACY_REFUSAL in flat


def test_armed_legacy_path_remains_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Arming the legacy entry point refuses without launching or running a dry cycle."""
    module = _cycle_module()
    monkeypatch.setenv(module.GATE_ENV, "approved")
    monkeypatch.setenv(module.ARM_ENV, "1")
    result = module.run_program("inner", "code", 1.0, 0.5, tmp_path)
    assert result["reason"] == LEGACY_REFUSAL
    assert result["ok"] is False
    assert result["launched"] is False
    assert result["called_launcher"] is False
    assert result["retries"] == 0
