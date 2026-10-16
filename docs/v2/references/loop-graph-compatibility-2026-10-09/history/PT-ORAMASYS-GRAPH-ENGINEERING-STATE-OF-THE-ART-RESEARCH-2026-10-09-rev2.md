---
title: "State-of-the-Art Graph Engineering for Agentic Systems — Status, Security Overlay, and Compatibility (Revision 2)"
date: 2026-10-09
status: "Revision 2 — research companion re-baselined against live code. Planning authority remains orama-system docs/v2; code target remains oramasys/oramasys."
revision_of: "PT-ORAMASYS-GRAPH-ENGINEERING-STATE-OF-THE-ART-RESEARCH-2026-08-26.md"
companion: "PT-ORAMASYS-PROMPT-LOOP-GRAPH-MINIGRAPH-MEMORY-2026-10-09-rev2.md"
scope:
  - "20 generic graph-engineering conventions, with status against live code"
  - "security and trust-boundary overlay (ownership, not new design)"
  - "LangGraph compatibility boundary"
  - "re-prioritised adoption plan with owner repository"
verification_basis:
  checked_on: 2026-10-09
  method: "read-only checkout of each repository's default branch; file and symbol presence, not test execution"
  heads:
    perpetua_tools: "e8d7333 (2026-10-07)"
    orama_system: "b131215 (2026-10-07)"
    perpetua_core: "c0795bc (2026-09-27)"
    oramasys_oramasys: "d1656b0 (2026-09-30)"
    telos: "9aa1863 (2026-09-27)"
    phylax: "475f6c2 (2026-09-27)"
    agate: "2089483 (2026-09-13)"
---

# State-of-the-Art Graph Engineering — Revision 2

> **Evidence labels**
>
> - **[V]** verified by reading the current default branch of the named repository on 2026-10-09 (presence of file, symbol, or field; tests *not* executed);
> - **[D]** stated by a canonical orama-system `docs/v2` record (cited by number);
> - **[P]** proposal in this document — not a contract until ratified in `docs/v2`;
> - **[X]** external research claim, not independently verified here.

> **Boundary rule used throughout.** orama-system `docs/v2` is the planning and
> documentation authority. `oramasys/oramasys` is the intended target of planned
> code unless a line says otherwise. `perpetua-core` is the dependency-minimal
> kernel and takes only what the kernel invariants allow.

---

# 0. Provenance and what changed

## 0.1 Source and context of the 2026-08-26 original

- It is the research companion to the 2026-08-26 memory recall. Both were
  **inputs** to the MiniGraph reconciliation run of 2026-08-26 and are listed by
  name in that plan, next to a third-party 99-line engine rewrite. [V]
- Apart from line wrapping it is identical to artifact `003-STATE-OF-THE-ART-RESEARCH-2026-08-26.md`
  in the reconciliation bundle. [V — diffed]
- Its X/Twitter sections were written as a *signal* survey and carry their own
  "method warning"; they are not technical evidence.

## 0.2 What became of it

Its doctrine was absorbed by orama-system `docs/v2/57` (final reconciliation),
`58` (observer pattern library) and `59` (state, mutation, observer
finalization), and merged into `perpetua-core` as Core PR #1. [D 57, 59]
Several items the original called "future" now exist in Core; several it called
"P0" are still open. §2 records which is which.

## 0.3 What Revision 2 adds

1. A per-convention **status** against live code (§2).
2. A **security and trust-boundary overlay** that assigns each concern to its
   existing owner instead of re-inventing it (§3).
3. A **LangGraph compatibility boundary** (§4).
4. A re-prioritised plan with **owner repository** per item (§6).
5. A GraphSpec policy-layer sketch aligned to Core's *real* field names (§7).
6. A confidence matrix with a "verified in repo" column (§10).

Unverifiable engagement numbers from the X sections were dropped (§5).

---

# 1. Executive synthesis (unchanged in substance)

