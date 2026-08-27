<!-- lint-ignore LINT-013 -->
# 57 — MiniGraph Final Reconciliation

**Status:** canonical architecture record — 2026-08-27  
**Date basis:** Asia/Manila (UTC+08:00)  
**Core repo:** `oramasys/perpetua-core`  
**Upper-layer authority:** `diazMelgarejo/orama-system`  
**Core PR:** <https://github.com/oramasys/perpetua-core/pull/1>

**Branch-name exception:** approved for the already-open reconciliation PRs only.

PR #333 and `oramasys/perpetua-core` PR #1 retain
`2026-08-27-minigraph-final-reconciliation`. Any successor branch MUST use
`yyyy-mm-dd-NNN-brief-summary`.

This record resolves the final face-off between the shipped MiniGraph, Kimi's
standalone rewrite, the Kimi/Claude review, and the graph-engineering research.
Future work MUST use this record when an older MiniGraph statement conflicts.

## Supersession map

This document preserves history but supersedes conflicting MiniGraph clauses.

| Earlier authority | Superseded clause | Current rule |
| --- | --- | --- |
| [`00-context-and-decisions.md`](00-context-and-decisions.md) D8 | `~70`/`65` physical-line target | Small/pure/irreducible is the invariant; physical line count is only a review signal. |
| [`01-kernel-spec.md`](01-kernel-spec.md) §4 | old loop and async-function-only invocation | `CompiledGraph` owns one scheduler; returned awaitables are awaited; contracts fail closed. |
| [`01-kernel-spec.md`](01-kernel-spec.md) streaming sketch | adapter may reimplement traversal | Adapters consume canonical `asteps()` events. |
| [`04-build-order.md`](04-build-order.md) Phase 2 | Phase 2 treated as permanently closed | R0–R2 is a correctness/architecture hardening addendum. |
| [`15-phase1-as-built.md`](15-phase1-as-built.md) | historical line counts/topology | Retained as history; this record and current tests define the runtime contract. |
| [`../superpowers/specs/2026-05-17-salvage-translation-design.md`](../superpowers/specs/2026-05-17-salvage-translation-design.md) | `<=80` hard cap and source-builder freeze | No hard cap; builder stays mutable; compiled topology is detached. |
| `docs/v2-kimi-minigraph-reconciliation-20260826` branch (old, un-merged; docs numbered 57/58 there, superseding-name-collision with this doc resolved by not merging their content directly) | Independent Kimi-rewrite reconciliation, its own max_steps/non-dict/empty-route findings, its own `asteps()` proposal, `minigraph_extras/` plugin naming | Superseded in full by this document — kept only as historical evidence that two independent efforts converged on the same design before either saw the other's work (max_steps semantics, non-dict rejection, empty-route rejection, the `asteps()`/`GraphEvent` seam all match exactly). Its `minigraph_extras/` naming is explicitly rejected by §9 above. |

Historical documents remain evidence of why the design evolved. Do not
mechanically restore their superseded constraints.

---

## 1. Control-structure doctrine

Use the least powerful control structure that makes the contract explicit.

```text
Prompt = one inference
Chain  = fixed pipeline
Loop   = bounded repetition
Graph  = explicit state machine
```

Promote to a graph when topology is domain logic: named states, branches,
cycles, multiple exits, interrupts, fan-out/fan-in, subgraphs, or traversal
provenance.

A graph is a state-transition contract, not merely a diagram.

---

## 2. Canonical state

`PerpetuaState` remains the one canonical in-process graph state.

Non-negotiable properties:

- Pydantic v2 `BaseModel`;
- `scratchpad: dict[str, Any]`;
- `nodes_visited: list[str]`;
- nodes return `dict` deltas;
- `PerpetuaState.merge()` applies sequential node deltas;
- graph-run state is neither PT long-term memory nor a durable checkpoint.

Kimi's `GraphState` remains historical design evidence only. Its additive
scratchpad and tuple-visit merge rules are not interchangeable with canonical
`PerpetuaState.merge()` semantics.

---

## 3. Builder and runtime ownership

The builder/runtime split is explicit.

