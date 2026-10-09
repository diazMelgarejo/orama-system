---
title: "ADR draft D-LG-3 — Replacement compatibility through explicit name ownership"
date: 2026-10-09
status: "DRAFT — proposed for orama-system docs/v2 (next free number, 71 at main b131215; check for collisions). Not ratified. Code target: oramasys/oramasys."
decision_owner: "human operator"
supersedes: "nothing; extends the 2026-10-09 compatibility-convergence plan and D-LG-2 (errata applied)"
related: ["docs/v2/57 §17", "docs/v2/59", "docs/v2/62", "docs/v2/32 §5", "docs/v2/47", "docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md", "convergence plan 2026-10-09"]
---

# D-LG-3 — Replacement compatibility through explicit name ownership

Evidence labels: **[V]** verified by reading or running on 2026-10-09; **[D]** canonical docs/v2; **[U]** user decision; **[P]** this proposal; **[X]** external behaviour not verified here.

## 1. Decision being designed [U]

Replacement compatibility is **in scope now**: unchanged code that does
`import langgraph …` runs on the oramasys stack. Also required:
- interoperability with real LangChain, LangGraph and Pydantic AI objects;
- no framework dependency in any of our packages;
- no kernel growth;
- parity is best-effort and subordinate to every hardware, authorization and egress rule.

## 2. Fixed constraints this design must not break

| Constraint | Source |
|---|---|
| One scheduler (`CompiledGraph._run()`); compatibility lives outside `engine.py` | [D 57 §17c, 59 §5] |
| No eager or required framework import; intentional lazy bridges allowed | [D convergence plan; V Core `LangGraphExporter`] |
| Never publish a distribution under an upstream name; never edit installed framework files; no global monkeypatch on detection | [D convergence plan] |
| Detection may select a bridge, never a replacement scheduler; replacement needs an explicit act | [D convergence plan] |
| Do not ship a partial `interrupt()` that only raises; do not claim `Command.goto` before a tested route hook | [D 57 §17a] |
| Endpoint security belongs to Telos, admission to Phylax | [D 62] |
| Core's two existing adapters stay in Core; new work goes in oramasys | [U] |

## 3. The core idea: one implementation, three layers, one owner per name

Replacement is **not a second implementation**. It is the namespace
implementation plus a name binding.

```text
                 unchanged caller code
                 import langgraph.graph
                          |
     L2  name binding  (explicit activation only)
         maps upstream module names -> native modules
                          |
     L1  native facade   orama.compat.native.langgraph.*
         StateGraph / START / END / add_conditional_edges ...
         compiles to GraphSpec -> MiniGraph -> CompiledGraph
                          |
     L0  perpetua-core   one scheduler, observations, adapters (unchanged)

     L3  bridges (lazy, caller-installed frameworks only)
         real Runnable <-> native node, real compiled graph as opaque node,
         Pydantic AI Agent as node
```

**The ownership rule.** In one process, each upstream top-level name has
exactly one owner, either `upstream` or `orama`. This is decided once, at
activation, then frozen and recorded. Python can bind a module name to only one
module, so making ownership explicit removes the whole class of "which
`langgraph` did I get?" conflicts. [P]

## 4. Profiles

| Profile | `langgraph` | `langchain_core` | `pydantic_ai` | Activation |
|---|---|---|---|---|
| **P0 native** (default) | upstream if installed | upstream if installed | upstream if installed | none; our namespace only |
| **P1 interop** | upstream | upstream | upstream | automatic, lazily, when a caller passes a real framework object to a bridge |
| **P2 replace-graph** (recommended first replacement target) | **orama** | upstream (caller-installed) or native minimal | upstream | explicit only |
| **P3 replace-all** | **orama** | **orama** | upstream | explicit only; gated, see §8 |

Pydantic AI is **never aliased**: it is bridge-only, which matches "patterns,
never runtime" [D reconciliation 2026-08-27; U].

### Why P2 first [P]

P2 shadows a single name. Everything else the application uses — messages,
prompts, tools, callbacks — stays genuine upstream code that the caller
installed.

