---
name: hermes-delegate
description: >
  Spawn 2-5 parallel Hermes AIAgent workers for independent subtasks.
  Use when a task has genuinely parallel workstreams (e.g. research + coding
  + review simultaneously). Each worker gets its own isolated context.
argument-hint: "<task1> | <task2> | <task3>"
disable-model-invocation: true
---

# hermes-delegate (relocated)

**Canonical location:**
[`bin/orama-system/skills/hermes-harness/commands/hermes-delegate/SKILL.md`](../../../bin/orama-system/skills/hermes-harness/commands/hermes-delegate/SKILL.md)

This file is a thin stub kept at the repo-root `skills/` path
specifically because Claude Code's slash-command discovery scans
repo-root `skills/` for this frontmatter shape
(`argument-hint`/`disable-model-invocation`) -- moving the real
content away entirely would have broken direct slash-command
invocability. All actual content, instructions, and updates now live
at the canonical path above; edit there, not here.
