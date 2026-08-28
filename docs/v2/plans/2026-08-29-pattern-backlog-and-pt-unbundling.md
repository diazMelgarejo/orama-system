# Pattern Backlog + Perpetua-Tools Unbundling Roadmap

**Date:** 2026-08-29  
**Date basis:** Asia/Manila (UTC+08:00)  
**Status:** canonical follow-on plan for the MiniGraph reconciliation  
**Parent plan:**
[`2026-08-27-minigraph-final-reconciliation.md`](2026-08-27-minigraph-final-reconciliation.md)

This plan places every still-live mined pattern and the current Perpetua-Tools
capability set into an explicit implementation phase and ownership boundary.
It does not turn deferred work into rejected work and does not move upper-layer
policy into the MiniGraph kernel.

The governing rule is:

> Mine semantic primitives from external systems, then place each primitive in
> the narrowest layer that can own it without duplicating scheduling, policy,
> persistence, or provider behavior.

## 1. Current repository boundaries

Existing durable repositories:

```text
oramasys/perpetua-core
  universal in-process execution mechanics

oramasys/oramasys
  application/service composition and future GraphSpec consumption

oramasys/agate
  hardware capability, affinity, and routing contracts

diazMelgarejo/orama-system
  methodology, GraphSpec authority, lint, evaluation, runtime/effect policy

diazMelgarejo/Perpetua-Tools
  current integrated implementation source for memory, telemetry, coordination,
  adapters, security helpers, and operational tooling during migration
```

No additional satellite repository name in this document is an existing repo or
commitment. First establish clean module/package contracts; split a module into
its own repository only when its dependency graph, release cadence, and ownership
justify doing so.

## 2. Completed execution foundation — R0 through R2.4

The final MiniGraph execution shape is already established:

```text
CompiledGraph._run()
  sole scheduler
        |
        v
GraphObservation(event, state, delta?)
        |
        +-----------------------+
        |                       |
        v                       v
GraphPlugin fan-out         GraphEvent
        |                       |
        |                       v
        |                    asteps()
        v
checkpointer / tracer / audit / trusted observers
```

`MiniGraph` remains a mutable construction builder. `compile()` is the detached
runtime boundary. `GraphEvent` is sanitized control-plane evidence.
`GraphObservation` is rich trusted in-process evidence.

### R2.4a — state-generation isolation correction

`PerpetuaState.merge()` requires both copy layers:

```python
self.model_copy(update=copy.deepcopy(delta), deep=True)
```

They close different alias classes:

- `deep=True` isolates nested mutable values inherited from the old state;
- `copy.deepcopy(delta)` isolates caller-owned mutable values supplied in the
  new delta.

Core PR #1 implements this at commit
`488bc6cc440247ca86811c46ae0dd05869898324` with a regression covering caller
mutation, merged-state mutation, and preservation of the prior generation.

### R2.4b — CI credential boundary correction

The same core commit sets:

```yaml
persist-credentials: false
```

on `actions/checkout@v4` so pull-request-controlled test code cannot read a
persisted checkout token when later steps do not need authenticated Git access.

Exact-head CI and review remain separate gates. Do not close these findings on
commit existence alone; verify the current PR head and review threads.

## 3. R2.5 — plugin criticality, failure policy, and backpressure

The recovered `GraphPlugin` work solved multicast delivery, but one policy seam
is still intentionally open.

Every plugin MUST receive the same ordered observations. What happens when a
plugin fails or cannot keep up must be explicit by plugin contract.

Initial policy classes:

```text
AUTHORITATIVE
  checkpoint, security audit, approval evidence
  synchronous/awaited
  failure fails the graph run

BEST_EFFORT
  metrics, non-authoritative exporter
  failure may be recorded and tolerated by explicit policy

BUFFERED_TELEMETRY
  allowed only when evidence loss semantics are declared
  MUST NOT be used for durability or authorization evidence
```

Default behavior remains synchronous ordered delivery. Do not make
`asyncio.create_task()` the implicit fan-out mechanism: detached delivery would
permit execution to outrun checkpointing and would detach observer failures from
the run that produced them.

Ownership:

