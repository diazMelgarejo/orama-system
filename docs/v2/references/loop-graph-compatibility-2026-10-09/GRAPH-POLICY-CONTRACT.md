# Graph-policy contract — revision 1

**Date:** 2026-10-09 UTC. **Code owner:** Oramasys. **Architecture:** [D-LG-1](ADR-D-LG-1-POLICY-OWNERSHIP.md).
The implemented subset is explicitly smaller than the security target.

## Identity and loading

The canonical document is bounded UTF-8 JSON (maximum 65,536 bytes). Nested
records are frozen, strict and reject extra keys. graph_id must exactly match
Core's canonical structural hash. policy_id is SHA-256 of the validated model
dump with sorted keys and compact JSON separators; it includes defaults.
Canonicalization identifies the policy; it does not validate signatures or
establish trust in its author.

| Schema-1 field | Constraint | Authority |
| --- | --- | --- |
| policy_schema_version | Literal string 1 | Parser compatibility |
| graph_id | 64 lowercase hex characters, exact structural match | Core structure |
| revision | Positive integer, no coercion | Document bookkeeping |
| budgets | Optional positive requests/input_tokens/output_tokens | Intent only in this slice |
| effects | At most 256 unique existing node names; pure/untrusted/provider | Conservative effect classification |
| replay | deny by default; idempotent requires logical operation_id | Intent, not deduplication |
| approval | deny-until-durable only | No executable overrides |

The reference is a repository-relative locator, not an executable include or
network URL. Loading is explicit; there is no automatic reference fetching.
The application transcludes a fresh summary and both hashes. Never execute from
that summary alone.

## Security target and refusal rules

Future execution must authenticate the policy owner, validate structural lint,
match the exact policy/graph revisions, apply Agate hardware decisions, Phylax
admission and Telos egress, and evaluate monotonic runtime budgets. Any failure
is a recorded refusal or pending HITL escalation. A human approval enables only
an existing authorized exception path; it does not replace hardware feasibility,
authentication or non-overridable rules.

Durable approval binds operator identity, graph_id, policy_id, operation/request
digest, scope, expiry and single-use accounting across crashes/resume. Schema 1
does not implement this. Foreign agent/provider runs remain blocked in production.
Missing effect declarations are not evidence that a node is pure: runtime
admission must default unknown effects to untrusted and validate all reachable
effectful nodes before enabling them.

Logical effect identity is (durable_run_id, logical_operation_id), effect kind
and canonical request digest. An attempt is evidence only. Remote unknown
outcomes require provider reconciliation/idempotency; audit JSONL is not dedupe.

## Evolution and acceptance

Reducers, joins, state-schema versions, implementation pins, evaluation rubrics
and policy-selection rules require explicit future schema versions. Unknown
fields fail closed today. Prefer an independent policy revision over adding
application fields to Core. Preserve policy revisions and decision lineage.

Implemented tests cover hash drift, strict input bounds, immutability, unknown
fields/nodes, size, reference traversal and application transclusion. Future
acceptance must additionally cover signed policy provenance, full reachable-node
effect coverage, policy substitution, budget exhaustion under parallel execution,
grant replay after a crash, unknown effect completion, revoked/expired grants,
and all applicable authority gates. These remain release blockers rather than
claims of this implementation.
