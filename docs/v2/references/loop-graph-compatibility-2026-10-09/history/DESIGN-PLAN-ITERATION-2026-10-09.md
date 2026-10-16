---
title: "Loop/Graph compatibility — design, plan and iteration record (D-LG-1, D-LG-4, lint, gap errors, rev2 register)"
date: 2026-10-09
status: "WORKING DRAFT. Nothing here is ratified. No repository was modified, commented on, merged or pushed."
supersedes_nothing: true
amends: ["rev2 gap register G1–G13", "rev2 convention table", "rev2 ownership map"]
inputs: ["Core PR #8 (head 7657cf4)", "Oramasys PR #23 (0c98513)", "Perpetua-Tools PR #430 (962eda5)", "Orama-System PR #388 (19a81cd)", "Greptile review 5468133419 on Core PR #8"]
evidence_labels: "[V] verified this session (read, or ran: say which) · [D] stated in a canonical docs/v2 record · [P] proposal, not decided · [X] not verified"
hygiene: "Categories only. No workstation paths, hostnames, addresses, identities or credentials appear in this file (docs/v2/47)."
---

# 0. How to read this document

One working document for seven requests. It is a design-and-iteration record, not a ratified decision.

| # | Request | Where | State |
|---|---|---|---|
| 1 | ADR + plan for the Pydantic AI agent bridge | §3 (ADR D-LG-4) | DRAFT, proposal |
| 2 | Plan for a FULL ADR on D-LG-1 (ownership) | §4 | DRAFT, proposal |
| 3 | "No eager imports" rule as a lint test | §5, Appendix A | Prototype written and run [V] |
| 4 | Unsupported symbols raise an ImportError subclass | §6 | Experiment run [V]; **the literal request cannot be met for symbols** (see §6.3) |
| 5 | Rev2 gap register, convention table, ownership map, with corrections | §7 | Re-recorded |
| 6 | Resolve the 8 non-blocking items | §8 | Resolved as proposals; none applied to a repo |
| 7 | Greptile review 5468133419 on Core PR #8 | §8 item 3, Appendix B | Finding valid; test + mutation check run [V] |

**Boundary rules in force (standing):** BR-1 Orama-System `docs/v2/` plans and documents. BR-2 `oramasys/oramasys` is the code target unless a record says otherwise. BR-3 Core is the dependency-minimal kernel; its two existing adapters stay in Core. BR-4 Telos owns endpoint security, Phylax generic admission, Agate hardware. Frameworks (LangChain, LangGraph, Pydantic AI) are **never** a requirement or dependency of any stack package; they are interop and test targets only.

## 0.1 What I ran, and what I did not

| Claim | Basis |
|---|---|
| Lint prototype: 11 tests pass on Core main (c0795bc) and on Core PR #8 head; planted `import langchain_core` is caught (2 of 11 fail, as intended) | [V] ran, Python 3.13 |
| Import-semantics results (§6) identical on Python 3.11, 3.12, 3.13 | [V] ran |
| Order test kills a completion-order mutant of `abatch` for limits None, 2, 100; cannot for limit 1 | [V] ran, mutation reverted afterwards (working tree clean) |
| Stub-based `LangGraphExporter` test passes against Core PR #8 | [V] ran |
| Core PR #8 CI: `pytest (3.11)` and `pytest (3.12)` success, Greptile review completed | [V] REST check-runs on the exact head |
| Core full suite "160 passed, 85.61%" | [X] not reproduced: one test file needs the external Agate fixture, which I did not install |
| Remote CI for Oramasys #23, PT #430, Orama #388 | [X] no API access to those repos |
| Any real LangChain / LangGraph / Pydantic AI behaviour | [X] none was installed or run. Pydantic AI API facts come from library documentation, not from running it |
| Oramasys behaviour with the bumped Core pin | [V] by reading only; Oramasys tests were **not** run |

# 1. Corrections that carry through this document

Collected once so later sections can rely on them.

1. **Core's adapters are not "topology-only".** `LangChainRunnableAdapter` runs the real graph (duck-typed, no `langchain_core` import, dict input needs `session_id`, returns `PerpetuaState`). `LangGraphExporter.to_langgraph` exports node callables *and* topology; the result runs under LangGraph's scheduler, and it passes no `path_map`, so `declared_targets` are lost. [V — and re-proved in §8 item 7 with a stub]
2. **`config` is not unused.** `abatch` honours `max_concurrency`; zero used to hang (`asyncio.Semaphore(0)`), fixed by Core PR #8. [V]
3. **A test extra is published dependency metadata.** Use locked oracle environments or non-published dependency groups. [D rev 3 N6]
4. **Import lint must allow lazy outward bridges**, not forbid all framework imports. Core's exporter lazy-imports `langgraph` by design. [V]
5. **Routing comparison needs a partial order** where supersteps permit concurrency. [D]
6. **Effect identity excludes the attempt.** Identity is `(durable_run_id, logical_operation_id)` + effect kind + request digest; attempt id is evidence only. My earlier `run_id:node:attempt` key was wrong. [D rev 3]
7. **No synthetic `+orama` version, no silent duck-typed fallback after a failed optional import, activation before worker threads and serialized.** Revision 3 supersedes my D-LG-3 on these. [D rev 3]
8. **The approval/HITL binding does not exist yet.** The nearest record keeps one-time tokens in an in-memory set cleared on restart; digest/scope/expiry/durable single-use is a NEW contract. Overrides stay denied/pending until a full vertical slice passes. [D; V]
9. **Telos, not Perpetua-Tools, owns v2 endpoint security.** Sandbox ladder, MCP pinning and canary scanning are already planned in docs 31/32. [D 62]

# 2. Priorities and sequencing

```text
Now (docs only)        D-LG-1 ADR (§4) -> ratify
                       D-LG-4 ADR (§3) -> ratify scope Phase 0 only
Small code, Core       order test + stub exporter test (§8.3, §8.7); lint test (§5)
Small code, Oramasys   lint test with bridge allowlist when the first bridge file lands
Gated                  anything that approves an effect (needs the durable refusal/HITL slice)
Gated                  Pydantic AI production bridge beyond Phase 1 (needs Telos-backed transport)
```

# 3. ADR D-LG-4 — Pydantic AI agent bridge (DRAFT)

