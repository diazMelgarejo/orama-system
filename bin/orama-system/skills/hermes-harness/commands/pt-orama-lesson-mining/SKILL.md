---
name: pt-orama-lesson-mining
description: >-
  Graduate session findings into Perpetua-Tools semantic memory via learn.py.
  Thin Hermes command; canonical lesson pipeline lives in Perpetua-Tools.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, codex, windows
parent_skill: hermes-harness
triggers:
  - pt-orama-lesson-mining
  - lesson mining
  - graduate lesson
allowed-tools: bash, file-operations
---

# PT-orama Lesson Mining

Use when a Hermes or Codex session produced durable operational insight that
should graduate into Perpetua-Tools `.agent` memory.

## Canonical runtime

Perpetua-Tools owns the lesson pipeline:

- Tool: `.agent/tools/learn.py`
- Semantic sink: `.agent/memory/semantic/LESSONS.md`
- Working audits: `.agent/memory/working/`

Resolve `PERPETUA_TOOLS_ROOT` at runtime (sibling checkout or env). Never
hardcode workstation paths in envelopes or commits.

## Invocation envelope (L3/L2)

```json
{
  "skill_id": "pt-orama-lesson-mining",
  "args": {
    "summary": "One-line durable insight",
    "confidence": 8
  },
  "agent_id": "hermes",
  "executor_id": "codex",
  "harness": "hermes",
  "orama_system_root": "$ORAMA_SYSTEM_PATH",
  "transport": {
    "partner": "codex",
    "profile": "bounded"
  }
}
```

## Boundaries

- Do not commit secrets, raw `~/.hermes` exports, or personal memory blobs.
- Do not overwrite LESSONS.md without user-visible summary in the result envelope.
- Prefer `learn.py` graduation over hand-editing semantic files.

## Execution contract

1. Confirm insight is durable (saves 5+ minutes next time), not a one-off error.
2. Run or delegate `learn.py` with bounded args from `args`.
3. Return core result shape with `files_modified` relative to `PERPETUA_TOOLS_ROOT`.

## Response shape

Core trio required. Optional `output.summary` echoes the graduated lesson title.
