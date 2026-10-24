---
description: Recommend the best model tier for the current task based on complexity, risk, and budget. When logic fails or verifiable criteria are missing, fall back to the harness default or an allowed alternative for the current task. Do not self-escalate.
---

# Model Route Command

Recommend the best model tier for the current task by complexity and budget.
Fallback logic follows
[Alexandria model-governance](https://github.com/oramasys/alexandria/blob/docs/mig-pack-ingest-20260925/docs/standards/model-governance.md)
(PR #1, tip `e7ee9db6`, status Proposed). Local pin: `docs/standards/model-governance.md`.
The fallback supplements this routing heuristic; it does not replace it.

## Usage

`/model-route [task-description] [--budget low|med|high]`

## Routing Heuristic

- `haiku` (`claude-haiku-5-5`): deterministic, low-risk mechanical changes
- `sonnet` (`claude-sonnet-5-5`): default for implementation and refactors
- `opus` (`claude-opus-5-5`): architecture, deep review, ambiguous requirements

## Fallback (when the heuristic cannot decide)

Use this when the heuristic fails, the task has no verifiable criteria, or the
recommended tier cannot run on the current harness:

- **Anthropic path** (Claude Code, Claude API/SDK, claude.ai): harness default
  `claude-sonnet-5-5` at medium effort.
- **Cursor / Grok Bot path:** harness default `grok-4.7` at medium effort with
  fast off; allowed alternatives `composer-2.5` or `gpt-5.6-terra` (medium) with
  fast off. `auto` is editor-only. `grok-4.5` and `grok-4.6` are outdated and
  never launched.
- Stay on the same path. Do not raise effort, turn on fast mode, or escalate to
  Opus or Fable on your own; report the gap instead.

## Required Output

- recommended model
- confidence level
- why this model fits
- fallback model if first attempt fails (harness default or an allowed
  alternative from the fallback section, never a self-escalation)

## Arguments

$ARGUMENTS:

- `[task-description]` optional free-text
- `--budget low|med|high` optional