```text
MiniGraph
  mutable topology builder
        |
        | compile()
        v
CompiledGraph
  detached topology snapshot
  sole scheduler owner
```

`MiniGraph.ainvoke(state)` compiles a fresh snapshot and delegates execution to
`CompiledGraph`.

Compilation detaches the topology, not arbitrary Python object internals.
Later builder node/edge changes MUST NOT alter an existing compiled graph.
The source builder remains mutable.

**Not an exception — copy-on-write applied at the topology layer, not
the value layer.** A repo-wide "always create new objects, never
mutate" rule was cited against this design; a direct search of
`CLAUDE.md`, `AGENTS.md`, and this repo's CodeRabbit config found no
such rule committed anywhere. Clarified directly (2026-08-27): the
actual intent behind that kind of rule is copy-on-write — append-only,
diff-on-top-of-original, like a git commit or a ZFS snapshot, never
destructively rewritten in place. `PerpetuaState.merge()` already
implements exactly that at the **value** layer, confirmed by reading
the code directly: `return self.model_copy(update=delta)` — a new
state object every call, the prior one untouched.

`MiniGraph`/`CompiledGraph` implement the identical guarantee one layer
up, at **topology**: `MiniGraph` is the working tree — mutable,
in-progress, exactly like files before a commit. `compile()` is the
commit. `CompiledGraph` is the snapshot, and this document already
states the git-commit-equivalent guarantee above: later builder
node/edge changes MUST NOT alter an existing compiled graph. Once
compiled, a `CompiledGraph` never changes retroactively, the same way a
git commit doesn't rewrite itself when the working tree keeps changing.
`add_node`/`add_edge` mutating the *builder* is a precondition for
copy-on-write at the compile boundary, not a violation of it — the
finding checked for mutation at the wrong boundary. Two independent
verifications converged on this same conclusion before either saw the
other's reasoning: this document's own architecture record above, and a
separate session's behavioral test confirming builder mutation after
`compile()` provably does not alter the already-compiled snapshot (a
real `add_node`/`add_edge` call after `compile()`, then re-running the
already-compiled graph and confirming its output is unaffected — not
just asserted). Rewriting `add_node`/`add_edge` to return new builder
instances would collapse the working-tree/commit distinction this
design deliberately preserves, not bring it into compliance with
anything.

---

## 4. Node invocation

The scheduler invokes first and inspects the returned object.

```python
result = node_fn(state)
if inspect.isawaitable(result):
    result = await result
```

This supports:

- async functions;
- sync functions;
- callable objects with `async __call__`, including `ToolNode`;
- sync functions that return awaitables.

A node result MUST be a `dict` delta. `None` or another type is a contract
error. The engine does not coerce falsey results to `{}`.

---

## 5. Routing and termination

`END = "__end__"` is the only normal terminal route.

Every static or conditional edge MUST resolve to a non-empty string. Invalid
route values fail closed rather than becoming implicit success.

Execution order is invariant.

```text
enter node
-> record visit
-> execute node
-> await returned awaitable if needed
-> validate dict delta
-> merge delta
-> evaluate outgoing edge against UPDATED state
```

Post-merge conditional routing is public graph semantics.

---

## 6. Cycle bounds

Every cycle remains bounded by `max_steps`.

`MaxStepsExceeded` has exact semantics.

```text
steps     = number of completed node executions
last_node = most recently entered node
```

The guard trips before an additional node would exceed the budget. With a
zero-step budget, the diagnostic is `steps=0` and `last_node=START`.

---

## 7. Interrupts

The kernel recognizes `Interrupt` structurally so it never imports plugins.

Required behavior:

- exception type name is `Interrupt`;
- `prompt` is required;
- `payload` is optional and read with `getattr(..., None)`;
- state becomes `interrupted`;
- metadata records node, prompt, and optional payload;
- unrelated exceptions propagate.

The old `interrupt_handler` constructor argument had no execution semantics and
is removed rather than preserved as a misleading no-op API.

This reconciliation does NOT claim durable resume. Durable HITL requires later
checkpoint, replay, and idempotency contracts.

