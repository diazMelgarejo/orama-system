# Phylax Monitorability — Part 3: Migration, Evaluation, and Assurance

**Status:** rollout, test, and operational assurance plan

**Companion parts:** [Part 1](phylax-monitorability-part-1-v1-evidence-contract.md) · [Part 2](phylax-monitorability-part-2-derived-inference.md)

## Migration ladder

| Stage | Change | Required proof | Rollback |
| --- | --- | --- | --- |
| M0 | existing v1 handoffs without monitorability | compatibility suite passes | none |
| M1 | optional strict PT envelope and redacted audit | schema, redaction, audit, liveness tests pass | omit envelope; keep reader |
| M2 | new-standard producers emit envelope | producer inventory is complete | disable emission only |
| M3 | Phylax v2 adapter consumes evidence in shadow mode | human-review calibration and privacy evidence | disable adapter; preserve audit |
| M4 | v2 handoffs require adapter-normalized envelope | all v2 producers and claimants migrated | route legacy callers through v1 adapter |
| M5 | guarded blocks for defined observable violations | independent evidence, review, false-block, and rollback gates | return to advisory mode |

No stage may be skipped. Stored v1 meaning never changes in place; the v2
adapter is the compatibility and interpretation boundary.

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
| OTel semantic drift | mapping-version regression flags review before projection changes |
| activity masquerades as heartbeat | admission/log/advisory leaves liveness unchanged |

## Operational controls

- Keep a policy-to-evidence matrix for every potential block rule.
- Version policy packs, monitor methods, calibration sets, redaction profiles,
  and OTel mappings independently.
- Audit all access to incident-scoped or user-authorized sealed material.
- Separate privacy classification from export authorization and from authority.
- Require a human-reviewed rollback path before changing `warn`/`escalate` to
  any enforcement behavior.
- Preserve append-only evidence and decision records; corrections are new,
  linked records rather than rewritten historical claims.

## Delivery gates

Before M3, confirm that PT contains no Phylax engine, collector, background
monitor, network export, or hidden raw-data channel. Before M5, confirm that
the same independently observable violation would be actionable without CoT;
CoT may improve detection and triage, never become the sole enforcement basis.

Every repository change records its owner, contract version, migration impact,
test evidence, and rollback decision. Telos changes only when an endpoint fact
is required; Core remains dependency-minimal and does not import application or
Phylax policy upward.
