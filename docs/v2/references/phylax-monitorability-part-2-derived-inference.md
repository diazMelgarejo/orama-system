# Phylax Monitorability — Part 2: Derived Inference and Decision Model

**Status:** subordinate v2 implementation guidance; not a Perpetua-Tools v1 implementation task

**Normative authority:** [Doc 60 — Canonical Phylax Monitorability Design
Specification](../60-phylax-monitorability-design-spec.md). Doc 60 defines the
epistemic classes and decision authority; this part specifies artifact and
adapter implementation detail that remains subordinate to it.

**Implementation modules:**
[Part 1 — v1 evidence contract](phylax-monitorability-part-1-v1-evidence-contract.md) ·
[Part 3 — migration and assurance](phylax-monitorability-part-3-migration-assurance.md)

## Objective

Phylax turns redacted operational evidence and legitimately accessible sealed
reasoning into calibrated safety signals. The epistemic meanings and authority
limits are normative in Doc 60. This module requires a concrete, append-only
implementation record for every non-observed artifact so it cannot be mistaken
for an observation or a decision.

## v2 inputs

The versioned adapter normalizes the v1 envelope rather than parsing Markdown,
logs, or raw agent output:

```python
from typing import Annotated
from pydantic import Field, model_validator

class PhylaxMonitorabilityInputV2(BaseModel):
    contract_version: Literal[2]
    source_handoff_version: Literal[1]
    redacted_observation_ref: OpaqueEvidenceRef
    policy_context: PolicyContextV2
    observable_evidence: list[ObservableEvidenceV2]
    sealed_reasoning_ref: OpaqueEvidenceRef | None = None
    otel_mapping_id: Literal["oramasys.phylax.otel-map.v1"]
    otel_semconv_baseline: Literal[
        "open-telemetry/semantic-conventions-genai@94f432d7126f5884d30a2cdde6f4e89908ebb6fd"
    ]
    mapping_review_id: OpaqueEvidenceRef
```

The adapter records source schema, redaction profile, evidence order, and the
producer’s attestation state. It rejects content-bearing identifiers and does
not elevate a producer-reported advisory to a Phylax decision.

## Derived Monitorability Artifact

Artifacts are append-only records in Phylax’s governed store. Decisions point
to artifact IDs; they do not copy raw evidence, CoT, or free-form hypotheses
into normal telemetry.

```python
class DerivedMonitorabilityArtifactV2(BaseModel):
    artifact_id: str
    status: Literal["active", "superseded", "retracted"]
    epistemic_status: Literal[
        "derived", "reconstructed", "interpolated", "forecast"
    ]
    subject_kind: Literal[
        "action", "action_sequence", "policy_state", "risk_trajectory"
    ]
    source_observation_refs: Annotated[list[OpaqueEvidenceRef], Field(min_length=1)]
    trace_relation: Literal[
        "same_span", "ancestor_span", "descendant_span",
        "correlated_only", "causal_unknown"
    ]
    method_id: str
    method_version: str
    model_id: str
    model_version: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    calibration_ref: OpaqueEvidenceRef | None = None
    calibration_version: str | None = None
    valid_from: datetime | None = None
    expires_at: datetime
    supersedes_artifact_ids: list[str]
    sealed_reasoning_ref: OpaqueEvidenceRef | None = None
    authority: Literal["advisory"]
    disposition: Literal["advisory", "escalate", "re_evaluate", "human_review"]

    @model_validator(mode="after")
    def enforce_temporal_and_calibration_rules(self):
        if (self.calibration_ref is None) != (self.calibration_version is None):
            raise ValueError("calibration reference and version must appear together")
        if self.artifact_id in self.supersedes_artifact_ids:
            raise ValueError("an artifact cannot supersede itself")
        if self.epistemic_status in {"reconstructed", "interpolated"}:
            if self.valid_from is None or self.valid_from >= self.expires_at:
                raise ValueError("reconstruction/interpolation needs a bounded interval")
        if self.epistemic_status == "forecast":
            if self.valid_from is None or self.valid_from >= self.expires_at:
                raise ValueError("forecast needs a future-bounded horizon")
        return self


def resolve_effective_status(
    artifact: DerivedMonitorabilityArtifactV2,
    all_artifacts: list[DerivedMonitorabilityArtifactV2],
) -> Literal["active", "superseded", "retracted"]:
    """Compute an artifact's real, current status -- never trust its own
    stored `status` field alone for this.

    Artifacts are append-only: once written, an artifact's own record can
    never be mutated to record that something *later* superseded it. A
    naive single supersedes-style field on the superseding artifact,
    checked in isolation, hits exactly the bug this codebase already found
    and fixed once this session in PT's lessons.jsonl -- a narrow
    correction's own `supersedes` pointer only linked one specific prior
    record, silently leaving other, equally-real duplicates unlinked and
    still rendering as live. The fix there, and the one specified here, is
    the same: never mutate old records: instead, resolve the reverse
    relationship by scanning at resolution time.

    An artifact's stored `status` field reflects only what was true when
    IT was written (e.g. "active" if nothing was known to supersede it
    yet). The actual, current status must be recomputed against the full
    artifact set on every resolution -- retracted always wins if present;
    otherwise, any artifact whose `supersedes_artifact_ids` includes this
    one's `artifact_id` makes it superseded, regardless of what its own
    stored `status` says.
    """
    if artifact.status == "retracted":
        return "retracted"
    for other in all_artifacts:
        if other.artifact_id == artifact.artifact_id:
            continue  # an artifact never supersedes itself -- defense in depth
                      # for records predating enforce_temporal_and_calibration_rules'
                      # construction-time rejection above
        if artifact.artifact_id in other.supersedes_artifact_ids:
            return "superseded"
    return artifact.status
```

