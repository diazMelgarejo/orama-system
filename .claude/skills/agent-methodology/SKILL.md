---
name: agent-methodology
description: orama-system 5-stage problem-solving methodology. Claude-only background knowledge.
user-invocable: false
---

The orama-system methodology (ὅραμα = vision/revelation) — 5 stages. Canonical
source: `bin/orama-system/references/oramasys-5-stages.md` (this card is the
condensed, agent-facing summary; the reference doc is authoritative).

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
