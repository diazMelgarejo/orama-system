---
title: "Prompt → Loop → Graph Engineering + perpetua-core MiniGraph Invariants (Revision 2)"
date: 2026-10-09
status: "Revision 2 — source-grounded recall; supersedes the 2026-08-26 memory recall. Planning authority remains orama-system docs/v2."
revision_of: "PT-ORAMASYS-PROMPT-LOOP-GRAPH-MINIGRAPH-MEMORY-2026-08-26.md"
companion: "PT-ORAMASYS-GRAPH-ENGINEERING-STATE-OF-THE-ART-RESEARCH-2026-10-09-rev2.md"
scope:
  - "ORAMASYS prompt / chain / loop / graph doctrine"
  - "PT .agent bounded-loop contract"
  - "perpetua-core MiniGraph kernel invariants as merged"
  - "repository ownership boundary for planned graph work"
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

# Prompt → Loop → Graph Engineering — Revision 2

Portable context for a fresh agent before prompt, workflow, or graph design.
It records doctrine, the verified state of the kernel, and **where planned work
belongs**.

> **Evidence labels used throughout**
>
> - **[V]** verified by reading the current default branch of the named repository on 2026-10-09 (presence of the file, symbol, or field — tests were *not* executed here);
> - **[D]** stated by a canonical orama-system `docs/v2` record (cited by number);
> - **[P]** proposal in this document — not a contract until ratified in `docs/v2`;
> - **[X]** external research claim, not independently verified here.

---

# 0. Provenance and what changed in Revision 2

## 0.1 Where the 2026-08-26 originals came from