Every non-observed artifact must include one or more source observation
references, its method and model identifiers/versions, confidence and
calibration metadata when calibrated, an expiry, a supersession list (empty when
it replaces nothing), and an explicitly non-authoritative disposition.
`reconstructed` and `interpolated` additionally require a bounded interval plus
bracketing source observations; `forecast` requires an explicit future horizon.

**What the model validator above enforces, and what it structurally cannot:**
`enforce_temporal_and_calibration_rules` checks that a claimed interval is
internally well-formed (`valid_from < expires_at`) and that calibration
fields are paired. It cannot verify that `source_observation_refs` actually
*bracket* that interval, because those are opaque references — resolving
them to real observation timestamps requires the observation store, which a
self-contained Pydantic model has no access to by design (the same
opaque-reference discipline that keeps raw evidence out of the model at all).
Bracketing enforcement is therefore a separate, repository-owned admission-time
validator: it resolves each `source_observation_refs` entry against the
observation store, confirms at least one resolved observation falls at or
before `valid_from` and at least one at or after `expires_at` for
`reconstructed`/`interpolated` artifacts, and rejects admission otherwise. No
`DerivedMonitorabilityArtifactV2` reaches the governed store without passing
through this validator first.
On correction or replacement, append a new artifact that identifies what it
supersedes rather than rewriting the earlier record. Expired or superseded
artifacts are not live evidence for a new decision.

This repository deliberately does not introduce a shadow Phylax runtime:
M0.1 names its owning package before implementation. That owning package must
implement the schema above and reject empty evidence, out-of-range confidence,
one-sided calibration metadata, invalid status-dependent intervals, and an
expired forecast before M3 can pass. Its conformance tests must also prove that
omitting either nullable `sealed_reasoning_ref`, `calibration_ref`, or
`valid_from` is accepted only where the status rule permits it.

| Conformance case | Required result |
| --- | --- |
| no `source_observation_refs` | reject before persistence |
| confidence below 0 or above 1 | reject before persistence |
| only one calibration field | reject before persistence |
| reconstruction/interpolation without a bounded interval | reject before persistence |
| forecast with no future-bounded horizon, or after `expires_at` | reject for decision use |
| omitted nullable field in a permitted status | accept without synthesizing a value |

## Decision contract and authority

```python
class PhylaxMonitorabilityDecisionV2(BaseModel):
    decision: Literal["allow", "warn", "escalate", "block"]
    severity: SeverityV2
    confidence: float
    policy_ids: list[str]
    observable_evidence_refs: list[OpaqueEvidenceRef]
    derived_artifact_refs: list[str]
    monitor_rationale_category: Literal[
        "observable_evidence", "policy_match", "confidence_threshold",
        "human_review", "insufficient_evidence"
    ]
    monitor_rationale_ref: OpaqueEvidenceRef | None = None
    human_review_required: bool
    retention_class: RetentionClassV2
```

