<!-- lint-ignore LINT-013 -->
# 01 — Kernel Spec (perpetua-core, v2.0 blocking)

> **Repository standard:** everything executable lives under `/src`; no root-level
> `scripts`/`tests`/`tools`/`examples`; data output and produced binaries stay
> `.gitignore`d, never committed with secrets, personal paths, or SecOps material.
> Additive — see [`46-repository-standard.md`](46-repository-standard.md).
> The only **blocking** spec for v2.0. Everything else (modules) ships at its own pace.
> **Revised D8 (2026-04-30)**: MiniGraph kernel = ~70 lines (essential services only).
> Tier-3 features (checkpointer, interrupts, subgraphs, tool, streaming, structured output)
> ship as **graph plugins** under `src/perpetua_core/graph/plugins/`, loaded on demand.
> Cold kernel has zero optional dependencies.

---

## Repo layout (`perpetua-core/`)

> **2026-08-27 correction:** this tree previously placed `perpetua_core/`
> and `tests/` as repo-root siblings, directly violating
> [`46-repository-standard.md`](46-repository-standard.md)'s "everything
> executable belongs under `/src`; no root-level `scripts`/`tests`/`tools`/
> `examples`" rule -- doc 46's own "why this is additive, not a conflict"
> section claimed this tree already complied, which was incorrect on
> direct comparison. Corrected below; every path reference in the rest of
> this document was updated to match, not just this diagram.
>
> **Packaging note, so this isn't a silent trap:** an `src`-layout package
> is not auto-discovered by `pip install -e .` without explicit
> configuration. `pyproject.toml` needs either
> `[tool.setuptools.packages.find] where = ["src"]` (setuptools) or the
> equivalent for whatever build backend is actually in use --
> confirm which one before implementing, this doc does not show the
> `[build-system]` table. Acceptance criterion 1 below
> (`python -c "import perpetua_core; ..."`) will fail with a bare
> `ModuleNotFoundError` if this step is skipped, not with an obviously
> layout-related error.

```text
perpetua-core/
├── pyproject.toml            # MIT license, deps: pydantic>=2, openai, pyyaml, aiosqlite
├── LICENSE                   # MIT
├── README.md
└── src/
    ├── perpetua_core/
    │   ├── __init__.py
    │   ├── state.py              # PerpetuaState (Pydantic v2)
    │   ├── message.py            # Message + role enums
    │   ├── llm.py                # LLMClient (async OpenAI-compat)
    │   ├── policy.py             # HardwarePolicyResolver + HardwareAffinityError
    │   ├── gossip.py             # GossipBus (SQLite event log)
    │   ├── graph/
    │   │   ├── __init__.py
    │   │   ├── engine.py         # MiniGraph core
    │   │   ├── nodes.py          # Node base + ToolNode
    │   │   ├── edges.py          # Edge + conditional edge router
    │   │   ├── checkpointer.py   # SQLite checkpointer (resumability)
    │   │   ├── interrupts.py     # HITL pause/resume
    │   │   ├── subgraphs.py      # Subgraph composition
    │   │   ├── streaming.py      # AsyncGenerator over node + state events
    │   │   └── tool.py           # @tool decorator (Pydantic v2 schema autogen)
    │   └── config/
    │       └── model_hardware_policy.example.yml
    └── tests/
        ├── test_state.py
        ├── test_policy.py
        ├── test_minigraph.py           # kernel in isolation — no plugins
        ├── test_plugins_checkpointer.py
        ├── test_plugins_interrupts.py
        ├── test_plugins_tool.py
        └── test_plugins_structured_output.py
```

**Kernel target: ~70 lines** (`graph/engine.py` only — START/END, node registry, edge routing, `ainvoke`).
**Plugin target: ~30–50 lines each** — loaded via `MiniGraph.use(plugin)`, never in engine imports.
Cold `MiniGraph()` with no plugins: pure Python, zero optional deps.

---

## 1. `PerpetuaState` (Pydantic v2)

