# The oramasys 5-Stage Methodology

Canonical sequence. Matches `references/oramasys-5-stages.md` exactly.

## Stage 1 — Context Immersion
Understand before acting. Gather context from the cheapest source first:
- `gbrain search`/`query` for semantic intent and past decisions
- CRG MCP tools for code structure and blast radius
- git log, existing docs, and constraints
Solve the *real* problem, not just the stated one.
Output: clear statement of the problem, constraints, and what already exists.

## Stage 2 — Visionary Architecture
Design the most elegant solution. Decompose into modules with clear boundaries.
- Run **CIDF `decide()`** before any content insertion (start at rank 1).
- Identify parallelizable work (informs Mode 2 vs Mode 3).
Output: modular design with rationale for each decision.

## Stage 3 — Ruthless Refinement
Eliminate everything non-essential. Elegance is when there is nothing left to
remove. Collapse duplication, delete dead paths, simplify interfaces.
Output: the minimal design that still satisfies all requirements.

## Stage 4 — Masterful Execution
- **Plan**: write `tasks/todo.md` for any 3+ step task.
- **Craft**: implement test-first (TDD).
- **Verify**: programmatically, never visually. Run the tests.
Output: working, tested code.

## Stage 5 — Crystallize Vision
- Assumptions ledger: what you assumed and why.
- Simplification story: what you removed and why it was safe.
- Inevitability argument: why this solution is the natural one.
- Capture lesson: append to LESSONS.md for self-improvement.
Output: documentation + a durable lesson.

---

## The 6 Operational Directives (always active)

| # | Directive | Trigger |
|---|---|---|
| 1 | Plan Node Default | any task with 3+ steps |
| 2 | Subagent Strategy | context window is crowded |
| 3 | Self-Improvement Loop | after ANY user correction |
| 4 | Verification Before Done | before marking any task complete |
| 5 | Demand Elegance | when a solution feels hacky |
| 6 | Autonomous Bug Fixing | on any bug report |

## Mode Selection (set by AFRP gate)

- **Mode 1** — inline, 1-2 steps, no subagents, CIDF inline.
- **Mode 2** — full 5-stage, 3-7 steps, optional subagents, CIDF at Stage 2.
- **Mode 3** — full 7-agent network via MCP, 8+ steps or parallel modules.
  Agents: orchestrator + context, architect, refiner, executor, verifier, crystallizer.
