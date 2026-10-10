# Contract — forward compatibility and upstream replacement

**Status:** approved design contract under [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).
Design only. Plan slice: [T6](PLAN-R4-EXECUTION.md#t6--replacement-cohorts-and-retained-v1-register).
Builds on D-LG-2/3 (history and [revision 3](../loop-graph-compatibility-2026-10-09/ADR-D-LG-3-REVISION-3.md))
and doc 57 §17. Compatibility is priority 2: it never weakens a safety invariant.

## 1. Inventory

Maintain a machine-readable API/version matrix covering modules, symbols, signatures,
type identity, config propagation, synchronous/asynchronous invocation, batch order,
streaming and callbacks, errors, serialization, graph topology and persistence. Include
loaders, retrieval, agents, integrations and provider APIs; Runnable and StateGraph alone
are not the inventory. Python and JS/TS are **separate** inventories, environments and
evidence: a Python pass establishes no JS parity.

Cell status is one of `implemented`, `policy-refused`, `technically-unsupported` or
`not-yet-implemented`. Only executed semantic conformance earns `implemented`. Count
missing, skipped and refusal cells separately. Publish no global "drop-in percentage"
from selected oracle passes. Keep the target broad while publishing truthful cohorts.
Every unimplemented cell records its owner and next gate.

Historical oracle versions (LangGraph 1.0.3, LangChain Core 1.0.7, Pydantic AI slim
1.0.18) are evidence, not an automatic choice of new targets. T0 pins new targets after
review.

## 2. Three explicit modes

| Mode | Meaning |
| --- | --- |
| Native API | Oramasys/Core API with no upstream package |
| Real-framework interoperability | Optional explicit, lazy, allowlisted imports of the real package |
| Isolated replacement | Unchanged upstream import paths, only inside a declared isolated environment |

Replacement refuses mixed or cached namespace ownership. It never replaces `sys.modules`
mid-run and never falsifies upstream distribution or version metadata. No default or
published-extra dependency on LangChain, LangGraph or Pydantic AI exists; real-framework
oracles are isolated test dependencies. Export under LangGraph's scheduler is interop
evidence, not proof that native Core replaces its semantics.

## 3. Required semantics

| Surface | Qualification required |
| --- | --- |
| LC Runnable/LCEL | Type identity where public behaviour needs it; sync/async/config/callback propagation; ordered batch and streaming |
| LG builders/routes | START/END, Command routing, dynamic Send, subgraphs/nesting, state and reducer behaviour via neutral Core mechanics |
| LG interrupts/resume | Stable interrupt identity, thread/config handling, node re-entry semantics, persistence, safe effects |
| Persistence/wire formats | Explicit serializers and version migrations; upstream saver/store contracts inventoried separately |
| Integrations/providers | Provider API/error/streaming contracts plus qualified transport and effects |
| Python / JS | Separate inventories, environments, evidence |

Upstream interrupts may **re-enter node code**. A compatible facade preserves the
observable contract for qualified pure cases and requires effect wrappers, or refuses
unsafe re-entry, for writes. A blanket ban or silent dedupe is not parity. R3's
name-ordered settlement is not every upstream parallelism semantic and must not be
advertised as one; add a reviewed execution-semantics version where needed.

Known gaps stay tracked: fan-out export is refused; dynamic Send, nesting, upstream
Runnable identity, some config, unbuffered synchronous streams, checkpoint wire parity and
durable continuation are not established by historical oracle passes.

## 4. Tiered import diagnostics

| Situation | Behaviour |
| --- | --- |
| Whole module unsupported | `ModuleNotFoundError` subtype with correct `.name` and actionable detail |
| Symbol unsupported via `__getattr__` | `AttributeError` subtype so `hasattr` and `getattr(default)` work |
| `from m import X` | May surface Python's generic `ImportError`; `explain()` supplies the richer gap record |
| Broken transitive dependency | Propagate the real exception; never relabel as a missing optional framework |

Static lint evaluates conservative literals, concatenation and literal-only f-strings.
Unresolved dynamic import arguments need explicit review. Runtime tripwires block eager
imports; lazy calls are checked statically too. Require exact `TYPE_CHECKING` branches and
reject stale allowlist entries. Test finder-returning-None, module errors and pytest
`importorskip`. Required oracle cells **fail** rather than skip when an environment is
missing.

## 5. Sequencing

Pure facade primitives first, then Runnable, config, callback and stream contracts. Effectful
and recovery cells wait for the HITL, transport and continuation slices. For Command, Send,
nesting and checkpoint parity, specify any missing neutral mechanics and an execution
version first; R3 fan-out does not already supply them. Compare normalized state, event and
error traces, input-order batch results and real streaming/cancel behaviour; serial
batching is a control, not proof of order invariance.

## 6. Acceptance tests

Matrix runner fails for missing required cells, silent skips, unsupported versions, stale
artifacts and incomplete inventories. Namespace, type, pickle, metadata and subprocess
identity checks. Cached-import refusal. Per-cohort implemented/refused/unsupported counts
with drift tests and rollback compatibility.
