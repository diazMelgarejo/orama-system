# Feature Extraction: LangGraph State Reducers & Parallelism

> **Reconciliation status (2026-08-28):** typed reducer pattern -- **ADOPT, targeted at R3**
> (explicit per-field reducers + join policy required before generic parallel fan-in is promoted) --
> not current `PerpetuaState.merge()` behavior, which is a single whole-delta apply using
> `model_copy(update=deepcopy(delta), deep=True)`. See
> [`RECONCILIATION-2026-08-27.md`](RECONCILIATION-2026-08-27.md).
>
> **Goal:** Repurpose the "Reducer" pattern for conflict-free state updates during parallel node execution.

## 1. The "V1 Hack" Baseline

In v0.9.9.8, orchestration was strictly sequential:

```python
# v1 style (sequential)

for stage in STAGE_SEQUENCE:
    output = await run_stage(stage, state)
    state.stage_outputs[stage.value] = output
```

**Problem**: No support for parallel agent work (e.g., 5 parallel Executors). If two agents write to
the same key, the last one wins, leading to data loss.

## 2. LangGraph "Magic" (Technical Analysis)

LangGraph uses **Reducers** defined in the state schema:

- **\`Annotated[list, operator.add]\`**: Appends all updates into a single list.
- **Custom Reducers**: Functions like \`merge_dicts(old, new)\` that can handle deep-merging or
  deduplication.

## 3. oramasys v2: R3 reducer target

Current `PerpetuaState.merge()` is deliberately a sequential whole-delta transition. It isolates
both the prior state and caller-owned delta values, but it does not define per-field reducer or
parallel join semantics:

```python
from copy import deepcopy

class PerpetuaState(BaseModel):
    def merge(self, delta: dict) -> "PerpetuaState":
        return self.model_copy(update=deepcopy(delta), deep=True)
```

R3 may add explicit reducer behavior such as accumulation and custom conflict resolution, but only
through declared per-field reducer and join policy. Do not retrofit those semantics into ordinary
sequential `merge()` implicitly.

A future reducer-aware sketch may look like:

```python
new_messages = self.messages + delta.get("messages", [])
new_scratchpad = {**self.scratchpad, **delta.get("scratchpad", {})}
```

Those operations are examples of **planned R3 reducer choices**, not current automatic behavior.

## 4. Integration with Primitives

- **Parallel Fan-Out — current:** whole deltas applied through `PerpetuaState.merge()` do not make
  conflicting parallel writes deterministic. If parallel branches are merged without R3 reducers
  and joins, conflicting fields remain completion/merge-order dependent and may overwrite one
  another.
- **Audit Trace — current:** `nodes_visited` records the traversal order produced by the scheduler;
  it is not a deterministic proof of parallel branch completion order. R3 must define explicit
  provenance if branch-completion evidence is required.
- **Safety — current:** copy isolation prevents aliasing between state generations, but it does not
  prevent last-write-wins conflicts between competing whole-delta updates.
- **R3 target:** explicit typed reducers plus join policy provide deterministic fan-in semantics,
  conflict handling, and branch provenance independent of completion timing.
