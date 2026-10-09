# D-LG-5 — Reducer and join declarations live in the structural GraphSpec

**Decision slice:** the ownership row only, directed by the operator on 2026-10-10.
It amends one row of [D-LG-1](ADR-D-LG-1-POLICY-OWNERSHIP.md). The R3 mechanics
(supersteps, reducer and join semantics, final field names) remain gated and need
their own ADR and a Core PR. No runtime code ships with this decision.

## Context

D-LG-1's field-placement table put "reducer/join declarations" under *Oramasys policy
design*. Its own rubric says a field belongs in Core "only when removing it prevents
structural execution or verification". The two disagree on this one row.

A reducer decides which value a field ends up with when branches write to it, so it
changes what a graph computes. If it lived only in a swappable policy file, one
`graph_id` could compute two different results, or Core could not run the graph
without policy. Both break D-LG-1's own promise that structure is verifiable without
policy.

Older records also describe `orama-system` as the "GraphSpec/NodeSpec/EdgeSpec
authority" (doc 57 §12 and the 2026-08-29 plan). In code there is exactly one
GraphSpec, Core's. `orama-system` holds no schema code. See erratum E12.

## Decision

1. **Core owns the schema.** Reducer tables, join declarations and any fan-out edge
   kinds are fields of the structural GraphSpec. They are part of `graph_id`.
2. **Oramasys authors the declarations** for its concrete graphs, in its graph
   builders, and owns `GraphPolicy`.
3. **Policy can only restrict.** A policy may require every concurrently written
   field to have a declared reducer, forbid `LAST` on audited fields, set a minimum
   join failure policy, or set budgets. It may not add, remove or change a
   declaration. Unknown policy fields keep failing closed.
4. **Orama `docs/v2` records the decision and the registry.** It holds no schema and
   no runtime code.
5. **Graphs that use none of this are unchanged.** They keep schema `"1"` and an
   identical `graph_id`. Core emits a new schema version only for a graph that
   declares reducers, joins or fan-out. Existing policy bindings stay valid.

## Rubric amendment

| Test | Result |
| --- | --- |
| Does it change the state the graph produces? | Core structural GraphSpec |
| Does it only narrow who may run it, or how far? | Oramasys policy |
| Does it only explain why? | Orama docs |

Where D-LG-1 and this ADR differ, this ADR controls for reducer and join
declarations only. Every other D-LG-1 row stands.

## Single authority, checked by a registry

For each fact exactly one place declares it. Everything else is derived or verified.
[`ownership-registry.json`](ownership-registry.json) lists every field of the
registered records with one owner and one category, and marks future fields as
`planned`.

Oramasys keeps a byte-identical, content-addressed snapshot as a test fixture and
runs conformance tests against the installed Core and its own `GraphPolicy`. The
tests fail if:

- a field exists in code but is missing from the registry, or has a different owner;
- a policy field is in the `computes` category;
- a `planned` entry already exists in code, so the registry must be updated when the
  field ships;
- the snapshot differs from the pinned digest, so a registry change is a reviewed
  change in both repositories.

## Alternatives

| Option | Assessment |
| --- | --- |
| Reducers and joins only in Oramasys policy (D-LG-1 table row) | Rejected: one `graph_id`, two possible results |
| A richer GraphSpec held in `orama-system` | Rejected: no runtime owner, and docs cannot enforce a hash |
| Core GraphSpec plus restrict-only policy | Adopted |
| Reducers as run-time arguments from policy | Rejected: Core would need policy to execute |

## Supersession

| Earlier statement | Status |
| --- | --- |
| D-LG-1 row "Reducer/join declarations and version/evaluation selection" | Split: reducer/join moves to Core; version and evaluation selection stay in Oramasys policy |
| Doc 57 §12 and 2026-08-29 plan, "orama-system GraphSpec authority" | Superseded by D-LG-1 for structure; read as "normative text" |
| 2026-08-29 plan §4, "orama-system owns GraphSpec declarations" | Read as "the application's graph definition", authored in Oramasys |
| Rev2 draft `policy.reducers` and `policy.joins` | Historical proposal; preserved unchanged in `history/` |

Historical files are not edited. Erratum E12 records the readings.

## Acceptance and rollback

- The registry parses and every registered record resolves in the pinned Core and
  the current Oramasys.
- Conformance tests pass in Oramasys CI, and fail when a field is added to code
  without a registry change.
- No Core, Oramasys runtime or policy-schema change ships with this ADR.

Rollback removes the registry, the tests and this ADR's amendment note. D-LG-1 reverts
to its prior row text, which is preserved in git history.