- generic delivery mechanics: `perpetua-core`;
- which plugin is authoritative/best-effort for a concrete run: `orama-system`
  runtime/effect policy or consuming application configuration.

## 4. R3 — reducers, joins, and deterministic parallelism

This phase incorporates the LangGraph reducer lesson and the unresolved part of
the Swarm/CrewAI/AutoGen mining.

Required reducer vocabulary:

```text
REJECT_CONFLICT
FIRST
LAST
CONCAT
UNION
CUSTOM
```

Required join vocabulary:

```text
ALL
ANY
FIRST_SUCCESS
QUORUM
CUSTOM
```

Required invariants:

- branch completion timing MUST NOT define merge semantics;
- every concurrently written field MUST have an explicit reducer or a
  fail-closed conflict rule;
- partial failure behavior MUST be declared by the join;
- reducer output MUST be deterministic under branch completion reordering;
- provenance MUST preserve which branch contributed each merged value when that
  matters for audit/evaluation.

Pattern placement:

```text
LangGraph typed reducers
  -> R3 reducer contract

Swarm handoff
  -> conditional edge / transfer state

CrewAI manager
  -> Planning -> Delegation -> Aggregation subgraph

AutoGen nested conversation
  -> bounded subgraph

parallel delegation
  -> only promoted after reducer + join semantics are explicit
```

`perpetua-core` may own generic reducer/join mechanics. `orama-system` owns
GraphSpec declarations saying which reducer/join applies to a concrete topology.

## 5. R4 — durable deterministic resume

No resumability feature is rejected.

Canonical classification:

```text
LangGraph checkpoint/thread identity
    ADOPT

Atomic successful-boundary checkpoints
    ADOPT / ADAPT

Durable resumability
    ADOPT — R4 target

"perfect resumption"
    REJECT WORDING ONLY

durable deterministic resume
    ADOPT TARGET
```

The goal is precise continuation from an explicit compatible saved boundary,
not total reversibility of external reality.

A durable checkpoint contract requires at least:

```text
checkpoint_id
parent_checkpoint_id
graph_id
graph_version
state_schema_version
run_id
logical step/node
saved state
created_at
replay boundary
```

Effect-bearing nodes additionally require an effect contract:

```text
effect_id
idempotency key / dedupe key
attempt identity
committed / unknown / compensated status
reconciliation policy
```

Recovery policy MUST distinguish:

- replay-safe pure computation;
- idempotent external effects;
- effects requiring deduplication;
- effects requiring compensation;
- ambiguous/irreversible effects requiring explicit human or policy
  reconciliation.

The existing `SqliteCheckpointer` remains a useful persistence primitive. R4
turns checkpointing into a complete resume contract rather than creating a
second checkpoint subsystem.

## 6. R5 — versioned GraphSpec, compiler, and fail-closed lint

`GraphSpec`, `NodeSpec`, and `EdgeSpec` belong to `orama-system`.

Recommended semantics:

```text
GraphSpec
  immutable/versioned value
  stable graph/node IDs
  with_node()/with_edge() persistent updates permitted
  diffable and promotion-friendly
        |
        | validate + compile
        v
MiniGraph
  mutable realization builder
        |
        v
CompiledGraph
  detached runtime snapshot
```

GraphSpec validation MUST reject invalid specifications before execution.
Minimum checks include:

- valid entry;
- valid static targets;
- unreachable-node policy;
- termination or bounded-cycle proof obligation;
- explicit parallel reducers and joins;
- stable graph/node IDs;
- schema/version compatibility;
- durable/effect policy for replay-sensitive nodes;
- declared budgets and allowed capabilities where policy requires them.

### Pydantic AI tool pattern in R5

Keep the mined primitive, not the framework runtime:

```text
inspect.signature
+ Pydantic create_model / JSON schema
+ docstring descriptions
+ strict argument validation
+ state/dependency injection
```

Generic schema derivation and `ToolNode` mechanics may live in `perpetua-core`.
GraphSpec tool declarations, approval/effect authority, and allowed-capability
policy remain above the kernel.

### Dynamic routing in R5

