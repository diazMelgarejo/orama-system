"""Regression checks for the normative Phylax monitorability design contracts."""

from pathlib import Path


ROOT = Path(__file__).parent.parent
PRINCIPAL_IDENTITY = ROOT / "docs/v2/61-pt-coordination-principal-identity-design.md"
DERIVED_INFERENCE = (
    ROOT / "docs/v2/references/phylax-monitorability-part-2-derived-inference.md"
)


def test_token_outcome_matrix_distinguishes_every_migration_stage() -> None:
    text = PRINCIPAL_IDENTITY.read_text(encoding="utf-8")

    assert "| State | M-id-1 (opt-in) | M-id-2 (deprecation window) | M-id-3" in text
    assert "| Unset | Falls back" in text
    assert "| Invalid or mismatched |" in text
    assert "| Revoked |" in text
    assert "| Valid |" in text
    assert "M-id-2" in text and "warning" in text
    assert "M-id-3" in text and "Rejected: token required" in text


def test_source_observation_admission_rejects_non_observed_targets() -> None:
    text = " ".join(DERIVED_INFERENCE.read_text(encoding="utf-8").split())

    assert "every resolved source target has epistemic class `Observed`" in text
    assert "rejects every non-`Observed` target before admission" in text
    assert "source reference resolves to Derived/Reconstructed/Interpolated/Forecast" in text
    assert "reject before persistence" in text