- The 2026-08-26 memory recall (this file's predecessor) and its research companion were **inputs** to a MiniGraph reconciliation run on 2026-08-26. The reconciliation plan lists both by name as `inputs:` alongside a standalone third-party 99-line engine rewrite, with `perpetua-core` as the target. [V — plan text in the reconciliation bundle]
- The research companion is, apart from line wrapping, the same document as artifact `003-STATE-OF-THE-ART-RESEARCH-2026-08-26.md` in that bundle. [V — diffed]
- The recall's own front matter pins its PT source to commit `17af5f7`, the merge of PT PR #372 on 2026-08-25. [V — commit resolved]
- Section 8.13 of the original contained a pasted question ("Which is better? … can we combine the best of both worlds?"). That is a chat artifact, not doctrine. It is answered in §8.13 below.

## 0.2 What those inputs became

The reconciliation was ratified as orama-system `docs/v2/57` (2026-08-27) and
refined by `58` and `59` (2026-08-28/29). It merged into `perpetua-core` as
`d1c0dfc` (Core PR #1). [D 57, 59] The corrective branch described in 57/59 as
"unmerged" has since landed — the regression file
`src/tests/graph/test_post_merge_convergence.py` exists on Core `main`. [V]

**Therefore this Revision 2 is not a new design.** It re-baselines the original
recall to the merged reality and adds the repository boundary rules and the
gap register in §16.

## 0.3 Change summary

| Area | 2026-08-26 text | Revision 2 |
| --- | --- | --- |
| Kernel surface | "Compiled surface: `ainvoke` only" | `ainvoke`, `aobserve`, `asteps`, `describe`, `validate`, `compile_validated` [V] |
| Scheduler | loop inside `ainvoke` | one private `_run()`; all views project from it [V, D 57] |
| Node result | falsey results tolerated | dict delta required [D 57] |
| Routing | unknown route → later `KeyError` | rejected at resolution [D 57, V test file present] |
| `GraphSpec` | "future" | structural `GraphSpec`/`NodeSpec`/`EdgeSpec` + lint **already in Core** [V] — ownership question open (§7.3) |
| Compile-freeze question (§8.13) | left open | resolved (§8.13) |
| Loop → graph bridge | missing | added (§4.10) [P] |
| Repository boundary | implicit | explicit rules BR-1…BR-6 (§7) |
| Front matter | invalid YAML (`scope:&`) | fixed |

---

# 1. The core engineering law

Use the **least powerful control structure that makes the contract explicit.**

```text
PROMPT  -> specify one inference
CHAIN   -> specify a pipeline
LOOP    -> specify bounded repetition
GRAPH   -> specify a state machine
```

Promote only when the **control semantics** require it, not because a task
"feels complex". [D 57 §1]

Foundation (the Amplifier Principle): intelligence amplifies whatever direction
is already encoded in the system, so the developer's centre of gravity moves
from syntax to specification, from writing to auditing, from implementation to
integration. Prompt quality is an engineering artifact: version it, constrain
it, audit it, define success and failure before execution, and graduate repeated
structure into reusable capability.

---

# 2. Prompt invariants

A prompt is the right abstraction for a **one-shot** task: one bounded objective,
one context, no durable retry state, no conditional topology.

Every engineered prompt makes four things explicit:

1. **Role / context** — whose perspective and what operating context.
2. **Goal / task** — one objective with a testable success condition.
3. **Constraints** — security policy, allowed/denied files, budget, compatibility, side-effect permissions, what must not change.
4. **Output contract** — the exact surface (sections, JSON schema, table, patch plan). If another stage consumes it, prefer a schema over prose.

Rules: define success and failure first; replace vague verbs with measurable
outcomes; one primary goal per prompt; state assumptions; label uncertainty
instead of inventing facts; debug as SYMPTOM → SUSPECT → FIX ONE THING → TEST →
RECORD LEARNING; never grow a prompt to emulate program control flow.

**Graduate out of a single prompt** when any of these becomes stable and
recurrent: fixed specialist stages, deterministic handoff schemas, repeated
critique/revision, checkpointing, retry policy, budget/stagnation stop rules,
external-write approval gates, conditional routing, interrupt/resume, or
parallel/subgraph behaviour.

---

# 3. Chains

A chain is a named, substantially acyclic pipeline whose stages have stable
input/output contracts that can be validated at the boundary.

**Invariant:** never use hidden conversational memory as the interface between
stages. Pass explicit, validated artifacts.

If a chain begins revisiting stages, needs attempt counters, must "try again but
differently", or must stop on stagnation, it has become a **loop**.

---

# 4. Loop engineering — the PT `.agent` contract

A loop is a **bounded, stateful control contract**, not "keep prompting until it
works". The values below were checked against PT `.agent/loops/` on 2026-10-09.

## 4.1 Explicit, resumable state [V]

Each loop names a state file (for `ci-sweeper`: under `.agent/runtime/loops/`).
It must be resumable from an observable checkpoint, never from hidden model
context.

## 4.2 Read contract and checkpoint before spending an attempt

The skills `loop-guard`, `loop-verifier`, `loop-constraints` (and `loop-triage`)
exist under `.agent/skills/`. [V]

```text
READ CONTRACT -> READ CHECKPOINT -> IS ANOTHER ATTEMPT LEGAL/USEFUL? -> ACT
```

## 4.3 Every loop is bounded [V]

`.agent/loops/budget.json` (schema_version 1):

```json
{ "max_attempts": 3, "max_runtime_seconds": 3600, "max_output_chars": 200000,
  "estimated_token_budget": 200000, "stagnation_threshold": 2 }
```

The numbers are configuration. The invariant is **finite bounds on attempts,
wall time, output, tokens, and stagnation**. No infinite autonomous retry.

## 4.4 Stagnation is a stop condition

Do not replay a failed approach. A retry must carry new deterministic evidence
and a materially changed strategy; otherwise stop and preserve the checkpoint.

## 4.5 Constraints fail closed

`.agent/loops/constraints.json` defines deny paths, allow paths, a changed-file
cap, and external-write approval. [V] A loop cannot reason its way around its
constraints; these are hard gates, not advisory prompt text.

## 4.6 Maker and checker are separate roles [V]

`ci-sweeper.json` declares `executor = maker`, `checker = checker`.
The deterministic verifier is authoritative: model approval is not a test pass,
and reviewer approval is not a passing acceptance command.

## 4.7 Isolate mutating loops [V]

`ci-sweeper.json`: `isolation.mode = worktree`, `base = HEAD`.

## 4.8 External writes need a separate gate [V]

`ci-sweeper.json`: `approval.before_first_mutating_run = true`,
`approval.before_external_write = true`.

## 4.9 Stop is a valid state

Pause, budget exhaustion, stagnation, and cancellation stop the loop **while
preserving the checkpoint**. A stop is a transition, not an exception to
"success".

## 4.10 Loop → graph bridge [P]

The original recall said to promote a loop to a graph but gave no mechanism for
carrying loop controls across. Only `retry_count` exists on `PerpetuaState`. [V]
The proposal below keeps the kernel unchanged.

| Loop control | Where it lives in a graph |
| --- | --- |
| attempt counter, stagnation fingerprint | fields in the state delta (`scratchpad`), written by the node that attempts |
| `max_attempts`, stagnation threshold | **edge predicates** reading that state (the retry edge is conditional) |
| `max_runtime_seconds`, token/output budget | **runtime policy** wrapped around `ainvoke`/`aobserve`; not a kernel feature |
| maker / checker | two nodes; the checker node runs the deterministic verifier command |
| constraints | a **pre-flight admission step** (Phylax-class), not prompt text |
| external-write approval | an *effect node* that interrupts for approval and declares replay/idempotency policy (companion §4) |
| checkpoint on stop | observer plugin persisting every `node.end`; lineage per companion §4 |

Terminal reasons must widen beyond the kernel's `done | interrupted` [V]:
`completed, interrupted, failed, cancelled, max_steps, budget_exhausted,
stagnated, policy_denied, timed_out`. That taxonomy belongs to the runtime
wrapper, not `engine.py`.

---

# 5. When a loop should graduate to a graph

Promote when **workflow topology becomes part of the domain**: more than one
named state; conditional routing on typed state; legitimate business/control
cycles; multiple exits; interrupt/resume states; branch-specific validation;
parallel paths; nested composition; traversal provenance that matters; a
topology that is more truthful drawn than described.

```text
NOT A GRAPH YET:   diagnose -> fix -> test --(retry)--> fix      (one bounded loop)

A GRAPH:           classify -> { security -> human_gate, code -> implement -> test,
                                 docs -> edit -> lint } -> finalize -> END
```

**Promotion rule:** if control flow must be explained with named states and
arrows to stay correct, encode those states and arrows as data/code, not prose.

---

# 6. Graph invariants (design-level)

- Typed state is the source of truth. Nodes receive state and return **dict deltas**. Edges inspect state and choose topology.
- Control never depends on hidden chat history.
- Cycles are legitimate but always bounded by a step cap.
- `START`/`END` are explicit sentinels; `END` is the only normal terminal route. [D 57 §5]
- The kernel owns universal mechanics only; everything else orbits it.

---

# 7. Repository boundary rules (operator instruction, 2026-10-09)

> **BR-1** `diazMelgarejo/orama-system` `docs/v2/` is the **planning and
> documentation authority** (specs, ADRs, doctrine, numbered records).
>
> **BR-2** `oramasys/oramasys` is the **intended target of planned application
> code**, unless a document says otherwise.
>
> **BR-3** `oramasys/perpetua-core` owns **dependency-minimal execution
> mechanics** and tested field-level kernel behaviour. It never imports upward.
>
> **BR-4** Specialist authorities keep their lanes: **Telos** — all endpoint-specific security; **Agate** — hardware capability, fit and placement; **Phylax** — generic admission, safety and monitorability; **provider owners** — provider protocol and lifecycle. [D 62; V Telos/Phylax READMEs]
>
> **BR-5** **Perpetua-Tools** is v1 evidence and learning authority. No v2 runtime imports PT endpoint-security code. [V Telos `docs/BOUNDARIES.md`; D 62]
>
> **BR-6** Executable behaviour in tested Core source outranks long code samples in prose. If they differ, repair the prose. [D 59 §7]

## 7.1 Ownership map

| Concern | Planning record (BR-1) | Code target (BR-2/3) | Current state |
| --- | --- | --- | --- |
| Scheduler, state merge, observation seam, structural interrupt | docs 01, 57, 58, 59 | `perpetua-core` | merged [V] |
| Structural `GraphSpec`/`NodeSpec`/`EdgeSpec`, `graph_id`, structural lint | docs 57 §12–13 | `perpetua-core` today | present in Core [V: `graph/spec.py`, `graph/lint.py`, `compile_validated`] |
| Policy-bearing spec: budgets, effect/replay policy, reducer/join declarations, versions, evaluation | docs 57 §12–14, plan 2026-08-29 R5/R6 | **`oramasys/oramasys`** [P, per BR-2] | not implemented — migration plan notes no executable successor [D] |
| Reducers and joins (R3) | docs 57 §10, plan §4 | Core mechanics only if a kernel seam is needed; policy in `oramasys` | open [V: parallel is ordered last-writer-wins] |
| Durable checkpoint lineage, deterministic resume, effect identity (R4) | docs 57 §11, plan §5 | checkpointer plugin (Core) + effect policy (`oramasys`) | open [V: `SqliteCheckpointer` stores session, node, state JSON only] |
| Route → dispatch → respond application graph | doc 16 | `oramasys/oramasys` `src/orama/graph/` | present [V: `perpetua_graph.py`] |
| Provider dispatch audit | docs 54, 55 | `oramasys/oramasys` `src/orama/providers/` | in-memory ledger default; JSONL ledger not wired [V] |
| Endpoint security for any network use by a node | doc 62 | `oramasys/telos` | implemented modules present [V] |
| Hardware placement | docs 07, 42 | `oramasys/agate` | route node already delegates to Agate [V] |
| Generic admission of graph artifacts | doc 60 | `oramasys/phylax` | owner defined; graph-artifact admission wiring not verified |
| Claim / lease / recovery controller | doc 68 | `oramasys/oramasys` `src/orama/orchestrator_controller/` | "no runtime code yet" [V] |

## 7.2 Pipeline implied by the boundaries [P]

```text
author intent
  -> GraphSpec (versioned value; planned in docs/v2, policy code in oramasys)
  -> structural lint            (Core: GraphSpec validation)
  -> policy lint                (oramasys: budgets, effects, joins, versions)
  -> admission                  (Phylax: artifact/capability)
  -> placement / eligibility    (Agate)
  -> realize into MiniGraph     (Core builder)
  -> execute via CompiledGraph  (Core)
  -> every network touch        (Telos dialer, never raw)
```

## 7.3 Open ownership conflict — needs an explicit record [P]

- docs 57 §12 and the 2026-09 migration plans say `GraphSpec`/lint/evaluation sit **above Core** (`orama-system` authority) and that moving ownership to `oramasys/oramasys` "requires a new explicit architecture decision". [D]
- Live Core already ships a **structural** `GraphSpec` and lint, added by Core PR #4 and pinned by oramasys PR #11. [V; D via PT status 2026-09-12]
- The operator instruction in BR-2 names `oramasys/oramasys` as the code target.

**Proposed resolution (D-LG-1, for ratification as a docs/v2 ADR):** Core keeps
the *structural* spec and structural lint (no policy, no execution). Everything
policy-bearing — budgets, effect/replay policy, reducer/join declarations,
graph/state/node-contract versions, locked evaluation, optimizer — is planned in
`docs/v2` and implemented in `oramasys/oramasys`. Doc 57 §12 should be amended
to say so. Until ratified, treat this as **proposed**, not decided.

---

# 8. MiniGraph — kernel invariants as merged

Sources: Core `src/perpetua_core/graph/engine.py` [V]; docs 57, 59 [D].

## 8.1 Purpose
A small, pure, irreducible state-machine kernel. Physical line count is a review
signal only (the file is now ~379 lines; the old ≤80 target is superseded). [V, D 57]

## 8.2 Import boundary
`engine.py` imports no plugins, providers, storage, network, telemetry
exporters, or upper-layer policy. Architecture tests enforce it; do not add
`try: import plugin` fallbacks.

## 8.3 State
`PerpetuaState` is a Pydantic v2 `BaseModel`; `scratchpad: dict[str, Any]`;
`nodes_visited: list[str]`. `merge()` applies **two** independent copy layers —
`model_copy(update=deepcopy(delta), deep=True)` — isolating the prior
generation, the caller's delta, and the new generation. [D 59 §2]
Graph-run state is neither PT long-term memory nor a durable checkpoint.

## 8.4 Sentinels and nodes
`START = "__start__"`, `END = "__end__"`. A node is `PerpetuaState -> dict`
(sync, async, async callable object such as `ToolNode`, or sync returning an
awaitable). The scheduler **invokes first, then inspects the returned object**
with `inspect.isawaitable`. A `None` or non-dict result is a contract error.

## 8.5 Edges
An edge is a static string or a synchronous `state -> str`. Every route must
resolve to a non-empty string that is `END` or a registered node; invalid routes
fail closed at resolution. Core also has a `ConditionalEdge` carrier used for
declared targets in descriptions. [V]

## 8.6 Execution order (invariant)

```text
enter node -> record visit -> execute -> await if needed -> validate dict
-> merge delta -> evaluate outgoing edge against the UPDATED state
```

## 8.7 Cycle bound
`max_steps` (default 200). `MaxStepsExceeded(steps, last_node)`:
`steps` = completed node executions, `last_node` = most recently entered node,
and with a zero budget the diagnostic is `steps=0`, `last_node=START`. [D 57 §6]

## 8.8 One scheduler, two projections [D 57 §8, 59 §5; V]

```text
CompiledGraph._run()  (sole scheduler)
   -> GraphObservation(event, state, delta?)   rich, trusted, in-process  -> aobserve()
   -> GraphEvent                               sanitized control data    -> asteps()
ainvoke() drains _run()
```

Event kinds: `edge.selected, node.start, node.end, interrupt, done`.
`GraphEvent` carries kind, node/target, completed-step count, terminal reason
only — **no** prompts, state, deltas, handles, provider policy, or exporter
config. Streaming and plugins must never re-implement traversal or touch
private `_nodes`/`_edges`.

## 8.9 Plugin observation
Canonical callback: `on_observation(observation)` — offered every kind, awaited
when awaitable, delivered in registration order, **fail-closed**, each listener
receiving a detached payload. A plugin filters to what it needs (the
checkpointer persists `node.end`). A bare async generator is single-consumer;
multi-observer runs use one `aobserve()` drain plus fan-out. [D 59 §6]

## 8.10 Interrupt boundary
The kernel recognises an exception structurally: type name `Interrupt` with a
`prompt` attribute; `payload` optional via `getattr(..., None)`. State becomes
`interrupted` with `metadata.interrupt_prompt / _payload / _node`. All other
exceptions propagate. The old no-op `interrupt_handler` argument was removed.
**This is not durable resume.** [D 57 §7]

## 8.11 Terminal reasons
The kernel's `terminal_reason` is `done | interrupted`. [V] Richer reasons are a
wrapper concern (§4.10).

## 8.12 Description and validation
`MiniGraph`/`CompiledGraph` expose `describe() -> GraphSpec` and `validate()`;
`compile_validated()` compiles only after structural validation. Description is
declarative and "never becomes a second scheduler". [V engine header]

## 8.13 Compile freeze — resolved (was an open question in the original)
- **Builder** (`MiniGraph`): intentionally mutable workspace; `add_node`/`add_edge` return `self`, matching the LangGraph-style builder contract. Making them persistent-value operations would silently break bare builder calls. [D 59 §3]
- **`compile()`** is the immutability boundary. Later builder mutations must not alter an existing `CompiledGraph`. [V: `test_engine_compile.py`, `test_builder_contract.py`]
- **Persistent structural sharing** is kept — for the future versioned `GraphSpec` value, which is where diffing/identity/promotion benefit from it. [D 59 §4]
- Governing policy: immutability is a **boundary property** (values and published snapshots immutable; builders and buffers may mutate if documented and non-leaking). [D 59 §1]
- Known limit: `GraphObservation` is frozen only at the top level; listener isolation relies on per-listener detached payloads, not deep freezing. [D 59 §1]

## 8.14 Builder and runtime surfaces
Builder: `add_node, add_edge, set_entry, compile, compile_validated, describe,
validate, ainvoke, nodes, edges`. Compiled: `ainvoke, aobserve, asteps,
describe, validate, nodes, edges` (read-only mappings). [V]

---

# 9. What must stay out of `engine.py`

Checkpoint persistence and durable resume; plugin-specific resume guards;
routing helpers; tools / `ToolNode`; subgraphs; streaming adapters; structured
output; parallel dispatch and merge reducers; retries and backoff; cost
accounting; provider/model clients; storage and network I/O; discovery; UI and
FastAPI; telemetry exporters; graph optimisation. [D 57 §9; V engine header]

Existing plugin tree (keep the namespace; do **not** create a parallel one):
`checkpointer, interrupt_guard, interrupts, observer, parallel, routing,
streaming, structured_output, subgraphs, tool, tool_node, validator`. [V]
Core also ships LangChain/LangGraph edge adapters under `graph/adapters/`;
the LangGraph one is an **outbound exporter** (builds a compiled LangGraph;
explicitly not scheduler parity), and the LangChain one is a duck-typed
Runnable-shape wrapper that runs the real MiniGraph. [V]

---

# 10. Original design targets vs accepted state

| Topic | Original salvage target | Accepted / merged state | Rule |
| --- | --- | --- | --- |
| Engine size | ≤80 lines | ~379 lines | small/pure/irreducible is the invariant; line count is a signal |
| Compile freeze | builder frozen after compile | builder mutable; compiled snapshot detached | current semantics canonical |
| Interrupts | all plugin-side | minimal structural interception in kernel | keep minimal, plugin-free |
| Edge model | generic Edge classes rejected | string or routing callable (+ declared-target carrier for description) | keep minimal |
| State | Pydantic `BaseModel` | confirmed | hard invariant |
| Plugin namespace | — | `perpetua_core/graph/plugins/` only | hard invariant |
| Python | 3.11+ | confirmed | hard invariant |
| Third-party standalone engine | proposed replacement | **rejected**; adopted improvements by invariant (returned-awaitable, single scheduler, strict delta/route, safe interrupt payload) | do not re-litigate [D 57] |

---

# 11. Graph testing invariants

Test files present on Core `main` [V — presence, not execution]:

- kernel: `test_engine_reconciliation.py`, `test_engine_compile.py`, `test_engine_max_steps.py`, `test_builder_contract.py`, `test_post_merge_convergence.py`, `test_minigraph.py`, `test_state_isolation.py`;
- structure: `test_graph_spec.py`, `test_graph_lint.py`, `test_graph_spec_engine_bridge.py`;
- property: `property/test_engine_invariants.py`;
- plugins: observer, parallel, routing, streaming, validator, tool_node, interrupt_guard, checkpointer, interrupts.

Boundary tests are architecture tests, not style tests: the engine imports no
plugins or optional dependencies; Core imports no Telos names. Integration tests
for plugins belong with the plugins and build small real graphs. Do not claim a
historical test still exists without checking.

---

# 12. Decision matrix

| Signal | Prompt | Chain | Loop | Graph |
| --- | :-: | :-: | :-: | :-: |
| One bounded objective | ✅ | | | |
| Fixed multi-stage sequence | | ✅ | | |
| Retry needed | | | ✅ | ✅ |
| Attempt / time / token budget | | | ✅ | ✅ |
| Persistent checkpoint | | | ✅ | ✅ |
| Stagnation detection | | | ✅ | ✅ |
| Independent checker | opt | opt | ✅ | ✅ |
| Conditional routing | | maybe | maybe | ✅ |
| Multiple named states / exits | | | maybe | ✅ |
| Interrupt / resume | | | maybe | ✅ |
| Parallel / subgraph | | | | ✅ |
| Traversal provenance matters | | | maybe | ✅ |

---

# 13. Promotion ladder

1. Start with a specified prompt (role, goal, constraints, output contract; success/failure defined).
2. Stable stages → chain with typed handoffs.
3. Repeating stage → bounded, checkpointed loop; maker ≠ deterministic verifier; constraints and external-write approval fail closed.
4. Topology becomes domain logic → typed graph (named nodes, static/conditional edges, START/END, bounded cycles, provenance, interrupt states).
5. Keep the engine a micro-kernel; plugins and upper layers carry storage, providers, tools, parallelism, checkpointing, streaming, structured output.
6. Compile a narrow runtime surface; builders construct, runtimes execute.
7. Test architecture as an invariant (import boundaries, cycle bounds).
8. Plan in `docs/v2`; build application code in `oramasys/oramasys`; leave endpoint security to Telos, placement to Agate, admission to Phylax.

---

# 14. Anti-patterns

**Prompt:** one giant prompt as a hidden program; conflicting goals; "keep trying until it works"; policy enforced by prose; inter-stage state in chat history.
**Loop:** infinite retry; no checkpoint; same approach after identical feedback; model self-approval as test success; remote mutation without an approval boundary; constraints only in prose.
**Graph:** a graph for a linear task; nodes that secretly own topology; provider/storage imports in the kernel; abstractions that obscure `state → delta`; conditional edges reading pre-node state; cycles without a step cap; plugin features absorbed into `engine.py`; reverse imports from Core into higher layers.
**Boundary (new):** a node dialing the network directly instead of through Telos; re-implementing SSRF/DNS/redirect logic outside Telos; importing PT endpoint-security code into a v2 runtime; putting planning prose in a code repo or application code in `docs/v2`; hard-coding concrete local identity, address, device, or path fragments in tracked policy (doc 47 — categories only, values in a local-only registry).

---

# 15. Security and trust boundaries touching this design

Full overlay is in the companion §2. The graph-relevant rules:

1. **Endpoint security is Telos's alone.** A node that reaches any endpoint does so through a Telos-backed provider invoker. The reference graph already says "no production network client belongs in this module". [V `perpetua_graph.py`]
2. **Specs carry no code.** `GraphSpec` serialises topology and stable provenance only; node/router code is never serialised or executed by the spec module. [V `spec.py` header]
3. **Natural language is never runtime authority.** It compiles to a typed, validated spec first. [D 57 §13]
4. **Fail closed.** Authoritative observer delivery, route resolution, spec validation, and admission all deny on ambiguity. [D 57, 59]
5. **Control telemetry may leave; content telemetry stays local.** `GraphEvent` is the sanitised projection. [V]
6. **The single-operator-LAN threat model (doc 45) governs which adversarial patterns apply.** Do not wire BFT/Sybil-style controls onto a self-administered topology without re-deriving the threat. [D 45]

---

# 16. Gap register

Every gap identified in the review of the 2026-08-26 files, with disposition.

| ID | Gap | Disposition in Rev 2 | Owner / target |
| --- | --- | --- | --- |
| G1 | Stale vs. merged Core (compiled surface, scheduler, GraphSpec) | fixed §0, §8 | docs/v2 |
| G2 | Open pasted question in §8.13 | resolved §8.13 | docs/v2 |
| G3 | Malformed YAML, garbled warning | fixed | — |
| G4 | Unverified test claims | replaced by presence-checked file list §11; execution still needed | Core CI |
| G5 | No loop → graph mechanism | proposed §4.10 | planned docs/v2; code `oramasys` |
| G6 | Kernel termination taxonomy too thin | proposed §4.10, §8.11 | wrapper in `oramasys` |
| G7 | `GraphSpec` ownership contradiction | proposed D-LG-1 §7.3 | ADR in docs/v2 |
| G8 | LangGraph-compatible surface vs. callable-edge design | compat stays outside the kernel; see companion §3 | adapters in Core, new surface planned in docs/v2, built in `oramasys` |
| G9 | Reducers/joins (R3), durable resume + effect identity (R4) still open | confirmed open §7.1 | docs 57 §10–11 |
| G10 | Boundary rules implicit | BR-1…BR-6 §7 | docs/v2 |
| G11 | Security not covered | §15 + companion §2 | Telos / Phylax / docs 31, 32, 34, 45, 47 |
| G12 | Provider dispatch ledger is audit, not dedupe; JSONL ledger unwired | recorded §7.1; effect identity belongs to R4 | `oramasys` |
| G13 | Graph-artifact admission wiring to Phylax unverified | recorded §7.1 | Phylax / `oramasys` |

---

# 17. Live-state snapshot (2026-10-09)

| Repository | Default-branch head | Open PRs (method) |
| --- | --- | --- |
| `perpetua-core` | `c0795bc`, 2026-09-27 | **none** — PRs #1–#7 all merged (API-confirmed) |
| `oramasys/oramasys` | `d1656b0`, 2026-09-30 | #22 knowledge CSP headers (merge ref present) |
| `oramasys/telos` | `9aa1863` | none (no merge refs) |
| `oramasys/phylax` | `475f6c2` | none (no merge refs) |
| `oramasys/agate` | `2089483` | none (no merge refs) |
| `oramasys/anamnesis` | `99bc106` | #1 CI matrix, #2 stack merge, #3 retrieval tests |
| `oramasys/alexandria` | `072f5bd` | #1 review/governance alignment |
| `orama-system` | `b131215` | #381 MD013 wrap, #385 dependency bump |
| `Perpetua-Tools` | `e8d7333` | #419, #427 dependency bumps; #422 governance docs fix |

Method note: only `perpetua-core` could be checked through the API. For the rest,
"open" is inferred from the presence of a pull *merge* ref, which GitHub keeps
only for open PRs; that inference matched Core's API result exactly. Treat the
other rows as high-confidence, not API-confirmed. **No open PR touches loop or
graph design.**

---

# 18. Source map

- orama-system `docs/v2/`: 01, 05, 16, 22, 31, 32, 34, 39, 45, 47, 54, 55, 57, 58, 59, 60, 62, 68, 69; `plans/2026-08-27-minigraph-final-reconciliation.md`; `plans/2026-08-29-pattern-backlog-and-pt-unbundling.md`; `references/` migration plans (2026-09-09) and errata.
- `perpetua-core`: `src/perpetua_core/graph/{engine,spec,lint}.py`, `graph/plugins/`, `graph/adapters/`, `docs/POST_MERGE_CONVERGENCE_2026-08-29.md`.
- `oramasys/oramasys`: `src/orama/graph/perpetua_graph.py`, `src/orama/providers/`, `docs/architecture/`.
- Perpetua-Tools `.agent/`: `loops/{budget,constraints,ci-sweeper,pr-babysitter,daily-triage}.json`, `skills/loop-*`, `memory/semantic/MINIGRAPH_*`, `PT_UNBUNDLING_MIGRATION_MAP_2026-08-29.md`, `memory/working/MIGRATION_DEBT_AFRP_CIDF_STATUS_2026-09-12.md`.
- Telos `docs/BOUNDARIES.md`; Phylax `README.md`.

---

# 19. One-sentence memory

> **Engineer the instruction as a prompt; graduate stable stages into a chain,
> bounded retries into a checkpointed loop, and stable branching into a typed
> graph; keep `perpetua-core`'s MiniGraph the smallest plugin-free kernel; plan
> in `orama-system/docs/v2`, build application code in `oramasys/oramasys`, and
> leave endpoint security, placement, and admission to Telos, Agate, and Phylax.**