```python
# src/perpetua_core/state.py
from __future__ import annotations
import copy
from typing import Any, Literal
from pydantic import BaseModel, Field

HardwareTier = Literal["mac", "windows", "shared"]
TaskType     = Literal["coding", "reasoning", "research", "ops"]
OptHint      = Literal["speed", "quality", "reasoning"]

class PerpetuaState(BaseModel):
    session_id: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    scratchpad: dict[str, Any]    = Field(default_factory=dict)
    status: Literal["idle", "running", "interrupted", "conflicted", "error", "done"] = "idle"
    error: str | None = None

    # Grok additions
    nodes_visited: list[str]    = Field(default_factory=list)
    metadata: dict[str, Any]    = Field(default_factory=dict)
    retry_count: int            = 0

    # routing hints
    target_tier: HardwareTier   = "shared"
    task_type: TaskType         = "reasoning"
    opt_hint: OptHint           = "quality"
    model_hint: str | None      = None

    def merge(self, delta: dict[str, Any]) -> "PerpetuaState":
        """Apply a node's output delta. Engine calls this per step.
        Both deep=True AND deepcopy(delta) are load-bearing, not
        defensive -- they close two DIFFERENT leaks, verified
        separately, not redundant with each other.

        deep=True alone: model_copy's default is shallow, so any
        nested mutable field NOT present in `delta` (scratchpad,
        messages, metadata, nodes_visited) would be the same dict/list
        object in both the old and new state. Verified: without
        deep=True, mutating the new state's scratchpad in place also
        corrupts the prior state's scratchpad through the shared
        reference.

        deepcopy(delta) additionally: deep=True deep-copies the
        EXISTING model's fields, then applies update=delta AFTERWARD
        -- the delta's own values are used as-is, not deep-copied. A
        caller passing a mutable object they still hold a reference to
        (not a fresh literal/spread) still aliases without this.
        Verified directly: `merge({"scratchpad": shared_dict})` then
        mutating the caller's own `shared_dict` afterward still leaked
        into the new state without wrapping delta in deepcopy() first
        -- found via the real oramasys/perpetua-core PR #1's own
        second review round, not caught by this repo's earlier
        deep=True-only fix."""
        return self.model_copy(update=copy.deepcopy(delta), deep=True)
```

Field rationale:

- `messages`/`scratchpad` — distinct: messages = chat-shaped LLM I/O;
  scratchpad = node-internal working memory
- `nodes_visited` — auditable graph traversal; GossipBus cross-reference key
  (Grok + Rule 4)
- `metadata` — extensible without schema bumps; `metadata["authorized_by"]`
  records human actor ID when an `Interrupt` is resolved via `aresume`
  (Grok + Rule 2)
- `retry_count` — first-class; reducers increment on retry (Grok)
- routing hints — kept on state so middle-of-graph routing decisions can read
  them
- `status="conflicted"` — terminal-until-human state raised when two or more
  guidelines conflict; treated identically to `"interrupted"` by the engine;
  cleared only by `aresume(conflict_resolution=...)` (Rule 5)

---

## 2. `LLMClient`

```python
# src/perpetua_core/llm.py
import os
from openai import AsyncOpenAI

DEFAULT_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
DEFAULT_API_KEY  = os.getenv("LLM_API_KEY", "ollama")

class LLMClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat(self, *, model: str, messages: list[dict], **kwargs):
        return await self._client.chat.completions.create(model=model, messages=messages, **kwargs)
```

**LAN endpoints** (from user memory, verified `routing.json` distributed=true):

- Mac LM Studio: `http://192.168.x.110:1234/v1`
- Windows LM Studio: `http://192.168.x.108:1234/v1`
- Local fallback: `http://localhost:11434/v1` (Ollama)

LAN routing belongs to the policy + graph layer, not the LLMClient itself. The client is a dumb dispatcher.

---

## 3. `HardwarePolicyResolver`

```python
# src/perpetua_core/policy.py
from typing import Literal
import yaml
from pathlib import Path

class HardwareAffinityError(RuntimeError):
    """Pre-spawn hardware affinity gate failure. Re-exported from v1."""

Verdict = Literal["ALLOW", "PREFER", "NEVER"]

class HardwarePolicyResolver:
    def __init__(self, policy_path: Path):
        self._policy = yaml.safe_load(policy_path.read_text())

    def check_affinity(self, *, model: str, target_tier: str) -> Verdict:
        rule = self._policy["models"].get(model)
        if rule is None:
            return "ALLOW"  # unknown models are unconstrained
        verdict = rule.get(target_tier, "ALLOW")
        if verdict == "NEVER":
            raise HardwareAffinityError(f"{model} forbidden on {target_tier}")
        return verdict
```

