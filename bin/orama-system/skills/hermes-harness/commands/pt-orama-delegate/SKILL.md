---
name: pt-orama-delegate
description: >-
  Act as a bounded Hermes local specialist for PT-orama subtasks without
  committing or leaking private state.
version: 1.0.0
license: Apache 2.0
compatibility: hermes, codex, windows, lm-studio
parent_skill: hermes-harness
triggers:
  - pt-orama-delegate
  - hermes delegate
  - local specialist
allowed-tools: bash, file-operations
---

# PT-orama Delegate

Use this command when Hermes is asked to handle a narrow PT-orama subtask as a
local/private specialist.

## Boundaries

- Do not commit, delete, deploy, force-push, or change provider/account settings.
- Do not reveal or request secrets.
- Do not copy raw Hermes home state or personal memory into repos.
- Prefer canonical orama-system skills and docs over one-off procedures.

## Execution Contract

1. Restate the subtask and assumptions.
2. Identify the canonical source docs or skills needed.
3. If local LM Studio is requested, verify a fast chat-completions canary first.
4. If AGY is requested, save the installer first (never `irm | iex`):
   `Invoke-WebRequest -Uri https://antigravity.google/cli/install.ps1 -OutFile "$env:TEMP\agy-install.ps1"`;
   skim first 40 lines; then `& powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\agy-install.ps1"`.
   Require visible `AGY_READY` output before dispatch.
5. Return focused output only for the delegated subtask.

## Response Shape

```text
SUBTASK:
ASSUMPTIONS:
RESULT:
VERIFICATION:
RISKS:
NEXT HANDOFF:
```
