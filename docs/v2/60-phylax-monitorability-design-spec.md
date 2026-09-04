# 60 — Canonical Phylax Monitorability Design Specification

> **Status:** canonical design authority; v1 is shipped as advisory-only and v2
> admission and enforcement remain future work
> **Date:** 2026-09-04
> **Observability vocabulary:**
> [55 — oramasys Agent Observability Contract](55-oramasys-agent-observability-contract-adr.md)
> **Implementation references:**
> [Part 1 — v1 evidence contract](references/phylax-monitorability-part-1-v1-evidence-contract.md) ·
> [Part 2 — derived inference](references/phylax-monitorability-part-2-derived-inference.md) ·
> [Part 3 — migration and assurance](references/phylax-monitorability-part-3-migration-assurance.md)

## 1. Status

Doc 60 is the canonical monitorability design authority. It binds current v1
producers and consumers to advisory-only compatibility while defining—not
claiming implementation of—the future v2 admission and enforcement boundary.

## 2. Scope

This document is the normative umbrella for Phylax monitorability. It fixes the
ownership, evidence meaning, authority, privacy, liveness, failure, and migration
boundaries above the three implementation references. The references provide
schemas and delivery detail; they do not widen the authority defined here.

The design preserves the shipped Perpetua-Tools (PT) v1 boundary:

- `monitorability` remains optional on a v1 handoff, so a handoff without it is
  valid;
- v1 monitorability is caller-reported, privacy-redacted, and advisory-only;
- `block` is invalid in v1; and
- stored v1 meaning is never reinterpreted in place. A versioned Phylax adapter
  is the only migration boundary into v2 semantics.

This specification does not place a Phylax engine, collector, policy pack,
retention service, or hidden raw-data channel in PT. It does not move application
routing into Phylax, generic policy into Telos, or policy into Core.

## 3. Definitions

This document uses the accepted vocabulary from
[Doc 55](55-oramasys-agent-observability-contract-adr.md):

- **Operation:** a duration-bearing invocation or execution represented as an
  OpenTelemetry span.
- **Event:** a point-in-time transition or decision represented as an
  `EventRecord`/`LogRecord` correlated to an operation.
- **Observation:** an emitted or verified record with identity, correlation,
  provenance, and privacy classification. Trace membership establishes
  correlation, not causation.
- **Observable evidence:** evidence of an action, policy state, approval, tool
  result, or other externally checkable fact independent of a monitor inference.
- **Monitor artifact:** a Phylax-governed append-only result whose epistemic
  status is `derived`, `reconstructed`, `interpolated`, or `forecast`.
- **Admission:** explicit acceptance by the versioned Phylax v2 contract. Schema
  validity or a producer-reported v1 advisory is not Phylax admission.
- **Sealed evidence:** separately governed, encrypted incident-scoped or
  user-authorized material addressed only through an opaque bounded reference.
  The reference is not the evidence and grants no access by itself.
- **Policy decision:** an immutable, attributed Phylax result evaluated under a
  versioned policy pack. An application approval remains a separate Orama
  decision.

## 4. Ownership

| Owner | Normative responsibility | Must not own through this design |
| --- | --- | --- |
| Perpetua-Tools | Producer schemas; typed event and packet emitters; strict validation and redaction; local evidence; evidence-reference syntax and integrity; local and remote adapter projections | Generic monitor semantics, policy packs, v2 admission, escalation policy, or a Phylax retention service |
| Phylax | Generic security/safety runtime checks; policy packs; monitor semantics; fast and forensic evaluation; escalation; derived-artifact and decision retention; v2 admission | PT producer validation, Orama workflow routing, Telos endpoint facts, or worker tools |
| Orama | Application routing; workflow composition; approvals; integration of PT and Phylax contracts | Producer event core, generic monitor policy, raw-evidence storage, or reinterpretation of advisory evidence as authority |
| Telos | Endpoint-specific evidence and endpoint enforcement | Generic monitorability policy, orchestration, or cross-endpoint decision semantics |
| Core | Policy-free graph/state primitives | Imports of Phylax, Orama application modules, Telos policy, or monitor-specific enforcement |

