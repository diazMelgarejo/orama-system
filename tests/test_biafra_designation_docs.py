"""Doc 76 section 15 and Wanda's card must describe the Cline route as the launcher really behaves.

The Biafra seats are designated to use Cline under the shared spend gate once the launcher can bound
total output and request count. While `_launcher_boundary_problem()` refuses, the docs may not say
the route runs. When the boundary is lifted this test fails, so the wording changes with the code.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/v2/76-biafra-outer-seat-canonical-plan.md"
HANDOFF = ROOT / "docs/v2/references/biafra/handoff-open-gaps-2026-11-17.md"
WANDA = ROOT / "bin/agents/wanda/SOUL.md"
BOTH_BOUNDS = "total output and request count"
PRESENT_TENSE_CLAIMS = ("seats use Cline", "already launches", "already runs")


def _boundary_reason() -> str | None:
    """Return the refusal reason the launcher boundary gives today."""
    spec = importlib.util.spec_from_file_location("biafra_cycle_designation_docs", ROOT / "bin/agents/biafra_cycle.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._launcher_boundary_problem()


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
    """Section 15 names the refusal and calls the Biafra Cline route a designation."""
    reason = _boundary_reason()
    assert reason is not None, "the launcher boundary was lifted: rewrite doc 76 section 15, then update this test"
    text = PLAN.read_text(encoding="utf-8")
    section = _flat(text.split("## 15.", 1)[1].split("\n## ", 1)[0])
    assert reason in section
    assert "designated" in section
    assert BOTH_BOUNDS in section, "section 15 must name both launcher bounds"
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
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in card, claim
