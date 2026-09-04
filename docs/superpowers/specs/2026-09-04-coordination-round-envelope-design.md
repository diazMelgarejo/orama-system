# Coordination-Round Envelope Design

**Status:** approved design direction; implementation requires this document's
review and a follow-up plan

**Date:** 2026-09-04

**Related authority:** [Doc 60 — Canonical Phylax Monitorability Design
Specification](../../v2/60-phylax-monitorability-design-spec.md) and
[Part 3 — Migration, Evaluation, and Assurance](../../v2/references/phylax-monitorability-part-3-migration-assurance.md)

## Goal

Close the coordination-header gap identified in the Phylax synthesis without
changing the shipped `HandoffPacketV1` wire contract or granting monitorability,
coordination, or telemetry records any new authority.

## Decision

Define a standalone, optional **CoordinationRoundEnvelope** as an M2 contract
and conformance target. This first step defines and tests the record only; it
does not require any producer to emit it, does not modify a v1 handoff, and
does not introduce a Phylax runtime.

The record groups multiple handoffs in one bounded coordination episode. It
holds the four currently unrepresented facts—round identity, controller,
explicit scope boundary, and stopping condition—without duplicating raw intent,
prompt text, or agent reasoning.

## Contract

```python
class CoordinationRoundEnvelopeV1(BaseModel):
    schema_version: Literal[1]
    round_id: BoundedIdentifier
    session_id: BoundedIdentifier
    controller_id: BoundedIdentifier
    objective_ref: OpaqueEvidenceRef
    out_of_scope_refs: list[OpaqueEvidenceRef] = Field(default_factory=list, max_length=20)
    stop_condition_codes: list[Literal[
        "task_complete", "approval_required", "validation_failure",
        "budget_exhausted", "deadline_reached", "operator_stop"
    ]] = Field(min_length=1, max_length=6)
    stop_condition_detail_refs: list[OpaqueEvidenceRef] = Field(default_factory=list, max_length=20)
    ordered_handoff_refs: list[OpaqueEvidenceRef] = Field(min_length=1, max_length=20)
    authorization_ref: OpaqueEvidenceRef
    authority: Literal["coordination_only"]
    liveness_effect: Literal["none"]
    created_at: datetime
    expires_at: datetime
    supersedes_round_ref: OpaqueEvidenceRef | None = None

    @model_validator(mode="after")
    def enforce_interval_and_reference_rules(self):
        if self.created_at >= self.expires_at:
            raise ValueError("round expires_at must follow created_at")
        if len(set(self.ordered_handoff_refs)) != len(self.ordered_handoff_refs):
            raise ValueError("ordered_handoff_refs must be unique")
        if len(self.model_dump_json().encode("utf-8")) > 8192:
            raise ValueError("serialized envelope must not exceed 8192 bytes")
        return self
```

### Adopted limits, and why

These are newly-adopted v1 numbers, stated explicitly rather than left as
vague "bounded" language, per direct resolution of the coordination-limits
open question. Not invented silently: `BoundedIdentifier`/`OpaqueEvidenceRef`
reuse Part 1's existing, already-shipped grammar (128 chars for identifiers,
confirmed directly against the real regex; ~73 chars for opaque references,
bounded by their own `{16,64}` hex-digest pattern) rather than defining a new
length. The four list-length caps (20 each) and the 8192-byte total-envelope
cap are genuinely new for this record, chosen conservatively rather than
derived from an existing production number, since none of the checked
existing budgets (`.agent/loops/budget.json`: `max_attempts=3`,
`max_output_chars=200000`, `max_changed_files=10`) map cleanly onto a
coordination-round envelope's specific shape. `stop_condition_codes` is
capped at 6 specifically (not 20), matching the literal's own fixed
enumeration size — a round can plausibly cite every stop condition at most
once each, so a higher cap would only mask a real bug (duplicate codes) as
valid data.

If v2 Phylax governance later sets different numbers before M2 lands, this
document's values are the ones to revise — they are the v1 baseline, not a
permanent ceiling.

`BoundedIdentifier` uses the established Part 1 bounded-identifier grammar.
`OpaqueEvidenceRef` uses the established Part 1 opaque-reference grammar and
does not itself grant access. The record has no free-form objective, scope, stop
condition, actor reasoning, prompt, output, host, path, URL, or credential
field. A detailed scope or stopping rationale belongs in governed evidence and
is reachable, if authorized, only through an opaque reference.

## Authority and ownership

| Concern | Decision |
| --- | --- |
| Contract owner | Orama defines the coordination-round integration contract; the eventual runtime owner is named before code is introduced. |
| Producer relationship | A later producer may reference a round, but a legacy `HandoffPacketV1` remains valid without one. |
| Application authority | `authority: coordination_only` cannot grant merge, publish, deployment, capability, or Phylax policy authority. |
| Monitorability authority | A round record is contextual evidence only. It cannot be used to authorize, block, or upgrade a derived monitor artifact. |
| Liveness | Creation, routing, observation, update, expiry, or archival of a round never refreshes worker liveness. |
| Sealed material | `objective_ref`, scope references, and stop-condition detail references are correlation handles; separate evidence authorization is still required. |

## Data flow

1. An Orama coordinator may create a bounded round record before dispatch.
2. Existing handoffs continue to validate independently under their v1 schema.
3. A later producer can attach an opaque round reference without copying the
   record into packet/audit telemetry.
4. Orama uses the record for workflow composition and operator review only.
5. Monitorability can correlate it as context but must apply the Doc 60
   epistemic and authorization rules independently.
6. On expiry or replacement, append a successor record; do not rewrite prior
   coordination history.

## Conformance requirements

The M2 implementation must provide fixtures and tests that prove all of the
following before producer emission can become a later requirement:

| Case | Expected result |
| --- | --- |
| valid round with opaque objective/scope references | accepted without copying referenced content |
| raw text, URI, path, secret, or duplicate handoff reference | rejected before storage or projection |
| no stop condition, invalid code, or an expired interval | rejected |
| `authority` other than `coordination_only` | rejected |
| record creation or update | leaves liveness unchanged |
| legacy v1 handoff with no round reference | remains valid and behaviorally unchanged |
| round context plus a derived artifact | cannot authorize a block, merge, deployment, or capability change |

## Rollout and non-goals

- **M2a (this integration):** publish the contract, fixtures, and conformance
  criteria; no producer-emission mandate.
- **M2b (separate decision):** inventory new-standard producers and decide
  whether/when an optional round reference becomes required for selected flows.
- **M3+:** Phylax may consume the context only through its existing admission,
  privacy, and observable-evidence gates.

Out of scope: changing PT v1 packet fields, introducing a Phylax repository or
runtime, persisting raw coordination prose in normal telemetry, changing worker
liveness, or creating merge/deployment enforcement.