---

## 8. One canonical execution seam

`CompiledGraph` owns one scheduler: `asteps()`. It is the actual traversal
loop, not a wrapper over a separate internal method — `01-kernel-spec.md`
§4's code (behaviorally verified, not just documented) has no `_run()`.
`ainvoke()` is a thin consumer that drains `asteps()` and returns the
final state; it does not duplicate the loop.

```text
CompiledGraph.asteps(state)  -- the scheduler itself
        |
        +--> ainvoke(state) drains it -> final PerpetuaState
        |
        +--> consumed directly for the structural GraphEvent stream
```

**2026-08-27 correction:** an earlier version of this diagram showed
`CompiledGraph._run(state)` as a separate scheduler with `ainvoke()`/
`asteps()` as two views over it. That method was never built or tested;
`asteps()` itself has been the real scheduler since it was first
implemented and verified. Fixed here to match the actual code rather
than describing a method that doesn't exist — adapters must consume
`asteps()` directly, not a `_run()` that isn't there.

Public event kinds are:

```text
edge.selected
node.start
node.end
interrupt
done
```

`GraphEvent` contains control-plane metadata only: event kind, node/target,
completed-step count, and terminal reason.

It does NOT contain raw prompts, state snapshots, node deltas, database handles,
provider policy, exporter configuration, or persistence logic.

Streaming, checkpoint, trace, and debugger adapters MUST consume this seam
instead of copying the scheduler or traversing private `_nodes`/`_edges`.

Per-kind fields and ordering are defined authoritatively in
`oramasys/perpetua-core`'s `GraphEvent` class and `CompiledGraph._run`, not
restated here — this document is the ownership/boundary record, not the
field-level contract. Coverage lives in that repo's `test_engine_reconciliation.py`
and `test_streaming.py`. Consult those directly; this session has no read
access to `oramasys/perpetua-core` to link exact paths/line ranges, so no
placeholder path is given as confirmed. Likely locations, following this
same document's own `src/`-layout convention (§4's code sample) but
**unverified**: `src/perpetua_core/graph/engine.py` and
`src/tests/test_engine_reconciliation.py` / `src/tests/test_streaming.py`
— confirm against the real tree before citing these as fact.

---

## 9. Plugin boundary

Keep the existing namespace.

```text
perpetua_core/graph/plugins/
```

Do not create `minigraph_extras/` or another parallel plugin system.

Generic plugin concerns remain outside `engine.py`:

- checkpointing;
- interrupts / resume guard;
- routing and validation;
- tools / `ToolNode`;
- subgraphs;
- streaming;
- structured LLM output;
- parallel dispatch.

The engine MUST NOT import plugins, providers, storage adapters, network
clients, telemetry exporters, or upper-layer graph policy.

---

## 10. Parallelism before expansion

The existing parallel helper's ordered last-writer-wins behavior is not a
sufficient generic fan-in contract.

Before richer parallel graph semantics ship, define explicit reducers and
joins.

```text
Reducer: REJECT_CONFLICT | FIRST | LAST | CONCAT | UNION | CUSTOM
Join:    ALL | ANY | FIRST_SUCCESS | QUORUM | CUSTOM
```

Branch completion timing MUST NOT silently define state merge behavior.
This is deferred R3 work.

---

## 11. Durability before resume

Upgrade the existing checkpointer rather than introducing a second subsystem.
A future durable identity should include at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
created_at
```

Durable replay also requires explicit effect idempotency/deduplication policy.
External-write nodes cannot be retried or resumed safely without that contract.

---

## 12. Upper-layer ownership

`perpetua-core` executes a realized graph. The final face-off assigns the
richer graph-specification and runtime-policy authority to `orama-system`.

Canonical future vocabulary:

```text
GraphSpec       reusable/versioned graph definition
GraphRun        one realized execution identity/configuration
GraphTrace      append-only observed execution evidence
GraphCheckpoint resumable state + compatibility lineage
```

`GraphSpec`, `NodeSpec`, `EdgeSpec`, lint, topology classification, budgets,
runtime outcome policy, effect policy, version selection, and evaluation belong
in `diazMelgarejo/orama-system`, not in `MiniGraph.engine.py`.

```text
diazMelgarejo/orama-system
  methodology + GraphSpec/NodeSpec/EdgeSpec authority
  lint + version selection + evaluation + runtime policy
                  |
                  | compiles/targets realized mechanics
                  v
