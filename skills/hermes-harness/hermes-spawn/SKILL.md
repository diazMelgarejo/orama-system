---
name: hermes-spawn
description: >
  Start, stop, or check a Hermes AIAgent session programmatically.
  Use when you need to spawn a Hermes agent for a task, check its status,
  or stop a running session. Requires credentials in the process environment;
  missing variables fail clearly (no automatic .env loading).
argument-hint: "<start|stop|status> [task description]"
disable-model-invocation: true
---

# hermes-spawn (relocated)

**Canonical location:**
[`bin/orama-system/skills/hermes-harness/commands/hermes-spawn/SKILL.md`](../../../bin/orama-system/skills/hermes-harness/commands/hermes-spawn/SKILL.md)

This file is a thin stub kept at the repo-root `skills/` path
specifically because Claude Code's slash-command discovery scans
repo-root `skills/` for this frontmatter shape
(`argument-hint`/`disable-model-invocation`) -- moving the real
content away entirely would have broken direct slash-command
invocability. All actual content, instructions, and updates now live
at the canonical path above; edit there, not here.
