---
name: hermes-orama
description: >
  Run the complete Orama 5-stage pipeline (Context → Architect → Refiner →
  Executor/Verifier → Crystallizer) by spawning Hermes AIAgent instances for
  each stage. Use for any complex task that benefits from multi-agent breakdown.
argument-hint: "<task description>"
disable-model-invocation: true
---

# hermes-orama (relocated)

**Canonical location:**
[`bin/orama-system/skills/hermes-harness/commands/hermes-orama/SKILL.md`](../../../bin/orama-system/skills/hermes-harness/commands/hermes-orama/SKILL.md)

This file is a thin stub kept at the repo-root `skills/` path
specifically because Claude Code's slash-command discovery scans
repo-root `skills/` for this frontmatter shape
(`argument-hint`/`disable-model-invocation`) -- moving the real
content away entirely would have broken direct slash-command
invocability. All actual content, instructions, and updates now live
at the canonical path above; edit there, not here.