When `langchain_core` is present, the facade's compiled graph is a **real
`langchain_core` Runnable subclass**, built lazily inside the bridge. Pipes in
both directions, `with_config`, `batch`, and the callback-driven streaming and
event machinery then come from upstream itself rather than a reimplementation.
That gives the most fidelity for the least code. [X — verify per matrix release
that upstream's generic `astream_events` is driven by callbacks we emit.]

When `langchain_core` is absent, the facade falls back to Core's existing
duck-typed Runnable shape. The shared fixtures must pass on both paths, and
fixtures that need upstream types are marked as such.

P3 means re-implementing `langchain_core` itself: messages, prompts, tools,
callbacks and tracing. That is an order of magnitude larger. It stays designed
but gated until the P2 matrix shows the approach holds.

## 5. Name binding mechanism (L2)

Sketch only. **Prototype check, 2026-10-09 [V]:** a ~40-line throwaway prototype, run against a *fake* package (not real LangGraph), confirmed four things:
- aliased and native names resolve to the same module object, so class identity holds;
- package submodule imports work;
- an unsupported submodule raises `CompatGapError`, and `except ImportError` catches it;
- a custom `find_distributions()` makes `importlib.metadata.version()` return `1.0.3+orama.1`, which `packaging` matches against `==1.0.3`, `>=1.0` and `<1.0.4`; late activation is refused.

Everything else below still needs its own test.

```python
# orama/compat/alias.py — sketch [P]
import importlib, importlib.abc, importlib.util, sys

class AliasFinder(importlib.abc.MetaPathFinder):
    """Serves upstream module names from native modules, for owned prefixes only."""
    def __init__(self, owned: dict[str, str]):          # {"langgraph": "orama.compat.native.langgraph"}
        self._owned = owned
    def find_spec(self, fullname, path=None, target=None):
        for upstream, native in self._owned.items():
            if fullname == upstream or fullname.startswith(upstream + "."):
                native_name = native + fullname[len(upstream):]
                if importlib.util.find_spec(native_name) is None:
                    raise CompatGapError(fullname)        # unsupported module: loud, ImportError subclass
                return importlib.util.spec_from_loader(
                    fullname, _AliasLoader(native_name),
                    is_package=native_name in _PACKAGES)  # packages keep submodule import working
        return None

class CompatGapError(ImportError):
    """Not provided under this profile. Names the release-matrix row and its status."""
```

Rules:

1. **Explicit activation only.** Either `python -m orama.compat run --profile replace-graph app.py`, or `orama.compat.activate("replace-graph")` called before any upstream import (for example in a test `conftest`). There is no `.pth`, no `sitecustomize`, and no activation by environment variable. Implicit global activation is a known abuse path, and it would silently change semantics.
2. **Fail fast on late activation.** If an owned name is already in `sys.modules` from another origin, refuse. A process cannot change owners mid-flight.
3. **Fail fast on shadowing.** If the real distribution is installed in the same environment and a profile would shadow it, refuse by default. `--shadow-installed` allows it explicitly, and the choice is recorded. That keeps "two langgraphs" from ever happening by accident.
4. **Same module object.** The aliased name and the native name resolve to the *same* module object, so class identity and `isinstance` hold.
5. **Gaps are `ImportError` subclasses.** `CompatGapError` names the matrix row: supported, partial, or blocked-on-R3/R4. Libraries that already write `try: from langgraph.types import Send / except ImportError:` degrade correctly. Blocked symbols are absent rather than present-but-raising, which honours doc 57 §17a for `interrupt()`. [P]
6. **Distribution metadata.** The same finder may provide a `find_distributions()` entry, so `importlib.metadata.version("langgraph")` answers. It reports the target matrix release with a PEP 440 local label, for example `X.Y.Z+orama.N`. Under PEP 440 a specifier without a local label ignores the candidate's local label, so `==X.Y.Z` and `>=` checks behave, while the `+orama` label keeps the substitution visible in every log. [V prototype with `packaging`; re-verify against pip's resolver in the oracle suite.]
7. **Serialized identities.** Facade classes keep their native `__module__` by default. Matching upstream module paths in persisted checkpoints is an R4 wire-format decision, not an aliasing side effect.

## 6. Bridges (L3), lazy and caller-installed