Foundry/Magentic-style dynamic routing belongs in GraphSpec/runtime policy.
Policy chooses or validates a realized route; MiniGraph executes the resulting
edge decision. The scheduler does not become a model-selection policy engine.

## 7. R6 — independent verification and evaluation

Karpathy's March of Nines and Foundry's evaluation patterns converge here.

Canonical law:

```text
mutator != evaluator
```

Required components:

- deterministic harnesses where a deterministic oracle exists;
- golden datasets for stable representative scenarios;
- independent verification nodes;
- LLM-as-judge only with frozen prompts/models/rubrics for a comparison window;
- quality, cost, latency, safety, and reliability metrics kept distinct;
- explicit acceptance/promotion thresholds;
- evaluator version recorded with every result.

A Verification/Sentinel node is an ordinary graph node at runtime. The kernel
must not understand what "verified", "elegant", or "acceptable" means.
Evaluation contracts and experiment governance belong in `orama-system`.

## 8. R7 — tool isolation, effect authority, and network/hardware policy

Foundry sandboxing is retained as a principle, but scheduling and security
policy remain separate concerns.

Required boundaries:

```text
perpetua-core
  generic tool invocation + validation mechanics

orama-system
  effect classification, approvals, sandbox requirement, runtime policy

agate
  hardware capability/affinity/routing contract

PT security/endpoint modules during migration
  concrete network endpoint authorization and transport hardening
```

A tool sandbox may be a generic reusable capability, but the decision that a
particular tool MUST be sandboxed belongs to upper-layer policy.

Endpoint/network policy must remain fail-closed and must not be folded into the
graph engine merely because graph nodes use networked tools.

## 9. R8 — Perpetua-Tools unbundling

PT is currently an integration-rich monorepo. Migration MUST be a strangler
process, not a bulk copy into `perpetua-core`.

### 9.1 Classification before movement

Every PT feature is first classified as one of:

```text
UNIVERSAL MECHANIC
  candidate for perpetua-core

SPEC / METHODOLOGY / EVALUATION POLICY
  orama-system

APPLICATION / SERVICE COMPOSITION
  oramasys/oramasys

HARDWARE CAPABILITY / AFFINITY POLICY
  oramasys/agate

MEMORY / OBSERVABILITY / COORDINATION / ADAPTER CAPABILITY
  satellite module boundary; repository split is optional and later
```

### 9.2 Universal mechanics that may move toward `perpetua-core`

Only dependency-minimal reusable mechanics qualify:

- `PerpetuaState` and graph execution contracts;
- `GraphEvent`, `GraphObservation`, generic plugin fan-out;
- generic ToolNode/tool-schema mechanics;
- generic checkpoint plugin interface and persistence abstraction;
- generic reducers/joins when R3 is specified;
- generic interrupt/subgraph/streaming primitives that remain provider- and
  policy-free.

The following MUST NOT be moved into core merely for convenience:

- provider clients;
- HTTP/API servers;
- endpoint allow/deny policy;
- hardware routing policy;
- telemetry exporters;
- fleet membership/network discovery;
- long-term memory stores;
- experiment/evaluation policy.

### 9.3 Memory capability boundary

Current PT examples include `.agent/memory`, `memory_store.py`,
`memory_embed.py`, `memory_rrf.py`, `memory_node.py`, and
`memory_governance.py`.

Target boundary:

```text
portable .agent files
  repo-local knowledge and operator state
        |
        v
memory engine module
  recall / ranking / embedding / episodic + semantic persistence / governance
```

The engine may later become a reusable satellite package/repository. The
repo-local `.agent` knowledge remains local to the repository consuming it.
Append-only historical memory and rendered-artifact rules remain intact during
migration.

### 9.4 Observability capability boundary

Current PT observability work includes:

- typed redacted domain observations;
- OpenTelemetry projection/export;
- OTLP endpoint validation and DNS pinning;
- internal-only Periscope trajectory storage;
- runtime producer lifecycle and smoke verification;
- `AuditLog` and redaction/provenance helpers.

Target boundary:

```text
runtime domain event
  -> redaction / privacy boundary
  -> typed observation
  -> optional exporter adapter
```