- The strongest generic convention is the **ladder**: use the least powerful
  control structure — prompt, then chain, then loop, then graph — and move up
  only when topology itself is the contract.
- 2026 systems converge on: explicit state, typed transitions, durable
  checkpoints, interrupt/resume, traceable routing, and a locked evaluator for
  any self-improvement loop.
- The highest-value addition remains a **graph-level policy layer** (budgets,
  effect semantics, reducers, versions) that lives *outside* the kernel.
- What changed: the kernel half of that story is now merged. The policy half is
  not, and its ownership is not yet ratified (see §8, D-LG-1).

---

# 2. The 20 conventions — status against live code

Legend: **Done** exists and is merged in the named repo; **Partial** some of it
exists; **Open** not present; **Out** deliberately outside the kernel.

| # | Convention | Status in live code | Where / note |
|---|---|---|---|
| 1 | Separate definition, execution, evidence | **Partial** | `GraphSpec`/`NodeSpec`/`EdgeSpec` and lint exist in Core; `CompiledGraph` is a detached snapshot; run/trace/checkpoint lineage records do not exist. [V; D 59 §3] |
| 2 | Version the graph schema | **Partial** | `schema_version` and a content-hash `graph_id` exist; no `graph_version`, no state-schema version. [V] |
| 3 | Stable node identity | **Partial** | `NodeSpec.name` plus `implementation_ref`; no implementation-version pin. [V] |
| 4 | Edges as contracts | **Partial** | `EdgeSpec` has `source`, `kind`, `target`, `router_ref`, `declared_targets`; strict route validation and unknown-route rejection at resolution exist. No payload-schema contract per edge. [V; D 59 §8] |
| 5 | Explicit state-merge semantics | **Partial** | Strict dict-delta; `merge()` uses `model_copy(update=deepcopy(delta), deep=True)`. Per-key reducers are roadmap **R3**. [V; D 59 §2] |
| 6 | Fan-out/fan-in join semantics | **Partial** | Parallel plugin exists with ordered last-writer-wins. That is a documented default, not a join contract. Roadmap **R3**. [V] |
| 7 | Retry at the node/effect boundary | **Out / Open** | Engine header states retries remain outside the kernel. [V] |
| 8 | Dedupe / idempotency story | **Open** | Effect identity belongs to **R4**. The outbound ledger in oramasys is the nearest existing mechanism. [V] |
| 9 | Interrupt/resume implies replay | **Partial** | Structural `Interrupt` recognition exists (terminal reason `interrupted`); it is **not** durable resume. Roadmap **R4**. [V; D 59] |
| 10 | Checkpoints are lineage | **Partial** | `SqliteCheckpointer` persists `session_id`, `node`, `state_json` on `node.end`. No parent link, no graph-version stamp. [V] |
| 11 | Run state vs long-term memory | **Done by doctrine** | Memory governance is outside the engine (companion §9). [D] |
| 12 | Explicit termination reasons | **Partial** | Only `done` and `interrupted`, plus `MaxStepsExceeded(steps, last_node)`. No `cancelled`, `budget_exhausted`, `stagnated`, `verifier_failed`. [V] |
| 13 | Observe routing decisions | **Done** | `edge.selected` observation and sanitized `GraphEvent`; `aobserve()` / `asteps()`. [V; D 59 §5] |
| 14 | Trace control metadata; redact payloads independently | **Done (structure)** | Rich `GraphObservation` (trusted, in-process) vs sanitized `GraphEvent`; detached per-listener payloads. Export-side redaction policy is not in Core. [V; D 59 §6] |
| 15 | Deterministic verifier surface | **Partial** | Lint is a static verifier. A graph-level runtime verifier is roadmap **R6**. [V] |
| 16 | Optimize only against multiple objectives | **Open** | Pareto lane is R6/G5; nothing built. |
| 17 | Graph only when topology is the contract | **Done by doctrine** | Ladder in companion §1–§5. [D] |
| 18 | Composition without kernel recursion | **Done** | Subgraphs exist as a plugin, not in the kernel. [V] |
| 19 | Cancellation first-class | **Open** | No cancel terminal reason or propagation contract. |
| 20 | Tiny kernel, evolve at the edges | **Done** | Engine is one private `_run()` scheduler (≈380 lines); header lists what stays outside. [V] |