Ownership follows the data, not the call site. Orama may route a PT envelope to
Phylax without owning its schema. PT may project a Phylax decision without
owning its semantics. Telos may enforce an endpoint fact without becoming the
generic safety evaluator.

## 5. Architecture and data flow

The normal path carries redacted typed records and opaque references only:

1. **PT emission.** A producer validates and emits the optional v1
   monitorability envelope with the handoff and produces allowlisted domain
   observations. Invalid input emits neither a queue admission nor an audit
   event.
2. **Orama routing.** Orama composes workflow and approval context, then routes
   the validated envelope/reference set. Routing does not attest to monitor
   truth and does not refresh worker liveness.
3. **Phylax admission.** In v2, the versioned adapter records source contract,
   redaction profile, ordered evidence, and producer attestation. It rejects
   content-bearing references and never elevates a reported v1 advisory into a
   Phylax decision.
4. **Phylax evaluation.** The fast lane evaluates intent, grants, policy state,
   and observable tool/action evidence. The forensic lane evaluates the
   redacted envelope and, only when separately authorized, a sealed reference.
   The monitor cannot invoke worker tools.
5. **Policy decision.** A trusted Phylax issuer creates an immutable attributed
   decision under a versioned policy pack. Orama separately decides application
   routing and approvals.
6. **Audit projection.** PT-owned adapters project an allowlisted, redacted
   event using Doc 55 operation/event, provenance, and transport rules. Normal
   audit and OTLP records contain neither raw evidence nor sealed material.

Sealed-evidence authorization, retrieval, decryption, access audit, and
retention form a separately governed branch from step 4. A handoff, trace, or
sealed reference never implicitly authorizes that branch.

MiniGraph supplies only the policy-free execution and observation boundary
defined through [the kernel specification](01-kernel-spec.md). Monitor-specific
logic remains above Core, and adapters consume canonical observation
projections rather than adding a second scheduler.

### 5.1 Primitive-reuse gate

Architecture records are not substitutes for executable-source verification.

| Candidate | Canonical status for monitorability work |
| --- | --- |
| P1 primitive reuse | Audit-gated until the relevant behavior is verified in executable source and tests |
| P2 primitive reuse | Audit-gated until the relevant behavior is verified in executable source and tests |
| P4 OTLP transport-boundary reuse | Confirmed; retain the PT-owned transport and projection boundary described by Doc 55 |
| P6 primitive reuse | Audit-gated until the relevant behavior is identified and verified in executable source and tests |

No plan may make a P1, P2, or P6 reuse claim a normative dependency before that
audit records the repository, revision, interface, and executable evidence.

### 5.2 System invariants

- Every record has one explicit epistemic class; observations and non-observed
  artifacts remain separate.
- A non-observed artifact can advise or escalate only. It cannot authorize,
  block, rewrite observed history, or grant/revoke a capability.
- A block requires both an independent observable policy violation and explicit
  Phylax admission under an authorized policy pack.
- Normal handoff, audit, and remote export remain redacted and never carry raw
  evidence, prompts, outputs, credentials, host identity, absolute paths, or
  chain-of-thought.
- Only an explicit successful worker presence action refreshes liveness.
- PT, Phylax, Orama, Telos, and Core retain the ownership and dependency
  directions in §4; no routing path changes those boundaries.

## 6. Canonical envelope