The graph kernel may emit structural evidence, but exporter/provider/network
configuration stays outside `perpetua-core`.

### 9.5 Coordination / mesh capability boundary

Current PT coordination-related modules include GossipBus, LAN gossip/discovery,
membership, heartbeat monitoring, peer records, fleet topology, witness quorum,
equivocation detection, monotonic transition gates, coordination bias detection,
and mesh authentication.

Treat these as a coherent coordination/mesh boundary. They may become one or
more satellite packages after their contracts are isolated. They are not graph
kernel responsibilities.

### 9.6 Endpoint, security, and hardware boundary

PT already contains package boundaries such as `packages/endpoint-policy` and
`packages/net_utils`, plus SSRF/egress enforcement, transport pinning, model
registry/transport, key helpers, and cost/effect guards.

Split by authority rather than file location:

- hardware capability and model affinity contract -> `agate`;
- generic endpoint/network authorization -> security/policy satellite boundary;
- application-specific cost/effect approval -> `orama-system` policy or
  consuming application;
- reusable low-level safe transport helpers -> satellite utility package, never
  embedded into MiniGraph scheduling.

### 9.7 Agent/provider adapter boundary

AlphaClaw, OpenClaw, MCP, local-agent, Perplexity, Periscope, and similar
integration code should become adapters around stable contracts, not authorities
for core semantics.

Current examples include:

- `packages/alphaclaw-adapter`;
- `packages/alphaclaw-mcp`;
- `packages/local-agents`;
- `packages/mcpb-agents`;
- AlphaClaw/OpenClaw managers/resolvers;
- provider clients and bridges;
- worker registry/spawn reconciliation.

Adapters MAY depend on core/public contracts. Core MUST NOT depend on adapters.

### 9.8 PT harness and operational loops

The `.agent/harness` hooks and `.agent/loops` such as CI sweeper, daily triage,
and PR babysitter are operational-agent infrastructure, not MiniGraph kernel
features.

Preserve them as a separate agent-runtime/operations boundary. They may consume
GraphSpec, memory, telemetry, and policy APIs but should not define those APIs.

## 10. Strangler migration procedure

For each capability cluster:

1. inventory source files, tests, schemas, CLI/API surfaces, data formats, and
   consumers;
2. freeze current behavior with regression/contract tests;
3. define the destination interface without changing behavior;
4. introduce the new package/module behind that interface;
5. run legacy and new implementations in differential/dual-write mode when
   safe and useful;
6. migrate consumers one by one;
7. observe parity and failure behavior over a declared compatibility window;
8. make the new module authoritative;
9. delete legacy copies and transitional mirrors only after no consumer depends
   on them;
10. record provenance and migration decisions in PT `.agent` memory and the
    owning repository's ADR/plan.

No migration is complete while two writable sources of truth silently coexist.
Temporary mirrors MUST name their authority and sunset condition.

## 11. R9 — optimization and trace learning

Production graph mutation remains after the foundations above.

Required prerequisites:

```text
versioned GraphSpec
+ deterministic reducers/joins
+ durable deterministic resume
+ effect policy
+ trace corpus
+ frozen independent evaluator
+ candidate isolation
+ explicit promotion gate
```

Only then promote controlled search over prompts, nodes, routing, topology, or
policies. Candidate generation may be automated; acceptance authority remains
independent.

## 12. Merge and follow-on sequence

1. close exact-head findings on `oramasys/perpetua-core` PR #1;
2. merge the core reconciliation only after exact-head CI/review is green;
3. merge orama-system PR #333 after its exact-head checks/review are green;
4. start R2.5/R3 from then-current `main` using correctly numbered dated
   branches;
5. implement R4/R5 as separate contracts rather than growing `engine.py`;
6. begin PT unbundling cluster-by-cluster with contract tests and explicit
   authority handoff;
7. start R9 optimization only after the durability/evaluation foundations are
   operational.

## Completion criterion

The long-term unbundling is complete when PT is no longer the accidental owner
of unrelated runtime concerns. Each capability has one authoritative module,
clear public contracts, tested migration provenance, and no hidden import from a
lower layer back into an upper policy/application layer.