**Reading the table.** Items 1–6, 9, 10 and 12 are "Partial" because Core ships
the *structural* half. The *policy* half is what the original called P0/P1 and
is what remains.

---

# 3. Security and trust-boundary overlay

This section does **not** add a security design. It records which existing owner
holds each concern, so that research claims are not read as gaps in the wrong
repository. Corrections to my own earlier statements are marked **(corrected)**.

## 3.1 Ownership map

| Concern | Owner | Note |
|---|---|---|
| Endpoint-specific security: SSRF, DNS rebinding, address pinning, redirect handling, TLS, purpose-scoped authorization | **Telos** | **(corrected)** An earlier pass attributed these gaps to Perpetua-Tools. In v2 they belong to Telos. No v2 runtime may import PT endpoint-security code. [D 62; V Telos `docs/BOUNDARIES.md`] |
| Generic admission — may an artifact enter a runnable graph; safety and monitorability | **Phylax** | Admission gate for specs. [D 62; V] |
| Hardware capability, fit, placement | **Agate** | Not a security control. |
| Sandbox ladder | `docs/v2/32` §5 | **(corrected)** Already planned; not a new gap. [D] |
| MCP tool pinning | `docs/v2/32` | **(corrected)** Already planned. [D] |
| Canary / scanner | future AC-SCAN in `docs/v2/31` | **(corrected)** Already planned. [D] |
| Loopback binding for local services | `docs/v2/34` | [D] |
| Single-operator LAN descope | `docs/v2/45` | Narrows the threat model; do not import multi-tenant assumptions. [D] |
| Telemetry spans (OTel `gen_ai`) | `docs/v2/55` | [D] |
| Portable-memory invariant (no private identifiers, credentials, endpoints, or workstation paths in tracked memory) | `docs/v2/47` | [D] |

## 3.2 Implications for graph work

1. **Effect nodes dial out only through a Telos-backed invoker.** A graph node
   must never open its own sockets. The outbound ledger in oramasys records
   effects; Telos decides whether an endpoint may be contacted. [P — consistent
   with 62]
2. **Admission before execution.** A `GraphSpec` that fails lint or Phylax
   admission must not be realized into a `MiniGraph`. Fail-closed, as in doc 59 §9. [D]
3. **Observer isolation is a security property.** The rich `GraphObservation`
   is trusted in-process evidence only; it may carry state and deltas. Anything
   crossing a process, file or network boundary uses the sanitized projection or
   an explicit redaction step. Frozen top-level fields do **not** deep-freeze
   contents; immutability of observations is a discipline for observer authors
   unless a deep-frozen variant is added. [D 59 §1]
4. **Tracked artifacts name categories, never values.** This document and its
   companion contain no workstation paths, addresses, identities or credentials,
   per `docs/v2/47`. Exact values live in an off-repo, local-only registry
   loaded at runtime. [D 47]

## 3.3 External security claims — status

| Claim family (from pasted external reports) | Status |
|---|---|
| SSRF defense-in-depth layering | Directionally standard; concrete implementation is a **Telos** matter. [X] |
| Specific Ollama CVE identifiers and fixed-version numbers | **Unverified here.** Do not cite versions from this file; check the vendor advisory at the time of use. [X] |
| MAESTRO / OWASP agentic mappings | Useful as a *checklist vocabulary*; not adopted as a normative control set. [X] |
| AIVSS scoring | Pre-1.0 as reported; **deferred**. [X] |
| gstack / GBrain / Hermes harness claims | Context only; do not treat as verified behaviour. [X] |

---

# 4. LangGraph compatibility boundary