oramasys/perpetua-core
  PerpetuaState + irreducible graph execution
```

`perpetua-core` MUST NOT import upward from `orama-system`.

`oramasys/oramasys` may later consume or host an approved projection of these
specifications. Ownership does not move there implicitly. Such a move requires
a new explicit architecture decision.

---

## 13. Graph lint target

Before executing a versioned `GraphSpec`, the `orama-system` layer should
validate at least:

- entry exists;
- static targets exist;
- unreachable nodes are rejected or explicitly allowed;
- every reachable path terminates or participates in a bounded cycle;
- parallel fan-in declares join/reducer behavior;
- durable/external-write nodes declare replay/effect policy;
- stable graph/node IDs are present;
- schema/version compatibility is explicit.

Natural-language topology, if introduced, MUST compile to a typed validated
`GraphSpec`. Prose is never runtime authority.

---

## 14. Optimization and evaluation

Automated graph evolution remains research-only until all of these exist:

```text
versioned GraphSpec
+ GraphTrace corpus
+ locked evaluator
+ quality/cost/latency/reliability metrics
+ candidate isolation
+ promotion gate
```

Hard rule:

> The component mutating a prompt, node, strategy, or graph may not alter the
> acceptance metric during the same experiment.

Trace-derived learning should enter governed memory/review, not uncontrolled
runtime self-rewrite.

---

## 15. Implementation status

**Proposed / in review** in `oramasys/perpetua-core` PR #1 (open, no merge
commit as of this review — Python 3.11/3.12 checks succeeded; add the merge
commit SHA here once it actually merges, not before):

- canonical `PerpetuaState` retained;
- returned-value awaitability;
- `CompiledGraph` scheduler ownership;
- strict node-delta and route validation;
- END-only normal termination;
- exact max-step diagnostics;
- optional structural interrupt payload;
- removal of the no-op `interrupt_handler` constructor surface;
- compile-detachment regression coverage;
- real `ToolNode`-inside-MiniGraph regression coverage;
- structural `GraphEvent` + `asteps()`;
- streaming as a scheduler adapter;
- a Python 3.11/3.12 test workflow for future PR verification.

Deferred intentionally:

- reducer/join redesign;
- checkpoint lineage and durable resume;
- runtime budgets/effect policy;
- `GraphSpec`/lint/evaluation implementation in `orama-system`;
- graph optimizer and trace miner.

**Action item, not yet confirmed done:** `01-kernel-spec.md`'s Repo
Layout section now nests `perpetua_core/` and `tests/` under `src/`
(2026-08-27 correction, matching `46-repository-standard.md`). Whether
`oramasys/perpetua-core`'s actual tree already matches this or still
needs migrating is unconfirmed — this session has no read access to
that repo. Whoever has real access: check first; if migration is
needed, do it as a `git mv` plus a `pyproject.toml` packaging-config
update (`[tool.setuptools.packages.find] where = ["src"]` or
equivalent) plus an import sanity check
(`python -c "import perpetua_core; ..."`), **as its own commit**,
separate from any behavior change, so either can be reverted
independently. If it already matches, note "no change needed" rather
than leaving this unconfirmed.

---

## 16. Acceptance invariants

Future changes MUST preserve:

1. one graph-state model: `PerpetuaState`;
2. one scheduler implementation;
3. async function/callable/returned-awaitable support;
4. ordered `list[str]` visit provenance;
5. post-merge conditional routing;
6. explicit END-only normal termination;
7. deterministic bounded cycles;
8. detached compiled topology;
9. no plugin/provider/storage imports in the kernel;
10. provider/exporter-independent structural events;
11. streaming without private topology traversal;
12. durable/dynamic/optimizer features outside the kernel until proven.

---

## 17. LangGraph / LangGraph.js drop-in compatibility — explicit by design

Internal implementation stays ours. **At the API surface, we target
drop-in compatibility with LangGraph (Python) and LangGraph.js
(TypeScript) by design — not an aspiration, a standing rule — for the
builder/topology API and the invoke/stream surface specifically.** This
was the original rationale for building a MiniGraph-shaped kernel in the
first place (see "we already are a LangGraph, just not named that way"
framing) and is made an explicit, binding decision here rather than an
implicit assumption a future agent has to rediscover. The scope
qualifier is not a hedge — see the very next paragraph for exactly why
full fidelity is out of scope for two specific subsystems, and never
claim "100% compatible" without it.

Full API research backing this section (exact current signatures, verified
against `langgraph` 1.2.x source and reference docs, not assumed from
memory): see the compatibility research artifact referenced in this PR's
conversation record. Two things established there that shape this section:

- LangGraph's **builder/topology API has been stable since v0.1 through
  v1.2** (the current stable line as of August 2026) — `add_node`,
  `add_edge`, `add_conditional_edges`, `compile` are unchanged. This makes
  "100% API compatible" a coherent, pin-able target, not a moving one.
- Full byte-for-byte fidelity is realistic for the **builder + invoke/stream
  surface**, but genuinely hard for the **exact streaming event schema**
  (`stream_mode` shapes, `astream_events` v2) and **checkpointer
  serialization internals**. Scope those explicitly rather than silently
  overclaiming "100%."

### 17a. Python — legacy AND current surface, both, not one or the other

The compatibility layer supports **both** the legacy v0.1-era method names
(still valid, not deprecated-for-removal per LangChain's own Release
Policy) and the current v1.2.x primitives, because real LangGraph-authored
code in the wild uses both:

**Legacy wrapper (aliases onto the canonical builder):**

```python
# perpetua_core/graph/plugins/langgraph_compat.py -- a PLUGIN, never
# imported by engine.py itself (per §9's plugin boundary).
def set_entry_point(self, key: str) -> "MiniGraph":
    """Equivalent to add_edge(START, key). Legacy LangGraph v0.1 name,
    kept because real code still uses it."""
    return self.set_start(key)

