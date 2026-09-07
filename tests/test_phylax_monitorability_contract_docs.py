"""Regression checks for the normative Phylax monitorability design contracts."""

import re

import pytest
from pathlib import Path


ROOT = Path(__file__).parent.parent
PRINCIPAL_IDENTITY = ROOT / "docs/v2/61-pt-coordination-principal-identity-design.md"
DERIVED_INFERENCE = (
    ROOT / "docs/v2/references/phylax-monitorability-part-2-derived-inference.md"
)
COORDINATION_ENVELOPE = (
    ROOT / "docs/superpowers/specs/2026-09-04-coordination-round-envelope-design.md"
)


def _extract_outcome_matrix_table(text: str) -> str:
    """Return the `PT_AGENT_TOKEN` outcome matrix table, anchored to its own
    heading rather than the whole document, so a later edit that removes a
    row here cannot be masked by identical-looking text living elsewhere."""
    marker = "**`PT_AGENT_TOKEN` outcome matrix:**"
    marker_index = text.index(marker)
    after_marker = text[marker_index + len(marker) :]

    table_lines = []
    for line in after_marker.splitlines():
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if not stripped.startswith("|"):
            break
        table_lines.append(stripped)

    assert table_lines, "Could not locate the PT_AGENT_TOKEN outcome matrix table"
    return "\n".join(table_lines)


def _extract_admission_validator_block(text: str) -> str:
    """Return the source-observation admission-validator paragraph, anchored
    between its opening and closing sentences, so the assertions below check
    that specific block instead of the whole document."""
    start_marker = (
        "Bracketing enforcement is therefore a separate, repository-owned "
        "admission-time"
    )
    end_marker = (
        "An unknown or\nclassless target is rejected rather than treated as observed."
    )
    start_index = text.index(start_marker)
    end_index = text.index(end_marker, start_index) + len(end_marker)
    return text[start_index:end_index]


def _extract_conformance_table(text: str) -> str:
    """Return the conformance-case table, anchored to its own header row."""
    header = "| Conformance case | Required result |"
    header_index = text.index(header)
    after_header = text[header_index:]

    table_lines = []
    for line in after_header.splitlines():
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if not stripped.startswith("|"):
            break
        table_lines.append(stripped)

    assert table_lines, "Could not locate the conformance-case table"
    return "\n".join(table_lines)


@pytest.mark.unit
def test_token_outcome_matrix_distinguishes_every_migration_stage() -> None:
    text = PRINCIPAL_IDENTITY.read_text(encoding="utf-8")
    table = _extract_outcome_matrix_table(text)

    assert (
        "| State | M-id-1 (opt-in) | M-id-2 (deprecation window) | M-id-3 (token required) |"
        in table
    )
    assert (
        "| Unset | Falls back to today's `PT_AGENT_ID`-only check | Falls back to "
        "the `PT_AGENT_ID`-only check and emits a deprecation warning | "
        "Rejected: token required |" in table
    )
    assert re.search(
        r"\| Invalid or mismatched \|.*Rejected: supplied token is unregistered "
        r"or does not match the requested `agent_id`.*\|.*\|.*\|",
        table,
    )
    assert re.search(
        r"\| Revoked \|.*Rejected: token's registered entry is revoked.*\|.*\|.*\|",
        table,
    )
    assert re.search(
        r"\| Valid \|.*Accepted: non-revoked token matches the requested "
        r"`agent_id`.*\|.*\|.*\|",
        table,
    )


@pytest.mark.unit
def test_source_observation_admission_rejects_non_observed_targets() -> None:
    text = DERIVED_INFERENCE.read_text(encoding="utf-8")
    admission_block = " ".join(_extract_admission_validator_block(text).split())
    conformance_table = _extract_conformance_table(text)

    assert "every resolved source target has epistemic class `Observed`" in admission_block
    assert "rejects every non-`Observed` target before admission" in admission_block
    assert (
        "An unknown or classless target is rejected rather than treated as observed"
        in admission_block
    )
    assert (
        "| source reference resolves to Derived/Reconstructed/Interpolated/Forecast "
        "| reject before persistence |" in conformance_table
    )


def _extract_decision_class_block(text: str) -> str:
    """Return the `PhylaxMonitorabilityDecisionV2` class definition, anchored
    to its own class header rather than the whole document."""
    marker = "class PhylaxMonitorabilityDecisionV2(BaseModel):"
    marker_index = text.index(marker)
    end_index = text.index("```", marker_index)
    return text[marker_index:end_index]


def _extract_coordination_envelope_block(text: str) -> str:
    """Return the `CoordinationRoundEnvelopeV1` class definition, anchored to
    its own class header rather than the whole document."""
    marker = "class CoordinationRoundEnvelopeV1(BaseModel):"
    marker_index = text.index(marker)
    end_index = text.index("def resolve_round_admissible", marker_index)
    return text[marker_index:end_index]


@pytest.mark.unit
def test_coordination_round_envelope_collections_are_deeply_immutable_and_unique() -> None:
    """frozen=True alone doesn't stop a caller mutating a list field in
    place -- this asserts the contract actually uses tuples (not lists) for
    its multi-value fields, and that duplicate stop_condition_codes are
    rejected, not just that the prose claims either."""
    text = COORDINATION_ENVELOPE.read_text(encoding="utf-8")
    contract = _extract_coordination_envelope_block(text)

    for field in ("out_of_scope_refs", "stop_condition_detail_refs", "ordered_handoff_refs"):
        assert f"{field}: tuple[OpaqueEvidenceRef, ...]" in contract, f"{field} is not a tuple"
    assert "stop_condition_codes: tuple[Literal[" in contract
    assert (
        'raise ValueError("stop_condition_codes must not contain duplicates")'
        in contract
    )


@pytest.mark.unit
def test_phylax_decision_schema_carries_its_own_provenance_fields() -> None:
    """The prose promises every decision has an issuer, immutable ID,
    policy-pack version, timestamp, and integrity hash -- this asserts the
    schema actually declares them, not just that the prose claims it does,
    and that a block decision without evidence is rejected."""
    text = DERIVED_INFERENCE.read_text(encoding="utf-8")
    decision_block = _extract_decision_class_block(text)

    for field in ("decision_id", "issuer_id", "policy_pack_version", "decided_at", "integrity_hash"):
        assert f"{field}:" in decision_block, f"missing provenance field: {field}"
    assert (
        'raise ValueError("block decisions require observable evidence")'
        in decision_block
    )
    assert (
        'raise ValueError("decided_at must be timezone-aware UTC")' in decision_block
    )