Research input (a pasted LangGraph v1.x report, unverified by me [X]) lists the
surface a compatibility layer would have to honour: `StateGraph`,
`add_conditional_edges`, `Command`, `Send`, `interrupt()` (which requires a
checkpointer), `StateSnapshot`, and `astream_events` v2. The hard-fidelity areas
are streaming event schemas, checkpoint serialization, and superstep semantics.

Position, consistent with the kernel invariants:

1. **Compatibility stays outside the kernel.** [D 57]
2. **What exists today [V, corrected in this pass]:** Core ships two adapters
   with *different* strengths. `LangChainRunnableAdapter` is a duck-typed
   Runnable-shape wrapper (`invoke`/`batch`/`stream` and async twins, plus `|`
   chaining) that runs the real MiniGraph and imports nothing from LangChain;
   `LangGraphExporter.to_langgraph()` builds a compiled LangGraph from the
   graph's nodes and edges (requires `langgraph` in the caller's environment) —
   execution then follows LangGraph's semantics, not MiniGraph's. An earlier
   draft of this file called both "topology-only"; that was wrong for the
   LangChain adapter.
3. **What cannot be claimed yet:** no inbound direction (LangGraph graph →
   MiniGraph), no `Command`/`Send` (depends on R3), no `interrupt()`/resume
   parity (R4), no `StateSnapshot` parity (checkpoint lineage, convention 10),
   no `astream_events` v2 schema. Until verified by a conformance suite, say
   "Runnable-shape interop plus LangGraph export", not "drop-in compatible".
4. **Conformance approach [P]:** a small suite of golden graphs run through both
   engines, comparing final state and the *ordered sequence of routing
   decisions*, not raw event payloads. Planned in `docs/v2`; built in
   `oramasys/oramasys` as a test harness that imports `langgraph` as an optional
   dev dependency, never as a Core dependency.

---

# 5. X / Twitter signal — condensed, low confidence

The original catalogued ten "signals" (A–J) with engagement figures. Those
figures cannot be verified from here and are dropped. The *qualitative* themes
that survive because independent technical sources also support them:

- Long-running harnesses need explicit context checks, decomposition, and
  blast-radius review. (Matches the PT `.agent` loop contract.)
- Delete scaffolding that newer models no longer need. (Applies to loops too.)
- A **locked evaluator** is the heart of any autonomous optimization loop.
- Runtime traces are the raw material for later improvement.
- Parallel specialists are common; more agents is not a better graph.
- Observability and cost visibility drive production value.
- Agent-native interfaces favour CLI/MCP and machine-readable docs.

The "loops → graphs" trend note stays **low confidence**: it is a sentiment, not
a measurement. Do not use social virality as technical proof.

---

# 6. Re-prioritised adoption plan with owners

"Plan" means planned in orama-system `docs/v2`. "Build" means code in
`oramasys/oramasys` unless noted. Phase names follow the original G0–G6.

## P0 — invariants to enforce now

| Item | Plan | Build | Maps to |
|---|---|---|---|
| Cycle bound on every loop and graph (max steps, runtime, output, stagnation) | existing loop contract; bridge proposal in companion §4.10 | oramasys policy layer; Core keeps `MaxStepsExceeded` | G0, convention 12 |
| Template / run / trace separated as records | `docs/v2` ADR | oramasys | G0–G1 |
| Mutator and evaluator are separate authorities | `docs/v2` | oramasys | R6 |
| Fail-closed admission (lint + Phylax) before realization | doc 59 §9, 62 | oramasys wiring to Phylax | G1 |
| Effect nodes dial only via Telos-backed invoker | doc 62 | oramasys | G4 |

## P1 — design next, do not rush into the kernel