**`model_hardware_policy.example.yml`:**

```yaml
# src/perpetua_core/config/model_hardware_policy.example.yml
version: 1
models:
  Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-v2:
    mac: NEVER
    windows: PREFER       # 24GB VRAM RTX 3080 — fits
    shared: ALLOW
  qwen3-coder:14b:
    # known-bad ID from v1 hallucination — explicitly NEVER on all tiers
    mac: NEVER
    windows: NEVER
    shared: NEVER
  llama-3.2-3B:
    mac: PREFER
    windows: ALLOW
    shared: ALLOW
```

Carries forward the `HardwareAffinityError` re-export pattern canonicalized in
`2026-04-28-perpetua-orama-master-revamp.md` Task 4.

---

## 4. `MiniGraph` engine — 70-line kernel + plugin system

State machine: nodes (callables that return state deltas), edges (router fns),
start/end. API-compatible with the LangGraph mental model so a future migration
to real LangGraph remains cheap. **Tier-3 features ship as plugins**, never
embedded in `engine.py`.

### 4a. Core engine (`graph/engine.py`)

> **2026-08-27 update:** superseded by
> [`57-minigraph-final-reconciliation.md`](57-minigraph-final-reconciliation.md)
> and
> [`58-minigraph-observer-pattern-library-reconciliation.md`](58-minigraph-observer-pattern-library-reconciliation.md),
> the canonical architecture records — read those first for the
> authoritative rules; this section is kept in sync with them, not the
> other way around. **Second update, same date:** the scheduler is now
> `_run()`, not `asteps()` — doc 58 established that `asteps()` alone
> is a sanitized, control-only projection (no state, no delta) and
> cannot serve as a plugin fan-out source; a `Checkpointer` needs the
> real delta, which sanitized events never carried. Verified directly
> before rewriting: the fan-out sample two sections below previously
> passed a hardcoded `{}` in place of the real delta because `asteps()`
> genuinely had no delta to give it. Fixed by introducing
> `GraphObservation` (rich: event + state + delta) as what `_run()`
> actually yields, with `aobserve()` exposing it to trusted in-process
> consumers and `asteps()` now a thin projection that strips it down to
> sanitized `GraphEvent` for streaming/API/UI.