| Direction | Bridge | Semantics |
|---|---|---|
| real `Runnable` → our graph | wrap as a MiniGraph node: `await runnable.ainvoke(projection(state))` → dict delta | runs inside one node; our scheduler stays authoritative |
| our graph → real LCEL | P2 Runnable subclass (above); otherwise Core's duck-typed adapter | upstream composes it like any Runnable |
| real compiled LangGraph → our graph | opaque subgraph node | **its own scheduler runs inside that node.** This is an explicit boundary, like a tool call, never a second scheduler for *our* graphs |
| our graph → real LangGraph | Core `LangGraphExporter` (unchanged) | executes under LangGraph semantics; documented as such |
| Pydantic AI `Agent` → our graph | agent-as-node; result validated into a delta; our `@tool` and dependency-injection patterns stay native | no aliasing, never a dependency |
| LangGraph.js / oramaclaw | same three layers in a separate ADR. Consumer-side package aliasing (an `npm:` alias in the caller's manifest) or an explicit `module.register()` loader hook; never publishing upstream names | [P/X] |

Detection follows the convergence plan:
- read installed distribution metadata;
- import only the specific bridge needed, at the moment it is needed;
- treat absent, supported, unsupported and broken installs as four distinct outcomes, each with its own actionable error.

## 7. Security and policy

1. **Activation is an admission event.** The profile, owned names, shadowing flag and versions are recorded as evidence and pass Phylax admission like any graph artifact. [P over D 62]
2. **Foreign code is not under our in-process egress control.** A bridged real tool or Runnable can open its own sockets, so Telos cannot be guaranteed in-process for it. Graphs containing foreign nodes are classified as **untrusted-effect graphs**. Phylax decides admission, and egress is enforced at the process or sandbox boundary per the doc 32 §5 sandbox ladder, never by trusting the foreign object. Our own effect nodes still dial only through the Telos-backed invoker. [P]
3. **Refusals follow the HITL contract.** That contract should be split out as its own record per the review; this ADR adds no policy path. Replacement never bypasses a gate.
4. **Import interception is powerful.** Its code must be small, audited, explicit-only, and covered by the late-activation and shadowing refusals above.

## 8. Staging

1. Ratify D-LG-3, then split out the HITL/refusal record.
2. Write the **P2 symbol inventory** for `langgraph` on the pinned v0.x and v1.x releases, with each row marked supported, partial or blocked.
3. Build L1 (native facade: builder, `START`/`END`, conditional edges, invoke/stream) plus L2 (finder, refusals, gap errors, metadata).
4. Build oracle environments as non-published dependency groups (PEP 735) or isolated lockfiles. Run unchanged upstream fixtures under P2, and the same fixtures against real upstream.
5. Add the L3 bridges: Runnable both ways, opaque LangGraph subgraph, Pydantic AI agent-as-node.
6. Follow R3 then R4 per the existing plan before promoting `Send`, `Command.goto`, `interrupt()` or checkpoint parity.
7. P3 only when the P2 matrix passes and an amendment to this ADR approves it.

## 9. Acceptance tests (minimum)

- Profile × install-state matrix: P0–P3 × {absent, supported, unsupported, broken} × {v0.x, v1.x}.
- Unchanged-import fixture under P2 gives the same result as real upstream on every row marked supported.
- Activation after an owned name is already imported is refused. Shadowing an installed distribution without the flag is refused.
- An optional `from … import <blocked>` raises `CompatGapError` and is caught by `except ImportError`.
- `importlib.metadata.version("langgraph")` under P2 carries `+orama`, and the specifier checks behave.
- A real `Runnable` piped both ways with the P2 graph, with callbacks observed.
- An opaque real LangGraph subgraph node runs, and our scheduler's observations stay complete around it.
- A Pydantic AI agent as a node works, with no `pydantic_ai` import outside the bridge.
- An untrusted-effect graph without Phylax admission is refused.
- Import-lint: no eager or required framework import anywhere; the bridge modules are the only allowlisted lazy importers.

## 10. Rejected alternatives

| Alternative | Why rejected |
|---|---|
| Publish packages named `langgraph` / `langchain-core` | Dependency confusion, name ownership, collides with real installs |
| `.pth` or `sitecustomize` auto-activation | Implicit global semantics change; known abuse vector |
| Monkeypatch the installed framework | Fragile across versions; mutates code we do not own |
| Run our graphs through upstream LangGraph when present | Breaks the one-scheduler rule and policy enforcement |
| Separate replacement implementation | Two code paths drift; replacement = namespace + binding instead |
| Replace `langchain_core` first (P3) | Largest surface, least leverage; P2 reuses upstream machinery instead |
