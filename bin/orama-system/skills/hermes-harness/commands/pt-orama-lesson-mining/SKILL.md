---
name: pt-orama-lesson-mining
description: >-
  Optional Hermes command for graduating durable session insights into semantic
  memory. Not required for harness operation; Perpetua-Tools is not a dependency.
version: 1.1.0.0
license: Apache 2.0
compatibility: hermes, codex, windows
parent_skill: hermes-harness
optional: true
status: optional-extension
triggers:
  - pt-orama-lesson-mining
  - lesson mining
  - graduate lesson
allowed-tools: bash, file-operations
---

# PT-orama Lesson Mining (optional)

**Optional extension.** Hermes harness authority, bootstrap, council, review, and
delegate flows do **not** require this command. orama-system has **no runtime
dependency** on Perpetua-Tools.

Use only when an operator explicitly wants to graduate a durable insight from a
session into a local semantic memory store they control.

## When to use

- Insight is reusable (saves 5+ minutes next time), not a one-off error.
- Operator has a memory graduation tool available (any harness-local `learn` CLI,
  MCP memory server, or manual LESSONS.md edit).
- User opted in via `--include-optional` on the thin-skill installer.

## Invocation envelope (L3/L2)

```json
{
  "skill_id": "pt-orama-lesson-mining",
  "args": {
    "summary": "One-line durable insight",
    "confidence": 8
  },
  "agent_id": "hermes",
  "executor_id": "hermes",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH"
}
```

## Boundaries

- Do not commit secrets or raw harness home exports.
- Do not assume any specific memory product, graduation CLI, or repo layout exists.
- If no graduation tool is configured, return `needs_input` with setup steps.

## Execution contract

1. Confirm the insight is durable and operator-approved.
2. If a local graduation tool is configured in `args.tool` or env, invoke it.
3. Otherwise return structured `output.summary` for manual paste into memory.
4. Populate core result shape (`status`, `files_modified`, `follow_up_actions`).

## Response shape

Core trio required. Optional `output.summary` echoes the graduated lesson title.