| Item | Plan | Build | Maps to |
|---|---|---|---|
| Reducers and join semantics | `docs/v2` (R3) | Core may take a minimal reducer hook only if ADR approves; policy in oramasys | R3 / G3 |
| Durable deterministic resume with effect identity | `docs/v2` (R4) | oramasys over Core checkpointer | R4 / G2, G4 |
| Checkpoint lineage (parent link, graph-version stamp) | `docs/v2` | oramasys record types | G2 |
| Extended terminal reasons (`cancelled`, `budget_exhausted`, `stagnated`, `verifier_failed`) | `docs/v2` | oramasys wrapper around Core's `done`/`interrupted` | G1 |
| Versioned GraphSpec with policy block | `docs/v2` (R5), **needs D-LG-1** | oramasys | R5 |
| Cancellation contract | `docs/v2` | oramasys | G4 |

## P2 — research lane

| Item | Plan | Build | Maps to |
|---|---|---|---|
| Offline graph optimizer, Pareto objectives | `docs/v2` | oramasys, offline only | R6 / G5 |
| Dynamic graph compiler (compile, not improvise) | `docs/v2` | oramasys, after G5 | G6 |
| LangGraph conformance harness | `docs/v2` | oramasys tests | §4 |

---

# 7. GraphSpec policy layer — sketch aligned to Core's real fields

Core's structural fields are the ground truth. The `policy` block below is a
**proposal [P]** for the oramasys layer; it is *not* part of Core's
`GraphSpec` and must not be added there unless D-LG-1 is ratified.

```yaml
# Structural part — mirrors perpetua-core GraphSpec [V]
schema_version: "1"          # str in Core; currently only "1" is supported [V]
nodes:
  - name: plan
    implementation_ref: "pkg.module:plan_node"
    metadata: {}
  - name: act
    implementation_ref: "pkg.module:act_node"
    metadata: {}
edges:
  - source: plan
    kind: static            # EdgeKind = "static" | "conditional" [V]
    target: act
    metadata: {}
  - source: act
    kind: conditional
    router_ref: "pkg.module:route_after_act"
    declared_targets: [plan, END]
    metadata: {}

# Policy part — PROPOSED, lives in oramasys [P]
policy:
  graph_version: "1.0.0"            # human-assigned; graph_id stays the content hash
  state_schema_version: 1
  bounds:
    max_steps: 25
    max_runtime_seconds: 3600
    max_output_chars: 200000
    stagnation_threshold: 2         # values mirror PT .agent/loops/budget.json [V]
  reducers:                         # R3
    scratchpad: last_writer_wins
    findings: append_unique
  joins:                            # R3
    - fan_in: [worker_a, worker_b]
      into: merge_findings
      on_partial_failure: fail_closed
  effects:                          # R4
    - node: act
      kind: external_write
      # effect identity = (durable run/thread id, logical_operation_id) + effect kind + request digest;
      # attempt_id is recorded per try but is NEVER part of the key (corrected 2026-10-09)
      operation_identity: [run_id, logical_operation_id]
      bind: [effect_kind, request_digest]   # changed request under same identity -> fail closed
      on_unknown_outcome: reconcile_with_provider   # a local "recorded" flag is not proof
      requires_approval: true
      egress: telos_invoker_only
  termination_reasons: [done, interrupted, cancelled, budget_exhausted, stagnated, verifier_failed]
  evaluation:                       # R6
    evaluator_ref: "pkg.module:locked_eval"
    locked: true
    objectives: [correctness, cost, latency]
  admission:
    lint: required
    phylax: required
```

Note: `schema_version` is a string and `EdgeKind` is `"static" | "conditional"` in Core `spec.py`. Every key under `policy` is [P].

---

# 8. Open boundary decision

**D-LG-1 [P] — unratified.** Doc 57 §12 and doc 59 §7 say orama-system owns
"GraphSpec policy, lint, evaluation", while Core already ships structural
spec and lint. Proposed resolution: **Core keeps the structural spec and lint**
(it needs them to remain self-verifying and dependency-minimal); the
**policy-bearing layer** — budgets, effect/replay, reducer/join, versions,
evaluation — is **planned in `docs/v2` and built in `oramasys/oramasys`**.
This requires an ADR amending doc 57 §12. Until ratified, treat §7's `policy`
block as a sketch only.