```python
# src/perpetua_core/graph/engine.py
import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, Union
from ..state import PerpetuaState

START = "__start__"
END = "__end__"

NodeFn = Callable[[PerpetuaState], Union[dict, Awaitable[dict]]]
EdgeFn = Callable[[PerpetuaState], str]  # returns next node name

class MaxStepsExceeded(RuntimeError):
    def __init__(self, steps: int, last_node: str) -> None:
        self.steps = steps          # completed node executions
        self.last_node = last_node  # most recently entered node
        super().__init__(f"max_steps exceeded at step {steps} (last_node={last_node!r})")

@dataclass(frozen=True)
class GraphEvent:
    """Sanitized, control-plane only. Safe for streaming/API/UI --
    excludes state and node deltas by design (§8)."""
    kind: str   # node.start/node.end/edge.selected/interrupt/done
    node: str
    steps: int

@dataclass(frozen=True)
class GraphObservation:
    """Rich, trusted, in-process record. Never crosses a process/API
    boundary. This is what `_run()` actually yields; GraphEvent is a
    projection over it, not the other way around."""
    event: GraphEvent
    state: PerpetuaState
    delta: dict | None = None

class CompiledGraph:
    """Detached topology snapshot; sole scheduler owner (§3, §8)."""

    def __init__(self, nodes: dict[str, NodeFn], edges: dict[str, EdgeFn | str], max_steps: int) -> None:
        self._nodes = dict(nodes)
        self._edges = dict(edges)
        self._max_steps = max_steps

    def _next(self, current: str, state: PerpetuaState) -> str:
        edge = self._edges.get(current, END)
        target = edge(state) if callable(edge) else edge
        if not isinstance(target, str) or not target:
            raise ValueError(f"edge from {current!r} resolved to invalid route: {target!r}")
        if target != END and target not in self._nodes:
            raise ValueError(f"edge from {current!r} resolved to unknown node: {target!r}")
        return target

    async def _run(self, state: PerpetuaState):
        """Sole scheduler. Yields rich GraphObservation records -- the
        one irreducible traversal truth every projection derives from.
        Never call this directly from plugin code; use aobserve() or
        asteps() below."""
        node = self._next(START, state)
        steps, last_node = 0, START
        while node != END:
            if steps >= self._max_steps:
                raise MaxStepsExceeded(steps, last_node)
            current = node
            yield GraphObservation(GraphEvent("node.start", current, steps), state)
            state = state.merge({"nodes_visited": [*state.nodes_visited, current]})
            last_node = current
            try:
                result = self._nodes[current](state)
                delta = await result if inspect.isawaitable(result) else result
            except Exception as exc:  # noqa: BLE001 -- duck-typed interrupt boundary (§7)
                if type(exc).__name__ == "Interrupt" and hasattr(exc, "prompt"):
                    state = state.merge({"status": "interrupted", "metadata": {
                        **state.metadata, "interrupt_prompt": exc.prompt,
                        "interrupt_payload": getattr(exc, "payload", None),
                        "interrupt_node": current,
                    }})
                    yield GraphObservation(GraphEvent("interrupt", current, steps), state)
                    return
                raise
            if not isinstance(delta, dict):
                raise TypeError(f"node {current!r} returned {type(delta).__name__}; expected dict delta")
            state = state.merge(delta)
            yield GraphObservation(GraphEvent("node.end", current, steps), state, delta)
            steps += 1
            node = self._next(current, state)
            yield GraphObservation(GraphEvent("edge.selected", current, steps), state)
        yield GraphObservation(GraphEvent("done", END, steps), state.merge({"status": "done"}))

    async def aobserve(self, state: PerpetuaState):
        """Rich projection over _run(). Trusted in-process consumers
        only -- checkpointer/tracer/audit/GraphPlugin dispatch (§7a).
        Carries real state and deltas; never expose this over a
        process/API boundary."""
        async for obs in self._run(state):
            yield obs

    async def asteps(self, state: PerpetuaState):
        """Sanitized projection over _run(). Safe for streaming/API/UI
        -- strips state and delta down to control-plane-only
        GraphEvent."""
        async for obs in self._run(state):
            yield obs.event

    async def ainvoke(self, state: PerpetuaState) -> PerpetuaState:
        final = state
        async for obs in self._run(state):
            final = obs.state
        return final

class MiniGraph:
    """Mutable topology builder, matching real LangGraph's own StateGraph
    idiom (verified against 8 independent real-world sources, not
    assumed): add_node/add_edge mutate self and return self, so the
    universal LangGraph pattern -- bare `builder.add_node(...)` calls
    in a loop or sequence, never reassigned -- works unmodified. A
    prior version of this class made add_node/add_edge return a NEW
    instance instead; that satisfied an abstract immutability review
    finding but was reverted (§3) after confirming it silently breaks
    every real LangGraph example checked: none of them capture the
    return value, so every add_node call would have been discarded.
    Immutability's correct boundary is compile() -- see §3."""

    def __init__(self, max_steps: int = 50) -> None:
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, EdgeFn | str] = {}
        self._max_steps = max_steps

    def add_node(self, name: str, fn: NodeFn) -> "MiniGraph":
        self._nodes[name] = fn
        return self

    def add_edge(self, src: str, dst: str | EdgeFn) -> "MiniGraph":
        self._edges[src] = dst
        return self

    def set_start(self, name: str) -> "MiniGraph":
        # START is a pseudo-node: its one edge points at the real entry
        # node, keeping entry resolution on the same lookup path as
        # every other transition.
        return self.add_edge(START, name)

    def compile(self) -> CompiledGraph:
        return CompiledGraph(self._nodes, self._edges, self._max_steps)

    async def ainvoke(self, state: PerpetuaState) -> PerpetuaState:
        return await self.compile().ainvoke(state)
```

