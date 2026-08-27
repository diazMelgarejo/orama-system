# Pattern Library Reconciliation — 2026-08-27

**Canonical parent:**
[`../../58-minigraph-observer-pattern-library-reconciliation.md`](
../../58-minigraph-observer-pattern-library-reconciliation.md)

This file classifies the existing v2 feature-extraction library against the
final MiniGraph architecture. The source pattern docs remain evidence; this
matrix states which adaptations are current, revised, deferred, or rejected.

| Source / pattern | Status | Canonical interpretation |
| --- | --- | --- |
| LangGraph thread/checkpoint identity | ADOPT | `session_id` plus future versioned checkpoint lineage. |
| LangGraph atomic node checkpoint boundary | ADAPT | Save at explicit successful boundaries; durable replay still needs version/replay/effect policy. |
| LangGraph "perfect resumption" wording | REJECT | Checkpoint existence alone does not prove safe replay/resume. |
| LangGraph typed reducers | ADOPT R3 | Explicit per-field reducers + join policy before generic parallel fan-in. |
| Pydantic AI signature/schema extraction | ADOPT | Reuse `inspect.signature` + Pydantic v2 model/schema generation. |
| Pydantic AI docstring metadata | ADOPT | Tool description ergonomics without adopting the framework runtime. |
| Pydantic AI runtime dependency | REJECT | Keep `perpetua-core` tool layer dependency-minimal. |
| Karpathy March of Nines | ADOPT | Deterministic harness + verification/evaluator doctrine. |
| Sentinel as kernel mechanic | MOVE UP | Verification topology/policy belongs in `orama-system`; MiniGraph executes ordinary nodes. |
| Swarm handoff | ADOPT | Conditional edge / explicit transfer state. |
| CrewAI manager hierarchy | ADOPT | Planning/delegation/aggregation as GraphSpec/subgraph topology. |
| AutoGen nested chats | ADAPT | Bounded subgraphs; recursion remains constrained by graph/run budgets. |
| Foundry golden-dataset evaluation | MOVE UP | `orama-system` evaluator/verification layer. |
| Foundry isolation | ADOPT PRINCIPLE | Tool/effect sandboxing policy, not engine scheduling. |
| Foundry dynamic routing | MOVE UP | GraphSpec/runtime/hardware policy produces realized edge decisions. |
| Historical GraphPlugin callbacks | RESTORE / EVOLVE | Preserve multicast push requirement through `GraphObservation` fan-out. |
| `asteps()` as sole observer solution | REJECT | Sanitized pull stream is not multicast and lacks state/delta for durability consumers. |
| `GraphEvent` | ADOPT | Sanitized control-plane projection for streaming/API/UI. |
| `GraphObservation` | ADOPT | Rich trusted in-process record for checkpointer/tracer/audit/plugin dispatch. |

## Correcting the state-reducer entry

The older catalogue says the LangGraph reducer adaptation is already:

```text
PerpetuaState.merge()
  accumulates messages
  deep-merges scratchpad
  appends nodes_visited
```

That is not the canonical current sequential contract.

Current behavior is intentionally simpler:

```text
PerpetuaState.merge(delta)
  -> Pydantic model_copy(update=delta)
```

`nodes_visited` accumulation is scheduler behavior. Generic reducer semantics
belong to R3 and MUST be explicit before parallel fan-in is promoted.

## Durability interpretation

The LangGraph checkpoint extraction remains useful, but "checkpoint after every
successful node" is only a persistence primitive.

Durable graph resume requires at least:

```text
checkpoint lineage
+ graph/version identity
+ state schema identity
+ replay boundary
+ effect idempotency / dedupe
```

Therefore the existing `SqliteCheckpointer` is a valid generic plugin primitive,
not yet a complete durable-runtime contract.

## Multi-agent interpretation

The existing Swarm/CrewAI/AutoGen extraction survives as topology patterns:

```text
handoff        -> conditional edge
manager        -> planning/delegation/aggregation subgraph
nested chat    -> bounded subgraph
parallel work  -> R3 reducers + explicit joins before generic promotion
```

This keeps framework-specific orchestration concepts out of the MiniGraph
kernel while preserving their useful control semantics.

## Evaluation interpretation

Karpathy and Foundry converge on the same upper-layer principle:

```text
mutation candidate
      |
      v
independent verifier / evaluator
      |
      v
accept / refine / reject
```

The component mutating a prompt, strategy, node, or graph MUST NOT define or
change the acceptance metric during the same experiment.
