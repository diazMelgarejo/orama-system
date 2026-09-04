# Phylax Monitorability — Part 2: Derived Inference and Decision Model

**Status:** v2 design authority; not a Perpetua-Tools v1 implementation task

**Companion parts:** [Part 1](phylax-monitorability-part-1-v1-evidence-contract.md) · [Part 3](phylax-monitorability-part-3-migration-assurance.md)

## Objective

Phylax turns redacted operational evidence and legitimately accessible sealed
reasoning into calibrated safety signals. It never presents an unobserved
thought, action, causal relation, or forecast as a canonical fact.

The design therefore separates four epistemic classes:

| Class | Meaning | Can establish an enforcement ground? |
| --- | --- | --- |
| Observed | directly emitted/verified action, policy state, tool result, or approval | yes, when policy permits |
| Derived | monitor classification over evidence | no by itself |
| Reconstructed/interpolated | bounded hypothesis about a gap between observations | no |
| Forecast/extrapolated | expiring estimate beyond the observation window | no |

Trace membership proves correlation, not causation. A sealed reasoning reference
may support a monitor inference but never by itself proves intent or authorizes
an action.

## v2 inputs

The versioned adapter normalizes the v1 envelope rather than parsing Markdown,
logs, or raw agent output:

```python
class PhylaxMonitorabilityInputV2(BaseModel):
    contract_version: Literal[2]
    source_handoff_version: Literal[1]
    redacted_observation_ref: OpaqueEvidenceRef
    policy_context: PolicyContextV2
    observable_evidence: list[ObservableEvidenceV2]
    sealed_reasoning_ref: OpaqueEvidenceRef | None
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
    epistemic_status: Literal[
        "derived", "reconstructed", "interpolated", "forecast"
    ]
    subject_kind: Literal[
        "action", "action_sequence", "policy_state", "risk_trajectory"
    ]
    source_evidence_refs: list[OpaqueEvidenceRef]
    trace_relation: Literal[
        "same_span", "ancestor_span", "descendant_span",
        "correlated_only", "causal_unknown"
    ]
    method_id: str
    method_version: str
    confidence: float
    calibration_ref: OpaqueEvidenceRef | None
    valid_from: datetime | None
    valid_until: datetime | None
    sealed_reasoning_ref: OpaqueEvidenceRef | None
    authority: Literal["advisory"]
```

`reconstructed` and `interpolated` require a bounded interval plus bracketing
evidence; `forecast` requires an explicit future horizon and expiry. A missing
action is never inserted into the canonical event ledger. A forecast that has
expired is not a live risk signal.

## Decision contract and authority

```python
class PhylaxMonitorabilityDecisionV2(BaseModel):
    decision: Literal["allow", "warn", "escalate", "block"]
    severity: SeverityV2
    confidence: float
    policy_ids: list[str]
    observable_evidence_refs: list[OpaqueEvidenceRef]
    derived_artifact_refs: list[str]
    monitor_rationale_summary: str
    human_review_required: bool
    retention_class: RetentionClassV2
```

Every decision has an issuer, immutable decision ID, policy-pack version,
timestamp, integrity hash, and append-only correlation to its source evidence.
`monitor_rationale_summary` is concise and redacted; it must not copy CoT.

A future `block` is valid only if all conditions hold:

1. at least one independently observable evidence reference proves the named
   policy violation;
2. the policy pack explicitly permits blocking that violation;
3. a trusted Phylax evaluator/issuer creates the decision; and
4. review, false-block, rollback, and retention controls are active.

A derived artifact may trigger warning, re-evaluation, sampling, or human
review. It cannot block, grant/revoke a capability, revise observed history, or
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