### 4b. Conditional edges + state reducers — built into engine

`add_edge(src, fn)` where `fn(state) -> str` is the conditional router. State
merge happens in `state.merge()` — single delta-application path; reducers can be
added by subclassing `PerpetuaState` and overriding `merge()`.

### 4c. SQLite checkpointer (`graph/plugins/checkpointer.py`)

```python
# src/perpetua_core/graph/plugins/checkpointer.py
import aiosqlite, json
from ...state import PerpetuaState

class SqliteCheckpointer:
    def __init__(self, db_path: str):
        self._db_path = db_path

    async def save(self, state: PerpetuaState, *, node: str):
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO checkpoints (session_id, node, state_json) VALUES (?, ?, ?)",
                (state.session_id, node, state.model_dump_json()),
            )
            await db.commit()

    async def load_latest(self, session_id: str) -> PerpetuaState | None:
        async with aiosqlite.connect(self._db_path) as db:
            row = await (await db.execute(
                "SELECT state_json FROM checkpoints WHERE session_id=? ORDER BY id DESC LIMIT 1",
                (session_id,),
            )).fetchone()
            return PerpetuaState.model_validate_json(row[0]) if row else None
```

Engine plumbing (in `engine.py`) accepts `checkpointer=...`; if set, persists after each node.

### 4d. HITL interrupts (`graph/plugins/interrupts.py`)

```python
# src/perpetua_core/graph/plugins/interrupts.py
class Interrupt(Exception):
    """Raised by a node to pause graph execution and surface a HITL prompt."""
    def __init__(self, prompt: str, payload: dict | None = None):
        self.prompt  = prompt
        self.payload = payload or {}
```

Engine catches `Interrupt`, sets `state.status = "interrupted"`, persists via
checkpointer, returns. Caller resumes by calling
`graph.aresume(session_id, user_response=...)` which loads checkpoint and
re-enters at the interrupting node.

MAESTRO 7-layer enforcement (v2.5) will use this primitive heavily for human-checkpoint gates.

### 4e. Subgraphs (`graph/plugins/subgraphs.py`)

A subgraph is just a `MiniGraph` exposed as a single node:

```python
# src/perpetua_core/graph/plugins/subgraphs.py
from ..engine import MiniGraph
from ...state import PerpetuaState

def as_node(subgraph: MiniGraph):
    async def node(state: PerpetuaState) -> dict:
        result = await subgraph.ainvoke(state)
        return result.model_dump()
    return node
```

Critical for microkernel modularity — each non-kernel module ships as a subgraph
that the kernel can compose.

### 4f. ToolNode contract (`graph/plugins/nodes.py`)

```python
# src/perpetua_core/graph/plugins/nodes.py
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from ...state import PerpetuaState

class ToolNode:
    """Subprocess CLI as a graph node. Used for Claude Code, Codex CLI, shell tools."""
    def __init__(self, cmd: list[str]):
        self._cmd = cmd

    async def __call__(self, state: PerpetuaState) -> dict:
        proc = await create_subprocess_exec(*self._cmd, stdout=PIPE, stderr=PIPE)
        out, err = await proc.communicate()
        return {
            "scratchpad": {**state.scratchpad, "tool_stdout": out.decode(), "tool_stderr": err.decode()},
            "metadata":   {**state.metadata,   "tool_exit": proc.returncode},
        }
```

API-compatible with LangGraph's ToolNode contract — same call shape so external
frameworks (post-D5 Plugin API) can hand us tools they constructed for
LangGraph.

### 4g. Streaming (`graph/plugins/streaming.py`)

```python
# src/perpetua_core/graph/plugins/streaming.py
from typing import AsyncGenerator
from ...state import PerpetuaState

# Yields ("node", node_name, delta) and ("token", token_str) events.
StreamEvent = tuple[str, str, dict] | tuple[str, str]

async def astream(graph, state: PerpetuaState) -> AsyncGenerator[StreamEvent, None]:
    """Wraps ainvoke; yields per-node deltas. Token-level streaming
    is enabled at the LLMClient layer (OpenAI streaming API)."""
    ...  # implementation in Phase 2
```

### 4h. `@tool` decorator (`graph/plugins/tool.py`)