**Status:** DRAFT [P]. Revision 3 (E4) deferred the production bridge "to a separate decision"; this is the draft of that decision. It does not reverse the standing rule: Pydantic AI is never a dependency.

## 3.1 Context

- Standing user decisions: adopt every unique, useful **pattern**; reject the dependency; run real Pydantic AI agents **only** as interop test targets. [User, recorded in D-LG-2 §1]
- Core already has `@tool` (signature → model), `tool_node` and `structured_output` plugins. [V]
- Pydantic AI surface relevant here (from its documentation [X: not run]): `Agent(model, deps_type=, output_type=, instructions=)`; `@agent.tool` with `RunContext[Deps]`; `run`, `run_sync`, `run_stream`, `run_stream_events`, `iter`; `result.output`, `result.usage`, `result.all_messages()`; `UsageLimits` raising `UsageLimitExceeded`; deferred tools via `DeferredToolRequests` / `DeferredToolResults` / `ToolDenied`; testing via `Agent.override(model=TestModel()/FunctionModel(fn))`, `models.ALLOW_MODEL_REQUESTS = False`, `capture_run_messages`.
- **Finding that shapes everything:** an agent's model provider opens its own network connection. A graph node must not open sockets; endpoint security is Telos's. So an agent run is an **untrusted-effect node** under the D-LG-3 rules, not a pure function. [P, consistent with D 62]

## 3.2 Options

| Option | What it is | Imports `pydantic_ai`? | Verdict |
|---|---|---|---|
| A. Test target only | Real agents run inside the conformance suite as black boxes, using `TestModel`/`FunctionModel` | In the test environment only | **Adopt (Phase 0)** |
| B. Graph-as-tool | A compiled graph exposed as a plain function (typed signature, docstring) that a caller registers with their own `Agent(tools=[...])` | **No.** Duck-typed; the caller owns the import | **Adopt (Phase 1)** |
| C. Agent-as-node | `as_node(agent, ...)` wraps a caller-supplied agent as a graph node | Lazy, inside one allowlisted bridge file | **Adopt (Phase 1), gated** |
| D. First-class runtime | Pydantic AI becomes how oramasys agents run | Yes | **Reject** (dependency rule) |
| E. Re-implement its features wholesale | Copy the feature set into the stack | No | **Reject**: patterns only (§3.6) |

## 3.3 Decision (proposed)

1. Phase 0 = Option A. Phase 1 = Options B and C, as separate modules in `oramasys/oramasys` (BR-2), outside the kernel.
2. Every bridge module imports nothing from the framework at module scope. Option B imports nothing at all. Option C may import inside one function in one allowlisted file (§5). If that import fails, the bridge **raises**; it never falls back silently to a duck-typed guess (rev 3).
3. The bridge is activated only by an explicit call by the caller, never by a side-effect import.
4. Real-model runs are **out of scope** until a Telos-backed transport and the durable refusal/HITL contract exist. All Phase 0/1 tests use `TestModel`/`FunctionModel` with `ALLOW_MODEL_REQUESTS = False`, plus a socket guard that fails the test on any connection attempt.

## 3.4 Agent-as-node contract (Option C) [P]

| Aspect | Rule |
|---|---|
| Node shape | `async def node(state) -> dict`: a delta, as for any node. No second scheduler. |
| Input | Caller supplies `prompt_from(state)` and `deps_from(state)`. The whole state is never passed by default. |
| Output | `output` is written under a caller-named scratchpad key; a pydantic-style object is stored via its dump method, detected by duck typing. |
| Usage | Token counts recorded as control metadata in the observation; message content stays local and never enters `GraphEvent`. |
| Budget | `UsageLimitExceeded` maps to a distinct termination reason `budget_exhausted` in the oramasys wrapper (convention 12). The kernel's `done`/`interrupted` set is not changed. |
| Deferred tools | Any `DeferredToolRequests` is converted to a structural `Interrupt` (terminal reason `interrupted`). Resume needs R4. **Until the durable approval contract is implemented, every deferred request is answered `ToolDenied` or left pending. Never auto-approved.** |
| Effect identity | The run is an effect: key = `(durable_run_id, logical_operation_id)` + kind + request digest. Retries are outside the kernel. |
| Network | The model object is caller-supplied. Production use must pass a Telos-backed transport or run under the sandbox ladder (docs 31/32). The bridge does not construct network clients. |
| Streaming | `run_stream_events`/`iter` feed the **sanitized** projection only. |

## 3.5 Graph-as-tool contract (Option B) [P]

A function `graph_tool(name, graph, *, input_model, output_key)` returning a callable with a proper `__name__`, `__doc__` and annotations (so a framework can derive a schema from the signature), running `graph.ainvoke`. No framework object is created or imported. The caller registers it however their framework requires.

## 3.6 Pattern harvest (no dependency) [P]

| Pydantic AI pattern | Our home | Disposition |
|---|---|---|
| Signature/docstring → tool schema | existing `@tool`; add docstring parameter descriptions | Adopt (already partly done) |
| Typed dependency injection (`RunContext[Deps]`) | a `NodeContext[Deps]` helper in `oramasys` | Adopt |
| Output validators + retry-with-feedback | wrapper outside the kernel | Adopt (retries stay outside) |
| `TestModel`/`FunctionModel` | our own `FakeProvider` for deterministic offline tests | Adopt |
| `capture_run_messages` | trace capture in the test harness | Adopt |
| Usage limits | budgets in the policy layer (D-LG-1) | Adopt |
| Deferred tools / approval | the durable refusal/HITL contract | Adopt as design input; **no code until the contract passes its vertical slice** |
| Agent runtime, model clients | — | Reject |

## 3.7 Test plan

| Id | Case | Environment |
|---|---|---|
| PA-1 | Agent with `TestModel` as a node: output lands in state | oracle env |
| PA-2 | Structured output validated and stored | oracle env |
| PA-3 | Tool call path: the tool runs, usage recorded | oracle env |
| PA-4 | `UsageLimits` breach → `budget_exhausted`, not a crash | oracle env |
| PA-5 | Deferred tool request → denied/pending, never approved | oracle env |
| PA-6 | Socket guard: zero connection attempts | oracle env |
| PA-7 | Lint: no eager import in the bridge; lazy import only in the allowlisted file | stack env, no framework installed |
| PA-8 | Bridge import failure raises; no silent fallback | stack env with a deliberately broken stub |
| PA-9 | Graph-as-tool: signature and docstring survive; runs the real graph | stack env, no framework |