The v1 wire contract remains
[`MonitorabilityEnvelopeV1`](references/phylax-monitorability-part-1-v1-evidence-contract.md#contract).
Doc 60 governs the meaning of its fields and the v2 adapter boundary; it does
not duplicate the subordinate schema.

| Field group | Canonical requirements |
| --- | --- |
| Version and source | Explicit schema version and source handoff version; no implicit reinterpretation |
| Identity and correlation | Legitimate operation/provider identifiers, stable logical `agent.id`, ephemeral non-host-derived instance identity, and valid W3C trace/span context |
| Provenance | Full source provenance under Doc 55; correlation is not a causal or authority claim |
| Policy context | Versioned policy-pack identity, risk tier, and capability-grant identifiers |
| Evidence | Ordered opaque evidence references with bounded grammar, length, and count |
| Advisory context | `allow`, `warn`, or `escalate`, explicitly marked producer-reported or accompanied by issuer/attestation state |
| Privacy | Explicit redaction policy and the truthful packet claim `raw_reasoning_persisted_in_packet: false` |
| Integrity | Manifest hash plus internally consistent ordered references; v1 validates syntax and consistency, not the truth of the underlying evidence |

The schema is closed and additive. Identifiers cannot contain content, URLs,
paths, credentials, prompts, outputs, or host identity. New standard producers
emit the envelope, but legacy v1 producers may omit it. Only a future v2
contract may require adapter-normalized monitorability.

## 7. Epistemic artifacts

Observed records never merge with non-observed artifacts in the canonical
event/evidence ledger. Each artifact points to source evidence and states its
own method, version, confidence, validity window where applicable, trace
relation, and `authority: advisory`.

| Epistemic class | Meaning | Additional constraint | Enforcement ground by itself |
| --- | --- | --- | --- |
| Observed | Directly emitted or independently verified action, state, result, or approval | Preserve provenance and distinguish observation from interpretation | May support a policy decision when the policy permits |
| Derived | Monitor classification computed over evidence | Identify method/version, confidence, and source references | Never |
| Reconstructed | Bounded hypothesis about an unobserved event or state within a gap | Requires a bounded interval and bracketing evidence | Never |
| Interpolated | Bounded estimate between observations | Requires a bounded interval and bracketing evidence | Never |
| Forecast | Estimate beyond the observation window | Requires an explicit horizon and expiry; an expired forecast is not live evidence | Never |

Missing actions are not inserted into observed history. Corrections are new,
linked append-only records. A sealed reasoning reference may support an
inference or triage, but it neither proves intent nor changes epistemic class.

## 8. Decision authority

| Input or actor | Permitted effect | Prohibited effect |
| --- | --- | --- |
| PT v1 reported monitor context | Advise `allow`, `warn`, or `escalate`; supply context to a future adapter | Block, grant/revoke capabilities, approve deployment/merge, or claim Phylax authority |
| Observed evidence | Establish a named policy fact when independently verifiable; support a policy decision | Issue a decision without the responsible policy authority |
| Derived, reconstructed, interpolated, or forecast artifact | Advise, warn, escalate, resample, request re-evaluation, or request human review | Authorize or block an action; revise observed history; grant/revoke a capability |
| Sealed reasoning | Improve permitted detection, calibration, or triage | Become the sole enforcement basis or appear in normal telemetry |
| Phylax v2 | Admit normalized evidence and issue a versioned policy decision | Bypass observable grounding, policy-pack authority, or operational gates |
| Orama | Route work, compose workflows, and issue application approvals | Convert advisory monitor output into a Phylax block |
| Telos | Enforce endpoint-specific facts within its endpoint contract | Define generic Phylax policy or cross-application authority |

A future `block` is valid only when all of these conditions hold:

1. independent observable evidence establishes the named policy violation;
2. the versioned policy pack explicitly permits blocking that violation;
3. a trusted Phylax evaluator/issuer explicitly admits the evidence and issues
   the decision; and
4. human review where required, false-block measurement, rollback, audit, and
   retention controls are active.

Therefore a non-observed artifact can only advise or escalate. It never
authorizes or blocks an action, even at high confidence or when correlated with
the same trace.

## 9. Privacy and evidence access

Normal handoff, audit, and remote export must never contain raw chain-of-thought,
prompts, outputs, credentials, host identity, absolute paths, or raw evidence.
Field-name denylists are insufficient; values and nested structures are
validated recursively against the allowlisted contract.

The following boundaries are independent:

- **Classification:** `internal_only` and `redacted` retain their Doc 55
  meanings. A `redacted` record is merely eligible for projection.
- **Destination authorization:** export requires an explicitly configured,
  validated destination. Classification never authorizes a network endpoint.
- **Evidence authorization:** an opaque reference provides correlation only.
  Access to sealed evidence requires a separate scoped authorization and an
  append-only access audit.
- **Decision authority:** possession of local or sealed evidence does not grant
  policy, application, capability, merge, or deployment authority.

Raw reasoning, when explicitly permitted, is limited to an encrypted,
incident-scoped or user-authorized sealed excerpt. It never enters PT queue or
GossipBus events, ordinary OTLP, the canonical envelope, or a monitor rationale
summary. Retention is explicit (`ephemeral`, `incident_scoped`, or
`user_authorized`) and owned by the governing evidence store.

## 10. Liveness

Only an explicit successful worker presence action refreshes liveness. The
following never do so:

- envelope validation or queue admission;
- a log, span, audit event, or adapter projection;
- monitor evaluation, advisory, escalation, or policy decision;
- evidence access or artifact retention; and
- stale-record cleanup.

Monitorability must not turn activity into proof that a worker is alive. A
failed or absent presence action remains failed or absent even if every other
step in the monitorability pipeline succeeds.

## 11. Evaluation and assurance

Evaluation uses the same task corpus across three governed scopes:

| Arm | Inputs | Purpose |
| --- | --- | --- |
| A | Observable actions and outcomes only | Operational baseline |
| B | A plus redacted envelope, intent, capability, and policy context | Provider-neutral monitorability value |
| C | B plus legitimately authorized sealed reasoning | Incremental value of reasoning access |

Each comparison measures precision, recall, false-warning rate, false-block
rate, time to warning/review, triage burden, validation failures, privacy
violations, and drift by model, prompt, provider, tool, policy, redaction, and
mapping version. Artifact evaluation additionally measures calibration error,
forecast precision by horizon, reconstruction disagreement with later observed
evidence, provenance completeness, expiry compliance, and independent
corroboration rate.

Uncertain or insufficient-data results remain explicit. They are not converted
to a degraded score or an enforcement action. Selection and estimation remain
separate for intervention-style evaluation. The detailed red-team matrix and
delivery assertions remain in
[Part 3](references/phylax-monitorability-part-3-migration-assurance.md).

## 12. Rollout and migration gates

No stage may be skipped. Every repository change records owner, contract
version, migration impact, test evidence, and rollback decision.

| Gate | Allowed change | Required evidence | Rollback |
| --- | --- | --- | --- |
| M0 | Existing v1 handoffs omit monitorability | Compatibility suite | None |
| M1 | Optional strict PT envelope and redacted audit | Schema, redaction, audit, and liveness tests | Omit envelope; retain reader |
| M2 | New-standard producers emit the envelope | Complete producer inventory | Disable emission only |
| M3 | Phylax v2 adapter runs in shadow mode | Human-review calibration, privacy evidence, and proof that PT contains no Phylax engine/collector/background monitor/network export/hidden raw channel | Disable adapter; preserve audit |
| M4 | v2 handoffs require adapter-normalized evidence | All v2 producers and claimants migrated | Route legacy callers through the v1 adapter |
| M5 | Guarded blocks for defined observable violations | Independent observable ground, explicit Phylax admission, review, false-block, rollback, audit, and retention gates | Return to advisory mode |

Before M5, the same independently observable violation must be actionable
without chain-of-thought. Reasoning access may improve detection or triage but
cannot become the enforcement basis.

## 13. Failure behavior

| Failure | Required behavior |
| --- | --- |
| v1 monitorability absent | Accept the otherwise valid legacy handoff; no monitor claim is inferred |
| Envelope invalid or contains prohibited content | Reject before queue admission and emit no audit event derived from the invalid packet |
| Evidence reference malformed, content-bearing, or inconsistent | Reject at the PT or v2 adapter boundary; do not dereference or repair heuristically |
| Producer advisory lacks trusted attestation | Preserve it as reported context only; never elevate it to a Phylax decision |
| Phylax unavailable during M3 shadowing | Preserve the v1 path and record bounded operational failure without inventing a decision |
| Required v2 admission unavailable at M4 or later | Fail the v2 admission; use only an explicitly configured v1 compatibility route |
| Sealed-evidence access denied or fails | Continue only with permitted redacted evidence and report insufficient data where needed; never broaden access |
| Forecast expired or reconstruction later contradicted | Exclude it from new decisions and append a linked correction/calibration record |
| Independent observable ground missing | Reject any proposed block; warning, escalation, or human review may remain advisory |
| Required decision/audit integrity append fails | Do not complete a v2 enforcement decision; do not convert failure into allow or block |
| Telemetry export fails or is unconfigured | Keep the validated local boundary; do not invent a collector, relax destination checks, or refresh liveness |

Failures are fail-closed at schema, privacy, access, admission, and enforcement
boundaries, while compatibility remains explicit: absent v1 monitorability is
valid, and v1 never blocks.

## 14. Deferred migration questions

The following are canonical open questions, not approved runtime work. They are
documented here so migration can resolve them with evidence rather than silently
inventing a second contract.

| Question | Current safe position | Resolution gate |
| --- | --- | --- |
| Coordination-round context | The standalone `CoordinationRoundEnvelopeV1` design groups controller, scope, and stop conditions without changing `HandoffPacketV1`; see the approved design record. | M2 producer inventory and contract/fixture conformance review before any producer-emission mandate. |
| Phylax runtime owner | No repository/package has yet been named as the executable v2 owner. | M0.1 names owner, dependency direction, validator location, and retention boundary before runtime code. |
| Derived-artifact persistence | Append-only governed storage is required, but no implementation store is selected. | M0.1/M3 privacy, access-audit, expiry, and rollback evidence. |
| OTel baseline evolution | The current adapter map is pinned; later GenAI semantic-convention updates are not implicit. | Mapping regression, explicit review identifier, and no-emission-before-approval gate. |

These questions are docs-only planning inputs until their named gate passes. They
do not authorize v2 code, change v1 compatibility, alter worker liveness, or
create a policy/enforcement path.

## 15. Source hierarchy

Use the following precedence when statements conflict:

1. This document governs Phylax monitorability ownership, epistemic meaning,
   decision authority, privacy, liveness, failure behavior, and migration gates.
2. [Doc 55](55-oramasys-agent-observability-contract-adr.md) governs canonical
   observation vocabulary, identifiers, provenance, privacy tiers, and adapter
   transport behavior.
3. [Part 1](references/phylax-monitorability-part-1-v1-evidence-contract.md),
   [Part 2](references/phylax-monitorability-part-2-derived-inference.md), and
   [Part 3](references/phylax-monitorability-part-3-migration-assurance.md)
   govern subordinate schema, artifact, evaluation, and rollout detail only
   where consistent with items 1 and 2.
4. [The kernel specification](01-kernel-spec.md) and the authorities to which it
   redirects govern MiniGraph. MiniGraph is not a monitorability policy or
   enforcement authority.
5. Current executable schemas and tests establish what is shipped. Historical
   implementation labels alone do not establish primitive availability or
   reuse fitness; the P1/P2/P6 audit gates in §5.1 remain in force.

When implementation diverges from this specification, preserve evidence and
compatibility, record the mismatch, and migrate through an explicit versioned
boundary. Do not silently reinterpret old records or broaden authority.
