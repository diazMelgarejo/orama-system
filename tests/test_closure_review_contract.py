"""Review procedures must bind CI evidence and preserve current publication authority."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_closure_removes_stale_push_hold_but_keeps_merge_barrier() -> None:
    """The ratification paragraph cannot contradict authorized publication."""
    text = (ROOT / "docs/v2/MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md").read_text()
    assert "The push hold\nand merge barrier remain in effect." not in text
    assert "The merge barrier remains in effect." in text


def test_operator_review_binds_tested_and_accepted_trees() -> None:
    """Synthetic merge evidence is not automatically exact-head evidence."""
    text = (ROOT / "docs/v2/closure/c3d-operator-review-procedure-2026-11-06.md").read_text()
    assert "tested commit" in text
    assert "base revisions" in text
    assert "tree" in text
    assert "accepted head" in text
    assert "No merge or deployment." in text


def test_operator_p95_amendment_preserves_historical_budget() -> None:
    """The dated amendment binds both populations without erasing history."""
    text = (ROOT / "docs/v2/MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md").read_text()
    assert "send p95 at most 50 ms" in text
    assert "C6 scheduled latency p95 and" in text
    assert "successful-call send latency p95 must each be at most 60 ms" in text
    assert "Three consecutive operator-run Mac" in text
