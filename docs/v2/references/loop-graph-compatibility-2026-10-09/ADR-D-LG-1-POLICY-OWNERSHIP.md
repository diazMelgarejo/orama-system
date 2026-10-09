# D-LG-1 — Structural graph and separately bound policy

**Amended 2026-10-10 by [D-LG-5](ADR-D-LG-5-REDUCER-JOIN-DECLARATIONS.md), reducer/join
row only.**

**Decision slice:** approved by the operator on 2026-10-09. This records the
explicit ownership amendment required by doc 57 §12 and doc 59 §7. Broader
replacement ADRs D-LG-2/3 remain proposals. Implementation is reviewed in
[Core #8](https://github.com/oramasys/perpetua-core/pull/8) and
[Oramasys #23](https://github.com/oramasys/oramasys/pull/23).

## Decision and alternatives

Core retains structural GraphSpec/NodeSpec/EdgeSpec, its content-hash graph_id,
structural lint and its one scheduler. Oramasys owns a separate, immutable,
versioned graph-policy file, bound to the exact graph_id. Orama docs/v2 owns
normative planning; it does not acquire a dependency on v2 runtime code.

| Option | Assessment |
| --- | --- |
| Separate policy file and application-level transclusion | Adopted: policy revisions do not invalidate structure; ownership is explicit |
| Documentation-only policy | Rejected for executable binding: prose cannot reject stale hashes |
| Policy fields in Core GraphSpec | Rejected: couples enforcement changes to kernel pins and mixes authorities |

The application graph definition is a PolicyBinding containing graph, policy
and a repository-relative policy reference. Its summary includes both hashes,
revision, budgets, approval disposition and effect declarations. The summary
is a projection, never an authorization token. Do not insert policy_id into
GraphSpec metadata: doing so couples the hashes and risks a circular identity.

## Field-placement rubric

| Field / operation | Owner | Reason |
| --- | --- | --- |
| Nodes, static edges, router refs, declared targets, max_steps | Core | Required to describe and verify structure |
| Structural schema_version and graph_id | Core | Kernel can verify them without policy imports |
| Budget ceilings, effects/replay intent, policy revision | Oramasys policy | Application choices evolve independently |
| Reducer/join declarations | Core structural GraphSpec (D-LG-5; was Oramasys policy) | They change the computed result, so they belong in `graph_id`; policy may only restrict |
| Version/evaluation selection | Oramasys policy design | Still gated; reject unknown fields in schema 1 |
| Effect identity, retries, durable grant use accounting | Oramasys composition | Outside the scheduler, requires provider reconciliation |
| Hardware placement, admission, endpoint transport | Agate, Phylax, Telos respectively | A graph document cannot replace those authorities |
| Architecture, acceptance gates, pattern research | Orama docs/v2 | Normative source, independent v1 system |

A field belongs in Core only when removing it prevents structural execution or
verification across applications. If it chooses who may execute, what effect
may happen, or how an application evaluates outcomes, it belongs above Core.
Adding a policy field requires a new schema revision and migration evidence;
unknown keys must fail closed rather than be silently ignored.

## Implemented slice and migration

Oramasys implements GraphPolicy, bounded strict JSON loading, independent
policy_id hashing and bind_policy lint. Its packaged default.json binds the
existing route → dispatch → respond graph. build_application_graph_definition()
exposes the transclusion without changing build_graph() behavior or Core's
structural schema.

Schema 1 is an intent/lint contract, not enforcement. Durable approvals,
reducers/joins, evaluation, global budget enforcement and effect deduplication
are not implemented by this slice. A replay declaration cannot authorize a
retry. The existing Agate and Telos gates remain mandatory.

First merge the design/evidence PRs; review and merge Core; then update the
Oramasys production pin to that immutable merged SHA and rerun its full suite.
The candidate is tested as an explicit local overlay, never substituted into
published dependency metadata before merge.

## Acceptance and rollback

Reject stale graph hashes, unknown keys, bool/string/zero/negative budgets,
duplicate or unknown effect nodes, mutable nested policy values, oversized JSON,
traversal references and idempotent declarations missing an operation identity.
Changing policy must leave graph_id unchanged; changing structure must require
rebinding. Verify the summary's policy_id against the canonical file.

Rollback removes the new binding consumer and policy file; no Core migration is
needed. Keep the approved decision and superseding history, even if code is
later reverted. See [policy contract](GRAPH-POLICY-CONTRACT.md) for remaining
security gates.
