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
WANDA = ROOT / "bin/agents/wanda/SOUL.md"
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


def test_section_15_matches_the_launcher_boundary() -> None:
    """Section 15 names the refusal and calls the Biafra Cline route a designation."""
    reason = _boundary_reason()
    assert reason is not None, "the launcher boundary was lifted: rewrite doc 76 section 15, then update this test"
    text = PLAN.read_text(encoding="utf-8")
    section = _flat(text.split("## 15.", 1)[1].split("\n## ", 1)[0])
    assert reason in section
    assert "designated" in section
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in section, claim


def test_wanda_card_calls_the_biafra_cline_route_a_designation() -> None:
    """Wanda's card scopes the Cline ban to her and does not say the Biafra route runs."""
    card = _flat(WANDA.read_text(encoding="utf-8"))
    assert "binds Wanda only" in card and "designated" in card
    for claim in PRESENT_TENSE_CLAIMS:
        assert claim not in card, claim