Every decision has an issuer, immutable decision ID, policy-pack version,
timestamp, integrity hash, and append-only correlation to its source evidence.
There is no persisted free-form rationale summary. The bounded category is safe
for ordinary telemetry; the optional rationale reference uses the Part 1 opaque
reference grammar, is never exported in normal telemetry, and may resolve only
inside the governed incident store. It must not carry or reveal CoT.

```python
def resolve_admissible_artifact_refs(
    derived_artifact_refs: list[str],
    all_artifacts: list[DerivedMonitorabilityArtifactV2],
    clock_now: datetime,
) -> tuple[list[str], list[tuple[str, str]]]:
    """A decision's own derived_artifact_refs list is never trusted as-is --
    every reference is re-resolved against the current artifact set at
    admission time, the same "never trust a stored/cached fact" discipline
    as resolve_effective_status() and resolve_round_admissible() above.
    Returns (admissible_refs, rejected) where each rejected entry states
    why: unknown_artifact_id, expired, or superseded_or_retracted (via
    resolve_effective_status(), not the artifact's own stored status
    field alone).
    """
    by_id = {a.artifact_id: a for a in all_artifacts}
    admissible: list[str] = []
    rejected: list[tuple[str, str]] = []
    for ref in derived_artifact_refs:
        artifact = by_id.get(ref)
        if artifact is None:
            rejected.append((ref, "unknown_artifact_id"))
            continue
        if clock_now >= artifact.expires_at:
            rejected.append((ref, "expired"))
            continue
        if resolve_effective_status(artifact, all_artifacts) != "active":
            rejected.append((ref, "superseded_or_retracted"))
            continue
        admissible.append(ref)
    return admissible, rejected
```

A `PhylaxMonitorabilityDecisionV2` may only be constructed from
`admissible_refs`, never the raw `derived_artifact_refs` a caller supplied --
an expired or superseded artifact must not silently continue backing a live
decision just because its `artifact_id` still appears in a list somewhere.

**A related, currently unenforced requirement, stated honestly rather than
silently left unaddressed:** doc 60 requires observed and non-observed
records to never merge (§ "Observed records never merge with non-observed
artifacts"). `source_observation_refs` on `DerivedMonitorabilityArtifactV2`
is documented as pointing to observation evidence, but neither this document
nor Part 1 yet defines a canonical `Observed`-class record schema to check
membership against -- so nothing here currently rejects a
`source_observation_refs` entry that actually points to another
non-observed (derived/reconstructed/interpolated/forecast) artifact, which
would let an inference chain build on inference rather than on real ground
truth. Closing this properly needs a canonical `ObservedEventV1`-style
schema (or equivalent epistemic-class tag on every referenceable record)
added to Part 1's evidence contract first; `resolve_admissible_artifact_refs`
above should then also reject any `source_observation_refs` entry whose
resolved record is not tagged `Observed`, with its own conformance case.
Flagged here as a concrete, named follow-up rather than assumed away.

A future `block` is valid only if all conditions hold:

1. at least one independently observable evidence reference proves the named
   policy violation;
2. the policy pack explicitly permits blocking that violation;
3. a trusted Phylax evaluator/issuer explicitly admits the evidence through the
   versioned Phylax v2 contract and creates the decision; and
4. review, false-block, rollback, and retention controls are active.

A derived artifact may have only the non-authoritative dispositions represented
above. It cannot block, grant/revoke a capability, revise observed history, or
create merge/deployment authority.

## Execution lanes and access

| Lane | Inputs | Output | Authority |
| --- | --- | --- | --- |
| Fast safety | intent, grants, policy state, observable tool evidence | allow/warn/escalate; later independently grounded block | Phylax policy pack |
| Forensic | redacted envelope and permitted sealed reference | incident evidence, advisory, calibration result | no worker-tool authority |

The agent cannot see monitor prompts, sampling choices, or thresholds. The
monitor cannot invoke worker tools. Retention is `ephemeral`, `incident_scoped`,
or `user_authorized`; raw reasoning is permitted only as an explicitly scoped,
encrypted sealed excerpt and never in PT queue/GossipBus events or ordinary OTLP.
