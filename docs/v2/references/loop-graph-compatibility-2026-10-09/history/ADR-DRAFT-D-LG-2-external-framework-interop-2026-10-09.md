---
title: "ADR draft D-LG-2 — External-framework interop surface (LangChain, LangGraph, Pydantic AI)"
date: 2026-10-09
status: "DRAFT — partially superseded 2026-10-09 by the orama-system compatibility-convergence plan; see Errata. Not ratified."
related: ["docs/v2/57", "docs/v2/59", "docs/v2/06-open-questions (OQ1)", "docs/v2/plans/2026-08-29 §9.7", "proposed D-LG-1"]
---

# D-LG-2 — External-framework interop surface

Evidence labels: **[V]** verified by reading code/docs on 2026-10-09 (tests not run); **[D]** canonical docs/v2; **[P]** proposal; **[U]** user decision recorded in this session.

## 1. Decisions recorded from the user [U]

1. LangChain, LangGraph and Pydantic AI are **never** a requirement or dependency of any oramasys-stack package, internal or kernel.
2. They are run **only** as test and interoperability targets (real applications, real agents).
3. Adapters are modules/plugins that form a **public outward surface**; nothing inside the stack consumes them.
4. "Drop-in" covers **both** the LangChain Runnable surface and the LangGraph public API, on **both v0.x and v1.x**, enforced by a conformance suite.
5. Pydantic AI: adopt every unique, useful **pattern**; reject the dependency; keep our own implementations.
6. Placement: existing Core adapters stay where they are; **new compat work is built in `oramasys/oramasys`**; planning stays in orama-system `docs/v2`.

## 2. Consistency with existing records

- Engine must not import plugins, providers, adapters or upper-layer policy [D 57 §9].
- Adapters consume `aobserve()`/`asteps()` projections and never reimplement traversal [D 57].
- Adapters may depend on Core public contracts; Core must not depend on adapters [D plan 2026-08-29 §9.7].
- Pydantic AI: signature/schema extraction and docstring metadata ADOPT; runtime dependency REJECT [D reconciliation 2026-08-27]. OQ1 (supplement vs replace) is answered here as **neither: patterns only** [U].
- Core `pyproject.toml` lists no LangChain/LangGraph/Pydantic AI dependency [V].

## 3. Current state [V]

| Surface | Exists in Core | Gap |
|---|---|---|
| LangChain Runnable shape | `LangChainRunnableAdapter`: `invoke/batch/stream`, async twins, `\|` chaining; runs the real graph; no `langchain_core` import | dict input needs `session_id`; output is `PerpetuaState`, not dict; `config` accepted but unused; no `astream_events`, `with_config`, `pipe`, schema introspection |
| LangGraph | `LangGraphExporter.to_langgraph()` (outbound; lazy-imports `langgraph`) | no inbound `StateGraph`-shaped builder; no `Command`, `Send`, `interrupt()` parity (blocked on R3/R4); no `StateSnapshot`, no `astream_events` v2 |
| Pydantic AI patterns | `@tool` (signature → `create_model`), `tool_node`, `structured_output` plugins | docstring metadata, `RunContext`-style dependency injection, output validators/retries (retries outside kernel) |

## 4. Honest limit

"100%" is unreachable while reducers/joins (R3) and durable deterministic resume (R4) are absent. Until then each symbol is labelled **supported**, **partial**, or **blocked-on-R3/R4** in the compat contract. The suite, not prose, is what may claim a symbol works.

## 5. Minimal steps (in order)

1. **Ratify** this ADR (and decide D-LG-1) in `docs/v2`. *Plan: orama-system.*
2. **Write the drop-in contract**: exact symbols per target, per version line (v0.x, v1.x), each marked supported / partial / blocked. *Plan: docs/v2; stored with the suite.*
3. **Conformance suite first** (oramasys): golden graphs run through MiniGraph and the real library; compare final state and the ordered routing sequence (not raw event payloads). Frameworks installed only via a test extra, never a dependency. Real Pydantic AI agents and real LangGraph/LangChain apps run as black-box interop cases. A scheduled run flags upstream drift on both version lines. *Build: oramasys.*
4. **Close gaps cheapest-first** (oramasys module, public outward surface): dict-in/dict-out mode; `RunnableConfig` and callbacks; `astream_events`; `with_config`/`pipe`; `StateGraph`-shaped builder facade. `Command`/`Send`/`interrupt()`/`StateSnapshot` only after R3/R4. Core's two adapters stay untouched.
5. **Harvest Pydantic AI patterns as plugins** (oramasys; none of these import `pydantic_ai`): docstring metadata, `RunContext`-style dependency injection, output validators and retry wrappers. *Retries stay outside the kernel.*
6. **Guard the boundary**: an import-lint test in Core and oramasys that fails if any non-test module imports `langchain*`, `langgraph*` or `pydantic_ai`.

## 6. Open items

- D-LG-1 (policy-layer ownership) is still unratified and interacts with step 4 for anything policy-bearing.
- Security: any compat surface that accepts external objects is an input boundary. Endpoint-touching behaviour goes through Telos; admission through Phylax [D 62]. No new security design is introduced here.
- Verified only by reading source; no test runs, and external library behaviour on v0.x/v1.x is [X] until the suite exists.

## Errata (2026-10-09, after review of the convergence plan)

1. §3 "`config` accepted but unused" is wrong: `abatch()` honors `max_concurrency`. Most other `RunnableConfig` semantics remain unproved. Note: `max_concurrency=0` currently hangs (`asyncio.Semaphore(0)`); verified by running it.
2. §5 step 3 "frameworks installed only via a test extra" is wrong: an optional extra is published dependency metadata. Use isolated locked environments or non-published dependency groups instead.
3. §5 step 6 import-lint as written would fail Core's existing `LangGraphExporter`, which lazily imports `langgraph` by design. The rule is: no *eager* or *required* import; intentional lazy outward bridges are allowlisted.
4. §5 step 3 "compare the ordered routing sequence" is insufficient: superstep execution needs partial-order comparison where the upstream contract permits concurrency.
5. §1 item 2 ("only test targets") is superseded for caller-installed bridges, per the later user direction recorded in the convergence plan; the default no-dependency rule stands.