```python
# src/perpetua_core/graph/plugins/tool.py
import inspect
from pydantic import create_model

def tool(fn):
    """Decorate a typed function; auto-derives a Pydantic v2 input schema."""
    sig = inspect.signature(fn)
    fields = {
        name: (param.annotation, ... if param.default is inspect.Parameter.empty else param.default)
        for name, param in sig.parameters.items()
    }
    InputModel = create_model(f"{fn.__name__}Input", **fields)
    fn._input_schema = InputModel
    fn._tool_name    = fn.__name__
    return fn
```

Mirrors Pydantic AI Slim's `@tool` ergonomics but emits plain Pydantic v2 — no
`pydantic-ai` runtime dep.

### 4i. Structured output validation

Implemented at `LLMClient.chat_structured(model, messages, output_schema:
type[BaseModel])` — calls LLM, validates against schema, retries with the schema
appended to the prompt on parse failure (max retries from env). Increments
`state.retry_count`.

---

## 5. `GossipBus` (SQLite event log)

```python
# src/perpetua_core/gossip.py
import aiosqlite, json, time
from typing import Literal

EventType = Literal["load", "route", "affinity_check", "dispatch", "error"]

class GossipBus:
    def __init__(self, db_path: str):
        self._db_path = db_path

    async def emit(self, event_type: EventType, payload: dict):
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO gossip (ts, event_type, payload_json) VALUES (?, ?, ?)",
                (time.time(), event_type, json.dumps(payload)),
            )
            await db.commit()

    async def subscribe(self, *, since: float = 0.0):
        # async-iterator of events newer than `since` — long-poll pattern
        ...
```

Replaces volatile `.json` blobs from v1 with a durable, queryable audit trail.
Shares the same SQLite database file as the checkpointer (`perpetua_core.db` by
default).

**Mesh federation (v2.1+, non-kernel):** Local `GossipBus` stays the source of
truth per particle. Cooperating orama / PT / perpetua-core instances may exchange
**frugal tail deltas** over LAN mesh (and optionally BLE later) without replacing
SQLite or adding Redis. See
[`43-gossipbus-mesh-transport.md`](43-gossipbus-mesh-transport.md).

---

## 6. FastAPI glass-window (lives in `oramasys`, depicted here for completeness)

```python
# oramasys/api/server.py — handlers ≤ 10 lines
from fastapi import FastAPI
from oramasys.graphs import perpetua_graph
from oramasys.api.contracts import RunRequest, RunResponse

app = FastAPI(title="oramasys")

@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    state  = req.to_state()
    result = await perpetua_graph.ainvoke(state)
    return RunResponse.from_state(result)
```

Lifted/skeletonized from today's `orama-system/api_server.py` per D9.
Internal-only contract for v2.0 (D5).

Security requirement: every non-health handler must declare a route capability
(`public`, `read`, `mutate`, `lifecycle`, `dangerous-worker`, etc.) and pass
through shared auth/capability middleware before reaching graph code. OWASP ASVS
V4 requires access control rules to be enforced on trusted server-side code and
the principle of least privilege; v2 implements that as route metadata, not UI
visibility or client-controlled booleans.

---

## 6b. Kernel-adjacent security contracts

These contracts are not optional modules; they are platform primitives consumed
by the kernel, graph plugins, API layer, and PT adapter boundary:

| Contract | Required shape |
| --- | --- |
| `Capability` enum | `public`, `read`, `mutate`, `lifecycle`, `file-read`, `file-write`, `model-egress`, `dangerous-worker`, `admin` |
| `AuthContext` | actor id, auth method, scopes/capabilities, source address, correlation id |
| `SecurityDecision` | allow/deny, required capability, reason, redaction class, audit event id |
| `EndpointPolicy` | scheme/host/port allowlist, redirect policy, host pinning, public-endpoint opt-in |
| `AuditEvent` | append-only event with actor, capability, target, decision, correlation id, redacted metadata |

The contracts implement the design gates in
[`24-security-first-platform.md`](24-security-first-platform.md) and keep
security behavior testable before any non-kernel module ships.

---

## Verification (kernel acceptance criteria)

