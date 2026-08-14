---
name: agent-methodology
description: Use when planning or executing non-trivial multi-step work with the orama-system five-stage methodology.
user-invocable: false
version: "1.0.0"
compatibility: claude-code, codex, gemini, openclaw, hermes
allowed-tools: bash, file-operations, web-search
when_to_use: Use for non-trivial multi-step planning, architecture, refactoring, and contract-changing work.
triggers:
  - multi-step problem solving
  - architecture work
  - complex refactor
  - careful task planning
---

## Purpose

The orama-system methodology (ὅραμα = vision/revelation) — 5 stages. Canonical
source: `bin/orama-system/references/oramasys-5-stages.md` (this card is the
condensed, agent-facing summary; the reference doc is authoritative).

## When To Use

Use this card for non-trivial multi-step planning, architecture, refactoring,
and contract-changing work.

## When Not To Use

Do not use it for a direct factual answer or an isolated formatting edit.

**1. Context Immersion** — Ground yourself deeply in the problem space before
proposing anything. Read git history, docs, and code; understand the entire
landscape and the *real* problem, not just the stated one.

**2. Visionary Architecture** — Map the solution space. Identify the critical
path and choose the minimal approach that satisfies the crystallized constraints.

**3. Ruthless Refinement** — Eliminate inconsistency and complexity. Simplify the
design before building; a simpler approach discovered here loops back to Architecture.

**4. Masterful Execution** — Implement with precision, one task at a time. Verify
each step before the next; tests revealing flawed assumptions loop back to any stage.

**5. Crystallize Vision** — Independent check: would a fresh agent, given only the
original problem and this output, agree it is solved? Distill the result to its
irreducible, verified core.

The stages form a feedback loop, not a strict line — loop back whenever a later
stage reveals the earlier one was wrong. Apply to every non-trivial task; skip no
stages.

## Boundaries

### Always Do

- Ground non-trivial work in the five stages and verify each changed boundary.
- Use the contract-migration gate when a durable or transport contract moves.

### Ask First

- Expanding an assigned task into a cross-repository implementation or a destructive action.

### Never Do

- Treat a local passing caller as proof that a cross-module contract is complete.
- Skip the verification stage for a non-trivial change.

## Contract Migration Gate

For a change to durable state, a return contract, an event envelope, a transport
payload, or lifecycle behavior, map the full vertical slice before implementation:
persistence → contract → callers → transport → lifecycle → tests. The canonical
method and regression matrix are in
[`../oramasys-method/references/contract-migration.md`](../oramasys-method/references/contract-migration.md).

## Runbook And Glossary

Runbook: ground, design, simplify, execute, verify, then crystallize the
result. AFRP is the query/audience router; CIDF is the insertion guard.

## Related Skills

- [`../agent-coordination-heartbeat/SKILL.md`](../agent-coordination-heartbeat/SKILL.md) — Monitor agent liveness, detect dead agents, and auto-release stale claims.
- [`../gossip-bus/SKILL.md`](../gossip-bus/SKILL.md) — Multi-agent event bus: intra-host (SQLite FTS5) and inter-host LAN peer (WS/SSE + file-drop) transports.


## Post-Review Micro-Remediation

When addressing review findings (CodeRabbit or human) on an open PR: cluster
findings by root cause, fix once at the abstraction level, keep every commit
mechanically attributable to its failure class, and never accumulate revert
chains — reset to a safety-ref-protected ancestor instead when policy allows.

Full doctrine: `bin/orama-system/references/post-review-micro-remediation.md`
