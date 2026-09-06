# Phylax Monitorability — Part 3: Migration, Evaluation, and Assurance

**Status:** subordinate rollout, test, and operational assurance guidance

**Normative authority:** [Doc 60 — Canonical Phylax Monitorability Design
Specification](../60-phylax-monitorability-design-spec.md). Doc 60 governs
ownership, authority, privacy, liveness, and the required admission gates; this
part supplies the rollout and assurance detail.

**Implementation modules:**
[Part 1 — v1 evidence contract](phylax-monitorability-part-1-v1-evidence-contract.md) ·
[Part 2 — derived inference](phylax-monitorability-part-2-derived-inference.md)

## Migration ladder

| Stage | Change | Required proof | Rollback |
| --- | --- | --- | --- |
| M0.1 | record the Phylax package/repository boundary before any Phylax runtime code | named owning repository/package, dependency direction, and confirmation that PT remains the producer/adapter boundary | no runtime code introduced |
| M0.2 | run the executable primitive-reuse inventory audit | for each P1, P2, and P6 candidate: repository, revision, interface, executable-source evidence, and tests; retain P4 only as the confirmed PT-owned transport/projection boundary | do not depend on an unverified reuse claim |
| M0.3 | existing v1 handoffs without monitorability | compatibility suite passes | none |
| M1 | optional strict PT envelope and redacted audit | schema, redaction, audit, liveness tests pass | omit envelope; keep reader |
| M2 | new-standard producers emit envelope | producer inventory is complete | disable emission only |
| M3 | Phylax v2 adapter consumes evidence in shadow mode | human-review calibration and privacy evidence | disable adapter; preserve audit |
| M4 | v2 handoffs require adapter-normalized envelope | all v2 producers and claimants migrated, and a mixed-version rollback test passes | legacy callers route through the v1 adapter; already-migrated v2 callers remain accepted by the v2 normalizer in advisory/shadow compatibility mode; both retain their original audit trail and gain no new enforcement authority |
| M5 | guarded blocks for defined observable violations | independent observable evidence, explicit Phylax v2 admission, review, false-block, and rollback gates | return to advisory mode |

No stage may be skipped. Stored v1 meaning never changes in place; the v2
adapter is the compatibility and interpretation boundary.

M0.1 and M0.2 are explicit pre-code gates, not deferred implementation work.
They keep Core policy-free, prevent upward imports of Phylax or application
modules, and prevent an architecture record from standing in for executable
reuse evidence.

## Evaluation design

Run the same task corpus through three monitor scopes:

| Arm | Inputs | What it measures |
| --- | --- | --- |
| A | actions and outcomes only | operational baseline |
| B | redacted envelope, intent, capabilities, and tool/action evidence | provider-neutral monitorability |
| C | B plus legitimately permitted sealed reasoning | incremental value of reasoning access |

Track precision, recall, false-warning and false-block rate, time to warning,
time to human review, triage burden per thousand runs, validation-failure rate,
privacy violations, and drift by model/prompt/provider/tool/policy version.

For Part 2 artifacts additionally track calibration error, forecast precision by
horizon, reconstruction disagreement with later observed evidence, source
provenance completeness, expiry compliance, and the rate at which a derived
signal becomes independently corroborated. Report uncertain/insufficient-data
results as such; never convert them into a degraded score or policy action.

Adapt public monitorability evaluation patterns only behind the governed v2
evaluation interface. Selection and estimation must be separated for
intervention-style results so noise-selected instances do not inflate reported
monitorability.

## Red-team matrix

| Threat | Required assertion |
| --- | --- |
| watcher-aware behavior | monitor signal remains advisory without observable ground |
| raw content smuggled into an opaque ID | validation rejects it before PT admission |
| tool result diverges from declared intent | trace-linked finding is recorded without asserting causal intent |
| provider summary impersonates CoT | summary remains bounded metadata/evidence, never raw reasoning |
| sealed reference copied into audit | allowlist projection omits it |
| monitor asks to block without evidence | decision validation rejects it |
| forecast survives beyond horizon | expired artifact cannot influence a new decision |
| OTel semantic drift | unknown, incompatible, or non-additive mappings reject or hold projection; no changed projection emits before explicit mapping approval |
| activity masquerades as heartbeat | admission/log/advisory leaves liveness unchanged |

## Artifact-specific authorization assertions

Every non-observed artifact is advisory-only. The following assertions prevent
an inference class from becoming an authorization bypass through a future
implementation or migration shortcut.

| Artifact class | Required assertion |
| --- | --- |
| forecast | a forecast may warn or escalate, but cannot authorize a block; any block requires independently observable evidence for the named violation and an explicit authorized Phylax v2 decision |
| reconstruction | a reconstruction may guide investigation, but cannot authorize a block or revise observed history; any block requires independently observable evidence and an explicit authorized Phylax v2 decision |
| interpolation | an interpolation may fill an analysis gap for triage, but cannot authorize a block; any block requires independently observable evidence and an explicit authorized Phylax v2 decision |
| provider summary | a provider summary remains bounded metadata/evidence rather than CoT and cannot authorize a block; any block requires independently observable evidence and an explicit authorized Phylax v2 decision |
| CoT-derived artifact | a legitimately accessed CoT-derived artifact may raise concern or improve triage, but cannot authorize a block; any block requires independently observable evidence and an explicit authorized Phylax v2 decision |

## Operational controls

- Keep a policy-to-evidence matrix for every potential block rule.
- Version policy packs, monitor methods, calibration sets, redaction profiles,
  and OTel mappings independently.
- Audit all access to incident-scoped or user-authorized sealed material.
- Separate privacy classification from export authorization and from authority.
- Require a human-reviewed rollback path before changing `warn`/`escalate` to
  any enforcement behavior.
- Before M4, run a mixed-version rollback acceptance test: a legacy v1 packet
  and a previously normalized v2 handoff are both accepted after rollback,
  preserve their respective audit records, and remain advisory-only.
- Before emitting a projection, run the pinned Part 1 mapping regression. A
  mapping delta is rejected or held pending an explicit review identifier; CI
  proves that no changed projection was emitted before that approval.
- Preserve append-only evidence and decision records; corrections are new,
  linked records rather than rewritten historical claims.

## Delivery gates

Before M3, confirm that PT contains no Phylax engine, collector, background
monitor, network export, or hidden raw-data channel. Before M5, confirm that
the same independently observable violation would be actionable without CoT;
CoT may improve detection and triage, never become the sole enforcement basis.

Before M3, the named Phylax owner must publish the repository-owned validator
and conformance suite specified by Part 2; this document does not substitute a
Markdown claim for executable validation.

Every repository change records its owner, contract version, migration impact,
test evidence, and rollback decision. Telos changes only when an endpoint fact
is required; Core remains dependency-minimal and does not import application or
Phylax policy upward.