---

# 9. What not to adopt

1. Do not replace MiniGraph with a large framework reflexively.
2. Do not add every production feature to `engine.py`; the header's exclusion
   list (persistence, retries, reducers, provider policy, telemetry export,
   optimization) is deliberate. [V]
3. Do not equate more agents with a better graph.
4. Do not allow evaluator drift inside optimization loops.
5. Do not use social virality as technical proof.
6. Do not import PT endpoint-security code into any v2 runtime. [D 62]
7. Do not claim "LangChain/LangGraph drop-in compatible" while only a Runnable-shape adapter and an outbound LangGraph exporter exist.

---

# 10. Confidence matrix

| Claim | Confidence | Verified in repo? |
|---|---|---|
| Ladder / least-powerful structure | High | Doctrine [D] |
| Kernel is one scheduler with two projections | High | Yes [V] |
| Merge isolation (`deepcopy` + `deep=True`) | High | Yes [V] |
| Structural GraphSpec and lint exist in Core | High | Yes [V] |
| Reducers / joins / durable resume are open | High | Yes — absent [V] |
| Terminal reasons limited to `done`/`interrupted` | High | Yes [V] |
| Telos owns endpoint security | High | Yes [V, D 62] |
| LangChain adapter is Runnable-shape and runs MiniGraph; LangGraph adapter is outbound export only | High | Yes [V] |
| LangGraph v1.x API surface list | Medium | No [X] |
| Ollama CVE specifics | Low | No [X] |
| AIVSS maturity | Low | No [X] |
| X engagement figures and trend | Low | No [X] |

**Not done in this revision:** no tests were executed; open-PR state was
API-confirmed only for `perpetua-core` (others inferred from pull refs).

---

# 11. Suggested research tests (carried forward, owner-tagged)

- **Structural (Core):** lint rejects unreachable nodes, undeclared route
  targets, duplicate names; unknown routes raise at resolution. Mostly present. [V]
- **State (Core):** the four merge-isolation cases in doc 59 §2. Present. [D]
- **Observer (Core):** multicast integrity, filtering, sync/async settlement,
  payload isolation, observer transparency. Present per doc 59 §6. [D]
- **Durability (oramasys, R4):** kill-and-resume yields the same final state;
  an effect recorded before the kill is not repeated.
- **Human-in-the-loop (oramasys, R4):** `interrupted` → approve → resume continues
  from the right node with state intact.
- **Joins (oramasys, R3):** result is independent of branch completion order.
- **Optimization (oramasys, R6):** evaluator is read-only to the mutator;
  a candidate graph that fails lint is never scored.
- **Conformance (oramasys, §4):** golden graphs, compare routing sequences.

---

# 12. Sources

Internal (read in this pass):

- orama-system `docs/v2`: 31, 32, 34, 39, 45, 47, 54, 55, 57, 58, 59, 62, 69, and the migration-plan notes.
- perpetua-core: `src/perpetua_core/graph/engine.py`, `spec.py`, `lint.py`, `plugins/parallel.py`, `plugins/checkpointer.py`, `graph/adapters/langgraph_adapter.py`, `docs/POST_MERGE_CONVERGENCE_2026-08-29.md`.
- oramasys: graph module, `providers/outbound_ledger.py`, architecture docs.
- Telos `docs/BOUNDARIES.md`; Phylax README.
- Perpetua-Tools `.agent` loops, migration-debt status, and the Telos tripwire note.

External (carried from the original; not re-verified in this revision):
LangGraph, Temporal, Microsoft Agent Framework, OpenAI Agents SDK, Google ADK,
Apache Beam/Pregel documentation; AFlow, AutoFlow, A²Flow and the 2026
workflow-optimization survey. See the 2026-08-26 original §15 for the full list.