Version lines to cover are set by the compatibility matrix; exact upstream versions are **not decided here** [X].

## 3.8 Consequences and rollback

Positive: nothing in the stack depends on the framework; the strongest Pydantic AI ideas arrive as our own code. Cost: two small bridge modules plus a fake provider to maintain. Rollback: delete the two modules; nothing else imports them (the lint in §5 enforces this).

## 3.9 Open questions for the operator

1. Phase 1 now, or Phase 0 only until the HITL slice exists?
2. Where should the oracle environment live (a locked environment inside Oramasys CI versus a separate repo)? Rev 3 prefers non-published dependency groups.
3. Which upstream version lines does the matrix pin?

# 4. Plan for the FULL ADR on D-LG-1 (ownership of the policy-bearing GraphSpec)

## 4.1 Why a full ADR is needed

Three records disagree or are silent:

- Doc 57 §12 and doc 59 §7 assign GraphSpec policy, lint and evaluation to Orama-System and say moving ownership to `oramasys/oramasys` "requires a new explicit architecture decision". [D]
- Core already ships a **structural** `GraphSpec`/`NodeSpec`/`EdgeSpec`, `graph_id`, and structural lint (Core PR #4), pinned by Oramasys. [V]
- BR-2 names `oramasys/oramasys` as the code target.

Three PRs call D-LG-1 an unratified proposal, but its text exists only under `history/` in Orama #388. No active ADR defines it. [V]

## 4.2 Proposed ADR skeleton (to be filed in `docs/v2`)

```text
Title      D-LG-1 — Ownership split of GraphSpec: structure in Core, policy above it
Status     Proposed (ratify by operator decision only)
Amends     doc 57 §12, doc 59 §7
Context    (§4.1 facts, with evidence labels)
Drivers    kernel stays dependency-minimal and self-verifying; policy changes faster than the
           kernel; one writer per concern; no second graph engine; pins must not break
Options    A, B, C (below)
Decision   Option A
Consequences, Migration, Acceptance tests, Rollback, Open questions, Ratification checklist
```

## 4.3 Options

| Option | Description | Assessment |
|---|---|---|
| **A (proposed)** | Core keeps the structural spec and structural lint. A separate, versioned **policy document** lives in `oramasys/oramasys`, planned in `docs/v2`, and is bound to a graph by `graph_id`. | Keeps Core small and self-verifying; no pin break; policy can evolve without touching the kernel |
| B | Policy stays only in `docs/v2` as prose until a later decision picks a code home | Leaves the contradiction in place; no code target (contradicts BR-2) |
| C | Move the structural spec and lint to Oramasys too | Breaks Core's self-verification and the existing pin; Core would no longer validate its own graphs |

## 4.4 The key design element: bind policy by `graph_id`, do not extend Core's fields

`graph_id` is a content hash of the structure [V]. A policy document carries `graph_id` and its own `policy_schema_version`. Consequences:

- The policy applies to the exact structure it was written for; any structural change invalidates the binding until re-linted.
- Core's `GRAPH_SPEC_SCHEMA_VERSION` (the string `"1"`) never has to change for policy additions.
- Core needs no knowledge of policy at all.

## 4.5 Classification rubric (which side a field belongs on)

A field is **structural (Core)** only if all hold: the kernel needs it to run or to validate topology; it is serializable as data with no code; it contains no operator policy. Otherwise it is **policy (above Core)**.

| Field / concern | Side |
|---|---|
| node names, edge kind (`static`/`conditional`), targets, `router_ref`, `declared_targets`, `implementation_ref` | Core |
| budgets, stop conditions, stagnation limits | policy |
| effect kind, replay policy, idempotency/operation identity declarations | policy |
| reducer/join declarations (R3) | policy; Core gets a mechanism seam only if needed |
| graph / state / node-contract versions beyond `schema_version` | policy |
| evaluation, locked evaluator, optimizer (R6) | policy |
| admission result | Phylax record, referenced by `graph_id` |

## 4.6 Pipeline the ADR should encode

```text
GraphSpec (structure) -> Core structural lint
  -> policy document (bound by graph_id) -> Oramasys policy lint
  -> Phylax admission -> Agate placement/eligibility
  -> realize into MiniGraph (Core builder) -> execute -> every network touch via Telos
```

## 4.7 Draft amendment text for doc 57 §12 [P]

> The structural `GraphSpec`, `NodeSpec`, `EdgeSpec`, `graph_id` and structural lint are owned by `perpetua-core` and carry no policy. All policy-bearing specification — budgets, effect and replay policy, reducer and join declarations, graph and contract versions, and evaluation — is specified in `docs/v2` and implemented in `oramasys/oramasys` as a separate document bound to a graph by `graph_id`. Core never imports it.

## 4.8 Work plan

1. Write the ADR (docs only) from §4.2–4.7.
2. Add a "policy" glossary entry and the rubric to doc 57.
3. Oramasys: define `PolicySpec` and policy lint behind the rubric; first fields are budgets and effect declarations (they unblock the Pydantic AI `budget_exhausted` mapping).
4. Acceptance tests: (a) a test that Core's spec module has no field in the policy column; (b) a test that changing structure changes `graph_id` and invalidates a bound policy; (c) the import-lint in §5 in both repos.
5. Ratification checklist: operator decision recorded; doc 57 and 59 amended in the same change; Core PR #4 and Oramasys PR #11 referenced as the existing facts.

## 4.9 Risks and open questions

- Two lint passes can drift; mitigate by one shared diagnostics format.
- Risk that "policy" absorbs fields the kernel truly needs later (reducers). The rubric's "mechanism seam in Core, policy above" rule handles this but must be re-checked at R3.
- Open: does the operator want the policy document to be a separate file or embedded in the application graph definition?

# 5. The "no eager imports" rule as a lint test

## 5.1 Rule

No module in a stack package may import LangChain, LangGraph or Pydantic AI at module scope, as a required dependency, or via a string-literal dynamic import. A **lazy** import inside a function is permitted only in an explicit allowlist of bridge files. `TYPE_CHECKING` imports are exempt.

## 5.2 Four layers (each catches what the others cannot)

| Layer | Catches | Misses |
|---|---|---|
| 1. AST scan, classify EAGER / LAZY / TYPING / DYNAMIC | static imports, nested functions and methods, string-literal `import_module`/`__import__` | non-literal dynamic imports |
| 2. Allowlist, per file and per root | a lazy import in the wrong file | — (and a second test fails if an allowlist entry matches nothing, so permission cannot go stale) |
| 3. Tripwire: import every module in a clean subprocess with a meta-path blocker | an import that the AST scan cannot see but import time triggers, even with the framework not installed | call-time lazy imports |
| 4. Metadata: dependency tables must not name a forbidden distribution | declared dependencies, including optional extras | — |

Plus 7 self-tests that prove the lint itself fires or stays quiet: five must-flag cases (eager import, `from` import of a submodule, lazy import outside the allowlist, string-literal dynamic import, lazy import in a nested class method) and two must-accept cases (`TYPE_CHECKING` import, look-alike names such as `langgraphish`).

## 5.3 Results [V]

| Target | Result |
|---|---|
| Core main (c0795bc) | 11 passed |
| Core PR #8 head | 11 passed |
| Core main + one planted eager import | 2 failed (AST test and tripwire), 9 passed |

The Core allowlist needs exactly one entry: the exporter's lazy `langgraph` import.

## 5.4 Defect found in my own prototype and fixed

The first run failed `test_allowlist_has_no_stale_entries` on both Core trees. Cause: I normalised the file path two different ways (the scan yielded paths relative to the source directory; the stale-entry check stripped a leading component that was not there). It was **not** a Core defect. Fixed by using one relative-path form everywhere. A `re.split` positional-argument deprecation warning was fixed at the same time.

## 5.5 Known limits [P]

- A non-literal dynamic import (built from a variable) is not detected statically.
- A module-level `try: import x except ImportError:` is classed EAGER and fails the rule. That is intended: it is the "silent fallback after a failed import" that revision 3 forbids.
- The tripwire sees only import-time behaviour.

## 5.6 Placement

Core now (one small test file, one allowlist entry), as a Core invariant. Oramasys when the first bridge file lands, with that bridge in the allowlist. Not applied to any repository by me; the full file is in Appendix A.

# 6. Unsupported symbols and the ImportError question

## 6.1 Experiments [V] (identical on Python 3.11, 3.12, 3.13)

| Design | `from m import X` | `hasattr` / `getattr(default)` | `pytest.importorskip` | `except ModuleNotFoundError` + `e.name` |
|---|---|---|---|---|
| Plain `ImportError` subclass for a **module** gap | raises it | n/a | **propagates** (a test errors instead of skipping) | **propagates** |
| `ModuleNotFoundError` subclass for a module gap (`name` set) | raises it | n/a | skips | handled as "absent"; still an `ImportError` |
| `__getattr__` raising an `ImportError` subclass for a **symbol** | raises it | **`hasattr` and `getattr(default)` raise instead of returning False/default** | n/a | n/a |
| `__getattr__` raising an `AttributeError` subclass | the interpreter replaces it with a generic `ImportError: cannot import name 'X' from 'm'`; `__cause__` and `__context__` are `None`, so the matrix row is not attached | `hasattr` False, `getattr(default)` returns default | n/a | n/a |
| One class inheriting both `ImportError` and `AttributeError` | **impossible** (layout conflict) | — | — | — |
| Dunder names | `__getattr__` must raise a plain `AttributeError`, because the `from` import machinery probes `__path__` and similar | | | |

## 6.2 Consequence

For **symbols**, an `ImportError` subclass is unsafe: it breaks feature detection (`hasattr`, `getattr(..., default)`) that third-party libraries use to decide what is supported. For **modules**, `ModuleNotFoundError` is the correct subclass, because every ecosystem tool already treats it as "absent" while it remains an `ImportError`.

## 6.3 Proposed design (tiered) [P]

| Tier | Situation | Raise | Why |
|---|---|---|---|
| 1 | A whole upstream module/namespace is unsupported | `CompatGapModuleError(ModuleNotFoundError)` with `name` set and a `matrix_row` attribute | still an `ImportError`; correct for `importorskip` and `except ModuleNotFoundError` |
| 2 | A symbol inside a supported module is unsupported | module `__getattr__` raises `CompatGapAttributeError(AttributeError)` with `matrix_row`; dunders raise a plain `AttributeError` | keeps `hasattr`/`getattr(default)` correct |
| 3 | The caller wants the reason for a failed `from m import X` | `compat.explain("pkg.sub.X")` returns the matrix row; error text from tier 2 names it when reached by attribute access | the interpreter drops the row on the `from` form |
| 4 | Installed but broken optional dependency | raise; **no** silent fallback | rev 3 |

**What this means for request 4.** "Unsupported symbols raise an `ImportError` subclass" can be satisfied for modules (tier 1) but **not safely for symbols**. The user-visible `from m import X` form does raise `ImportError`, but it is the interpreter's generic one. I recommend the tiered design and ask the operator to confirm. Rejected alternative: exporting stub classes for unsupported symbols that fail on use. They make `hasattr` return True and so falsely advertise support.

## 6.4 Conformance-suite hazard

Because tier 1 behaves as "absent", `pytest.importorskip` will **skip** rather than fail. The suite must mark every matrix row as expected-gap/xfail-strict so a gap cannot hide as a silent skip.

## 6.5 Tests to add

1. Tier 1 is a `ModuleNotFoundError` and an `ImportError`, with `name` and `matrix_row` set.
2. Tier 2: `hasattr` False; `getattr(default)` returns default; attribute access raises with `matrix_row`.
3. Dunder access raises a plain `AttributeError`.
4. `from m import X` raises `ImportError`; `explain` returns the row.
5. Same results on 3.11, 3.12, 3.13.

# 7. Rev2 gap register, convention table and ownership map — re-recorded with corrections

Evidence for the underlying Core facts is in the two rev2 files; this section carries them forward with every correction applied. "Δ" marks what changed.

## 7.1 Gap register

| ID | Gap | Status now | Owner / target | Δ |
|---|---|---|---|---|
| G1 | Stale vs merged Core | closed | docs/v2 | — |
| G2 | Open pasted question (compile freeze) | closed | docs/v2 | — |
| G3 | Malformed YAML | closed | — | — |
| G4 | Unverified test claims | **partly evidenced**: Core #8 CI green on 3.11/3.12; I ran 29 focused tests and the lint/order/stub prototypes; full suite and coverage not reproduced | Core CI | updated |
| G5 | No loop → graph mechanism | proposed | docs/v2; code `oramasys` | — |
| G6 | Kernel termination taxonomy thin | proposed; `budget_exhausted` first needed by §3.4 | wrapper in `oramasys` | note added |
| G7 | GraphSpec ownership contradiction | **ADR plan written (§4)**; unratified | docs/v2 | updated |
| G8 | LangGraph surface vs callable-edge design | adapters stay in Core; new work in oramasys; **corrected description of Core adapters (§1.1)** | Core / oramasys | corrected |
| G9 | Reducers/joins (R3), durable resume + effect identity (R4) | open | docs 57 §10–11 | — |
| G10 | Boundary rules implicit | BR-1…BR-6 recorded | docs/v2 | — |
| G11 | Security not covered | overlay recorded; Telos corrected (not PT) | Telos / Phylax | corrected |
| G12 | Provider ledger is audit, not dedupe; JSONL ledger unwired | **open** | `oramasys` | — |
| G13 | Graph-artifact admission wiring to Phylax unverified | **open** | Phylax / `oramasys` | — |
| **G14** | No "no eager imports" lint in any PR | prototype passes; not yet adopted (§5) | Core, Oramasys | new |
| **G15** | Approval/HITL binding (digest, policy revision, scope, expiry, durable single-use) does not exist | NEW contract, unimplemented; overrides stay denied/pending | docs/v2 record; code `oramasys` | new |
| **G16** | `LangGraphExporter` tests skipped without `langgraph` | stub test proposed (§8.7) | Core | new |
| **G17** | `abatch` order test cannot detect completion-order results | improved test + mutation check done (§8.3) | Core | new |
| **G18** | Unsupported-symbol error shape unspecified | tiered design proposed (§6) | oramasys | new |
| **G19** | Pydantic AI bridge undecided | D-LG-4 drafted (§3) | docs/v2; oramasys | new |
| **G20** | Exporter drops `declared_targets` (no `path_map`) | recorded; fix is an outbound-export improvement, not a kernel change | Core adapter | new |

## 7.2 Convention table (20 conventions against live code)

Legend: Done · Partial · Open · Out (deliberately outside the kernel).

| # | Convention | Status | Note and corrections |
|---|---|---|---|
| 1 | Separate definition, execution, evidence | Partial | Spec and lint exist; `CompiledGraph` is a detached snapshot; no run/trace/checkpoint lineage records |
| 2 | Version the graph schema | Partial | `schema_version` is the string `"1"` and a content-hash `graph_id` exists; no `graph_version`, no state-schema version. Policy versions live above Core (§4.4) |
| 3 | Stable node identity | Partial | `NodeSpec.name` + `implementation_ref`; no implementation-version pin |
| 4 | Edges as contracts | Partial | `EdgeKind` is `static` or `conditional`; `router_ref`, `declared_targets`; strict route validation; no payload-schema contract. **Exporter drops `declared_targets` (G20)** |
| 5 | Explicit state-merge semantics | Partial | Strict dict-delta; `merge()` uses deep copy; per-key reducers are R3 |
| 6 | Fan-out/fan-in join semantics | Partial | Ordered last-writer-wins by default, not a join contract; R3 |
| 7 | Retry at the node/effect boundary | Out/Open | Engine header excludes retries; the Pydantic AI retry pattern lands outside the kernel (§3.6) |
| 8 | Dedupe / idempotency | Open | **Corrected:** identity = `(durable_run_id, logical_operation_id)` + effect kind + request digest; attempt id is evidence only; `durable_run_id` must survive resume. Ledger is audit, not dedupe (G12) |
| 9 | Interrupt/resume implies replay | Partial | Structural `Interrupt` only; not durable resume (R4). Deferred tool requests map here (§3.4) |
| 10 | Checkpoints are lineage | Partial | `SqliteCheckpointer` stores session, node, state JSON; no parent link or graph-version stamp |
| 11 | Run state vs long-term memory | Done by doctrine | Memory governance outside the engine |
| 12 | Explicit termination reasons | Partial | `done`, `interrupted`, plus `MaxStepsExceeded`; `budget_exhausted` is the first proposed addition (wrapper, §3.4) |
| 13 | Observe routing decisions | Done | `edge.selected`, sanitized `GraphEvent`, `aobserve()`/`asteps()` |
| 14 | Trace control metadata; redact payloads | Done (structure) | Rich `GraphObservation` (trusted) vs sanitized `GraphEvent`; export-side redaction policy not in Core. Frozen top-level fields do not deep-freeze contents |
| 15 | Deterministic verifier surface | Partial | Structural lint; runtime verifier is R6 |
| 16 | Multi-objective optimization | Open | R6 |
| 17 | Graph only when topology is the contract | Done by doctrine | Ladder: prompt → chain → loop → graph |
| 18 | Composition without kernel recursion | Done | Subgraphs are a plugin |
| 19 | Cancellation first-class | Open | No cancel reason or propagation contract |
| 20 | Tiny kernel, evolve at the edges | Done | One private `_run()` scheduler; header lists exclusions (persistence, retries, reducers, provider policy, telemetry, optimization) |

## 7.3 Ownership map

| Concern | Planning record (BR-1) | Code target | State |
|---|---|---|---|
| Scheduler, state merge, observation seam, structural interrupt | docs 01, 57, 58, 59 | Core | merged [V] |
| Structural spec, `graph_id`, structural lint | doc 57 §12–13 | Core | present [V]; stays (D-LG-1 Option A) |
| Policy document: budgets, effect/replay, reducers/joins, versions, evaluation | docs 57 §12–14, R5/R6 | `oramasys/oramasys` | not implemented; ownership unratified (§4) |
| Reducers/joins (R3) | doc 57 §10 | Core mechanism seam only if needed; policy above | open |
| Durable resume, effect identity (R4) | doc 57 §11 | checkpointer plugin (Core) + effect policy (oramasys) | open |
| Existing LangChain Runnable adapter and LangGraph exporter | docs 57, 59 | **Core (stay)** | present [V]; corrected description (§1.1) |
| New compat layer, facades, bridges, conformance suite | docs/v2 plan (#388) | `oramasys/oramasys` | planned |
| Pydantic AI bridge (agent-as-node, graph-as-tool) | D-LG-4 (§3) | `oramasys/oramasys` | draft |
| "No eager imports" lint | this document §5 | Core (one allowlist entry) and Oramasys (bridge files) | prototype |
| Unsupported-symbol error classes | this document §6 | `oramasys/oramasys` | proposed |
| Durable refusal/HITL contract | `2026-10-09-compatibility-refusal-hitl-contract.md` (#388) | `oramasys/oramasys` | NEW, unimplemented; overrides denied/pending |
| Route → dispatch → respond graph | doc 16 | `oramasys` `src/orama/graph/` | present [V] |
| Provider dispatch audit | docs 54, 55 | `oramasys` providers | in-memory ledger default; JSONL unwired [V] |
| Endpoint security for any node's network use | doc 62 | **Telos** | implemented modules present [V] |
| Hardware placement | docs 07, 42 | **Agate** | route node delegates [V] |
| Generic admission of graph artifacts | doc 60 | **Phylax** | owner defined; wiring unverified (G13) |
| Claim/lease/recovery controller | doc 68 | `oramasys` | "no runtime code yet" [V] |
| Sandbox ladder, MCP pinning, canary scanning | docs 31, 32 | per doc | already planned (corrected: not new gaps) |

## 7.4 Live state (replaces rev2 §17 on the PR rows)

| Repo | Open change | Head | Checks |
|---|---|---|---|
| perpetua-core | PR #8 (abatch fix) | 7657cf4 | `pytest (3.11)`, `pytest (3.12)` success; Greptile completed [V] |
| oramasys | PR #23 (docs) | 0c98513 | [X] not checkable |
| Perpetua-Tools | PR #430 (docs) | 962eda5 | [X] not checkable |
| orama-system | PR #388 (docs, 19 files) | 19a81cd | [X] not checkable |

Rev2 §17 said Core had no open PRs; that is now superseded by #8.

# 8. The eight non-blocking items

| # | Item | Resolution | Applied to a repo? |
|---|---|---|---|
| 1 | Stale tense | See 8.1 | No |
| 2 | Cross-links 404 until #388 lands | See 8.2 | No |
| 3 | Greptile P2 (order test) | See 8.3, Appendix B | No |
| 4 | No import-lint test | See §5 | No |
| 5 | D-LG-1 has no active ADR | See §4 | No |
| 6 | Pin bump larger than the fix | See 8.6 | No |
| 7 | Exporter tests skipped | See 8.7, Appendix B | No |
| 8 | +2246 lines in one docs PR | See 8.8 | No |

(The review's ninth point, the narrow markdownlint exemption, was a confirmation with no action.)

## 8.1 Stale tense

Found [V] in the Orama #388 tree:

- The convergence plan's revision paragraph says Core's fix is "local, not yet published".
- The #388 README's status line (line 4) still uses "locally", and its line 32 says the cross-repository links name intended publication paths and calls the files "local".
- The PT follow-up's "publication pending" wording is **not verified**: my PT clone is main and does not contain it.

Resolution: after all four merge, one follow-up commit rewrites those sentences to the past tense ("Core's bounded fix is merged at <sha>"). Do it after merge so the text is true at each moment. Suggested wording for the plan paragraph: "Core's bounded adapter fix is merged; the full replacement program is not implemented."

## 8.2 Cross-links

[V] The Orama README path and the PT evidence-plan path are both **absent from their repositories' main today** and present only in the PR trees. Core's compatibility doc links to both. Resolution: merge order **#388 → #430 → Core #8 → Oramasys #23**; after the first two merge, re-check every link in the last two. Oramasys #23's own links were not checked (not in my tree) [X].

## 8.3 Greptile review 5468133419 (P2) — accepted

**Finding.** `test_abatch_valid_bounds_preserve_input_order` uses synchronous nodes, so a change returning results in completion order would still pass. Valid.

**Evidence [V].** I mutated `abatch` to return in completion order (`as_completed`). The PR's current test still **passes** (4 of 4). A test where the first input finishes last (an `ainvoke` override that sleeps for the first input) **fails** the mutant for limits None, 2 and 100. Limit 1 cannot distinguish the orders because execution is serial; that is expected, and it is kept as a control. The mutation was reverted and the working tree is clean.

**Resolution.** Replace the order test with the delayed-first-input form (Appendix B), as a Core follow-up commit on PR #8 or a small PR after it. Suggested reply text for the review thread (not posted):

> Agreed, and thank you. The synchronous nodes cannot tell input order from completion order. I reproduced this by mutating `abatch` to return in completion order: the current test passes the mutant. A variant where the first input finishes last fails the mutant for `None`, 2 and 100 (limit 1 is serial, so it cannot differ). I will push that test.

## 8.4 Import-lint (item 4)

Resolved by §5 and Appendix A: prototype passes on Core main and PR #8 and catches a planted violation.

## 8.5 D-LG-1 ADR (item 5)

Resolved as a plan by §4; the ADR file itself is still to be written and ratified by the operator.

## 8.6 Pin bump (item 6)

[V by reading] Seven Core commits separate the Oramasys pin (8dde861) from Core main (c0795bc). Their content:

- 6 source files under `discovery/`, 29 insertions and 126 deletions; 3 test files; a `pyproject.toml` change that **removes Core's own pinned Telos dependency**. Nothing under `graph/`.
- Core's registry loses `autodetect`/`register_by_ip` and the internal probe module, and gains `record()`. Network probing is now stated to belong to composition.

Impact on Oramasys, from reading its code: it imports `Backend`, `BackendHealth`, `BackendKind`, `BackendRegistry`, `select_backend` and both error classes; the exported name set is **identical** at both commits. Its `DiscoveryBackendRegistry` defines its own `autodetect`, `register_by_ip` and probe, and its `_store` prefers `record()` and falls back to `_backends`, so it already tolerates both Core shapes. Oramasys also declares Telos itself, at the same commit Core used to pin, so dropping Core's Telos pin does not remove it. **Risk: low, but unproven.** Resolution: the pin-bump follow-up states the seven-commit scope and reruns the **whole Oramasys suite** (not run by me).

## 8.7 Exporter tests skipped (item 7)

[V] A stub test injects a fake `langgraph.graph` (`StateGraph`, `START`, `END`) into `sys.modules` and checks, with no real framework: nodes added in order; START/END translated; conditional edges registered; `compile()` called. It passes against PR #8. It also **proves G20**: `add_conditional_edges` is called without a `path_map`. The stub test proves our wiring only; it says nothing about real LangGraph semantics, which stay [X] until the oracle environment exists. Resolution: add the stub test to Core (dependency-free) and keep the real-framework test skipped in normal CI.

## 8.8 Size of #388

By the diff stat [V]: 2246 added lines = **1423 preserved history** (63%: both rev2 files, D-LG-2, D-LG-3, the review, two history scripts, history README) + **823 active** (37%). The active part is: convergence plan 225, README 77, resolutions 64, ADR rev 3 53, hand-off 65, verification 58, refusal/HITL contract 52, three evidence scripts 227, lint-config 2. Resolution: no split needed (history is byte-preserved); review order — README, resolutions, contract, ADR rev 3, then the plan; the evidence scripts last.

# 9. Iteration log and next steps

| Iteration | Change | Reason |
|---|---|---|
| 1 | Lint prototype, 4 layers | Item 4 and the D-LG-2 erratum |
| 2 | Fixed path-key bug in my own stale-allowlist test | Run failed on both Core trees; cause was my normalisation, not Core |
| 3 | Fixed the `re.split` deprecation | Warning in every run |
| 4 | Ran the import-semantics experiments | The request wanted an ImportError subclass; evidence shows it is unsafe for symbols |
| 5 | Re-ran the `from` form and recorded the lost `__cause__` | Needed to justify `compat.explain` |
| 6 | Order test + mutation | Greptile P2 |
| 7 | Stub exporter test | Item 7 and G20 |
| 8 | Pin-bump read | Item 6 |

**Next steps, in order:** (1) operator confirms §3.9, §4.9 and the §6.3 tiering; (2) file the D-LG-1 ADR in `docs/v2`; (3) land the order test, stub test and lint test in Core; (4) merge #388 → #430 → #8 → #23; (5) the stale-tense follow-up commit; (6) rerun Oramasys on the bumped pin; (7) build the oracle environment before any real-framework claim.

**Not verified in this document:** real behaviour of any external framework; Oramasys, PT and Orama CI; Oramasys tests on the new Core pin; Core's full-suite count and coverage; the PT "publication pending" sentence.

# Appendix A — lint test (prototype, runs as-is with pytest)

Set `FRAMEWORK_LINT_SRC` to the package source directory, or run from a repo root with `src/<pkg>/`. Requires Python 3.11+ (`tomllib`). The allowlist shown is the Core one.

```python
"""No eager / required third-party-framework imports (D-LG-2 errata 3, D-LG-3).

Portable: set FRAMEWORK_LINT_SRC to the package source dir to scan (default: ./src/<pkg>).
Four independent layers, because each catches what the others cannot:
  1. AST scan   - classifies every import as EAGER (module scope), LAZY (inside a function),
                  or TYPING (inside `if TYPE_CHECKING:`); also flags string-literal dynamic imports.
  2. Allowlist  - only named bridge files may contain LAZY imports; EAGER is never allowed.
  3. Tripwire   - imports the package in a clean subprocess with a meta-path blocker that
                  records any attempt to import a forbidden root (works whether or not the
                  framework is installed).
  4. Metadata   - pyproject dependency tables must not name a forbidden distribution.
"""
from __future__ import annotations
import ast, os, re, subprocess, sys, textwrap, tomllib
from pathlib import Path

FORBIDDEN_ROOTS = ("langchain", "langchain_core", "langchain_community", "langchain_openai",
                   "langgraph", "pydantic_ai", "pydantic_ai_slim")
FORBIDDEN_DISTS = ("langchain", "langgraph", "pydantic-ai")      # prefix match on normalised names
# path (relative to the scanned src dir) -> forbidden roots it may import LAZILY
LAZY_ALLOWLIST = {"graph/adapters/langgraph_adapter.py": {"langgraph"}}

def _root(name: str) -> str: return name.split(".")[0]
def _forbidden(name: str) -> bool: return _root(name) in FORBIDDEN_ROOTS

def classify(path: Path):
    """Yield (lineno, root, kind) with kind in EAGER|LAZY|TYPING|DYNAMIC."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    def walk(node, depth_fn, typing):
        for child in ast.iter_child_nodes(node):
            fn = depth_fn or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
            ty = typing or (isinstance(child, ast.If) and "TYPE_CHECKING" in ast.unparse(child.test))
            if isinstance(child, ast.Import):
                for a in child.names:
                    if _forbidden(a.name): yield child.lineno, _root(a.name), "TYPING" if ty else "LAZY" if fn else "EAGER"
            elif isinstance(child, ast.ImportFrom) and child.module and child.level == 0:
                if _forbidden(child.module): yield child.lineno, _root(child.module), "TYPING" if ty else "LAZY" if fn else "EAGER"
            elif isinstance(child, ast.Call):
                f = child.func; fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if fname in ("import_module", "__import__") and child.args and isinstance(child.args[0], ast.Constant) \
                        and isinstance(child.args[0].value, str) and _forbidden(child.args[0].value):
                    yield child.lineno, _root(child.args[0].value), "DYNAMIC"
            yield from walk(child, fn, ty)
    yield from walk(tree, False, False)

def scan(src: Path):
    findings = []
    for p in sorted(src.rglob("*.py")):
        rel = p.relative_to(src).as_posix()
        for lineno, root, kind in classify(p):
            findings.append((rel, lineno, root, kind))
    return findings

def violations(src: Path):
    bad = []
    for rel, lineno, root, kind in scan(src):
        allowed = LAZY_ALLOWLIST.get(rel, set())
        if kind == "TYPING": continue
        if kind == "LAZY" and root in allowed: continue
        bad.append(f"{rel}:{lineno} {kind} import of '{root}'")
    return bad

def _src_dir() -> Path:
    env = os.environ.get("FRAMEWORK_LINT_SRC")
    return Path(env) if env else next(Path("src").glob("*/__init__.py")).parent

# ------------------------------------------------------------------ real checks
def test_ast_no_eager_or_unlisted_framework_imports():
    assert violations(_src_dir()) == []

def test_allowlist_has_no_stale_entries():
    """An allowlist entry that no longer matches code is dead permission: remove it."""
    seen = {(rel, root) for rel, _, root, k in scan(_src_dir()) if k == "LAZY"}
    for rel, roots in LAZY_ALLOWLIST.items():
        for root in roots: assert (rel, root) in seen, f"stale allowlist entry {rel}:{root}"

def test_tripwire_import_of_every_module_touches_no_framework():
    pkg = _src_dir().name
    code = textwrap.dedent(f"""
        import importlib, importlib.abc, pkgutil, sys
        hits = []
        class Trip(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path=None, target=None):
                if name.split('.')[0] in {FORBIDDEN_ROOTS!r}: hits.append(name)
        sys.meta_path.insert(0, Trip())
        sys.path.insert(0, {str(_src_dir().parent)!r})
        top = importlib.import_module({pkg!r})
        for m in pkgutil.walk_packages(top.__path__, top.__name__ + '.'):
            try: importlib.import_module(m.name)
            except ImportError as e:
                if e.name and e.name.split('.')[0] in {FORBIDDEN_ROOTS!r}: hits.append(m.name + ' ->' + e.name)
        print('HITS=' + repr(hits))
    """)
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120)
    assert "HITS=[]" in r.stdout, r.stdout + r.stderr

def test_metadata_declares_no_framework_dependency():
    py = _src_dir().parent.parent / "pyproject.toml"
    if not py.exists(): return
    d = tomllib.loads(py.read_text(encoding="utf-8"))["project"]
    names = list(d.get("dependencies", [])) + [x for g in d.get("optional-dependencies", {}).values() for x in g]
    norm = [re.split(r"[ <>=!~;\[@]", n.strip(), maxsplit=1)[0].lower().replace("_", "-") for n in names]
    assert [n for n in norm if n.startswith(FORBIDDEN_DISTS)] == []

# ------------------------------------------------------------------ the lint tests itself
def _write(tmp, rel, body):
    p = tmp / "pkg" / rel; p.parent.mkdir(parents=True, exist_ok=True)
    (tmp / "pkg" / "__init__.py").touch(); p.write_text(textwrap.dedent(body)); return tmp / "pkg"

def test_lint_flags_eager_import(tmp_path):
    assert violations(_write(tmp_path, "a.py", "import langgraph\n"))
def test_lint_flags_from_import_and_submodule(tmp_path):
    assert violations(_write(tmp_path, "a.py", "from langchain_core.runnables import Runnable\n"))
def test_lint_flags_lazy_import_outside_allowlist(tmp_path):
    assert violations(_write(tmp_path, "a.py", "def f():\n    import langgraph\n"))
def test_lint_flags_dynamic_string_import(tmp_path):
    assert violations(_write(tmp_path, "a.py", "import importlib\nimportlib.import_module('pydantic_ai')\n"))
def test_lint_flags_nested_class_method_lazy(tmp_path):
    assert violations(_write(tmp_path, "a.py", "class C:\n    def m(self):\n        from pydantic_ai import Agent\n"))
def test_lint_accepts_typing_only(tmp_path):
    assert violations(_write(tmp_path, "a.py", "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import langgraph\n")) == []
def test_lint_ignores_unrelated_lookalike(tmp_path):
    assert violations(_write(tmp_path, "a.py", "import langgraphish\nimport pydantic\n")) == []
```

# Appendix B — order test and stub exporter test (prototype)

Run from a Core checkout with its own pytest configuration (the source path comes from `pythonpath`).

```python
import asyncio, sys, types
import pytest
from perpetua_core.graph.adapters.langchain_adapter import LangChainRunnableAdapter
from perpetua_core.graph.adapters.langgraph_adapter import LangGraphExporter
from perpetua_core.graph.engine import END, START, MiniGraph
from perpetua_core.state import PerpetuaState

def _g():
    g = MiniGraph()
    g.add_node("a", lambda s: {"scratchpad": {**s.scratchpad, "a": True}})
    g.add_edge(START, "a"); g.add_edge("a", END)
    return g

@pytest.mark.parametrize("limit", [None, 1, 2, 100])
def test_order_is_input_order_not_completion_order(limit):
    class Slow(LangChainRunnableAdapter):
        async def ainvoke(self, item, config=None):
            # first input finishes LAST
            await asyncio.sleep(0.05 if item.session_id == "first" else 0)
            return await super().ainvoke(item, config=config)
    r = asyncio.run(Slow(_g()).abatch(
        [PerpetuaState(session_id="first"), PerpetuaState(session_id="second")],
        {"max_concurrency": limit}))
    assert [x.session_id for x in r] == ["first", "second"]

def test_exporter_with_stub_langgraph(monkeypatch):
    calls = {"nodes": [], "edges": [], "cond": [], "compiled": 0}
    class SG:
        def __init__(self, schema): self.schema = schema
        def add_node(self, n, f): calls["nodes"].append(n)
        def add_edge(self, a, b): calls["edges"].append((a, b))
        def add_conditional_edges(self, a, fn, *path_map): calls["cond"].append((a, len(path_map)))
        def compile(self): calls["compiled"] += 1; return "compiled"
    mod = types.ModuleType("langgraph"); gm = types.ModuleType("langgraph.graph")
    gm.START, gm.END, gm.StateGraph = "__start__", "__end__", SG
    mod.graph = gm
    monkeypatch.setitem(sys.modules, "langgraph", mod); monkeypatch.setitem(sys.modules, "langgraph.graph", gm)
    g = MiniGraph()
    g.add_node("a", lambda s: {}); g.add_node("b", lambda s: {})
    g.add_edge(START, "a"); g.add_edge("a", lambda s: "b"); g.add_edge("b", END)
    assert LangGraphExporter.to_langgraph(g, PerpetuaState) == "compiled"
    assert calls["nodes"] == ["a", "b"]
    assert ("__start__", "a") in calls["edges"] and ("b", "__end__") in calls["edges"]
    assert calls["cond"] == [("a", 0)]  # no path_map passed: declared targets are lost
```