1. `python -c "import perpetua_core; perpetua_core.MiniGraph()"` succeeds — no
   circular imports, no missing deps.
2. `pytest src/tests/test_state.py` — Pydantic v2 round-trip + `merge()` delta
   application.
3. `pytest src/tests/test_policy.py` — `check_affinity()` raises
   `HardwareAffinityError` for NEVER tiers.
4. `pytest src/tests/test_minigraph.py` — 3-node graph (start → middle → end)
   runs end-to-end with state delta merging and `nodes_visited` populated.
5. **Future gate, not current** —
   `pytest src/tests/test_plugins_checkpointer.py`: save then load
   reproduces identical state. Deferred per
   [`57-minigraph-final-reconciliation.md`](57-minigraph-final-reconciliation.md)
   §11/§15 ("checkpoint lineage and durable resume"); not a current gate.
6. `pytest src/tests/test_plugins_interrupts.py` — node raises
   `Interrupt`, graph status becomes `"interrupted"` (current, structural
   recognition only). **Future gate, not current:**
   checkpoint-saved-and-`aresume`-continues-correctly is durable resume,
   deferred alongside item 5.
7. `pytest src/tests/test_plugins_tool.py` — `@tool`-decorated function
   exposes correct `_input_schema` Pydantic model.
8. `pytest src/tests/test_plugins_structured_output.py` —
   `chat_structured()` retries on parse failure and increments
   `retry_count`.
9. **Import boundary lint**: `grep -r "from oramasys" perpetua-core/` returns
   nothing. (CI gate.)
10. Live integration: graph node calls Mac LM Studio (`192.168.x.110:1234`) and
    Windows LM Studio (`192.168.x.108:1234`) per `model_hardware_policy.yml`
    routing; `agent_log` table in SQLite shows correct dispatch sequence.
11. **Idempotent filesystem helpers** (mandatory for every plugin that touches the
    fs): every helper ships with the 4/5-state guard test from
    `11-idempotency-and-guard-patterns.md` §2. No fs helper is accepted in
    `src/perpetua_core/graph/plugins/` without passing
    `test_ensure_symlink_all_four_states_idempotent` (or equivalent for its op
    type). (CI gate.)
12. **Validator agreement** (mandatory when two or more modules enforce the same
    allowlist): `test_validators_agree_on_*` CI gate — every shared
    allowlist/denylist must live in `src/perpetua_core/config/` and both bash and
    python validators must read from it. See
    `11-idempotency-and-guard-patterns.md` §3. (CI gate.)
13. **HITL interrupt is always-escapable (Rule 3)**:
    `pytest src/tests/test_plugins_interrupts.py::test_interrupt_not_suppressible_by_node`
    — any node that internally catches `Interrupt` and does not re-raise causes
    this test to fail (current, testable now). **Future gate, not current:**
    `status="interrupted"`/`"conflicted"` can only be cleared by `aresume()`
    assumes durable resume, deferred alongside items 5-6 above.
14. **GossipBus is append-only (Rule 4)**:
    `pytest src/tests/test_gossip.py::test_no_delete_or_update` — `GossipBus`
    exposes no `delete`, `update`, or `truncate` method. All events are permanent.
    Test queries the event count before and after a deliberately invalid operation
    and asserts no rows were removed.
15. **Authorization event emitted before ToolNode subprocess (Rule 2)**:
    `pytest src/tests/test_tool_node.py::test_authorization_event_precedes_subprocess`
    — GossipBus receives an `authorization` event with non-empty `actor_id` and
    `tool_cmd` fields before any process is spawned. Test uses a mock bus and
    asserts event ordering.
16. **Route capability manifest complete**: every non-health FastAPI route has a
    declared capability and test coverage for unauthenticated denial where
    capability is not `public`.
17. **No bearer-in-HTML invariant**: UI/bootstrap tests assert no raw
    control-plane token appears in rendered HTML, JSON bootstrap blobs, logs, or
    frontend bundles.
18. **Endpoint egress policy**: model probes use an unprivileged client, strip
    control-plane auth headers, reject unknown/public hosts by default, and pin
    or require approval before persistence.
19. **Security event redaction**: audit tests include fake API keys, bearer tokens,
    prompts, and raw transcripts and assert stored/logged events contain only
    redacted metadata.