def set_finish_point(self, key: str) -> "MiniGraph":
    """Equivalent to add_edge(key, END)."""
    return self.add_edge(key, END)
```

**Current surface (v1.2.x), targeted explicitly:**

- `START`/`END` sentinels — already canonical in `engine.py` §4 itself, not
  a compat-layer addition (this is the one piece that belongs in the
  kernel proper, since the kernel already needed universal sentinels for
  its own correctness — see §4's amendment history).
- `Command(update=..., goto=...)` — combines a state update with routing
  in one node return value. **Design, not yet verified**: a compat-layer
  node wrapper would detect a returned `Command` and translate `update`
  into the normal dict-delta merge path; the `goto` → routing-decision
  translation through the scheduler's `_next` flow has no test
  demonstrating it actually selects the expected node yet. Do not
  present this as working until a real compatibility test exists —
  implemented as a plugin wrapper around node execution, not a kernel
  change, when it is built.
- `Send(node, arg)` — map-reduce fan-out. Depends on §10's deferred
  reducer/join redesign (R3); do not implement `Send` support before R3
  lands, since `Send`'s correctness depends on exactly the reducer
  semantics R3 defines.
- `interrupt(value)` — the current preferred HITL primitive (persist +
  resume via `Command(resume=...)`), distinct from and more capable than
  the structural `Interrupt` exception the kernel recognizes (§7). The
  kernel's structural recognition is the substrate; a full `interrupt()`
  implementation requires the durable checkpoint lineage §11 defers.
  **Do not implement a partial `interrupt()`** (e.g. one that raises but
  doesn't actually persist/resume) — that silently breaks HITL examples
  in a way that is worse than clearly not supporting it yet.
- `add_conditional_edges(source, path, path_map=None)` — already
  expressible via the canonical `add_edge(src, dst_fn)` pattern; the
  compat layer's version is a thin rename/signature-adapter, not new
  logic.

**Explicitly out of scope for now, and why:** `astream_events(version="v2")`
(the fine-grained callback event vocabulary) and full `BaseCheckpointSaver`
serialization fidelity. Both are real, substantial subsystems in their own
right; claiming compatibility with either before implementing them for
real would be the "silently overclaim 100%" failure mode this section
exists to prevent.

### 17b. JavaScript/TypeScript — `oramaclaw`, targeting LangGraph.js exactly

A **separate, JS-facing module named `oramaclaw`** targets LangGraph.js's
exact naming (verified current as of August 2026, not assumed from the
Python API by analogy):

```typescript
import { StateGraph, Annotation, START, END, Command } from "oramaclaw";

const StateAnnotation = Annotation.Root({
  foo: Annotation<string>,
});

const graph = new StateGraph(StateAnnotation)
  .addNode("nodeA", nodeA, { ends: ["nodeB", "nodeC"] })  // ends: declares
  .addNode("nodeB", nodeB)                                 // Command.goto
  .addNode("nodeC", nodeC)                                 // destinations
  .addEdge(START, "nodeA")
  .compile();
```

`addNode`/`addEdge` (camelCase, not the Python `add_node`/`add_edge`
snake_case — JS convention, verified, not a naming inconsistency to
"fix"), `Annotation.Root({...})` for state-schema definition, and the
`ends: [...]` third-argument option on `addNode` (declares valid
`Command.goto` destinations for an edgeless/`Command`-routed node,
confirmed against LangGraph.js's official "Use the graph API" guide and
its `Command` how-to doc) are the three surfaces named explicitly for
this module to target.

**Where `oramaclaw` lives and what it bundles with:** Perpetua-Tools,
alongside the existing `packages/alphaclaw-adapter/` and
`packages/alphaclaw-mcp/` — matching the pattern already established and
verified for those two packages (PT `lesson_a5b40efe18d5`). `oramaclaw` is
described as bundled with "ALL AlphaClaw- and OpenClaw-related controllers
and commandeering components," which means it **steers those processes at
runtime** (spawn/HTTP, matching `alphaclaw-adapter`'s own verified design)
— it does **not** import from or modify `diazMelgarejo/AlphaClaw`'s
repository. This boundary is load-bearing, not incidental: the same
"runtime-only, never repo-level" distinction that let `alphaclaw-adapter`
work stay in scope under the standing AlphaClaw exclusion applies
identically here. Any future implementation of `oramaclaw` must confirm
this runtime-only relationship directly (grep for git/repo operations
against AlphaClaw's own repo, same check already performed and recorded
for `alphaclaw-adapter`) before writing anything, not assume it.

### 17c. The compatibility layer is a plugin, not a kernel change

Both 17a and 17b live outside `engine.py`, consistent with §9's plugin
boundary — a LangGraph-compatibility shim is exactly the kind of
"capability-specific" concern `mk-1.md`'s micro-kernel principle assigns
to plugins, not the kernel. The kernel's only concession to this goal is
the `START`/`END` sentinel choice itself (§4), made because the kernel
needed universal sentinels for its own internal correctness anyway —
everything else (legacy aliases, `Command`/`Send` translation, the JS
module entirely) is additive surface area with zero kernel changes
required to add or remove it, matching the same enforcement discipline
§9 already establishes for every other plugin.

**Implementation status: in progress, not indefinitely deferred.** Unlike
§10/§11's genuinely deferred R3/R4 work (blocked on real prerequisites —
reducer/join semantics, checkpoint lineage — that don't exist yet), this
compatibility layer has no such blocker beyond this document itself
landing as the reference. `perpetua-core` code changes for 17a/17b begin
as soon as this record is merged and available to implement against; do
not read the design-only caveats above (`Command` routing unverified,
`Send` waiting on R3 specifically) as "the whole compat layer is
deferred" — only those two named pieces are, for the specific reasons
stated next to each.

---

The north star remains:

> Keep intelligence flexible inside nodes, control semantics explicit in the
> graph, effects auditable at boundaries, evaluation independent from mutation,
> and the kernel smaller in responsibility than the ecosystem around it.