---

## 7. Gemini Hardening Updates (2026-05-02)

### 7a. GraphPlugin Protocol

> **2026-08-27 update — provenance fully resolved, synthesis corrected.**
> Earlier note here treated this Protocol as superseded/historical.
> That was too dismissive of real groundwork; corrected below.
>
> **Provenance, traced to primary sources, not speculated:**
> [`05-feasibility-review.md`](05-feasibility-review.md) (2026-05-01)
> first named these exact method signatures, recommending them
> specifically so the `SqliteCheckpointer` and `HITL Interrupts`
> plugins would have "documented hooks... rather than monkey-patching
> the `ainvoke` loop" — a named leaky-abstraction concern, not an
> arbitrary choice.
> [`08-technical-architecture-review.md`](08-technical-architecture-review.md)
> (2026-05-02, titled "Gemini-Analyzer" — an explicit label naming the
> AI collaborator used, not informal attribution) implements that
> recommendation near-verbatim in its own §F1, explicitly framed as
> *differentiating* from LangGraph/CrewAI's own patterns, not copying
> either. An earlier hypothesis here (LangChain `BaseCallbackHandler`
> as the model) is not supported by the primary source and is retracted.
>
> **The real gap this Protocol correctly anticipated:** `asteps()` is a
> single-consumer, pull-based async generator. `ainvoke()` already
> drains it internally. Verified directly: two tasks racing over the
> same async generator via `asyncio.gather` show one consumer silently
> starving the other, with no error raised. If the Checkpointer AND
> Interrupts AND a future tracer all need to observe one `ainvoke()`
> call, a bare `asteps()` drain cannot support that without real
> additional plumbing — exactly the multi-consumer need `GraphPlugin`
> was designed for.
>
> **Synthesis, verified working, not just proposed — second correction,
> same date:** the first version of this fix drained `asteps()` and
> passed a hardcoded `{}` in place of the real delta, because
> `asteps()`'s sanitized `GraphEvent` genuinely carries no delta at
> all. Fixed: the dispatcher now drains `aobserve()` — the rich
> `GraphObservation` projection §4a defines — exactly once, and fans
> out to every registered `GraphPlugin` listener with the real state
> and delta:
>
> ```python
> # plugin-layer, not engine.py -- consumes aobserve(), never reimplements it
> async def run_with_plugins(compiled_graph, state, plugins: list[GraphPlugin]):
>     async for obs in compiled_graph.aobserve(state):
>         for p in plugins:
>             if obs.event.kind == "node.start":
>                 p.on_node_start(obs.state, obs.event.node)
>             elif obs.event.kind == "node.end":
>                 p.on_node_end(obs.state, obs.event.node, obs.delta)
> ```
>
> Verified directly: a `Checkpointer` plugin now genuinely receives the
> node's real output delta (e.g. `{"scratchpad": {"real_value": 42}}`)
> instead of an empty dict, while a `Tracer` plugin observes the exact
> same run without racing or starving the checkpointer — both drained
> from one `aobserve()` pass. `asteps()` stays the sanitized surface
> for streaming/API/UI, unaffected by this fix.
>
> This keeps `GraphPlugin` as a real, live consumer-facing interface —
> not historical content — while keeping the kernel's one-scheduler
> invariant intact (`_run()` remains the sole scheduler; `aobserve()`
> and `asteps()` are both projections over it, never duplicate
> traversal logic). Both pieces of groundwork preserved, neither a
> casualty of the other.

To ensure architectural integrity, all Tier-3 plugins MUST implement the following Protocol:

```python
class GraphPlugin(Protocol):
    def on_node_start(self, state: PerpetuaState, node_name: str) -> None: ...
    def on_node_end(self, state: PerpetuaState, node_name: str, delta: dict) -> None: ...
```

### 7b. Infinite Loop Guard

The `MiniGraph.ainvoke` loop MUST enforce a `max_steps` limit (default: 50) to
prevent runaway processes and billing spikes.

### 7c. High-Performance GossipBus

The `GossipBus.emit()` method MUST be non-blocking. Implementation should use an
`asyncio.Queue` with a background worker that performs batched SQLite commits every
500ms.
